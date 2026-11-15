"""Native Linux sysfs/hwmon/drm sensor provider (AMD, Intel, CPU temps without root)."""

from __future__ import annotations

from pathlib import Path
import sys

from src.sensors.base import GpuProvider
from src.sensors.models import GpuInfo, GpuSample


def _read_int(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _read_str(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def read_linux_cpu_temp(hwmon_root: Path = Path("/sys/class/hwmon")) -> tuple[float | None, str | None]:
    """Read CPU package/Tctl temperature from Linux /sys/class/hwmon."""
    if not hwmon_root.is_dir():
        return None, None

    preferred = ("k10temp", "zenpower", "coretemp", "cpu_thermal", "acpitz")
    candidates: list[tuple[int, str, Path]] = []
    for hw_dir in sorted(hwmon_root.iterdir()):
        name = _read_str(hw_dir / "name") or ""
        if name in preferred:
            candidates.append((preferred.index(name), name, hw_dir))

    candidates.sort(key=lambda item: item[0])
    for _, chip_name, hw_dir in candidates:
        for temp_input in sorted(hw_dir.glob("temp*_input")):
            val = _read_int(temp_input)
            if val is None or val <= 0:
                continue
            label_file = temp_input.with_name(temp_input.name.replace("_input", "_label"))
            label = (_read_str(label_file) or "").lower()
            if any(k in label for k in ("tctl", "tdie", "package", "cpu")) or not label:
                return round(val / 1000.0, 1), chip_name
    return None, None


class LinuxDrmGpuProvider(GpuProvider):
    """Reads AMD and Intel GPU metrics from Linux /sys/class/drm/card*/device."""

    _VENDOR_MAP = {
        "0x1002": "amd",
        "0x8086": "intel",
        "0x10de": "nvidia",
    }

    def __init__(self, drm_root: Path = Path("/sys/class/drm"), skip_nvidia: bool = True) -> None:
        self._drm_root = drm_root
        self._skip_nvidia = skip_nvidia
        self._cards: list[tuple[GpuInfo, Path]] = []
        if sys.platform.startswith("linux") or drm_root != Path("/sys/class/drm"):
            self._discover()

    def _discover(self) -> None:
        if not self._drm_root.is_dir():
            return
        idx = 0
        for card_dir in sorted(self._drm_root.glob("card[0-9]*")):
            if "-" in card_dir.name:
                continue
            device_dir = card_dir / "device"
            if not device_dir.is_dir():
                continue
            vendor_hex = (_read_str(device_dir / "vendor") or "").lower()
            vendor = self._VENDOR_MAP.get(vendor_hex, "unknown")
            if self._skip_nvidia and vendor == "nvidia":
                continue
            if vendor == "unknown":
                continue

            vram_total = _read_int(device_dir / "mem_info_vram_total")
            vram_total_mb = round(vram_total / (1024.0 * 1024.0), 0) if vram_total else None
            name = f"{vendor.upper()} GPU ({card_dir.name})"
            info = GpuInfo(
                index=idx,
                name=name,
                vendor=vendor,
                backend="sysfs",
                vram_total_mb=vram_total_mb,
            )
            self._cards.append((info, device_dir))
            idx += 1

    def is_available(self) -> bool:
        return len(self._cards) > 0

    def list_gpus(self) -> list[GpuInfo]:
        return [info for info, _ in self._cards]

    def read_gpu(self, local_index: int) -> GpuSample | None:
        if local_index < 0 or local_index >= len(self._cards):
            return None
        info, dev = self._cards[local_index]

        util_raw = _read_int(dev / "gpu_busy_percent")
        util_percent = float(util_raw) if util_raw is not None else None

        vram_used_raw = _read_int(dev / "mem_info_vram_used")
        vram_used_mb = round(vram_used_raw / (1024.0 * 1024.0), 0) if vram_used_raw is not None else None

        temp_c: float | None = None
        fan_rpm: int | None = None
        power_watts: float | None = None
        power_limit_watts: float | None = None
        clock_mhz: int | None = None
        mem_clock_mhz: int | None = None

        hwmon_base = dev / "hwmon"
        if hwmon_base.is_dir():
            for hw_dir in sorted(hwmon_base.iterdir()):
                t_raw = _read_int(hw_dir / "temp1_input")
                if t_raw is not None and temp_c is None:
                    temp_c = round(t_raw / 1000.0, 1)
                f_raw = _read_int(hw_dir / "fan1_input")
                if f_raw is not None and fan_rpm is None:
                    fan_rpm = f_raw
                p_raw = _read_int(hw_dir / "power1_average") or _read_int(hw_dir / "power1_input")
                if p_raw is not None and power_watts is None:
                    power_watts = round(p_raw / 1_000_000.0, 1)
                pcap_raw = _read_int(hw_dir / "power1_cap") or _read_int(hw_dir / "power1_cap_default")
                if pcap_raw is not None and pcap_raw > 0 and power_limit_watts is None:
                    power_limit_watts = round(pcap_raw / 1_000_000.0, 1)
                freq_raw = _read_int(hw_dir / "freq1_input")
                if freq_raw is not None and clock_mhz is None:
                    clock_mhz = int(round(freq_raw / 1_000_000.0))
                mclk_raw = _read_int(hw_dir / "freq2_input")
                if mclk_raw is not None and mem_clock_mhz is None:
                    mem_clock_mhz = int(round(mclk_raw / 1_000_000.0))

        return GpuSample(
            index=local_index,
            name=info.name,
            vendor=info.vendor,
            available=True,
            util_percent=util_percent,
            clock_mhz=clock_mhz,
            mem_clock_mhz=mem_clock_mhz,
            temp_c=temp_c,
            fan_rpm=fan_rpm,
            vram_used_mb=vram_used_mb,
            vram_total_mb=info.vram_total_mb,
            power_watts=power_watts,
            power_limit_watts=power_limit_watts,
        )

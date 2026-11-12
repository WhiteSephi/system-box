"""Cross-platform baseline system provider using psutil (no admin required)."""

from __future__ import annotations

import time

import psutil

from src.sensors.base import SystemProvider
from src.sensors.models import CpuSystemSample


class PsutilSystemProvider(SystemProvider):
    """Reads CPU, per-core peak, clock, RAM, Disk I/O, and uptime via psutil."""

    def __init__(self) -> None:
        self._last_disk_io = self._safe_disk_io()
        self._last_disk_ts = time.monotonic()
        # Prime psutil cpu_percent so the first real poll returns a meaningful delta
        try:
            psutil.cpu_percent(interval=None, percpu=True)
        except Exception:
            pass

    @staticmethod
    def _safe_disk_io():
        try:
            return psutil.disk_io_counters()
        except Exception:
            return None

    @staticmethod
    def _read_linux_psutil_temp() -> tuple[float | None, str | None]:
        sensors_fn = getattr(psutil, "sensors_temperatures", None)
        if sensors_fn is None:
            return None, None
        try:
            temps = sensors_fn(fahrenheit=False)
        except Exception:
            return None, None
        if not temps:
            return None, None

        # Prefer well-known CPU sensor labels
        preferred_chips = ("k10temp", "zenpower", "coretemp", "cpu_thermal", "acpitz")
        for chip in preferred_chips:
            entries = temps.get(chip)
            if not entries:
                continue
            for entry in entries:
                label = (entry.label or "").lower()
                if any(k in label for k in ("tctl", "tdie", "package", "cpu")):
                    if entry.current and entry.current > 0:
                        return float(entry.current), chip
            for entry in entries:
                if entry.current and entry.current > 0:
                    return float(entry.current), chip
        return None, None

    def read_system(self) -> CpuSystemSample:
        """Collect current CPU, RAM, Disk I/O, and uptime metrics."""
        per_core: list[float] = []
        try:
            per_core = psutil.cpu_percent(interval=None, percpu=True)
        except Exception:
            per_core = []

        if per_core:
            cpu_percent = sum(per_core) / len(per_core)
            cpu_max_core = max(per_core)
        else:
            try:
                cpu_percent = float(psutil.cpu_percent(interval=None))
            except Exception:
                cpu_percent = 0.0
            cpu_max_core = cpu_percent

        cpu_freq_mhz: float | None = None
        try:
            freq = psutil.cpu_freq()
            if freq and freq.current > 0:
                cpu_freq_mhz = float(freq.current)
        except Exception:
            cpu_freq_mhz = None

        ram_used_gb = 0.0
        ram_total_gb = 0.0
        ram_percent = 0.0
        try:
            vm = psutil.virtual_memory()
            ram_used_gb = vm.used / (1024.0 ** 3)
            ram_total_gb = vm.total / (1024.0 ** 3)
            ram_percent = float(vm.percent)
        except Exception:
            pass

        disk_read_mb_s = 0.0
        disk_write_mb_s = 0.0
        now = time.monotonic()
        cur_io = self._safe_disk_io()
        if cur_io is not None and self._last_disk_io is not None:
            dt = max(0.05, now - self._last_disk_ts)
            read_bytes = max(0, cur_io.read_bytes - self._last_disk_io.read_bytes)
            write_bytes = max(0, cur_io.write_bytes - self._last_disk_io.write_bytes)
            disk_read_mb_s = (read_bytes / dt) / (1024.0 * 1024.0)
            disk_write_mb_s = (write_bytes / dt) / (1024.0 * 1024.0)
        self._last_disk_io = cur_io
        self._last_disk_ts = now

        uptime_seconds = 0
        try:
            uptime_seconds = max(0, int(time.time() - psutil.boot_time()))
        except Exception:
            uptime_seconds = 0

        cpu_temp_c, temp_source = self._read_linux_psutil_temp()

        return CpuSystemSample(
            cpu_percent=round(cpu_percent, 1),
            cpu_max_core_percent=round(cpu_max_core, 1),
            cpu_freq_mhz=round(cpu_freq_mhz, 0) if cpu_freq_mhz is not None else None,
            cpu_temp_c=round(cpu_temp_c, 1) if cpu_temp_c is not None else None,
            temp_source=temp_source,
            ram_used_gb=round(ram_used_gb, 2),
            ram_total_gb=round(ram_total_gb, 2),
            ram_percent=round(ram_percent, 1),
            disk_read_mb_s=round(disk_read_mb_s, 1),
            disk_write_mb_s=round(disk_write_mb_s, 1),
            uptime_seconds=uptime_seconds,
        )

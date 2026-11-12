"""Tests for SensorManager, Linux sysfs/hwmon parsing, and graceful fallbacks."""

from __future__ import annotations

from pathlib import Path

from src.sensors.base import GpuProvider, SystemProvider
from src.sensors.linux_hwmon import LinuxDrmGpuProvider, read_linux_cpu_temp
from src.sensors.manager import SensorManager
from src.sensors.models import CpuSystemSample, GpuInfo, GpuSample


class _FakeSystemProvider(SystemProvider):
    def read_system(self) -> CpuSystemSample:
        return CpuSystemSample(cpu_percent=12.5, cpu_max_core_percent=42.0, ram_used_gb=8.0, ram_total_gb=32.0, ram_percent=25.0)


class _BrokenSystemProvider(SystemProvider):
    def read_system(self) -> CpuSystemSample:
        raise RuntimeError("sensor read failed")


class _FakeGpuProvider(GpuProvider):
    def __init__(self, gpus: list[GpuInfo], fail_read: bool = False) -> None:
        self._gpus = gpus
        self._fail_read = fail_read

    def is_available(self) -> bool:
        return len(self._gpus) > 0

    def list_gpus(self) -> list[GpuInfo]:
        return list(self._gpus)

    def read_gpu(self, local_index: int) -> GpuSample | None:
        if self._fail_read:
            raise OSError("gpu read failed")
        info = self._gpus[local_index]
        return GpuSample(index=local_index, name=info.name, vendor=info.vendor, available=True, util_percent=55.0)


def test_sensor_manager_multi_gpu_selection() -> None:
    p1 = _FakeGpuProvider([GpuInfo(index=0, name="Generic Test GPU A", vendor="nvidia", backend="nvml")])
    p2 = _FakeGpuProvider([GpuInfo(index=0, name="Generic Test GPU B", vendor="amd", backend="sysfs")])
    mgr = SensorManager(system_provider=_FakeSystemProvider(), gpu_providers=[p1, p2])

    assert len(mgr.list_gpus()) == 2
    snap0 = mgr.poll(selected_gpu_index=0)
    assert snap0.active_gpu.name == "Generic Test GPU A"
    snap1 = mgr.poll(selected_gpu_index=1)
    assert snap1.active_gpu.name == "Generic Test GPU B"
    assert snap1.active_gpu.index == 1


def test_sensor_manager_graceful_on_errors() -> None:
    p1 = _FakeGpuProvider([GpuInfo(index=0, name="Generic Test GPU A", vendor="amd", backend="sysfs")], fail_read=True)
    mgr = SensorManager(system_provider=_BrokenSystemProvider(), gpu_providers=[p1])
    snap = mgr.poll(selected_gpu_index=0)
    assert snap.cpu.cpu_percent == 0.0
    assert snap.active_gpu.available is False


def test_linux_sysfs_drm_and_hwmon(tmp_path: Path) -> None:
    drm = tmp_path / "drm"
    dev = drm / "card0" / "device"
    hw = dev / "hwmon" / "hwmon0"
    hw.mkdir(parents=True)
    (dev / "vendor").write_text("0x1002\n", encoding="utf-8")
    (dev / "gpu_busy_percent").write_text("42\n", encoding="utf-8")
    (dev / "mem_info_vram_total").write_text(str(8192 * 1024 * 1024), encoding="utf-8")
    (dev / "mem_info_vram_used").write_text(str(2048 * 1024 * 1024), encoding="utf-8")
    (hw / "temp1_input").write_text("61000\n", encoding="utf-8")
    (hw / "fan1_input").write_text("1500\n", encoding="utf-8")

    provider = LinuxDrmGpuProvider(drm_root=drm, skip_nvidia=True)
    assert provider.is_available()
    sample = provider.read_gpu(0)
    assert sample is not None
    assert sample.util_percent == 42.0
    assert sample.temp_c == 61.0
    assert sample.fan_rpm == 1500
    assert sample.vram_used_mb == 2048.0
    assert sample.vram_total_mb == 8192.0

    hw_root = tmp_path / "hwmon"
    k10 = hw_root / "hwmon1"
    k10.mkdir(parents=True)
    (k10 / "name").write_text("k10temp\n", encoding="utf-8")
    (k10 / "temp1_label").write_text("Tctl\n", encoding="utf-8")
    (k10 / "temp1_input").write_text("54500\n", encoding="utf-8")
    temp, src = read_linux_cpu_temp(hw_root)
    assert temp == 54.5
    assert src == "k10temp"

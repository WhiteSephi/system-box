"""Data models for hardware telemetry samples."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class GpuInfo:
    """Static descriptor for a detected GPU."""

    index: int
    name: str
    vendor: str = "unknown"  # "nvidia", "amd", "intel", "unknown"
    backend: str = "none"  # "nvml", "sysfs", "pdh", "none"
    vram_total_mb: float | None = None
    driver_version: str | None = None


@dataclass(slots=True)
class GpuSample:
    """Real-time GPU telemetry sample."""

    index: int = 0
    name: str = "Keine GPU erkannt"
    vendor: str = "unknown"
    available: bool = False
    util_percent: float | None = None
    clock_mhz: int | None = None
    mem_clock_mhz: int | None = None
    temp_c: float | None = None
    hotspot_temp_c: float | None = None
    fan_rpm: int | None = None
    fan_percent: int | None = None
    vram_used_mb: float | None = None
    vram_total_mb: float | None = None
    power_watts: float | None = None
    power_limit_watts: float | None = None
    driver_version: str | None = None
    throttle_reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CpuSystemSample:
    """Real-time CPU, memory, disk and uptime telemetry sample."""

    cpu_percent: float = 0.0
    cpu_max_core_percent: float = 0.0
    cpu_freq_mhz: float | None = None
    cpu_temp_c: float | None = None
    temp_source: str | None = None
    ram_used_gb: float = 0.0
    ram_total_gb: float = 0.0
    ram_percent: float = 0.0
    swap_used_gb: float = 0.0
    swap_total_gb: float = 0.0
    swap_percent: float = 0.0
    page_faults_per_sec: float | None = None
    disk_read_mb_s: float = 0.0
    disk_write_mb_s: float = 0.0
    uptime_seconds: int = 0


@dataclass(slots=True)
class SystemSnapshot:
    """Combined snapshot produced on each polling tick."""

    cpu: CpuSystemSample = field(default_factory=CpuSystemSample)
    gpus: list[GpuInfo] = field(default_factory=list)
    active_gpu: GpuSample = field(default_factory=GpuSample)

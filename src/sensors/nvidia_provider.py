"""NVIDIA GPU sensor provider via NVML (pynvml / nvidia-ml-py), no admin required."""

from __future__ import annotations

from src.sensors.base import GpuProvider
from src.sensors.models import GpuInfo, GpuSample

try:
    import pynvml  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - optional runtime dependency
    pynvml = None


class NvidiaGpuProvider(GpuProvider):
    """Queries NVIDIA GPUs through NVML on Windows and Linux."""

    def __init__(self) -> None:
        self._initialized = False
        self._gpus: list[GpuInfo] = []
        self._init_nvml()

    def _init_nvml(self) -> None:
        if pynvml is None:
            return
        try:
            pynvml.nvmlInit()
            self._initialized = True
            count = int(pynvml.nvmlDeviceGetCount())
            for idx in range(count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(idx)
                raw_name = pynvml.nvmlDeviceGetName(handle)
                name = raw_name.decode("utf-8", errors="replace") if isinstance(raw_name, bytes) else str(raw_name)
                vram_total_mb: float | None = None
                try:
                    mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    vram_total_mb = round(mem.total / (1024.0 * 1024.0), 0)
                except Exception:
                    pass
                self._gpus.append(
                    GpuInfo(
                        index=idx,
                        name=name,
                        vendor="nvidia",
                        backend="nvml",
                        vram_total_mb=vram_total_mb,
                    )
                )
        except Exception:
            self._initialized = False
            self._gpus = []

    def is_available(self) -> bool:
        return self._initialized and len(self._gpus) > 0

    def list_gpus(self) -> list[GpuInfo]:
        return list(self._gpus)

    @staticmethod
    def _decode_throttle_reasons(mask: int) -> list[str]:
        if pynvml is None or mask == 0:
            return []
        reasons: list[str] = []
        checks = (
            ("nvmlClocksThrottleReasonHwThermalSlowdown", "Thermal"),
            ("nvmlClocksThrottleReasonSwThermalSlowdown", "Thermal"),
            ("nvmlClocksThrottleReasonSwPowerCap", "PowerCap"),
            ("nvmlClocksThrottleReasonHwSlowdown", "HW-Slowdown"),
            ("nvmlClocksEventReasonHwThermalSlowdown", "Thermal"),
            ("nvmlClocksEventReasonSwPowerCap", "PowerCap"),
        )
        for attr, label in checks:
            flag = getattr(pynvml, attr, 0)
            if flag and (mask & flag) and label not in reasons:
                reasons.append(label)
        return reasons

    def read_gpu(self, local_index: int) -> GpuSample | None:
        if not self.is_available() or local_index < 0 or local_index >= len(self._gpus):
            return None
        info = self._gpus[local_index]
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(local_index)
        except Exception:
            return None

        util_percent: float | None = None
        try:
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            util_percent = float(util.gpu)
        except Exception:
            pass

        clock_mhz: int | None = None
        try:
            clock_mhz = int(pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_GRAPHICS))
        except Exception:
            pass

        mem_clock_mhz: int | None = None
        try:
            mem_clock_mhz = int(pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_MEM))
        except Exception:
            pass

        temp_c: float | None = None
        try:
            temp_c = float(pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU))
        except Exception:
            pass

        fan_percent: int | None = None
        try:
            fan_percent = int(pynvml.nvmlDeviceGetFanSpeed(handle))
        except Exception:
            pass

        fan_rpm: int | None = None
        rpm_fn = getattr(pynvml, "nvmlDeviceGetFanSpeedRPM", None)
        if rpm_fn is not None:
            try:
                fan_rpm = int(rpm_fn(handle))
            except Exception:
                pass

        vram_used_mb: float | None = None
        vram_total_mb = info.vram_total_mb
        try:
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            vram_used_mb = round(mem.used / (1024.0 * 1024.0), 0)
            vram_total_mb = round(mem.total / (1024.0 * 1024.0), 0)
        except Exception:
            pass

        power_watts: float | None = None
        try:
            power_mw = pynvml.nvmlDeviceGetPowerUsage(handle)
            power_watts = round(power_mw / 1000.0, 1)
        except Exception:
            pass

        power_limit_watts: float | None = None
        try:
            limit_mw = pynvml.nvmlDeviceGetEnforcedPowerLimit(handle)
            power_limit_watts = round(limit_mw / 1000.0, 0)
        except Exception:
            pass

        throttle_reasons: list[str] = []
        try:
            mask = int(pynvml.nvmlDeviceGetCurrentClocksThrottleReasons(handle))
            throttle_reasons = self._decode_throttle_reasons(mask)
        except Exception:
            pass

        return GpuSample(
            index=local_index,
            name=info.name,
            vendor="nvidia",
            available=True,
            util_percent=util_percent,
            clock_mhz=clock_mhz,
            mem_clock_mhz=mem_clock_mhz,
            temp_c=temp_c,
            fan_rpm=fan_rpm,
            fan_percent=fan_percent,
            vram_used_mb=vram_used_mb,
            vram_total_mb=vram_total_mb,
            power_watts=power_watts,
            power_limit_watts=power_limit_watts,
            throttle_reasons=throttle_reasons,
        )

    def close(self) -> None:
        if self._initialized and pynvml is not None:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass
            self._initialized = False

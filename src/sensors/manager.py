"""Unified SensorManager coordinating platform-specific GPU and CPU/System providers."""

from __future__ import annotations

import sys
import time

from src.sensors.base import GpuProvider, SystemProvider
from src.sensors.disk_space import read_disk_spaces
from src.sensors.linux_hwmon import LinuxDrmGpuProvider, read_linux_cpu_temp
from src.sensors.models import CpuSystemSample, DiskSpaceInfo, GpuInfo, GpuSample, SystemSnapshot
from src.sensors.nvidia_provider import NvidiaGpuProvider
from src.sensors.psutil_provider import PsutilSystemProvider
from src.sensors.windows_fallback import WindowsPdhGpuProvider, read_hwinfo_cpu_temp


class SensorManager:
    """Discovers available hardware providers and produces safe SystemSnapshots."""

    def __init__(
        self,
        system_provider: SystemProvider | None = None,
        gpu_providers: list[GpuProvider] | None = None,
    ) -> None:
        self._system_provider = system_provider or PsutilSystemProvider()
        self._gpu_entries: list[tuple[GpuInfo, GpuProvider, int]] = []
        self._cached_disks: list[DiskSpaceInfo] = []
        self._last_disk_space_ts: float = 0.0
        self._last_disk_space_opts: tuple[bool, bool] | None = None

        if gpu_providers is not None:
            providers = gpu_providers
        else:
            providers = self._create_default_gpu_providers()

        self._gpu_providers = providers
        self._rebuild_gpu_index()

    @staticmethod
    def _create_default_gpu_providers() -> list[GpuProvider]:
        providers: list[GpuProvider] = []
        nv = NvidiaGpuProvider()
        has_nvidia = nv.is_available()
        if has_nvidia:
            providers.append(nv)

        if sys.platform.startswith("linux"):
            drm = LinuxDrmGpuProvider(skip_nvidia=has_nvidia)
            if drm.is_available():
                providers.append(drm)
        elif sys.platform == "win32" and not has_nvidia:
            pdh = WindowsPdhGpuProvider(skip_nvidia=False)
            if pdh.is_available():
                providers.append(pdh)

        return providers

    def _rebuild_gpu_index(self) -> None:
        self._gpu_entries.clear()
        global_idx = 0
        for provider in self._gpu_providers:
            try:
                if not provider.is_available():
                    continue
                for local_idx, info in enumerate(provider.list_gpus()):
                    indexed_info = GpuInfo(
                        index=global_idx,
                        name=info.name,
                        vendor=info.vendor,
                        backend=info.backend,
                        vram_total_mb=info.vram_total_mb,
                    )
                    self._gpu_entries.append((indexed_info, provider, local_idx))
                    global_idx += 1
            except Exception:
                continue

    def list_gpus(self) -> list[GpuInfo]:
        """Return all discovered GPUs with global indices."""
        return [info for info, _, _ in self._gpu_entries]

    def list_disks(self) -> list[str]:
        """Return all discovered physical disk devices."""
        try:
            return self._system_provider.list_disks()
        except Exception:
            return []

    def list_disk_choices(self) -> list[tuple[str, str]]:
        """Return (device_key, display_label) pairs for physical disk selection."""
        try:
            return self._system_provider.list_disk_choices()
        except Exception:
            return []

    def poll(
        self,
        selected_gpu_index: int = 0,
        disk_device: str = "",
        storage_deduplicate: bool = True,
        storage_show_boot: bool = False,
    ) -> SystemSnapshot:
        """Collect CPU/system and selected GPU metrics without raising on missing sensors."""
        try:
            cpu_sample = self._system_provider.read_system(disk_device=disk_device)
        except Exception:
            cpu_sample = CpuSystemSample()

        # Enrich CPU temperature if baseline provider had none
        if cpu_sample.cpu_temp_c is None:
            if sys.platform.startswith("linux"):
                temp, src = read_linux_cpu_temp()
                if temp is not None:
                    cpu_sample.cpu_temp_c = temp
                    cpu_sample.temp_source = src
            elif sys.platform == "win32":
                temp, src = read_hwinfo_cpu_temp()
                if temp is not None:
                    cpu_sample.cpu_temp_c = temp
                    cpu_sample.temp_source = src

        gpu_list = self.list_gpus()
        active_gpu = GpuSample(available=False)
        if gpu_list:
            clamped_idx = max(0, min(selected_gpu_index, len(self._gpu_entries) - 1))
            info, provider, local_idx = self._gpu_entries[clamped_idx]
            try:
                sample = provider.read_gpu(local_idx)
                if sample is not None:
                    sample.index = info.index
                    active_gpu = sample
            except Exception:
                active_gpu = GpuSample(index=info.index, name=info.name, vendor=info.vendor, available=False)

        now = time.monotonic()
        opts = (storage_deduplicate, storage_show_boot)
        if self._last_disk_space_opts != opts or (now - self._last_disk_space_ts) >= 5.0:
            try:
                self._cached_disks = read_disk_spaces(
                    deduplicate_devices=storage_deduplicate,
                    show_boot=storage_show_boot,
                )
            except Exception:
                self._cached_disks = []
            self._last_disk_space_ts = now
            self._last_disk_space_opts = opts

        return SystemSnapshot(cpu=cpu_sample, gpus=gpu_list, active_gpu=active_gpu, disks=list(self._cached_disks))

    def close(self) -> None:
        """Close all underlying providers."""
        try:
            self._system_provider.close()
        except Exception:
            pass
        for provider in self._gpu_providers:
            try:
                provider.close()
            except Exception:
                pass

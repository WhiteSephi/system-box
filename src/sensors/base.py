"""Abstract base interfaces for sensor providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.sensors.models import CpuSystemSample, GpuInfo, GpuSample


class GpuProvider(ABC):
    """Abstract provider for GPU discovery and real-time metrics."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this provider can query at least one GPU on this system."""

    @abstractmethod
    def list_gpus(self) -> list[GpuInfo]:
        """Return all GPUs managed by this provider."""

    @abstractmethod
    def read_gpu(self, local_index: int) -> GpuSample | None:
        """Read a live telemetry sample for the given provider-local GPU index."""

    def close(self) -> None:
        """Release any native handles."""


class SystemProvider(ABC):
    """Abstract provider for CPU, memory, disk, and temperature metrics."""

    def list_disks(self) -> list[str]:
        """Return available physical disk device names for per-disk I/O monitoring."""
        return []

    @abstractmethod
    def read_system(self, disk_device: str = "") -> CpuSystemSample:
        """Read a live CPU/system telemetry sample."""

    def close(self) -> None:
        """Release any native handles."""

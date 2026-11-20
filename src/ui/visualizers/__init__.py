"""Modular alternative telemetry visualizers for CpuSystemWidget."""

from src.ui.visualizers.cpu_viz import CoreBarsWidget, CoreHeatmapWidget
from src.ui.visualizers.io_viz import DualIoMeterWidget, ImpulseBarsWidget, MirrorGraphWidget, PageMatrixWidget
from src.ui.visualizers.memory_viz import RamGridBoxWidget, RamSegmentedBarWidget

__all__ = [
    "CoreBarsWidget",
    "CoreHeatmapWidget",
    "RamGridBoxWidget",
    "RamSegmentedBarWidget",
    "ImpulseBarsWidget",
    "PageMatrixWidget",
    "DualIoMeterWidget",
    "MirrorGraphWidget",
]

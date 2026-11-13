"""Tests for SystemBox widgets, compact mode, HiDPI scaling and snapshot updates."""

from __future__ import annotations

import os

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

from src.config import AppConfig
from src.sensors.models import CpuSystemSample, GpuSample, SystemSnapshot
from src.ui.clock_widget import ClockWidget, format_uptime
from src.ui.cpu_widget import CpuSystemWidget
from src.ui.gpu_widget import GpuWidget
from src.ui.graph_canvas import MiniLiveGraphWidget


def _ensure_qapp() -> QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app  # type: ignore[return-value]


def test_format_uptime() -> None:
    assert format_uptime(45) == "0m"
    assert format_uptime(3660) == "1h 01m"
    assert format_uptime(90060) == "1d 1h 01m"


def test_widgets_update_scaling_and_compact_mode() -> None:
    _ensure_qapp()
    cfg = AppConfig()
    cfg.ui_scale_percent = 250

    snap = SystemSnapshot(
        cpu=CpuSystemSample(
            cpu_percent=18.2,
            cpu_max_core_percent=64.0,
            cpu_freq_mhz=4500.0,
            cpu_temp_c=None,
            ram_used_gb=12.4,
            ram_total_gb=32.0,
            ram_percent=38.8,
            disk_read_mb_s=12.3,
            disk_write_mb_s=4.5,
            uptime_seconds=7200,
        ),
        active_gpu=GpuSample(
            index=0,
            name="Generic Test GPU",
            vendor="nvidia",
            available=True,
            util_percent=73.0,
            clock_mhz=2100,
            temp_c=64.0,
            fan_rpm=1450,
            fan_percent=48,
            vram_used_mb=6144.0,
            vram_total_mb=16384.0,
            power_watts=195.0,
            power_limit_watts=300.0,
            throttle_reasons=["PowerCap"],
        ),
    )

    clock = ClockWidget(cfg)
    gpu = GpuWidget(cfg)
    cpu = CpuSystemWidget(cfg)

    for w in (clock, gpu, cpu):
        w.update_snapshot(snap)
        w.apply_config()

    assert "Generic Test GPU" in gpu.lbl_title.text()
    assert gpu.lbl_throttle.isVisibleTo(gpu)
    assert not cpu.lbl_temp_pill.isVisibleTo(cpu)

    clock.close()
    gpu.close()
    cpu.close()


def test_widget_edge_snapping() -> None:
    app = _ensure_qapp()
    cfg = AppConfig()
    clock = ClockWidget(cfg)
    screen = app.primaryScreen()
    if screen is not None:
        avail = screen.availableGeometry()
        snapped = clock._snap_position(QPoint(avail.x() + 8, avail.y() + 10), snap_dist=14)
        assert snapped.x() == avail.x()
        assert snapped.y() == avail.y()
    clock.close()


def test_graph_dynamic_min_ceiling() -> None:
    _ensure_qapp()
    graph = MiniLiveGraphWidget(history_len=15, max_value=128.0, dynamic_scale=True, min_ceiling=128.0)
    assert graph.current_ceiling() == 128.0

    graph.push_value(500.0)
    assert graph.current_ceiling() == 600.0

    # Subsequent zero samples must keep the peak ceiling until the spike scrolls out
    for _ in range(14):
        graph.push_value(0.0)
    assert graph.current_ceiling() == 600.0

    # One more zero pushes the spike out of the 15-sample window
    graph.push_value(0.0)
    assert graph.current_ceiling() == 128.0
    graph.close()

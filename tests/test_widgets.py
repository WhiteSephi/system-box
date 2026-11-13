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


def test_widget_extreme_sizes_no_overlap_or_clipping() -> None:
    app = _ensure_qapp()
    cfg = AppConfig()
    snap = SystemSnapshot(
        cpu=CpuSystemSample(
            cpu_percent=42.5,
            cpu_max_core_percent=88.0,
            cpu_freq_mhz=4800.0,
            cpu_temp_c=61.0,
            ram_used_gb=14.2,
            ram_total_gb=32.0,
            ram_percent=44.4,
            page_faults_per_sec=250.0,
            disk_read_mb_s=15.4,
            disk_write_mb_s=8.2,
            uptime_seconds=3600,
        ),
        active_gpu=GpuSample(
            index=0,
            name="Generic Test GPU",
            vendor="nvidia",
            available=True,
            util_percent=65.0,
            clock_mhz=2100,
            temp_c=58.0,
            fan_rpm=1450,
            fan_percent=48,
            vram_used_mb=6144.0,
            vram_total_mb=16384.0,
            power_watts=195.0,
            power_limit_watts=300.0,
        ),
    )

    gpu = GpuWidget(cfg)
    cpu = CpuSystemWidget(cfg)
    clock = ClockWidget(cfg)

    for w in (gpu, cpu, clock):
        w.show()
        w.update_snapshot(snap)
        # Test extra-small (minimumSize) and extra-large sizes
        for target_size in (w.minimumSize(), w.minimumSize() * 2):
            w.resize(target_size)
            app.processEvents()
            for lbl in w.findChildren(type(gpu.lbl_title)):
                if not lbl.isVisibleTo(w) or not lbl.text():
                    continue
                pos = lbl.mapTo(w, QPoint(0, 0))
                assert pos.x() >= 0 and pos.y() >= 0
                assert pos.x() + lbl.width() <= w.width() + 1
                assert pos.y() + lbl.height() <= w.height() + 1

    # Verify GPU Row 2: no text clipping & no overlap at minimum size, full details at large size
    gpu.resize(gpu.minimumSize())
    app.processEvents()
    assert not gpu.lbl_power_max.isVisibleTo(gpu)
    for lbl in (gpu.lbl_temp, gpu.lbl_power):
        assert lbl.fontMetrics().horizontalAdvance(lbl.text()) <= lbl.width() + 1

    gpu.resize(640, 360)
    app.processEvents()
    assert gpu.lbl_power_max.isVisibleTo(gpu)
    assert "(48%)" in gpu.lbl_fan_pwr.text()
    assert gpu._temp_box.geometry().right() < gpu._fan_box.geometry().left()
    assert gpu._fan_box.geometry().right() < gpu._pwr_box.geometry().left()

    gpu.close()
    cpu.close()
    clock.close()


def test_gpu_temp_warning_badge() -> None:
    app = _ensure_qapp()
    cfg = AppConfig()
    cfg.gpu_temp_warn_c = 80
    gpu = GpuWidget(cfg)
    gpu.show()

    cool_snap = SystemSnapshot(
        cpu=CpuSystemSample(0, 0, 0, None, 0, 0, 0, 0, 0, 0, 0),
        active_gpu=GpuSample(
            index=0, name="Generic Test GPU", vendor="nvidia", available=True,
            util_percent=30.0, clock_mhz=1800, temp_c=72.0,
        ),
    )
    gpu.update_snapshot(cool_snap)
    app.processEvents()
    assert not gpu.lbl_throttle.isVisibleTo(gpu)

    hot_snap = SystemSnapshot(
        cpu=CpuSystemSample(0, 0, 0, None, 0, 0, 0, 0, 0, 0, 0),
        active_gpu=GpuSample(
            index=0, name="Generic Test GPU", vendor="nvidia", available=True,
            util_percent=99.0, clock_mhz=2500, temp_c=84.0,
        ),
    )
    gpu.update_snapshot(hot_snap)
    app.processEvents()
    assert gpu.lbl_throttle.isVisibleTo(gpu)
    assert "TEMP 84°C" in gpu.lbl_throttle.text()
    gpu.close()

"""Tests for SystemBox widgets, compact mode, HiDPI scaling and snapshot updates."""

from __future__ import annotations

import os

from PySide6.QtWidgets import QApplication

from src.config import AppConfig
from src.sensors.models import CpuSystemSample, GpuSample, SystemSnapshot
from src.ui.clock_widget import ClockWidget, format_uptime
from src.ui.cpu_widget import CpuSystemWidget
from src.ui.gpu_widget import GpuWidget


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

    # Toggle compact mode
    cfg.get_widget("gpu").compact_mode = True
    cfg.get_widget("cpu").compact_mode = True
    gpu.apply_config()
    cpu.apply_config()
    assert gpu.lbl_compact.isVisibleTo(gpu)
    assert cpu.lbl_compact.isVisibleTo(cpu)

    clock.close()
    gpu.close()
    cpu.close()

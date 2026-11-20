from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QMessageBox

from src.config import AppConfig
from src.sensors.models import CpuSystemSample, SystemSnapshot
from src.ui.cpu_widget import CpuSystemWidget
from src.ui.settings_dlg import SettingsDialog
from src.ui.visualizers.memory_viz import power_of_two_grid


def _ensure_qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_config_viz_modes_roundtrip_and_whitelist(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.json"
    cfg = AppConfig()
    assert cfg.cpu_viz_mode == "graph"
    assert cfg.ram_viz_mode == "graph"
    assert cfg.pf_viz_mode == "graph"
    assert cfg.disk_viz_mode == "graph"

    cfg.cpu_viz_mode = "core_bars"
    cfg.ram_viz_mode = "grid_blocks"
    cfg.pf_viz_mode = "pulse_meter"
    cfg.disk_viz_mode = "dual_meter"
    assert cfg.save(cfg_path)

    loaded = AppConfig.load(cfg_path)
    assert loaded.cpu_viz_mode == "core_bars"
    assert loaded.ram_viz_mode == "grid_blocks"
    assert loaded.pf_viz_mode == "pulse_meter"
    assert loaded.disk_viz_mode == "dual_meter"

    # Invalid values must fall back to "graph"
    raw = json.loads(cfg_path.read_text(encoding="utf-8"))
    raw["cpu_viz_mode"] = "invalid_mode"
    raw["ram_viz_mode"] = 123
    cfg_path.write_text(json.dumps(raw), encoding="utf-8")
    sanitized = AppConfig.load(cfg_path)
    assert sanitized.cpu_viz_mode == "graph"
    assert sanitized.ram_viz_mode == "graph"


def test_power_of_two_grid_scaling() -> None:
    assert power_of_two_grid(8.0) == (8, 8, 1)
    assert power_of_two_grid(16.0) == (16, 8, 2)
    assert power_of_two_grid(32.0) == (32, 8, 4)
    assert power_of_two_grid(61.4) == (64, 16, 4)
    assert power_of_two_grid(128.0) == (64, 16, 4)


def test_cpu_widget_renders_all_visualizer_modes() -> None:
    app = _ensure_qapp()
    cfg = AppConfig()
    cfg.cpu_show_page_faults = True
    cfg.cpu_show_disk_io = True
    w = CpuSystemWidget(cfg)
    w.show()

    snap = SystemSnapshot(
        cpu=CpuSystemSample(
            cpu_percent=42.5,
            cpu_max_core_percent=88.0,
            cpu_cores=[12.0, 88.0, 45.0, 25.0, 91.0, 10.0, 33.0, 52.0],
            cpu_freq_mhz=4600.0,
            ram_used_gb=23.6,
            ram_total_gb=61.4,
            ram_percent=38.4,
            page_faults_per_sec=1200.0,
            disk_read_mb_s=45.2,
            disk_write_mb_s=128.7,
        )
    )

    modes = [
        ("graph", "graph", "graph", "graph"),
        ("core_bars", "grid_blocks", "pulse_meter", "dual_meter"),
        ("core_heatmap", "segmented_bar", "impulse_bars", "activity_leds"),
    ]
    for idx, (c_m, r_m, p_m, d_m) in enumerate(modes):
        cfg.cpu_viz_mode = c_m
        cfg.ram_viz_mode = r_m
        cfg.pf_viz_mode = p_m
        cfg.disk_viz_mode = d_m
        w.on_apply_config()
        w.update_snapshot(snap)
        app.processEvents()
        assert w.stack_cpu.currentIndex() == idx
        assert w.stack_ram.currentIndex() == idx
        assert w.stack_pf.currentIndex() == idx
        assert w.stack_disk.currentIndex() == idx
        pixmap = w.grab()
        assert pixmap.width() > 0 and pixmap.height() > 0

    w.close()


def test_settings_dialog_system_viz_and_save() -> None:
    _ensure_qapp()
    cfg = AppConfig()
    cfg.save = lambda: None
    dlg = SettingsDialog(cfg, [], lambda: None, disks=[])

    assert dlg.cmb_ram_viz.itemText(1) == "Speicherblöcke"

    dlg.cmb_cpu_viz.setCurrentIndex(1)
    dlg.cmb_ram_viz.setCurrentIndex(1)
    dlg.cmb_pf_viz.setCurrentIndex(2)
    dlg.cmb_disk_viz.setCurrentIndex(1)
    with patch("src.ui.settings_dlg.set_autostart"):
        dlg._save_to_config()

    assert cfg.cpu_viz_mode == "core_bars"
    assert cfg.ram_viz_mode == "grid_blocks"
    assert cfg.pf_viz_mode == "impulse_bars"
    assert cfg.disk_viz_mode == "dual_meter"

    with patch("src.ui.settings_dlg.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
        dlg._reset_defaults()
    assert dlg.cmb_cpu_viz.currentData() == "graph"
    assert dlg.cmb_ram_viz.currentData() == "graph"
    assert dlg.cmb_pf_viz.currentData() == "graph"
    assert dlg.cmb_disk_viz.currentData() == "graph"
    dlg.close()


def test_disk_choices_friendly_labels_in_settings() -> None:
    _ensure_qapp()
    cfg = AppConfig()
    cfg.cpu_disk_device = "PhysicalDrive1"
    cfg.save = lambda: None
    choices = [
        ("PhysicalDrive0", "Generic NVMe SSD 1TB (C:)"),
        ("PhysicalDrive1", "Generic SATA SSD 500GB (D:, E:)"),
    ]
    dlg = SettingsDialog(cfg, [], lambda: None, disks=choices)
    assert dlg.cmb_disk.itemText(1) == "Generic NVMe SSD 1TB (C:)"
    assert dlg.cmb_disk.itemData(1) == "PhysicalDrive0"
    assert dlg.cmb_disk.currentText() == "Generic SATA SSD 500GB (D:, E:)"
    assert dlg.cmb_disk.currentData() == "PhysicalDrive1"
    dlg.close()

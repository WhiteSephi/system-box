from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtCore import QPoint, QTimer
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QApplication, QLabel, QMenu

from src.config import AppConfig
from src.sensors.models import GpuInfo, SystemSnapshot
from src.sensors.psutil_provider import PsutilSystemProvider
from src.themes import THEMES
from src.ui.cpu_widget import CpuSystemWidget
from src.ui.settings_dlg import SettingsDialog


def _ensure_qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_settings_dialog_themes_disks_and_hardware_label() -> None:
    app = _ensure_qapp()
    cfg = AppConfig()
    cfg.save = lambda: None  # avoid writing to user config
    applied: list[bool] = []
    gpus = [GpuInfo(index=0, name="AMD GPU (card1)", vendor="amd", backend="sysfs")]
    disks = ["nvme0n1", "nvme1n1"]

    dlg = SettingsDialog(cfg, gpus, lambda: applied.append(True), disks=disks)
    dlg.tabs.setCurrentIndex(SettingsDialog.TAB_KEYS["about"])
    dlg.show()
    app.processEvents()

    # Hardware label in About tab should get full width and sufficient height
    hw_labels = [lbl for lbl in dlg.findChildren(QLabel) if "AMD GPU" in lbl.text()]
    assert len(hw_labels) == 1
    assert hw_labels[0].width() >= 400
    assert hw_labels[0].height() >= hw_labels[0].fontMetrics().height()

    # Theme preview and immediate apply
    assert all("FRITZ!Box" not in name for name in THEMES)
    idx_mono = dlg.cmb_theme.findText("Minimalist Monochrome (Weiß & Grau)")
    assert idx_mono >= 0
    dlg.cmb_theme.setCurrentIndex(idx_mono)
    dlg.cmb_theme.activated.emit(idx_mono)
    assert dlg.btn_col_primary.hex_color == "#FFFFFF"

    idx_amber = dlg.cmb_theme.findText("Amber Terminal (Bernstein & Graphit)")
    assert idx_amber >= 0
    dlg.cmb_theme.setCurrentIndex(idx_amber)
    with patch("src.ui.settings_dlg.set_autostart"):
        dlg._apply_preset_theme()
    assert cfg.primary_color == "#FFB300"
    assert len(applied) == 1

    # Disk selection saved to config
    assert dlg.cmb_disk.itemText(0) == "Alle Datenträger (Summe)"
    assert dlg.cmb_disk.count() == 3
    dlg.cmb_disk.setCurrentIndex(2)
    with patch("src.ui.settings_dlg.set_autostart"):
        dlg._save_to_config()
    assert cfg.cpu_disk_device == "nvme1n1"

    dlg.close()


def test_context_menu_matches_trafficbox_layout() -> None:
    _ensure_qapp()
    cfg = AppConfig()
    w = CpuSystemWidget(cfg)
    captured: list[str] = []

    def capture_and_close() -> None:
        for top in QApplication.topLevelWidgets():
            if isinstance(top, QMenu) and top.isVisible():
                for act in top.actions():
                    captured.append("---" if act.isSeparator() else act.text())
                top.close()

    QTimer.singleShot(50, capture_and_close)
    ev = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(10, 10), QPoint(100, 100))
    w.contextMenuEvent(ev)
    assert captured == [
        "Einstellungen...",
        "---",
        "Immer im Vordergrund",
        "Position sperren",
        "---",
        "Widget ausblenden",
        "---",
        "Über SystemBox...",
        "Beenden",
    ]
    w.close()


def test_psutil_per_disk_io_selection_and_switch_reset() -> None:
    fake_all_1 = SimpleNamespace(read_bytes=1_000_000, write_bytes=500_000)
    fake_nvme0_1 = SimpleNamespace(read_bytes=200_000, write_bytes=100_000)
    fake_nvme0_2 = SimpleNamespace(read_bytes=200_000 + 10 * 1024 * 1024, write_bytes=100_000)

    with (
        patch("src.sensors.psutil_provider.psutil.disk_io_counters") as mock_io,
        patch("src.sensors.psutil_provider.psutil.cpu_percent", return_value=[10.0, 20.0]),
        patch("src.sensors.psutil_provider.psutil.virtual_memory") as mock_vm,
        patch("src.sensors.psutil_provider.psutil.swap_memory") as mock_sw,
    ):
        mock_vm.return_value = SimpleNamespace(used=4 * 1024**3, total=16 * 1024**3, percent=25.0)
        mock_sw.return_value = SimpleNamespace(used=0, total=0, percent=0.0)

        mock_io.return_value = fake_all_1
        prov = PsutilSystemProvider()

        # Switch to specific disk -> delta must reset to 0.0 (no cross-device spike)
        mock_io.side_effect = lambda perdisk=False: {"nvme0n1": fake_nvme0_1} if perdisk else fake_all_1
        s1 = prov.read_system(disk_device="nvme0n1")
        assert s1.disk_read_mb_s == 0.0

        # Second poll on same disk -> positive throughput
        mock_io.side_effect = lambda perdisk=False: {"nvme0n1": fake_nvme0_2} if perdisk else fake_all_1
        s2 = prov.read_system(disk_device="nvme0n1")
        assert s2.disk_read_mb_s > 0.0


def test_app_tray_menu_escaping_and_visibility() -> None:
    from src.app import SystemBoxApp

    app = _ensure_qapp()
    cfg = AppConfig()
    cfg.save = lambda: None
    with (
        patch("src.app.SensorManager") as mock_mgr_cls,
        patch("src.app.QSystemTrayIcon.show"),
    ):
        mock_mgr_cls.return_value.list_gpus.return_value = []
        mock_mgr_cls.return_value.list_disks.return_value = []
        mock_mgr_cls.return_value.poll.return_value = SystemSnapshot()
        controller = SystemBoxApp(app, cfg)
        labels = [act.text() for act in controller._tray_widget_actions.values()]
        assert "Uhrzeit && Datum" in labels
        assert "CPU && System" in labels
        controller._poll_timer.stop()
        for w in controller._widgets.values():
            w.close()

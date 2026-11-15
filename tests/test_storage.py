from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from src.config import AppConfig
from src.sensors.disk_space import format_storage_size, read_disk_spaces
from src.sensors.models import DiskSpaceInfo, SystemSnapshot
from src.ui.storage_widget import StorageWidget


def _ensure_qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_linux_btrfs_deduplication_and_mnt_labels() -> None:
    fake_parts = [
        SimpleNamespace(device="/dev/nvme1n1p2", mountpoint="/var/log", fstype="btrfs", opts="rw,subvol=/@log"),
        SimpleNamespace(device="/dev/nvme1n1p2", mountpoint="/", fstype="btrfs", opts="rw,subvol=/@"),
        SimpleNamespace(device="/dev/nvme1n1p2", mountpoint="/home", fstype="btrfs", opts="rw,subvol=/@home"),
        SimpleNamespace(device="/dev/nvme0n1p1", mountpoint="/mnt/Daten", fstype="ext4", opts="rw"),
        SimpleNamespace(device="tmpfs", mountpoint="/tmp", fstype="tmpfs", opts="rw"),
        SimpleNamespace(device="/dev/nvme1n1p1", mountpoint="/boot/efi", fstype="vfat", opts="rw"),
    ]

    def fake_usage(mnt: str):
        if mnt == "/mnt/Daten":
            return SimpleNamespace(total=2000 * 1024**3, used=1200 * 1024**3, free=800 * 1024**3, percent=60.0)
        return SimpleNamespace(total=500 * 1024**3, used=110 * 1024**3, free=390 * 1024**3, percent=22.0)

    with (
        patch("src.sensors.disk_space.sys.platform", "linux"),
        patch("src.sensors.disk_space.psutil.disk_partitions", return_value=fake_parts),
        patch("src.sensors.disk_space.psutil.disk_usage", side_effect=fake_usage),
    ):
        disks = read_disk_spaces(deduplicate_devices=True, show_boot=False)
        assert [d.mountpoint for d in disks] == ["/", "/mnt/Daten"]
        assert disks[0].label == "System (/)"
        assert disks[1].label == "Daten (/mnt/Daten)"

        disks_all = read_disk_spaces(deduplicate_devices=False, show_boot=True)
        assert len(disks_all) == 5  # tmpfs still filtered


def test_windows_cdrom_filter_and_labels() -> None:
    fake_parts = [
        SimpleNamespace(device="C:\\", mountpoint="C:\\", fstype="NTFS", opts="rw,fixed"),
        SimpleNamespace(device="D:\\", mountpoint="D:\\", fstype="", opts="cdrom"),
    ]

    def fake_usage(mnt: str):
        return SimpleNamespace(total=1000 * 1024**3, used=400 * 1024**3, free=600 * 1024**3, percent=40.0)

    with (
        patch("src.sensors.disk_space.sys.platform", "win32"),
        patch("src.sensors.disk_space._get_windows_volume_label", return_value="Windows"),
        patch("src.sensors.disk_space.psutil.disk_partitions", return_value=fake_parts),
        patch("src.sensors.disk_space.psutil.disk_usage", side_effect=fake_usage),
    ):
        disks = read_disk_spaces()
        assert len(disks) == 1
        assert disks[0].label == "Windows (C:)"


def test_storage_widget_renders_and_warns() -> None:
    _ensure_qapp()
    cfg = AppConfig()
    cfg.storage_warn_percent = 85
    cfg.storage_show_free_first = True
    w = StorageWidget(cfg)

    snap = SystemSnapshot(
        disks=[
            DiskSpaceInfo(
                device="/dev/nvme1n1p2",
                mountpoint="/",
                label="System (/)",
                fstype="btrfs",
                total_gb=461.8,
                used_gb=101.1,
                free_gb=360.7,
                percent=22.0,
            ),
            DiskSpaceInfo(
                device="/dev/sda1",
                mountpoint="/mnt/Backup",
                label="Backup (/mnt/Backup)",
                fstype="ext4",
                total_gb=1024.0,
                used_gb=930.0,
                free_gb=94.0,
                percent=90.8,
            ),
        ]
    )
    w.update_snapshot(snap)
    assert not w.lbl_empty.isVisible()
    assert len(w._rows) == 2
    assert w._rows[0].lbl_name.text() == "System (/)"
    assert "360.7 GB frei von 461.8 GB" in w._rows[0].lbl_sub.text()
    assert w._rows[1].bar._fill_color.name().lower() == cfg.temp_color.lower()
    assert format_storage_size(2048.0) == "2.00 TB"

    # Hide the second mountpoint and re-apply config
    cfg.storage_hidden_mountpoints = ["/mnt/Backup"]
    w.on_apply_config()
    assert not w._rows[0].isHidden()
    assert w._rows[1].isHidden()
    w.close()


def test_settings_dialog_storage_drive_selection(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from src.ui.settings_dlg import SettingsDialog

    app = QApplication.instance() or QApplication([])
    assert app is not None

    cfg = AppConfig()
    cfg.storage_hidden_mountpoints = ["D:\\"]
    disks = [
        DiskSpaceInfo(device="C:\\", mountpoint="C:\\", label="Laufwerk (C:)", fstype="NTFS", total_gb=500.0, used_gb=250.0, free_gb=250.0, percent=50.0),
        DiskSpaceInfo(device="D:\\", mountpoint="D:\\", label="Laufwerk (D:)", fstype="NTFS", total_gb=1000.0, used_gb=600.0, free_gb=400.0, percent=60.0),
    ]
    dlg = SettingsDialog(config=cfg, gpus=[], on_apply=lambda: None, storage_disks=disks)
    assert dlg._storage_drive_checks["C:\\"].isChecked()
    assert not dlg._storage_drive_checks["D:\\"].isChecked()

    dlg._storage_drive_checks["C:\\"].setChecked(False)
    dlg._storage_drive_checks["D:\\"].setChecked(True)
    dlg._save_to_config()
    assert cfg.storage_hidden_mountpoints == ["C:\\"]
    dlg.close()

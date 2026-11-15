"""Tests for cross-platform autostart command generation and start delay clamping."""

from __future__ import annotations

from pathlib import Path

from src.autostart import get_linux_autostart_cmd, get_windows_autostart_cmd, sync_kwin_skip_taskbar_rule
from src.config import AppConfig


def test_autostart_commands(tmp_path: Path) -> None:
    vbs = tmp_path / "start_windows.vbs"
    vbs.write_text("", encoding="utf-8")
    win_cmd = get_windows_autostart_cmd(tmp_path)
    assert "wscript.exe" in win_cmd
    assert "--autostart" in win_cmd

    sh = tmp_path / "start_linux.sh"
    sh.write_text("", encoding="utf-8")
    lin_cmd = get_linux_autostart_cmd(tmp_path)
    assert "start_linux.sh" in lin_cmd
    assert "--autostart" in lin_cmd


def test_start_delay_clamping() -> None:
    cfg = AppConfig()
    cfg.start_delay_sec = 999
    cfg.sanitize()
    assert cfg.start_delay_sec == 60
    cfg.start_delay_sec = -5
    cfg.sanitize()
    assert cfg.start_delay_sec == 0


def test_sync_kwin_skip_taskbar_rule_preserves_existing(tmp_path: Path) -> None:
    import os
    from unittest.mock import patch

    kwinrules = tmp_path / "kwinrulesrc"
    kwinrules.write_text(
        "[General]\nOrder=TrafficBox-Position\n\n[TrafficBox-Position]\nDescription=TrafficBox Placement\n",
        encoding="utf-8",
    )

    with (
        patch("src.autostart.sys.platform", "win32"),
    ):
        assert sync_kwin_skip_taskbar_rule() is False

    with (
        patch("src.autostart.sys.platform", "linux"),
        patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path)}),
        patch("shutil.which", return_value=None),
    ):
        assert sync_kwin_skip_taskbar_rule() is True

    updated = kwinrules.read_text(encoding="utf-8")
    assert "[TrafficBox-Position]" in updated
    assert "[SystemBox-Taskbar]" in updated
    assert "wmclass=.*[Ss]ystem[Bb]ox.*" in updated
    assert "skiptaskbar=true" in updated
    assert "skiptaskbarrule=2" in updated
    assert "TrafficBox-Position,SystemBox-Taskbar" in updated

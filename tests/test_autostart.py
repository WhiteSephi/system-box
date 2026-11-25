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
    import sys
    from types import SimpleNamespace
    from unittest.mock import patch

    try:
        import fcntl as real_fcntl
    except ImportError:
        real_fcntl = None

    kwinrules = tmp_path / "kwinrulesrc"
    kwinrules.write_text(
        "[General]\ncustomKey=keep\nrules=TrafficBox-Position\nOrder=TrafficBox-Position\n\n"
        "[TrafficBox-Position]\nDescription=TrafficBox Placement\nskptaskbar=true\n",
        encoding="utf-8",
    )

    with (
        patch("src.autostart.sys.platform", "win32"),
    ):
        assert sync_kwin_skip_taskbar_rule() is False

    flock_ops: list[int] = []
    if real_fcntl is not None:
        lock_ex, lock_un = real_fcntl.LOCK_EX, real_fcntl.LOCK_UN
        orig_flock = real_fcntl.flock

        def _recording_flock(fd: int, op: int) -> None:
            flock_ops.append(op)
            orig_flock(fd, op)

        fcntl_ctx = patch("fcntl.flock", side_effect=_recording_flock)
    else:
        lock_ex, lock_un = 2, 8

        def _fake_flock(fd: int, op: int) -> None:
            flock_ops.append(op)

        fake_fcntl = SimpleNamespace(LOCK_EX=lock_ex, LOCK_UN=lock_un, flock=_fake_flock)
        fcntl_ctx = patch.dict(sys.modules, {"fcntl": fake_fcntl})

    with (
        patch("src.autostart.sys.platform", "linux"),
        patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path)}),
        patch("shutil.which", return_value=None),
        fcntl_ctx,
    ):
        assert sync_kwin_skip_taskbar_rule() is True
        # Idempotent second call must not duplicate entries
        assert sync_kwin_skip_taskbar_rule() is True

    assert (tmp_path / ".kwinrulesrc.lock").is_file()
    assert flock_ops == [lock_ex, lock_un, lock_ex, lock_un]

    updated = kwinrules.read_text(encoding="utf-8")
    assert "customKey=keep" in updated
    assert "[TrafficBox-Position]" in updated
    assert "[SystemBox-Taskbar]" in updated
    assert updated.count("[SystemBox-Taskbar]") == 1
    assert "wmclass=.*[Ss]ystem[Bb]ox.*" in updated
    assert "skiptaskbar=true" in updated
    assert "skiptaskbarrule=2" in updated
    assert "rules=TrafficBox-Position,SystemBox-Taskbar" in updated
    assert "Order=TrafficBox-Position,SystemBox-Taskbar" in updated
    assert "count=2" in updated


def test_sync_kwin_skip_taskbar_rule_does_not_clobber_on_read_error(tmp_path: Path) -> None:
    import os
    from unittest.mock import patch

    kwinrules = tmp_path / "kwinrulesrc"
    original = "[General]\nOrder=TrafficBox-Position\n\n[TrafficBox-Position]\nDescription=Keep\n"
    kwinrules.write_text(original, encoding="utf-8")

    with (
        patch("src.autostart.sys.platform", "linux"),
        patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path)}),
        patch.object(Path, "read_text", side_effect=OSError("permission denied")),
    ):
        assert sync_kwin_skip_taskbar_rule() is False

    assert kwinrules.read_text(encoding="utf-8") == original


def test_autostart_path_escaping(tmp_path: Path) -> None:
    sub = tmp_path / "O'Brien's Dir $100%"
    sub.mkdir(parents=True, exist_ok=True)

    win_cmd = get_windows_autostart_cmd(sub)
    assert "sys.argv[1]" in win_cmd
    # Path must NOT be interpolated inside the -c Python code string
    code_part, trailing = win_cmd.rsplit("sys.exit(main(['--autostart']))\"", 1)
    assert "O'Brien" not in code_part
    assert f'"{sub}"' in trailing

    sh = sub / "start_linux.sh"
    sh.write_text("", encoding="utf-8")
    lin_cmd = get_linux_autostart_cmd(sub)
    assert "\\$100%%" in lin_cmd
    assert lin_cmd.startswith('"')
    assert lin_cmd.endswith(' --autostart')

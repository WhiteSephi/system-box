"""Cross-platform autostart integration for Windows (Registry) and Linux/KDE (XDG)."""

from __future__ import annotations

import os
from pathlib import Path
import sys

from src.config import atomic_write_text

APP_NAME = "SystemBox"
DESKTOP_FILENAME = "systembox.desktop"
_DESKTOP_EXEC_SPECIAL = set('"\'\\$`><~|&;*?#()%')


def _sanitize_desktop_value(value: str) -> str:
    """Strip CR/LF characters so single-line .desktop fields cannot be broken."""
    return value.replace("\r", "").replace("\n", "")


def _escape_desktop_exec_arg(arg: str) -> str:
    """Escape an argument for FreeDesktop .desktop Exec= lines."""
    clean = _sanitize_desktop_value(arg)
    if any(ch.isspace() or ch in _DESKTOP_EXEC_SPECIAL for ch in clean):
        escaped = (
            clean.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("`", "\\`")
            .replace("$", "\\$")
            .replace("%", "%%")
        )
        return f'"{escaped}"'
    return clean


def get_project_root() -> Path:
    """Return the root directory of the project."""
    return Path(__file__).resolve().parent.parent


def _get_linux_autostart_file() -> Path:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config_home / "autostart" / DESKTOP_FILENAME


def get_windows_autostart_cmd(project_root: Path | None = None) -> str:
    """Generate the Windows command string for autostart."""
    if project_root is None:
        project_root = get_project_root()
    if getattr(sys, "frozen", False):
        exe = str(sys.executable).replace('"', "")
        return f'"{exe}" --autostart'
    vbs_script = project_root / "start_windows.vbs"
    if vbs_script.is_file():
        script_arg = str(vbs_script).replace('"', "")
        return f'wscript.exe "{script_arg}" --autostart'
    python_exe = Path(sys.executable)
    pythonw = python_exe.with_name("pythonw.exe")
    exe_to_use = str(pythonw if pythonw.is_file() else python_exe).replace('"', "")
    root_arg = str(project_root).replace('"', "")
    return (
        f'"{exe_to_use}" -c '
        f'"import os, sys; p = sys.argv[1]; sys.path.insert(0, p); os.chdir(p); '
        f'from src.main import main; sys.exit(main([\'--autostart\']))" '
        f'"{root_arg}"'
    )


def get_linux_autostart_cmd(project_root: Path | None = None) -> str:
    """Generate the Linux Exec command string for autostart."""
    if project_root is None:
        project_root = get_project_root()
    if getattr(sys, "frozen", False):
        return f"{_escape_desktop_exec_arg(str(sys.executable))} --autostart"
    sh_script = project_root / "start_linux.sh"
    if sh_script.is_file():
        return f"{_escape_desktop_exec_arg(str(sh_script))} --autostart"
    return f"{_escape_desktop_exec_arg(str(sys.executable))} -m src.main --autostart"


def is_autostart_enabled() -> bool:
    """Check whether autostart is currently configured on the current OS."""
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ,
            ) as key:
                winreg.QueryValueEx(key, APP_NAME)
                return True
        except OSError:
            return False
    return _get_linux_autostart_file().is_file()


def set_autostart(enabled: bool) -> bool:
    """Enable or disable application autostart on Windows or Linux."""
    project_root = get_project_root()

    if sys.platform == "win32":
        try:
            import winreg

            cmd = get_windows_autostart_cmd(project_root)
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                if enabled:
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                else:
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                    except FileNotFoundError:
                        pass
            return True
        except OSError as exc:
            if sys.stderr is not None:
                print(f"[WARN] Windows-Autostart konnte nicht gesetzt werden: {exc}", file=sys.stderr)
            return False

    desktop_file = _get_linux_autostart_file()
    try:
        if enabled:
            exec_cmd = get_linux_autostart_cmd(project_root)
            content = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=SystemBox\n"
                "Comment=Live System & GPU Desktop Widgets\n"
                f"Path={_sanitize_desktop_value(str(project_root))}\n"
                f"Exec={exec_cmd}\n"
                "Icon=utilities-system-monitor\n"
                "Terminal=false\n"
                "Categories=System;Monitor;Qt;\n"
                "X-KDE-autostart-after=panel\n"
            )
            atomic_write_text(desktop_file, content)
        elif desktop_file.is_file():
            desktop_file.unlink()
        return True
    except OSError as exc:
        if sys.stderr is not None:
            print(f"[WARN] Linux-Autostart konnte nicht gesetzt werden: {exc}", file=sys.stderr)
        return False


def sync_kwin_skip_taskbar_rule() -> bool:
    """Register or update a KWin window rule on KDE Plasma to hide SystemBox widgets from taskbar and Alt+Tab."""
    if not sys.platform.startswith("linux"):
        return False

    import re
    import shutil
    import subprocess

    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    kwinrules = config_home / "kwinrulesrc"

    rule_name = "SystemBox-Taskbar"
    rule_section = (
        f"[{rule_name}]\n"
        "Description=SystemBox Hide from Taskbar\n"
        "wmclass=.*[Ss]ystem[Bb]ox.*\n"
        "wmclassmatch=3\n"
        "wmclasscomplete=false\n"
        "skiptaskbar=true\n"
        "skiptaskbarrule=2\n"
        "skipswitcher=true\n"
        "skipswitcherrule=2\n"
    )

    try:
        content = kwinrules.read_text(encoding="utf-8") if kwinrules.is_file() else "[General]\ncount=0\nrules=\nOrder=\n"
    except OSError:
        content = "[General]\ncount=0\nrules=\nOrder=\n"

    pattern = rf"\[{re.escape(rule_name)}\].*?(?=\n\[|\Z)"
    if re.search(pattern, content, flags=re.DOTALL):
        content = re.sub(pattern, rule_section.strip(), content, flags=re.DOTALL)
    else:
        content = content.rstrip() + "\n\n" + rule_section.strip()

    gen_match = re.search(r"\[General\](.*?)(?=\n\[|\Z)", content, flags=re.DOTALL)
    if gen_match:
        gen_body = gen_match.group(1)
        r_m = re.search(r"rules=([^\n]*)", gen_body)
        rules_list = [r.strip() for r in r_m.group(1).split(",") if r.strip()] if r_m else []
        if rule_name not in rules_list:
            rules_list.append(rule_name)

        o_m = re.search(r"Order=([^\n]*)", gen_body)
        order_list = [r.strip() for r in o_m.group(1).split(",") if r.strip()] if o_m else []
        if rule_name not in order_list:
            order_list.append(rule_name)

        count_val = max(len(rules_list), len(order_list), 1)
        lines = [line for line in gen_body.split("\n") if not line.startswith(("rules=", "Order=", "count="))]
        lines = [line for line in lines if line.strip()]
        new_gen = (
            "\n[General]\n"
            + "\n".join(
                lines
                + [
                    f"count={count_val}",
                    f"rules={','.join(rules_list)}",
                    f"Order={','.join(order_list)}",
                ]
            )
            + "\n"
        )
        content = content[: gen_match.start()] + new_gen.lstrip() + content[gen_match.end() :]
    else:
        content = f"[General]\ncount=1\nrules={rule_name}\nOrder={rule_name}\n\n" + content

    try:
        atomic_write_text(kwinrules, content.strip() + "\n")
    except OSError as exc:
        if sys.stderr is not None:
            print(f"[WARN] kwinrulesrc konnte nicht geschrieben werden: {exc}", file=sys.stderr)
        return False

    qdbus_bin = shutil.which("qdbus6") or shutil.which("qdbus")
    if qdbus_bin:
        try:
            subprocess.run(
                [qdbus_bin, "org.kde.KWin", "/KWin", "reconfigure"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=1.0,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            if sys.stderr is not None:
                print(f"[WARN] KWin-Reload fehlgeschlagen: {exc}", file=sys.stderr)
    return True

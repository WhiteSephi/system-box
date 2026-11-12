"""Entry point for the cross-platform SystemBox Desktop Widget Suite."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import signal
import sys

from PySide6.QtWidgets import QApplication

from src.app import SystemBoxApp
from src.config import AppConfig


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="SystemBox – Cross-platform Live Desktop Widgets (Clock, GPU, CPU/System)"
    )
    parser.add_argument(
        "--workdir",
        type=str,
        default="",
        help="Optional working directory (used by autostart entry).",
    )
    parser.add_argument(
        "--autostart",
        action="store_true",
        help="Indicates launch via OS autostart (applies configured start_delay_sec).",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run a short verification of UI, sensors and event loop, then exit.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Launch the SystemBox application."""
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args.workdir:
        target_dir = Path(args.workdir)
        if target_dir.is_dir():
            os.chdir(target_dir)

    if sys.platform.startswith("linux") and "QT_QPA_PLATFORM" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "xcb;wayland"

    app = QApplication(sys.argv)
    app.setApplicationName("SystemBox")
    app.setDesktopFileName("systembox")
    app.setQuitOnLastWindowClosed(False)

    config = AppConfig.load()
    if args.autostart and config.start_delay_sec > 0 and not args.self_test:
        import time

        time.sleep(config.start_delay_sec)

    controller = SystemBoxApp(app, config)

    def _handle_terminate_signal(_signum: int, _frame: object) -> None:
        controller.quit_application()

    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is not None:
            try:
                signal.signal(sig, _handle_terminate_signal)
            except (OSError, ValueError):
                pass

    if args.self_test:
        from PySide6.QtCore import QTimer

        QTimer.singleShot(1200, controller.quit_application)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

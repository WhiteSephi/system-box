"""Global pytest fixtures ensuring strict isolation and clean Qt/logger teardown."""

from __future__ import annotations

import gc
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent, QTimer, qInstallMessageHandler
from PySide6.QtWidgets import QApplication
import pytest


def _cleanup_qt_state() -> None:
    """Stop active QTimers, close/delete remaining top-level widgets, and flush DeferredDelete."""
    app = QApplication.instance()
    if app is None:
        return

    for widget in list(app.topLevelWidgets()):
        try:
            for timer in widget.findChildren(QTimer):
                timer.stop()
            widget.close()
            widget.deleteLater()
        except RuntimeError:
            pass

    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def _cleanup_logger_state() -> None:
    """Close/remove rotating log handlers and detach Qt message handler."""
    import src.logger as app_logger_mod

    qInstallMessageHandler(None)
    app_logger_mod._qt_handler_installed = False
    app_logger_mod._previous_qt_handler = None

    root = logging.getLogger("systembox")
    for handler in list(root.handlers):
        if isinstance(handler, RotatingFileHandler):
            root.removeHandler(handler)
            handler.close()


@pytest.fixture(scope="session", autouse=True)
def qapp_session():
    """Keep a single QApplication alive for the test session and tear it down cleanly."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

    qInstallMessageHandler(None)
    _cleanup_qt_state()
    gc.collect()
    app.quit()


@pytest.fixture(autouse=True)
def isolate_user_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect config/log dirs to tmp_path, stub autostart, and clean up Qt/loggers per test."""
    monkeypatch.setattr("src.config.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("src.logger.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("src.ui.settings_dlg.set_autostart", lambda enabled: True)
    monkeypatch.setattr("src.ui.settings_dlg.is_autostart_enabled", lambda: False)
    yield
    _cleanup_qt_state()
    _cleanup_logger_state()

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from src.config import AppConfig
from src.logger import (
    PrivacyRedactionFilter,
    build_github_issue_url,
    collect_diagnostics_report,
    get_log_dir,
    get_log_file,
    read_recent_logs,
    redact_sensitive_text,
    set_debug_logging,
    setup_logging,
)
from src.ui.settings_dlg import SettingsDialog


def _ensure_qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_redact_sensitive_text() -> None:
    home = str(Path.home())
    sample = (
        f"User file at {home}\\secret.txt, connected to 192.168.1.105:8080, "
        "local is 127.0.0.1, token=super_secret_token123&password=my_password!"
    )
    redacted = redact_sensitive_text(sample)
    assert home not in redacted
    assert "~" in redacted
    assert "192.168.1.105" not in redacted
    assert "<IP>:8080" in redacted
    assert "127.0.0.1" in redacted  # Safe IP preserved
    assert "super_secret_token123" not in redacted
    assert "token=***" in redacted
    assert "password=***" in redacted


def test_privacy_redaction_filter() -> None:
    filt = PrivacyRedactionFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Error with password=%s on 10.0.0.5",
        args=("secret_pass",),
        exc_info=None,
    )
    assert filt.filter(record) is True
    formatted = record.getMessage()
    assert "secret_pass" not in formatted
    assert "<IP>" in formatted


def test_setup_logging_and_debug_toggle(tmp_path: Path) -> None:
    with patch("src.logger.get_config_dir", return_value=tmp_path):
        log_file = setup_logging(debug=False)
        assert log_file.is_file()
        logger = logging.getLogger("systembox")
        assert logger.level == logging.INFO

        logger.info("Test info message with token=abcdef12345")
        set_debug_logging(True)
        assert logger.level == logging.DEBUG
        logger.debug("Test debug message 10.0.0.88")

        logs = read_recent_logs()
        assert "Test info message" in logs
        assert "token=***" in logs
        assert "Test debug message" in logs
        assert "<IP>" in logs


def test_collect_diagnostics_report(tmp_path: Path) -> None:
    with patch("src.logger.get_config_dir", return_value=tmp_path):
        cfg = AppConfig()
        cfg.debug_logging = True
        report = collect_diagnostics_report(cfg, qt_version="6.8.0")
        assert "### System-Diagnose (anonymisiert)" in report
        assert "SystemBox" in report
        assert "Qt 6.8.0" in report
        assert "### Letzte Log-Einträge" in report

        url, truncated = build_github_issue_url(report, "https://github.com/WhiteSephi/system-box/issues")
        assert url.startswith("https://github.com/WhiteSephi/system-box/issues/new?")
        assert "%5BBug%5D" in url or "[Bug]" in url
        assert not truncated


def test_settings_dialog_diagnostics_buttons(tmp_path: Path) -> None:
    _ensure_qapp()
    with patch("src.logger.get_config_dir", return_value=tmp_path):
        cfg = AppConfig()
        cfg.save = lambda: None
        dlg = SettingsDialog(cfg, [], lambda: None, disks=[])

        assert hasattr(dlg, "chk_debug_logging")
        assert hasattr(dlg, "btn_open_logs")
        assert hasattr(dlg, "btn_copy_diag")
        assert hasattr(dlg, "btn_about_issues")

        # Copy diagnostics action
        with patch("src.ui.settings_dlg.QMessageBox.information"), patch.object(
            QApplication, "clipboard"
        ) as mock_cb:
            mock_clip_instance = mock_cb.return_value
            dlg._copy_diagnostics_to_clipboard()
            mock_clip_instance.setText.assert_called_once()
            args, _ = mock_clip_instance.setText.call_args
            assert "SystemBox" in args[0]

        # Save debug logging
        dlg.chk_debug_logging.setChecked(True)
        dlg._save_to_config()
        assert cfg.debug_logging is True

        dlg.close()

"""Global pytest fixtures ensuring strict isolation from host user profiles and autostart."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_user_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect config/log directories to tmp_path and stub OS autostart queries/writes."""
    monkeypatch.setattr("src.config.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("src.logger.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("src.ui.settings_dlg.set_autostart", lambda enabled: True)
    monkeypatch.setattr("src.ui.settings_dlg.is_autostart_enabled", lambda: False)

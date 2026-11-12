"""Tests for AppConfig persistence, validation, scaling and theme presets."""

from __future__ import annotations

from pathlib import Path

from src.config import AppConfig
from src.themes import THEMES


def test_config_roundtrip_and_clamping(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.json"
    cfg = AppConfig()
    cfg.ui_scale_percent = 999
    cfg.opacity = 5
    cfg.refresh_interval_ms = 50
    cfg.get_widget("gpu").scale_percent = 250
    cfg.save(cfg_file)

    loaded = AppConfig.load(cfg_file)
    assert loaded.ui_scale_percent == 300
    assert loaded.opacity == 20
    assert loaded.refresh_interval_ms == 500
    assert loaded.effective_scale("gpu") == 2.5
    assert loaded.effective_scale("clock") == 3.0


def test_apply_theme_updates_colors() -> None:
    cfg = AppConfig()
    cfg.apply_theme("Cyberpunk Neon (Cyan & Pink)")
    assert cfg.primary_color == THEMES["Cyberpunk Neon (Cyan & Pink)"]["primary"]
    assert cfg.background_color == THEMES["Cyberpunk Neon (Cyan & Pink)"]["bg"]

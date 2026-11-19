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
    cfg.gpu_temp_warn_c = 150
    cfg.get_widget("gpu").scale_percent = 250
    cfg.save(cfg_file)

    loaded = AppConfig.load(cfg_file)
    assert loaded.ui_scale_percent == 300
    assert loaded.opacity == 20
    assert loaded.refresh_interval_ms == 500
    assert loaded.gpu_temp_warn_c == 105
    assert loaded.effective_scale("gpu") == 2.5
    assert loaded.effective_scale("clock") == 3.0


def test_apply_theme_updates_colors() -> None:
    cfg = AppConfig()
    cfg.apply_theme("Cyberpunk Neon (Cyan & Pink)")
    assert cfg.primary_color == THEMES["Cyberpunk Neon (Cyan & Pink)"]["primary"]
    assert cfg.background_color == THEMES["Cyberpunk Neon (Cyan & Pink)"]["bg"]


def test_config_hardening_rejects_malformed_json_and_qss_injection(tmp_path: Path) -> None:
    # Non-dict JSON root must fall back to sanitized defaults cleanly
    list_cfg = tmp_path / "list.json"
    list_cfg.write_text("[1, 2, 3]", encoding="utf-8")
    loaded_list = AppConfig.load(list_cfg)
    assert loaded_list.opacity == 85
    assert loaded_list.refresh_interval_ms == 1000

    # Invalid types, method-name spoofing, and QSS injection strings must all be rejected
    bad_cfg = tmp_path / "bad.json"
    bad_cfg.write_text(
        """{
            "opacity": "invalid",
            "refresh_interval_ms": null,
            "ui_scale_percent": true,
            "save": "overwrite",
            "title_color": "#FFF; background: url(x)",
            "primary_color": "red",
            "vram_color": "#112233",
            "widgets": {
                "gpu": {"width": "bad", "scale_percent": true, "opacity": "abc"}
            }
        }""",
        encoding="utf-8",
    )
    loaded = AppConfig.load(bad_cfg)
    defaults = AppConfig()
    assert loaded.opacity == defaults.opacity
    assert loaded.refresh_interval_ms == defaults.refresh_interval_ms
    assert loaded.ui_scale_percent == defaults.ui_scale_percent
    assert callable(loaded.save)
    assert loaded.title_color == defaults.title_color
    assert loaded.primary_color == defaults.primary_color
    assert loaded.vram_color == "#112233"
    assert loaded.get_widget("gpu").scale_percent is None
    assert loaded.get_widget("gpu").opacity is None

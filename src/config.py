"""Configuration management and environment variable loader for SystemBox."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import sys

from src.themes import DEFAULT_THEME_NAME, THEMES


def _log_warn(msg: str) -> None:
    """Safely log a warning even when running as a windowless GUI binary."""
    if sys.stderr is not None:
        try:
            print(msg, file=sys.stderr)
        except OSError:
            pass


def get_config_dir() -> Path:
    """Return platform-specific configuration directory with portable local/ fallback."""
    if getattr(sys, "frozen", False):
        base_root = Path(sys.executable).resolve().parent
    else:
        base_root = Path(__file__).resolve().parent.parent
    local_dir = base_root / "local"
    if (local_dir / "config.json").is_file():
        return local_dir

    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    cfg_dir = base / "systembox"
    try:
        cfg_dir.mkdir(parents=True, exist_ok=True)
        return cfg_dir
    except OSError:
        local_dir.mkdir(parents=True, exist_ok=True)
        return local_dir


@dataclass
class WidgetConfig:
    """Per-widget layout and behavior overrides."""

    enabled: bool = True
    pos_x: int = -1
    pos_y: int = -1
    width: int = 320
    height: int = 240
    scale_percent: int | None = None  # None = inherit global ui_scale_percent
    opacity: int | None = None  # None = inherit global opacity
    always_on_top: bool | None = None  # None = inherit global always_on_top
    locked_pos: bool | None = None  # None = inherit global locked_pos

    def sanitize(self, default_width: int = 320, default_height: int = 240) -> None:
        """Clamp and validate widget configuration values."""
        self.enabled = bool(self.enabled)
        self.width = max(140, min(1600, int(self.width or default_width)))
        self.height = max(60, min(1400, int(self.height or default_height)))
        self.pos_x = int(self.pos_x) if isinstance(self.pos_x, (int, float)) else -1
        self.pos_y = int(self.pos_y) if isinstance(self.pos_y, (int, float)) else -1
        if self.scale_percent is not None:
            self.scale_percent = max(70, min(300, int(self.scale_percent)))
        if self.opacity is not None:
            self.opacity = max(20, min(100, int(self.opacity)))


def _default_widgets() -> dict[str, WidgetConfig]:
    return {
        "clock": WidgetConfig(enabled=True, width=250, height=185),
        "gpu": WidgetConfig(enabled=True, width=330, height=270),
        "cpu": WidgetConfig(enabled=True, width=330, height=250),
    }


@dataclass
class AppConfig:
    """Persistent global configuration for SystemBox."""

    # Polling & History
    refresh_interval_ms: int = 1000  # 500..5000 ms
    history_seconds: int = 60

    # Global Window & Scaling
    ui_scale_percent: int = 100  # 70..300 %
    opacity: int = 85  # 20..100 %
    always_on_top: bool = False
    locked_pos: bool = False
    autostart: bool = False

    # Settings Dialog Geometry
    settings_pos_x: int = -1
    settings_pos_y: int = -1
    settings_width: int = 680
    settings_height: int = 540

    # Widget-specific Options
    selected_gpu_index: int = 0
    clock_show_seconds: bool = True
    clock_show_uptime: bool = True
    clock_24h: bool = True
    cpu_show_max_core: bool = True
    cpu_show_disk_io: bool = True
    cpu_show_page_faults: bool = False
    gpu_show_power_fan: bool = True
    gpu_vram_warn_percent: int = 90

    # Theme & Colors
    theme_name: str = DEFAULT_THEME_NAME
    primary_color: str = THEMES[DEFAULT_THEME_NAME]["primary"]
    secondary_color: str = THEMES[DEFAULT_THEME_NAME]["secondary"]
    temp_color: str = THEMES[DEFAULT_THEME_NAME]["temp"]
    vram_color: str = THEMES[DEFAULT_THEME_NAME]["vram"]
    background_color: str = THEMES[DEFAULT_THEME_NAME]["bg"]
    border_color: str = THEMES[DEFAULT_THEME_NAME]["border"]
    grid_color: str = THEMES[DEFAULT_THEME_NAME]["grid"]
    title_color: str = THEMES[DEFAULT_THEME_NAME]["title"]
    muted_color: str = THEMES[DEFAULT_THEME_NAME]["muted"]

    # Independent Widgets
    widgets: dict[str, WidgetConfig] = field(default_factory=_default_widgets)

    @property
    def ui_scale(self) -> float:
        """Return global UI scaling factor as float (1.0 = 100%)."""
        return max(0.7, min(3.0, self.ui_scale_percent / 100.0))

    def get_widget(self, key: str) -> WidgetConfig:
        """Return WidgetConfig for key, creating defaults if missing."""
        if key not in self.widgets:
            defaults = _default_widgets()
            self.widgets[key] = defaults.get(key, WidgetConfig())
        return self.widgets[key]

    def effective_scale(self, key: str) -> float:
        """Return effective scale factor for a given widget."""
        w = self.get_widget(key)
        pct = w.scale_percent if w.scale_percent is not None else self.ui_scale_percent
        return max(0.7, min(3.0, pct / 100.0))

    def effective_opacity(self, key: str) -> int:
        """Return effective opacity (20..100) for a given widget."""
        w = self.get_widget(key)
        return max(20, min(100, w.opacity if w.opacity is not None else self.opacity))

    def effective_always_on_top(self, key: str) -> bool:
        """Return effective always-on-top flag for a given widget."""
        w = self.get_widget(key)
        return w.always_on_top if w.always_on_top is not None else self.always_on_top

    def effective_locked_pos(self, key: str) -> bool:
        """Return effective locked-position flag for a given widget."""
        w = self.get_widget(key)
        return w.locked_pos if w.locked_pos is not None else self.locked_pos

    def apply_theme(self, theme_name: str) -> None:
        """Apply a named theme preset to the color attributes."""
        theme = THEMES.get(theme_name)
        if not theme:
            return
        self.theme_name = theme_name
        self.primary_color = theme["primary"]
        self.secondary_color = theme["secondary"]
        self.temp_color = theme["temp"]
        self.vram_color = theme["vram"]
        self.background_color = theme["bg"]
        self.border_color = theme["border"]
        self.grid_color = theme["grid"]
        self.title_color = theme["title"]
        self.muted_color = theme["muted"]

    def sanitize(self) -> None:
        """Validate, coerce types and clamp ranges for all configuration attributes."""
        self.refresh_interval_ms = max(500, min(5000, int(self.refresh_interval_ms)))
        self.history_seconds = max(15, min(300, int(self.history_seconds)))
        self.ui_scale_percent = max(70, min(300, int(self.ui_scale_percent)))
        self.opacity = max(20, min(100, int(self.opacity)))
        self.selected_gpu_index = max(0, int(self.selected_gpu_index))
        self.gpu_vram_warn_percent = max(50, min(99, int(self.gpu_vram_warn_percent)))

        defaults = _default_widgets()
        for key, default_wc in defaults.items():
            if key not in self.widgets or not isinstance(self.widgets[key], WidgetConfig):
                self.widgets[key] = default_wc
            self.widgets[key].sanitize(default_wc.width, default_wc.height)

    @classmethod
    def config_path(cls) -> Path:
        """Return the active config.json path."""
        return get_config_dir() / "config.json"

    @classmethod
    def load(cls, path: Path | None = None) -> AppConfig:
        """Load configuration from JSON file or return sanitized defaults."""
        target = path or cls.config_path()
        if not target.is_file():
            cfg = cls()
            cfg.sanitize()
            return cfg

        try:
            raw = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _log_warn(f"[WARN] Konnte config.json nicht laden ({exc}), nutze Defaults.")
            cfg = cls()
            cfg.sanitize()
            return cfg

        cfg = cls()
        for key, value in raw.items():
            if key == "widgets" and isinstance(value, dict):
                loaded_widgets: dict[str, WidgetConfig] = {}
                defaults = _default_widgets()
                for w_key, w_default in defaults.items():
                    w_raw = value.get(w_key)
                    if isinstance(w_raw, dict):
                        valid_fields = {f.name for f in w_default.__dataclass_fields__.values()}
                        filtered = {k: v for k, v in w_raw.items() if k in valid_fields}
                        loaded_widgets[w_key] = WidgetConfig(**filtered)
                    else:
                        loaded_widgets[w_key] = w_default
                cfg.widgets = loaded_widgets
            elif hasattr(cfg, key):
                setattr(cfg, key, value)

        cfg.sanitize()
        return cfg

    def save(self, path: Path | None = None) -> bool:
        """Persist configuration to JSON file."""
        self.sanitize()
        target = path or self.config_path()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            payload = asdict(self)
            target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            return True
        except OSError as exc:
            _log_warn(f"[WARN] Konnte config.json nicht speichern: {exc}")
            return False

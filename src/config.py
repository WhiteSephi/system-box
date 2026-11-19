"""Configuration management and environment variable loader for SystemBox."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from src.themes import DEFAULT_THEME_NAME, THEMES

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$")


def _safe_int(value: object, default: int, low: int | None = None, high: int | None = None) -> int:
    """Safely coerce an integer value (rejecting booleans) and clamp it to optional bounds."""
    if isinstance(value, bool):
        num = default
    else:
        try:
            num = int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            num = default
    if low is not None:
        num = max(low, num)
    if high is not None:
        num = min(high, num)
    return num


def _safe_color(value: object, default: str) -> str:
    """Validate that value is a strict #RRGGBB / #RRGGBBAA hex color to prevent QSS injection."""
    if isinstance(value, str):
        cleaned = value.strip()
        if _HEX_COLOR_RE.fullmatch(cleaned):
            return cleaned.upper()
    return default


def atomic_write_text(target: Path, content: str) -> None:
    """Write UTF-8 text atomically via a temporary file in the same directory and os.replace."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(content)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_path, target)
    except Exception as exc:
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        if isinstance(exc, OSError):
            raise
        raise OSError(str(exc)) from exc


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
        self.width = _safe_int(self.width or default_width, default_width, 140, 1600)
        self.height = _safe_int(self.height or default_height, default_height, 60, 1400)
        self.pos_x = _safe_int(self.pos_x, -1)
        self.pos_y = _safe_int(self.pos_y, -1)
        if self.scale_percent is not None:
            if isinstance(self.scale_percent, bool):
                self.scale_percent = None
            else:
                try:
                    int(self.scale_percent)
                except (TypeError, ValueError):
                    self.scale_percent = None
                else:
                    self.scale_percent = _safe_int(self.scale_percent, 100, 70, 300)
        if self.opacity is not None:
            if isinstance(self.opacity, bool):
                self.opacity = None
            else:
                try:
                    int(self.opacity)
                except (TypeError, ValueError):
                    self.opacity = None
                else:
                    self.opacity = _safe_int(self.opacity, 85, 20, 100)
        if self.always_on_top is not None:
            self.always_on_top = bool(self.always_on_top)
        if self.locked_pos is not None:
            self.locked_pos = bool(self.locked_pos)


def _default_widgets() -> dict[str, WidgetConfig]:
    return {
        "clock": WidgetConfig(enabled=True, width=250, height=185),
        "gpu": WidgetConfig(enabled=True, width=330, height=270),
        "cpu": WidgetConfig(enabled=True, width=330, height=250),
        "storage": WidgetConfig(enabled=True, width=330, height=185),
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
    snap_to_edges: bool = True
    autostart: bool = False
    start_delay_sec: int = 0  # 0..60 s (used with --autostart)

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
    cpu_disk_device: str = ""
    cpu_show_page_faults: bool = False
    gpu_show_power_fan: bool = True
    gpu_show_mem_clock: bool = False
    gpu_show_driver_version: bool = False
    gpu_temp_warn_c: int = 80
    storage_warn_percent: int = 85
    storage_deduplicate_devices: bool = True
    storage_show_free_first: bool = True
    storage_show_boot: bool = False
    storage_hidden_mountpoints: list[str] = field(default_factory=list)

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
        self.refresh_interval_ms = _safe_int(self.refresh_interval_ms, 1000, 500, 5000)
        self.history_seconds = _safe_int(self.history_seconds, 60, 15, 300)
        self.ui_scale_percent = _safe_int(self.ui_scale_percent, 100, 70, 300)
        self.opacity = _safe_int(self.opacity, 85, 20, 100)
        self.always_on_top = bool(self.always_on_top)
        self.locked_pos = bool(self.locked_pos)
        self.snap_to_edges = bool(self.snap_to_edges)
        self.autostart = bool(self.autostart)
        self.start_delay_sec = _safe_int(self.start_delay_sec, 0, 0, 60)

        self.settings_pos_x = _safe_int(self.settings_pos_x, -1)
        self.settings_pos_y = _safe_int(self.settings_pos_y, -1)
        self.settings_width = _safe_int(self.settings_width, 680, 400, 3000)
        self.settings_height = _safe_int(self.settings_height, 540, 300, 2200)

        self.selected_gpu_index = _safe_int(self.selected_gpu_index, 0, 0, None)
        self.clock_show_seconds = bool(self.clock_show_seconds)
        self.clock_show_uptime = bool(self.clock_show_uptime)
        self.clock_24h = bool(self.clock_24h)
        self.cpu_show_max_core = bool(self.cpu_show_max_core)
        self.cpu_show_disk_io = bool(self.cpu_show_disk_io)
        self.cpu_disk_device = self.cpu_disk_device if isinstance(self.cpu_disk_device, str) else ""
        self.cpu_show_page_faults = bool(self.cpu_show_page_faults)
        self.gpu_show_power_fan = bool(self.gpu_show_power_fan)
        self.gpu_show_mem_clock = bool(self.gpu_show_mem_clock)
        self.gpu_show_driver_version = bool(self.gpu_show_driver_version)
        self.gpu_temp_warn_c = _safe_int(self.gpu_temp_warn_c, 80, 50, 105)
        self.storage_warn_percent = _safe_int(self.storage_warn_percent, 85, 50, 99)
        self.storage_deduplicate_devices = bool(self.storage_deduplicate_devices)
        self.storage_show_free_first = bool(self.storage_show_free_first)
        self.storage_show_boot = bool(self.storage_show_boot)
        if not isinstance(self.storage_hidden_mountpoints, list):
            self.storage_hidden_mountpoints = []
        else:
            self.storage_hidden_mountpoints = [
                str(m) for m in self.storage_hidden_mountpoints if isinstance(m, str) and m.strip()
            ]

        self.theme_name = self.theme_name if isinstance(self.theme_name, str) else DEFAULT_THEME_NAME
        theme_defaults = THEMES[DEFAULT_THEME_NAME]
        self.primary_color = _safe_color(self.primary_color, theme_defaults["primary"])
        self.secondary_color = _safe_color(self.secondary_color, theme_defaults["secondary"])
        self.temp_color = _safe_color(self.temp_color, theme_defaults["temp"])
        self.vram_color = _safe_color(self.vram_color, theme_defaults["vram"])
        self.background_color = _safe_color(self.background_color, theme_defaults["bg"])
        self.border_color = _safe_color(self.border_color, theme_defaults["border"])
        self.grid_color = _safe_color(self.grid_color, theme_defaults["grid"])
        self.title_color = _safe_color(self.title_color, theme_defaults["title"])
        self.muted_color = _safe_color(self.muted_color, theme_defaults["muted"])

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

        if not isinstance(raw, dict):
            _log_warn("[WARN] Ungültiges config.json-Format (kein Objekt), nutze Defaults.")
            cfg = cls()
            cfg.sanitize()
            return cfg

        cfg = cls()
        valid_fields = {f.name for f in fields(cls)} - {"widgets"}
        for key, value in raw.items():
            if key == "widgets" and isinstance(value, dict):
                loaded_widgets: dict[str, WidgetConfig] = {}
                defaults = _default_widgets()
                for w_key, w_default in defaults.items():
                    w_raw = value.get(w_key)
                    if isinstance(w_raw, dict):
                        valid_w_fields = {f.name for f in fields(w_default)}
                        filtered = {k: v for k, v in w_raw.items() if k in valid_w_fields}
                        loaded_widgets[w_key] = WidgetConfig(**filtered)
                    else:
                        loaded_widgets[w_key] = w_default
                cfg.widgets = loaded_widgets
            elif key in valid_fields:
                setattr(cfg, key, value)

        cfg.sanitize()
        return cfg

    def save(self, path: Path | None = None) -> bool:
        """Persist configuration to JSON file atomically."""
        self.sanitize()
        target = path or self.config_path()
        try:
            payload = asdict(self)
            atomic_write_text(target, json.dumps(payload, indent=2, ensure_ascii=False))
            return True
        except OSError as exc:
            _log_warn(f"[WARN] Konnte config.json nicht speichern: {exc}")
            return False

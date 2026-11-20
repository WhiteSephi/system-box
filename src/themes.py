"""Curated color themes and palette definitions for SystemBox (aligned with TrafficBox)."""

from __future__ import annotations

THEMES: dict[str, dict[str, str]] = {
    "SystemBox Standard (Gelb & Blau)": {
        "primary": "#4A9EFF",
        "secondary": "#FFEA00",
        "temp": "#FF5252",
        "vram": "#00E676",
        "bg": "#1C2428",
        "border": "#5E616C",
        "grid": "#32383D",
        "title": "#E0E4E8",
        "muted": "#9AA4AE",
    },
    "Cyberpunk Neon (Cyan & Pink)": {
        "primary": "#00E5FF",
        "secondary": "#FF007F",
        "temp": "#FF9100",
        "vram": "#00E676",
        "bg": "#0D1117",
        "border": "#00E5FF",
        "grid": "#21262D",
        "title": "#58A6FF",
        "muted": "#8B949E",
    },
    "Emerald Matrix (Giftgrün & Minze)": {
        "primary": "#00E676",
        "secondary": "#00B0FF",
        "temp": "#FFD600",
        "vram": "#69F0AE",
        "bg": "#0A140F",
        "border": "#1B4D3E",
        "grid": "#132E25",
        "title": "#E8F5E9",
        "muted": "#81C784",
    },
    "Amber Terminal (Bernstein & Graphit)": {
        "primary": "#FFB300",
        "secondary": "#29B6F6",
        "temp": "#FF5252",
        "vram": "#66BB6A",
        "bg": "#181A1F",
        "border": "#4A4E58",
        "grid": "#2A2E37",
        "title": "#F5F7FA",
        "muted": "#9AA0AC",
    },
    "Minimalist Monochrome (Weiß & Grau)": {
        "primary": "#FFFFFF",
        "secondary": "#A3A3A3",
        "temp": "#D4D4D4",
        "vram": "#8C8C8C",
        "bg": "#121212",
        "border": "#404040",
        "grid": "#262626",
        "title": "#F5F5F5",
        "muted": "#A3A3A3",
    },
}

DEFAULT_THEME_NAME = "SystemBox Standard (Gelb & Blau)"

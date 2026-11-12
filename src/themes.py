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
    "FRITZ!Box Classic (AVM Rot & Blau)": {
        "primary": "#0066CC",
        "secondary": "#FFC107",
        "temp": "#E0001B",
        "vram": "#28A745",
        "bg": "#1F2326",
        "border": "#495057",
        "grid": "#343A40",
        "title": "#F8F9FA",
        "muted": "#ADB5BD",
    },
    "Minimalist Monochrome (Weiß & Grau)": {
        "primary": "#FFFFFF",
        "secondary": "#90CAF9",
        "temp": "#FF8A80",
        "vram": "#B0BEC5",
        "bg": "#121212",
        "border": "#37474F",
        "grid": "#263238",
        "title": "#ECEFF1",
        "muted": "#90A4AE",
    },
}

DEFAULT_THEME_NAME = "SystemBox Standard (Gelb & Blau)"

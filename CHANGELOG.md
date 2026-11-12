# Changelog

Alle relevanten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.
Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).

## [0.2.1] - 2026-11-12
### Changed
- Beschriftung im Einstellungs-Dialog von „Transparenz“ auf „Deckkraft“ korrigiert.
- Tab- und Gruppen-Bezeichnungen neutralisiert („Sensoren & Metriken“, „GPU-Metriken“) und `&`-Zeichen in Qt-Labels korrekt escaped (`&&`).

## [0.2.0] - 2026-11-12
### Added
- Zentrale Konfiguration (`src/config.py`) und Theme-Presets (`src/themes.py`) angelehnt an TrafficBox.
- Plattformübergreifendes Sensor-Provider-Pattern (`src/sensors/`): `psutil`, `pynvml` (NVIDIA), Linux `sysfs`/`hwmon`/`drm` sowie Windows PDH/HWiNFO-Fallbacks ohne Admin-Zwang.
- Drei frei verschieb- und skalierbare Desktop-Widgets (`ClockWidget`, `GpuWidget`, `CpuSystemWidget`) inkl. Live-Graphen, Kompaktmodus, Throttle- & VRAM-Warnindikatoren sowie Peak-Core- und Disk-I/O-Metriken.
- Zentraler Einstellungs-Dialog (`src/ui/settings_dlg.py`), System-Tray-Controller (`src/app.py`, `src/ui/tray.py`), Startskripte (`start_linux.sh`, `start_windows.vbs`), `SystemBox.spec` und Unit-Tests.

## [0.1.0] - 2026-11-12
### Added
- Initiales Projekt-Setup aus dem Basis-Template (`WhiteSephi/project-template`) erstellt.
- Projektstruktur, `README.md` und `requirements.txt` für Python 3.11+ / PySide6 vorbereitet.

# Changelog

Alle relevanten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.
Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).

## [0.7.2] - 2026-11-13
### Added
- Multi-Size App-Icon (`assets/app_icon.ico`, 16–256 px) direkt aus dem Vektor-Tray-Icon (`render_systembox_pixmap`) erzeugt und in `SystemBox.spec` für die Windows-`.exe` eingebunden.

## [0.7.1] - 2026-11-12
### Fixed
- Tab `Allgemein` in `SettingsDialog` mit `QScrollArea` und größerer Standardhöhe versehen, damit Gruppen und Checkboxen bei vielen Optionen nicht vertikal zusammengeschoben werden.

## [0.7.0] - 2026-11-12
### Added
- Plattformübergreifende Autostart-Integration (`src/autostart.py`) für Windows (Registry `HKCU\...\Run`) und Linux/KDE (`~/.config/autostart/systembox.desktop`) analog zu TrafficBox.
- Sektion „Systemstart & Autostart“ im Tab `Allgemein` inkl. konfigurierbarer Startverzögerung beim Booten (`0–60 Sek.`, `--autostart`).

## [0.6.0] - 2026-11-12
### Added
- Magnetisches Einrasten (Screen & Widget Snapping) beim Verschieben: Widgets docken automatisch an Bildschirmrändern sowie bündig (oder mit sauberem Abstand) an anderen SystemBox-Widgets an (`snap_to_edges`, abschaltbar im Tab `Allgemein`).

## [0.5.4] - 2026-11-12
### Changed
- Bezeichnung der Einzelkern-Spitzenauslastung im `CPU & System`-Widget und den Einstellungen von `Peak` auf `Max-Kern` geändert.

## [0.5.3] - 2026-11-12
### Changed
- Temperatur-Anzeige (`lbl_temp`) im `GpuWidget` farblich an die Temperatur-Kurve (`temp_color`) angepasst, passend zur farblichen Zuordnung beim Kombi-Graph.

## [0.5.2] - 2026-11-12
### Fixed
- Uhrzeit-Schriftgröße im `ClockWidget` passt sich per `QFontMetricsF` automatisch an die verfügbare Breite an, sodass das 12-Stunden-Format (`AM`/`PM`) nicht mehr abgeschnitten wird.

## [0.5.1] - 2026-11-12
### Removed
- Kompaktmodus („nur Zahlen“) aus den Widgets, dem Kontextmenü, dem Einstellungs-Dialog und der Konfiguration entfernt.

## [0.5.0] - 2026-11-12
### Added
- Kombi-Graph-Unterstützung in `MiniLiveGraphWidget` (zweite Überlagerungs-Kurve im selben Graphen mit gemeinsamer dynamischer/prozentualer Y-Skala).
- GPU-Widget: Leistungsaufnahme (`W / Limit`) farblich hervorgehoben und als zweite Kurve (% des Power-Limits) im Temperatur-Graphen dargestellt.
- CPU & System-Widget: Disk Read und Write als zwei getrennte Kurven im gemeinsamen Disk-I/O-Kombi-Graphen.

## [0.4.0] - 2026-11-12
### Added
- Eigene, optional zuschaltbare `PageFaults/sec`-Sektion mit Live-Graph im `CPU & System`-Widget (Windows `NtQuerySystemInformation` `PageReadIoCount` / Linux `/proc/vmstat` `pgmajfault` ohne Admin-Rechte).
- „Über“-Reiter im Einstellungs-Dialog im TrafficBox-Design (Versions-Badge, GitHub/Releases/Issues/Konfig-Ordner-Buttons, System-Diagnose).

## [0.3.0] - 2026-11-12
### Added
- Eigene Einstellungs-Reiter pro Widget (`Allgemein`, `Uhrzeit & Datum`, `GPU-Monitor`, `CPU & System`, `Design & Themes`, `Über SystemBox`).
- Optionale PageFaults-/Swap-Anzeige neben der RAM-Auslastung im `CPU & System`-Widget (`cpu_show_page_faults`).

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

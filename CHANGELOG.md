# Changelog

Alle relevanten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.
Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).

## [1.0.0] - 2026-11-25
### Added
- **4 frei verschieb- und skalierbare Live-Desktop-Widgets:**
  - **Uhrzeit & Datum (`ClockWidget`):** 24h-/12h-Format, dynamisch skalierter Datums-Block (Tag, Monat, Wochentag, Jahr), Sekunden-Fortschrittsbalken und optionale System-Uptime.
  - **GPU-Monitor (`GpuWidget`):** Live-Auslastung, GPU-/VRAM-Takt, Temperatur, Lüfterdrehzahl (RPM / % inkl. Vektor-Lüftericon), Leistungsaufnahme (Watt vs. Power-Limit als Kombi-Graph), VRAM-Belegung, Temperatur-Warnschwelle, Drosselungs-Indikatoren und optionale Treiberversion.
  - **System (`CpuSystemWidget`):** CPU-Gesamtlast, Max-Kern-Auslastung, Frequenz, CPU-Temperatur, RAM-Auslastung, optionaler PageFaults/sec-Graph sowie kombinierter Disk-I/O-Monitor (Read/Write) mit gezielter Laufwerksauswahl inkl. Modell und Laufwerksbuchstaben.
  - **Modulare System-Visualizer:** Optional umschaltbare Darstellungsformen pro Metrik neben dem Live-Verlaufsgraphen – *Kerne als Balken (Equalizer)*, *Kern-Heatmap-Grid*, *Speicherblöcke* (8/16/32/64er Raster), *Segment-Füllbalken*, *Page-Matrix*, *R/W-Meter (Peak-Hold)* und *Spiegel-Graph (R/W)*.
  - **Datenträger (`StorageWidget`):** Speicherplatz-Übersicht mit Fortschrittsbalken, konfigurierbarer Warnschwelle, Einzel-Ausblendung von Laufwerken, Btrfs-Subvolume-Deduplizierung unter Linux, Windows-Volume-Labels und Doppelklick zum Öffnen im Dateimanager.
- **Plattformübergreifende Sensorik (ohne Admin-Rechte):**
  - Native Unterstützung für **NVIDIA** (`nvidia-ml-py` / NVML), **Linux** (`sysfs`/`hwmon`/`drm`, `/proc/vmstat`) sowie **Windows** (`psutil`, PDH, `NtQuerySystemInformation` & optionales HWiNFO Shared Memory).
- **Desktop-Integration, Themes & Bedienung:**
  - Plattformübergreifend für **Windows 10/11** und **Linux / KDE Plasma** (Wayland/XWayland/X11 inkl. `libX11`/EWMH-Taskleisten-Ausblendung und `fcntl.flock`-gesicherter `kwinrulesrc`-Synchronisation).
  - System-Tray-Menü, magnetisches Einrasten an Bildschirmrändern und anderen Widgets (Edge Snapping), HiDPI-UI-Skalierung (`70–300 %`), kuratierte Farb-Themes mit modernem Color-Picker, plattformübergreifender Autostart (`0–60 s` Startverzögerung) und optionaler Portabel-Modus (`local/config.json`).
- **Sicherheit, Datenschutz & Diagnose:**
  - 100 % lokale Verarbeitung ohne Telemetrie; atomares Speichern (`atomic_write_text`) und strenge Validierung aller Konfigurationswerte gegen fehlerhafte JSON-Strukturen und QSS-Injection.
  - Datensparsames Rotating-File-Logging (`logs/systembox.log`, max. `3 × 1 MB`) mit automatischer Maskierung sensibler Daten (`PrivacyRedactionFilter`) sowie Vorschau-Dialog für anonymisierte GitHub-Fehlerberichte im „Über“-Tab.
- **Open-Source-Release, Tests & Automatisierung:**
  - Veröffentlicht unter der **MIT-Lizenz** (`LICENSE`) mit isolierter `pytest`-Testsuite und `.github/workflows/` für automatische CI-Tests (Linux & Windows) sowie reproduzierbare Windows-Standalone-Releases (`SystemBox.exe` + `SHA256SUMS.txt`).

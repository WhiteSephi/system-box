# Changelog

Alle relevanten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.
Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).

## [0.15.0] - 2026-11-20
### Added
- **Optionale Darstellungsmodi für `CPU & System` (`src/ui/visualizers/`, `src/ui/cpu_widget.py`, `src/config.py`, `src/sensors/models.py`, `src/sensors/psutil_provider.py`):**
  - Standard bleibt überall der Live-Verlaufsgraph (`graph`).
  - **CPU:** `Kerne als Balken (Equalizer)` (`core_bars`) und `Kern-Heatmap-Grid` (`core_heatmap`) auf Basis der Einzelkern-Auslastung (`CpuSystemSample.cpu_cores`).
  - **RAM:** `Speicherblöcke` (`grid_blocks`, automatisch skaliert auf 8/16/32/64 Blöcke je nach installiertem RAM) und `Segment-Füllbalken` (`segmented_bar`).
  - **PageFaults/sec:** `Page-Matrix` (`page_matrix`, aufblitzende und ausglühende Speicherzellen).
  - **Disk I/O:** `R/W-Meter (Peak-Hold)` (`dual_meter`) und `Spiegel-Graph (R/W)` (`mirror_graph`, Read nach oben, Write nach unten).
  - Whitelist-Validierung für `cpu_viz_mode`, `ram_viz_mode`, `pf_viz_mode` und `disk_viz_mode` in `AppConfig`.

### Changed
- **Einheitliche Benennung `System` & kompaktere Gruppe (`src/ui/cpu_widget.py`, `src/app.py`, `src/ui/settings_dlg.py`):**
  - Widget-Titel, Tray-Eintrag und Anzeige-Tab einheitlich auf `System` umbenannt.
  - Neue Gruppe `Darstellung` direkt im `System`-Tab ergänzt.
  - Disk-I/O-Auswahl zeigt nun kompakte Laufwerksnamen inkl. Modell und zugeordneter Laufwerksbuchstaben (`PsutilSystemProvider.list_disk_choices()`).
  - Schriftgrößen von Wochentag-Badge, Monats-Badge und Jahreszahl im Uhrzeit-Widget (`src/ui/clock_widget.py`) skalieren nun proportional zur Box-Größe.

## [0.14.6] - 2026-11-20
### Changed
- **Theme-Auswahl & Monochrome-Palette verfeinert (`src/themes.py`, `src/ui/color_picker.py`, `src/ui/settings_dlg.py`):**
  - Farbpalette `Minimalist Monochrome (Weiß & Grau)` auf reine Weiß-/Grautöne abgestimmt.
  - Separaten Button `Theme anwenden` entfernt; die Auswahl in `cmb_theme` übernimmt die Vorlage direkt in die Farbfelder (Speichern wie gewohnt über `Übernehmen` oder `OK`).
  - `ColorButton` emittiert bei manueller Farbänderung `color_changed`, sodass `cmb_theme` automatisch das passende Preset oder `Benutzerdefiniert` anzeigt.

## [0.14.5] - 2026-11-19
### Changed
- **Einstellungsdialog flexibler skalierbar & „Über“-Tab umgebrochen (`src/ui/settings_dlg.py`):**
  - Mindestgröße des Einstellungsdialogs von `720×520 px` auf `500×420 px` gesenkt, damit sich das Fenster auch schmaler zusammenschieben lässt.
  - Action-Buttons im `Über`-Tab (`GitHub`, `Releases`, `Fehler melden`, `Konfig-Ordner`) als 2×2-`QGridLayout` angeordnet.
  - Alle Info-Labels unter `System-Diagnose & Rechtliches` mit `setWordWrap(True)` und `Expanding`-Größenrichtlinie versehen, damit bei schmalem Fenster nichts rechts abgeschnitten wird.

## [0.14.4] - 2026-11-19
### Changed
- **Einstellungsdialog gestrafft & mit Erklär-Tooltips versehen (`src/ui/settings_dlg.py`):**
  - Lange Checkbox- und Form-Labels über alle Tabs hinweg gekürzt (z. B. `Mit Systemstart automatisch starten`, `Immer im Vordergrund`, `An Rändern & Widgets einrasten`, `24-Stunden-Format`, `Lüfter & Leistung (Watt) anzeigen`, `Max-Kern-Auslastung (%) anzeigen`, `PageFaults/sec-Graph anzeigen`, `Freien Speicher zuerst anzeigen`).
  - Einheitliche, kurze Erklär-Tooltips für sämtliche Optionen, Slider, Farbbuttons, Laufwerks-Checkboxen und Dialog-Aktionsbuttons ergänzt.

## [0.14.3] - 2026-11-19
### Changed
- **Kompakte Einstellungs-Tabs & gebündelter `Anzeige`-Tab (`src/ui/settings_dlg.py`):**
  - Tab-Leiste von 8 auf 7 kompakte Tabs reduziert (`Allgemein`, `Anzeige`, `Uhrzeit`, `GPU`, `System`, `Datenträger`, `Über`), sodass alle Tabs ab `720 px` Breite ohne horizontale Scrollpfeile sichtbar sind.
  - `Anzeige` und `Design & Themes` über eine schlanke Segmented-Umschaltleiste (`Darstellung & Widgets` | `Themes & Farben`) in `Anzeige` zusammengeführt; Direktsprünge über `select_tab("display")` bzw. `select_tab("theme")` wählen direkt die passende Unterseite.
  - Bereich `Abfrage & Verlauf` (`Aktualisierungs-Intervall` und `Graph-Verlaufslänge`) thematisch nach `Allgemein` verschoben.

## [0.14.2] - 2026-11-19
### Fixed
- **Sicherheits- & Stabilitäts-Härtung (`src/config.py`, `src/autostart.py`, `start_windows.vbs`, `src/sensors/disk_space.py`, `src/sensors/psutil_provider.py`, `src/sensors/windows_fallback.py`):**
  - `AppConfig.load()` prüft auf Objekt-Typ (`dict`), nutzt eine explizite Dataclass-Feld-Whitelist statt `hasattr()` und validiert alle Zahlen-, Bool- und Hex-Farbwerte (`_safe_int`, `_safe_color` gegen QSS-Injection).
  - Atomares Speichern via `atomic_write_text()` (Temp-Datei + `fsync` + `os.replace`) für `config.json`, Linux `.desktop` und `~/.config/kwinrulesrc`.
  - Autostart-Kommandos und `start_windows.vbs` escapen Pfade/Argumente sauber (`sys.argv[1]` statt String-Interpolation, Desktop-Entry-Escaping).
  - Explizite 64-Bit-`ctypes`-Signaturen (`argtypes`/`restype`) für `GetVolumeInformationW`, `NtQuerySystemInformation` und `pdh.dll` sowie strikte Größenlimits (`16 MiB`) + Context-Manager für HWiNFO Shared Memory ergänzt.

## [0.14.1] - 2026-11-16
### Changed
- **Einheitliche Benennung `Datenträger` (`src/ui/storage_widget.py`, `src/ui/settings_dlg.py`, `src/app.py`):** Redundantes `Datenträger & Speicher` im Widget-Titel, Tray-Menü, Anzeige-Tab und in der Gruppenüberschrift einheitlich zu `Datenträger` verkürzt.

## [0.14.0] - 2026-11-15
### Added
- **Laufwerke einzeln ausblenden (`src/config.py`, `src/ui/settings_dlg.py`, `src/ui/storage_widget.py`):** Im Einstellungs-Tab `Datenträger` werden jetzt alle erkannten Laufwerke unter `Angezeigte Laufwerke` mit Checkbox aufgelistet, sodass einzelne Laufwerke (z. B. Cloud- oder Netzlaufwerke unter Windows) gezielt abgewählt werden können (`storage_hidden_mountpoints`).

## [0.13.1] - 2026-11-14
### Changed
- **Tab `Datenträger` in den Einstellungen (`src/ui/settings_dlg.py`):** Btrfs-/Windows-Hinweise aus den Checkbox-Texten entfernt, Linux-spezifische Optionen (`Identische Laufwerke zusammenfassen`, `Boot-Partitionen`) nur noch unter Linux eingeblendet und Mindestbreite des Einstellungsfensters auf `720 px` erhöht, damit alle 8 Tabs ohne Scroll-Pfeile passen.

## [0.13.0] - 2026-11-14
### Added
- **4. Widget `Datenträger & Speicher` (`src/sensors/disk_space.py`, `src/ui/storage_widget.py`, `src/sensors/models.py`, `src/sensors/manager.py`, `src/config.py`, `src/app.py`, `src/ui/settings_dlg.py`):**
  - Plattformübergreifende Speicherplatz-Übersicht mit Fortschrittsbalken, Prozentwert, freiem/belegtem Speicher (wie Windows „Dieser PC“) und Doppelklick zum Öffnen im Dateimanager.
  - Intelligente Linux-Filterung & Deduplizierung (Btrfs-Subvolumes `@`/`@home`/`@log` auf demselben Gerät werden auf einen Eintrag zusammengefasst; `/mnt/...` und `/run/media/...` erscheinen mit lesbarem Namen; Pseudo-Dateisysteme und `/boot*` werden optional ausgeblendet).
  - Unter Windows automatische Volume-Label-Erkennung via `GetVolumeInformationW` und Ausblendung leerer optischer Laufwerke.
  - Neuer Tab `Datenträger` in den Einstellungen (Warnschwelle %, Btrfs-Deduplizierung, Anzeigeformat, `/boot`-Anzeige) sowie Tray-Menü-Eintrag.

## [0.12.1] - 2026-11-14
### Changed
- **Modularisierung & Testausbau (`src/ui/color_picker.py`, `src/ui/linux_x11.py`, `src/ui/settings_dlg.py`, `src/ui/base_widget.py`, `tests/test_settings_and_app.py`):**
  - `ModernColorPickerPopup`, `ColorButton` und `make_swatch_icon` aus `settings_dlg.py` nach `src/ui/color_picker.py` ausgelagert.
  - `set_x11_skip_taskbar_libx11` aus `base_widget.py` nach `src/ui/linux_x11.py` ausgelagert.
  - Neue Unit-/Offscreen-Tests für `SettingsDialog`, Kontextmenü, `PsutilSystemProvider` (Per-Disk I/O) und `SystemBoxApp`-Tray-Menü ergänzt.
### Fixed
- **Tray-Menü Escaping (`src/app.py`):** `&`-Zeichen in `Uhrzeit && Datum` und `CPU && System` korrekt für Qt escaped.

## [0.12.0] - 2026-11-14
### Added
- **Laufwerks-Auswahl für Disk I/O (`src/config.py`, `src/sensors/base.py`, `src/sensors/psutil_provider.py`, `src/sensors/manager.py`, `src/app.py`, `src/ui/settings_dlg.py`, `src/ui/cpu_widget.py`):** Im Tab `CPU & System` kann jetzt über `Disk I/O Laufwerk` zwischen `Alle Datenträger (Summe)` (Standard) und einzelnen erkannten physischen Laufwerken (z. B. `nvme0n1`, `nvme1n1`) gewählt werden.

## [0.11.5] - 2026-11-14
### Fixed
- **Watt-Graph im GPU-Widget (`src/sensors/linux_hwmon.py`, `src/ui/gpu_widget.py`):**
  - `LinuxDrmGpuProvider` liest nun optional `power1_cap` / `power1_cap_default` aus `hwmon` als `power_limit_watts` aus.
  - Fehlt `power_limit_watts` (z. B. bei APUs/iGPUs ohne `power1_cap`), nutzt `GpuWidget` einen dynamischen Fallback (`max(30.0, observed_max * 1.2)`), sodass die sekundäre Watt-Kurve im Temperatur-/Power-Graph nun immer gezeichnet wird.

## [0.11.4] - 2026-11-14
### Changed
- **Theme-Auswahl & Vorlagen (`src/themes.py`, `src/ui/settings_dlg.py`):**
  - Unpassende `FRITZ!Box Classic`-Vorlage durch `Amber Terminal (Bernstein & Graphit)` ersetzt.
  - Auswahl eines Themes im Dropdown (`cmb_theme.activated`) aktualisiert die Farbfelder sofort zur Vorschau; ein Klick auf `Theme anwenden` speichert und übernimmt das Theme direkt live auf alle Widgets.

## [0.11.3] - 2026-11-14
### Changed
- **Widget-Kontextmenü an TrafficBox angeglichen (`src/ui/base_widget.py`):** Reihenfolge und Beschriftung der Einträge vereinheitlicht (`Einstellungen...`, `Immer im Vordergrund`, `Position sperren`, `Widget ausblenden`, `Über SystemBox...`, `Beenden`). Dadurch entfällt auch das fehlende `&`-Mnemonic-Problem bei `CPU & System ausblenden`.

## [0.11.2] - 2026-11-14
### Fixed
- **Hardware-Zeile im `Über`-Tab (`src/ui/settings_dlg.py`):** `FieldGrowthPolicy.ExpandingFieldsGrow` für das Diagnose-`QFormLayout` sowie `QSizePolicy(Expanding, Preferred)` und Maus-Textauswahl für das Hardware-`QLabel` gesetzt, sodass umgebrochene GPU-Bezeichnungen nicht mehr vertikal abgeschnitten werden.

## [0.11.1] - 2026-11-13
### Fixed
- **Linux-Taskleiste (`src/ui/base_widget.py`, `src/autostart.py`, `src/main.py`):**
  - In `BaseDesktopWidget.showEvent()` wird nun über `_apply_x11_skip_taskbar()` direkt per `libX11.so.6` (`XChangeProperty` + `_NET_WM_STATE_ADD` `XSendEvent`, mit `xprop` als Fallback) das EWMH-Atom `_NET_WM_STATE_SKIP_TASKBAR, _NET_WM_STATE_SKIP_PAGER` auf die X11/XWayland-Window-ID gesetzt.
  - Analog zu TrafficBox trägt `sync_kwin_skip_taskbar_rule()` beim Start unter Linux automatisch eine KWin-Fensterregel (`[SystemBox-Taskbar]` mit `skiptaskbar=true`, `skiptaskbarrule=2`, `skipswitcher=true`, `skipswitcherrule=2`, `wmclass=.*[Ss]ystem[Bb]ox.*`) in `~/.config/kwinrulesrc` ein und lädt KWin per `qdbus6`/`qdbus` neu, sodass die Widgets unter KDE Plasma (Wayland & XWayland) zuverlässig aus Taskleiste und Alt+Tab verschwinden.

## [0.11.0] - 2026-11-13
### Added
- **Optionale GPU-Treiberinfos (`src/sensors/models.py`, `src/sensors/nvidia_provider.py`, `src/sensors/linux_hwmon.py`, `src/config.py`, `src/ui/settings_dlg.py`, `src/ui/gpu_widget.py`):** Im Tab `GPU-Monitor` lassen sich jetzt optional `VRAM-Takt (MHz) anzeigen` (`gpu_show_mem_clock`, Standard `False`) und `Treiberversion im Header anzeigen` (`gpu_show_driver_version`, Standard `False`) aktivieren.

## [0.10.0] - 2026-11-13
### Changed
- **GPU-Temperatur-Warnschwelle statt VRAM-Warnschwelle (`src/config.py`, `src/ui/settings_dlg.py`, `src/ui/gpu_widget.py`):** `gpu_vram_warn_percent` durch `gpu_temp_warn_c` (Standard `80 °C`, Bereich `50–105 °C`) ersetzt. Ab Erreichen des Schwellenwerts zeigt das GPU-Widget oben im Header ein deutliches Warn-Badge (`TEMP XX°C`, ggf. kombiniert mit aktiven Drosselungsgründen) inklusive Tooltip.

## [0.9.1] - 2026-11-13
### Fixed
- **Versionsanzeige im `Über`-Tab (`src/__init__.py`):** `__version__` auf den aktuellen Stand (`0.9.1`) aktualisiert, damit im `Über`-Tab der Einstellungen immer die korrekte Version angezeigt wird.

## [0.9.0] - 2026-11-13
### Added
- **Header-Zahnrad-Button für GPU & CPU (`src/ui/base_widget.py`, `src/ui/gpu_widget.py`, `src/ui/cpu_widget.py`, `src/ui/settings_dlg.py`, `src/app.py`):** GPU- und CPU-Widget zeigen oben rechts ein vektorbasiert gezeichnetes Zahnrad-Symbol (analog zu TrafficBox), das beim Klick direkt den passenden Einstellungs-Tab (`GPU-Monitor` bzw. `CPU & System`) öffnet.

## [0.8.2] - 2026-11-13
### Fixed
- **GPU-Leistungslinie im Graphen (`src/ui/graph_canvas.py`, `src/ui/gpu_widget.py`):** Wenn „Lüfter (RPM/%) und Leistungsaufnahme (Watt) anzeigen“ deaktiviert ist, wird nun über `set_secondary_enabled(False)` auch die gelbe Leistungslinie aus dem Temperatur-Graphen entfernt.

## [0.8.1] - 2026-11-13
### Changed
- **Einstellungen-Feinschliff (`src/ui/settings_dlg.py`):**
  - `UI-Skalierung` mit diskreten 5%-Stufen (Slider `14..60`, Tickmarks), `SpinBox` (`70–300%`) und `100% (Standard)`-Button an TrafficBox angeglichen; Einzel-Widget-Skalierung ebenfalls mit `5%`-Schritten.
  - Alle 7 Tabs in `QScrollArea` (`_wrap_in_scroll`) eingewickelt sowie Monitor-Bounds-Prüfung (`_restore_geometry`) und Geometrie-Speicherung bei `closeEvent`/`hideEvent` ergänzt.

## [0.8.0] - 2026-11-13
### Added
- **Neuer Tab `Anzeige` (`src/ui/settings_dlg.py`):** Globale Skalierung, Deckkraft, einzelne Desktop-Widgets sowie Abfrage/Verlauf in einen eigenen `Anzeige`-Tab ausgelagert; `Allgemein` enthält nun einheitlich `Systemstart & Autostart` und `Fenster-Verhalten & Position`.
- **`Reset (Standardwerte)`:** Button zum Zurücksetzen aller Einstellungen auf die `AppConfig`-Standardwerte ergänzt.

### Changed
- **Farben & Themes an TrafficBox angeglichen:** `ModernColorPickerPopup` (Palette-Grid, Live-Hex-Eingabe + erweiterter System-Farbwähler) und 2-Spalten-Layout (`Graphen & Metriken` | `Widget Design`) übernommen.

## [0.7.8] - 2026-11-13
### Fixed
- **Live-Resize-Neuberechnung (`src/ui/gpu_widget.py`):** Breite in `_apply_row2_responsive()` direkt aus `self.width()` statt verzögertem `_sec_temp.width()` berechnet und `_fan_box` mit `QSizePolicy.Fixed` + `invalidate()` versehen, sodass beim Verkleinern nichts mehr abgeschnitten wird.
- **Unit-Tests (`tests/test_widgets.py`):** `test_widget_extreme_sizes_no_overlap_or_clipping` prüft alle Widgets bei Minimal- und Maximalgröße auf Überlappungen und Text-Clipping.

## [0.7.7] - 2026-11-13
### Fixed
- **Responsives GPU-Layout (`src/ui/gpu_widget.py`):** Zeile 2 (Temp/Lüfter/Leistung) blendet bei schmaler Widget-Breite automatisch schrittweise optionale Details aus (`(31%)` → `max <Limit> /` → `RPM`-Text), sodass bei zentriertem Lüfter nichts mehr überlappt oder abgeschnitten wird.

## [0.7.6] - 2026-11-13
### Changed
- **GPU-Widget Feinschliff (`src/ui/gpu_widget.py`):** Lüfter-Block (`_fan_box`) über symmetrische `Ignored`-Container links und rechts exakt auf die horizontale Widget-Mitte zentriert; Leistungsanzeige kompakter als `max <Limit> / <Aktuell> W` formatiert.

## [0.7.5] - 2026-11-13
### Changed
- **Binary-Größe reduziert (`SystemBox.spec`):** Windows-Pfadnormalisierung (`\` → `/`) für den `PySide6/translations`-Filter korrigiert (inkl. Ausschluss von `qt_help_*`) sowie ungenutzte Qt-Plugins (`qpdf.dll`, `qwebp.dll`, `qtiff.dll`, `qsvg.dll`, `qsvgicon.dll`, `qtuiotouchplugin.dll` u. a.) entfernt. `SystemBox.exe` schrumpft dadurch von `25,87 MB` auf `23,01 MB`.

## [0.7.4] - 2026-11-13
### Fixed
- **PageFaults/sec-Skalierung (`src/ui/graph_canvas.py`, `src/ui/cpu_widget.py`):** Dynamische Y-Achsen-Skalierung (`dynamic_scale=True`, `min_ceiling=128.0`) über den gesamten sichtbaren Verlauf aktiviert. Zuvor wurde das Maximum nach einem Spike sofort wieder auf `128` zurückgesetzt, wodurch vorherige Spitzenwerte im Graphen oben abgeschnitten wurden.

## [0.7.3] - 2026-11-13
### Changed
- **GPU-Widget (`src/ui/gpu_widget.py`):** Lüfterdrehzahl (`RPM`) mittig zwischen Temperatur (links) und Leistung (rechts) zentriert und mit einem eigenen vektorbasierten 3-Blatt-Lüftericon (`FanIconWidget` via `QPainter`) versehen.
- **GPU-Leistungsanzeige:** Max.-Leistung (`max <N> W`) dezent in Grau weiter Richtung Mitte und aktuelle Leistung (`<N> W`) farbig ganz rechts außen platziert.
- **Optik & Konsistenz:** Dezente 1-px-Header-Trennlinie im GPU- und CPU-Widget ergänzt sowie Prozentangaben in beiden Widgets einheitlich ohne Leerzeichen (`%`) formatiert.

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

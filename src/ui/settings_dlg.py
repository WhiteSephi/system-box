"""Central Settings Dialog for SystemBox (aligned with TrafficBox look & feel)."""

from __future__ import annotations

from collections.abc import Callable
import platform
import sys

from PySide6.QtCore import Qt, QUrl, qVersion
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src import __version__
from src.config import AppConfig
from src.sensors.models import GpuInfo
from src.themes import THEMES
from src.ui.tray import create_systembox_icon


class ColorButton(QPushButton):
    """Compact button displaying a color swatch and opening QColorDialog on click."""

    def __init__(self, hex_color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._hex_color = hex_color
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(26)
        self.setMinimumWidth(96)
        self.clicked.connect(self._pick_color)
        self._update_style()

    @property
    def hex_color(self) -> str:
        return self._hex_color

    @hex_color.setter
    def hex_color(self, value: str) -> None:
        self._hex_color = value
        self._update_style()

    def _update_style(self) -> None:
        col = QColor(self._hex_color)
        text_col = "#000000" if col.lightness() > 140 else "#FFFFFF"
        self.setText(self._hex_color.upper())
        self.setStyleSheet(
            f"background-color: {self._hex_color}; color: {text_col}; "
            "border: 1px solid #5E616C; border-radius: 4px; font-weight: bold;"
        )

    def _pick_color(self) -> None:
        chosen = QColorDialog.getColor(QColor(self._hex_color), self, "Farbe wählen")
        if chosen.isValid():
            self.hex_color = chosen.name().upper()


class SettingsDialog(QDialog):
    """Tabbed settings dialog for widgets, sensors, scaling and themes."""

    def __init__(
        self,
        config: AppConfig,
        gpus: list[GpuInfo],
        on_apply: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self._gpus = gpus
        self._on_apply = on_apply

        self.setWindowTitle("SystemBox Einstellungen")
        self.setWindowIcon(create_systembox_icon(self.config.primary_color))
        self.setMinimumSize(620, 480)
        self.resize(self.config.settings_width, self.config.settings_height)
        if self.config.settings_pos_x >= 0 and self.config.settings_pos_y >= 0:
            self.move(self.config.settings_pos_x, self.config.settings_pos_y)

        self._build_ui()
        self._load_from_config()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self.tabs.addTab(self._build_general_tab(), "Allgemein")
        self.tabs.addTab(self._build_clock_tab(), "Uhrzeit && Datum")
        self.tabs.addTab(self._build_gpu_tab(), "GPU-Monitor")
        self.tabs.addTab(self._build_cpu_tab(), "CPU && System")
        self.tabs.addTab(self._build_theme_tab(), "Design && Themes")
        self.tabs.addTab(self._build_about_tab(), "Über")

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_apply = QPushButton("Übernehmen")
        btn_apply.clicked.connect(self._apply_changes)
        btn_ok = QPushButton("OK")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self._accept_changes)
        btn_cancel = QPushButton("Abbrechen")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_apply)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        root.addLayout(btn_row)

    def _build_general_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        # Global appearance
        grp_global = QGroupBox("Globale Darstellung && Verhalten")
        form = QFormLayout(grp_global)

        scale_row = QHBoxLayout()
        self.sld_scale = QSlider(Qt.Orientation.Horizontal)
        self.sld_scale.setRange(70, 300)
        self.sld_scale.setSingleStep(5)
        self.lbl_scale_val = QLabel("100 %")
        self.lbl_scale_val.setMinimumWidth(48)
        self.sld_scale.valueChanged.connect(lambda v: self.lbl_scale_val.setText(f"{v} %"))
        scale_row.addWidget(self.sld_scale, 1)
        scale_row.addWidget(self.lbl_scale_val)
        form.addRow("Globale Skalierung:", scale_row)

        op_row = QHBoxLayout()
        self.sld_opacity = QSlider(Qt.Orientation.Horizontal)
        self.sld_opacity.setRange(20, 100)
        self.lbl_opacity_val = QLabel("85 %")
        self.lbl_opacity_val.setMinimumWidth(48)
        self.sld_opacity.valueChanged.connect(lambda v: self.lbl_opacity_val.setText(f"{v} %"))
        op_row.addWidget(self.sld_opacity, 1)
        op_row.addWidget(self.lbl_opacity_val)
        form.addRow("Deckkraft:", op_row)

        self.chk_always_on_top = QCheckBox("Alle Widgets immer im Vordergrund halten")
        self.chk_locked_pos = QCheckBox("Positionen aller Widgets sperren")
        form.addRow("", self.chk_always_on_top)
        form.addRow("", self.chk_locked_pos)
        layout.addWidget(grp_global)

        # Per-widget toggles & compact mode
        grp_widgets = QGroupBox("Einzelne Desktop-Widgets")
        w_form = QFormLayout(grp_widgets)

        self._widget_checks: dict[str, tuple[QCheckBox, QCheckBox, QSpinBox]] = {}
        for key, label in (("clock", "Uhrzeit & Datum"), ("gpu", "GPU-Monitor"), ("cpu", "CPU & System")):
            row = QHBoxLayout()
            chk_en = QCheckBox("Aktiv")
            chk_cmp = QCheckBox("Kompaktmodus (nur Zahlen)")
            spn_sc = QSpinBox()
            spn_sc.setRange(0, 300)
            spn_sc.setSpecialValueText("Global")
            spn_sc.setSuffix(" %")
            spn_sc.setToolTip("Individuelle Skalierung (0 = Global übernehmen)")
            row.addWidget(chk_en)
            row.addWidget(chk_cmp)
            row.addStretch(1)
            row.addWidget(QLabel("Skalierung:"))
            row.addWidget(spn_sc)
            w_form.addRow(f"{label}:", row)
            self._widget_checks[key] = (chk_en, chk_cmp, spn_sc)

        layout.addWidget(grp_widgets)

        grp_poll = QGroupBox("Abfrage && Verlauf")
        p_form = QFormLayout(grp_poll)
        self.spn_interval = QSpinBox()
        self.spn_interval.setRange(500, 5000)
        self.spn_interval.setSingleStep(250)
        self.spn_interval.setSuffix(" ms")
        p_form.addRow("Aktualisierungs-Intervall:", self.spn_interval)

        self.spn_history = QSpinBox()
        self.spn_history.setRange(15, 300)
        self.spn_history.setSuffix(" Samples")
        p_form.addRow("Graph-Verlaufslänge:", self.spn_history)
        layout.addWidget(grp_poll)

        layout.addStretch(1)
        return tab

    def _build_clock_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        grp_clk = QGroupBox("Anzeige-Optionen (Uhrzeit && Datum)")
        c_form = QFormLayout(grp_clk)
        self.chk_clock_24h = QCheckBox("24-Stunden-Format verwenden")
        self.chk_clock_sec = QCheckBox("Sekunden-Fortschrittsbalken anzeigen")
        self.chk_clock_uptime = QCheckBox("System-Uptime anzeigen")
        c_form.addRow("", self.chk_clock_24h)
        c_form.addRow("", self.chk_clock_sec)
        c_form.addRow("", self.chk_clock_uptime)
        layout.addWidget(grp_clk)
        layout.addStretch(1)
        return tab

    def _build_gpu_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        grp_gpu = QGroupBox("GPU-Sensorik && Anzeige")
        g_form = QFormLayout(grp_gpu)
        self.cmb_gpu = QComboBox()
        if self._gpus:
            for g in self._gpus:
                self.cmb_gpu.addItem(f"[{g.index}] {g.name} ({g.backend})", g.index)
        else:
            self.cmb_gpu.addItem("Keine GPU erkannt", 0)
        g_form.addRow("Aktive GPU:", self.cmb_gpu)

        self.chk_gpu_power_fan = QCheckBox("Lüfter (RPM/%) und Leistungsaufnahme (Watt) anzeigen")
        g_form.addRow("", self.chk_gpu_power_fan)

        self.spn_vram_warn = QSpinBox()
        self.spn_vram_warn.setRange(50, 99)
        self.spn_vram_warn.setSuffix(" %")
        g_form.addRow("VRAM-Warnschwelle:", self.spn_vram_warn)
        layout.addWidget(grp_gpu)
        layout.addStretch(1)
        return tab

    def _build_cpu_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        grp_cpu = QGroupBox("CPU, RAM && System-Metriken")
        c_form = QFormLayout(grp_cpu)
        self.chk_cpu_max_core = QCheckBox("Peak-Kern-Auslastung anzeigen (höchster Einzelkern)")
        self.chk_cpu_page_faults = QCheckBox("PageFaults/sec (Hard Page Faults) Graph anzeigen")
        self.chk_cpu_disk = QCheckBox("Disk I/O (Lesen/Schreiben MB/s) anzeigen")
        c_form.addRow("", self.chk_cpu_max_core)
        c_form.addRow("", self.chk_cpu_page_faults)
        c_form.addRow("", self.chk_cpu_disk)
        layout.addWidget(grp_cpu)
        layout.addStretch(1)
        return tab

    def _build_theme_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        grp_preset = QGroupBox("Theme-Schnellauswahl (wie TrafficBox)")
        p_row = QHBoxLayout(grp_preset)
        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems(list(THEMES.keys()))
        btn_theme = QPushButton("Theme anwenden")
        btn_theme.clicked.connect(self._apply_preset_theme)
        p_row.addWidget(QLabel("Vorlage:"))
        p_row.addWidget(self.cmb_theme, 1)
        p_row.addWidget(btn_theme)
        layout.addWidget(grp_preset)

        grp_colors = QGroupBox("Individuelle Farben")
        c_form = QFormLayout(grp_colors)
        self.btn_col_primary = ColorButton(self.config.primary_color)
        self.btn_col_secondary = ColorButton(self.config.secondary_color)
        self.btn_col_temp = ColorButton(self.config.temp_color)
        self.btn_col_vram = ColorButton(self.config.vram_color)
        self.btn_col_bg = ColorButton(self.config.background_color)
        self.btn_col_border = ColorButton(self.config.border_color)
        self.btn_col_grid = ColorButton(self.config.grid_color)
        self.btn_col_title = ColorButton(self.config.title_color)
        self.btn_col_muted = ColorButton(self.config.muted_color)

        c_form.addRow("Primär-Graph (GPU/CPU):", self.btn_col_primary)
        c_form.addRow("Sekundär-Graph (RAM):", self.btn_col_secondary)
        c_form.addRow("Temperatur / Warnung / Monat:", self.btn_col_temp)
        c_form.addRow("VRAM / Disk / Wochentag:", self.btn_col_vram)
        c_form.addRow("Hintergrund:", self.btn_col_bg)
        c_form.addRow("Rahmen:", self.btn_col_border)
        c_form.addRow("Raster (Grid):", self.btn_col_grid)
        c_form.addRow("Titel & Hauptwerte:", self.btn_col_title)
        c_form.addRow("Sekundärtext:", self.btn_col_muted)
        layout.addWidget(grp_colors)

        layout.addStretch(1)
        return tab

    def _build_about_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        repo_url = "https://github.com/WhiteSephi/system-box"
        releases_url = f"{repo_url}/releases"
        issues_url = f"{repo_url}/issues"

        # Group 1: Über SystemBox (analog TrafficBox)
        grp_about = QGroupBox("Über SystemBox")
        about_layout = QVBoxLayout(grp_about)
        about_layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)
        lbl_icon = QLabel()
        lbl_icon.setPixmap(create_systembox_icon(self.config.primary_color).pixmap(44, 44))
        lbl_icon.setFixedSize(48, 48)
        top_row.addWidget(lbl_icon, 0, Qt.AlignmentFlag.AlignTop)

        info_col = QVBoxLayout()
        info_col.setSpacing(3)
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        lbl_name = QLabel("<b style='font-size: 14pt;'>SystemBox</b>")
        lbl_ver = QLabel(f"v{__version__}")
        lbl_ver.setStyleSheet(
            f"color: {self.config.primary_color}; border: 1px solid {self.config.primary_color}; "
            "border-radius: 5px; padding: 1px 7px; font-weight: bold;"
        )
        title_row.addWidget(lbl_name)
        title_row.addWidget(lbl_ver)
        title_row.addStretch(1)
        info_col.addLayout(title_row)

        lbl_desc = QLabel(
            "Schlankes Live-Desktop-Widget-System für Uhrzeit/Datum, GPU- und CPU/System-Metriken."
        )
        lbl_desc.setWordWrap(True)
        info_col.addWidget(lbl_desc)
        top_row.addLayout(info_col, 1)
        about_layout.addLayout(top_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        for text, url in (
            ("🌐 GitHub", repo_url),
            ("🚀 Releases", releases_url),
            ("🐛 Fehler melden", issues_url),
        ):
            btn = QPushButton(text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, u=url: QDesktopServices.openUrl(QUrl(u)))
            btn_row.addWidget(btn)

        btn_cfg = QPushButton("📁 Konfig-Ordner")
        btn_cfg.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cfg.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(AppConfig.config_path().parent)))
        )
        btn_row.addWidget(btn_cfg)
        about_layout.addLayout(btn_row)
        layout.addWidget(grp_about)

        # Group 2: System-Diagnose & Rechtliches
        grp_diag = QGroupBox("System-Diagnose && Rechtliches")
        d_form = QFormLayout(grp_diag)
        d_form.setVerticalSpacing(6)

        mode_str = "Binary" if getattr(sys, "frozen", False) else "Quellcode"
        os_str = f"{platform.system()} {platform.release()} ({platform.machine()})"
        runtime_str = f"{os_str} • Python {platform.python_version()} • Qt {qVersion()} • {mode_str}"
        d_form.addRow("Laufzeit:", QLabel(runtime_str))

        cfg_dir = AppConfig.config_path().parent
        loc_str = f"Portabel ({cfg_dir})" if cfg_dir.name == "local" else f"Systemprofil ({cfg_dir})"
        lbl_loc = QLabel(loc_str)
        lbl_loc.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        d_form.addRow("Speicherort:", lbl_loc)

        gpu_str = ", ".join(f"[{g.index}] {g.name} ({g.backend})" for g in self._gpus) or "Keine dedizierte GPU erkannt"
        lbl_gpu = QLabel(gpu_str)
        lbl_gpu.setWordWrap(True)
        d_form.addRow("Hardware:", lbl_gpu)

        d_form.addRow("Hinweise:", QLabel("Open Source (MIT) • 100 % lokal ohne Telemetrie"))
        layout.addWidget(grp_diag)

        layout.addStretch(1)
        return tab

    def _apply_preset_theme(self) -> None:
        name = self.cmb_theme.currentText()
        theme = THEMES.get(name)
        if not theme:
            return
        self.btn_col_primary.hex_color = theme["primary"]
        self.btn_col_secondary.hex_color = theme["secondary"]
        self.btn_col_temp.hex_color = theme["temp"]
        self.btn_col_vram.hex_color = theme["vram"]
        self.btn_col_bg.hex_color = theme["bg"]
        self.btn_col_border.hex_color = theme["border"]
        self.btn_col_grid.hex_color = theme["grid"]
        self.btn_col_title.hex_color = theme["title"]
        self.btn_col_muted.hex_color = theme["muted"]

    def _load_from_config(self) -> None:
        self.sld_scale.setValue(self.config.ui_scale_percent)
        self.sld_opacity.setValue(self.config.opacity)
        self.chk_always_on_top.setChecked(self.config.always_on_top)
        self.chk_locked_pos.setChecked(self.config.locked_pos)

        for key, (chk_en, chk_cmp, spn_sc) in self._widget_checks.items():
            wc = self.config.get_widget(key)
            chk_en.setChecked(wc.enabled)
            chk_cmp.setChecked(wc.compact_mode)
            spn_sc.setValue(wc.scale_percent if wc.scale_percent is not None else 0)

        self.spn_interval.setValue(self.config.refresh_interval_ms)
        self.spn_history.setValue(self.config.history_seconds)

        idx = self.cmb_gpu.findData(self.config.selected_gpu_index)
        if idx >= 0:
            self.cmb_gpu.setCurrentIndex(idx)

        self.chk_gpu_power_fan.setChecked(self.config.gpu_show_power_fan)
        self.spn_vram_warn.setValue(self.config.gpu_vram_warn_percent)
        self.chk_cpu_max_core.setChecked(self.config.cpu_show_max_core)
        self.chk_cpu_page_faults.setChecked(self.config.cpu_show_page_faults)
        self.chk_cpu_disk.setChecked(self.config.cpu_show_disk_io)
        self.chk_clock_sec.setChecked(self.config.clock_show_seconds)
        self.chk_clock_uptime.setChecked(self.config.clock_show_uptime)
        self.chk_clock_24h.setChecked(self.config.clock_24h)

        t_idx = self.cmb_theme.findText(self.config.theme_name)
        if t_idx >= 0:
            self.cmb_theme.setCurrentIndex(t_idx)

    def _save_to_config(self) -> None:
        self.config.ui_scale_percent = self.sld_scale.value()
        self.config.opacity = self.sld_opacity.value()
        self.config.always_on_top = self.chk_always_on_top.isChecked()
        self.config.locked_pos = self.chk_locked_pos.isChecked()

        for key, (chk_en, chk_cmp, spn_sc) in self._widget_checks.items():
            wc = self.config.get_widget(key)
            wc.enabled = chk_en.isChecked()
            wc.compact_mode = chk_cmp.isChecked()
            sc_val = spn_sc.value()
            wc.scale_percent = sc_val if sc_val >= 70 else None

        self.config.refresh_interval_ms = self.spn_interval.value()
        self.config.history_seconds = self.spn_history.value()
        self.config.selected_gpu_index = int(self.cmb_gpu.currentData() or 0)
        self.config.gpu_show_power_fan = self.chk_gpu_power_fan.isChecked()
        self.config.gpu_vram_warn_percent = self.spn_vram_warn.value()
        self.config.cpu_show_max_core = self.chk_cpu_max_core.isChecked()
        self.config.cpu_show_page_faults = self.chk_cpu_page_faults.isChecked()
        self.config.cpu_show_disk_io = self.chk_cpu_disk.isChecked()
        self.config.clock_show_seconds = self.chk_clock_sec.isChecked()
        self.config.clock_show_uptime = self.chk_clock_uptime.isChecked()
        self.config.clock_24h = self.chk_clock_24h.isChecked()

        self.config.theme_name = self.cmb_theme.currentText()
        self.config.primary_color = self.btn_col_primary.hex_color
        self.config.secondary_color = self.btn_col_secondary.hex_color
        self.config.temp_color = self.btn_col_temp.hex_color
        self.config.vram_color = self.btn_col_vram.hex_color
        self.config.background_color = self.btn_col_bg.hex_color
        self.config.border_color = self.btn_col_border.hex_color
        self.config.grid_color = self.btn_col_grid.hex_color
        self.config.title_color = self.btn_col_title.hex_color
        self.config.muted_color = self.btn_col_muted.hex_color

        self.config.settings_pos_x = self.x()
        self.config.settings_pos_y = self.y()
        self.config.settings_width = self.width()
        self.config.settings_height = self.height()
        self.config.save()

    def _apply_changes(self) -> None:
        self._save_to_config()
        self._on_apply()

    def _accept_changes(self) -> None:
        self._apply_changes()
        self.accept()

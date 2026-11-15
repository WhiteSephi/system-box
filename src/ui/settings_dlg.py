"""Central Settings Dialog for SystemBox (aligned with TrafficBox look & feel)."""

from __future__ import annotations

from collections.abc import Callable
import platform
import sys

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QUrl, qVersion
from PySide6.QtGui import QCloseEvent, QDesktopServices, QHideEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src import __version__
from src.autostart import is_autostart_enabled, set_autostart
from src.config import AppConfig
from src.sensors.models import GpuInfo
from src.themes import THEMES
from src.ui.color_picker import ColorButton
from src.ui.tray import create_systembox_icon


class SettingsDialog(QDialog):
    """Tabbed settings dialog for widgets, sensors, scaling and themes."""

    TAB_KEYS = {
        "general": 0,
        "display": 1,
        "clock": 2,
        "gpu": 3,
        "cpu": 4,
        "storage": 5,
        "theme": 6,
        "about": 7,
    }

    def __init__(
        self,
        config: AppConfig,
        gpus: list[GpuInfo],
        on_apply: Callable[[], None],
        parent: QWidget | None = None,
        initial_tab: str = "",
        disks: list[str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self._gpus = gpus
        self._disks = list(disks) if disks is not None else []
        self._on_apply = on_apply

        self.setWindowTitle("SystemBox Einstellungen")
        self.setWindowIcon(create_systembox_icon(self.config.primary_color))
        self.setMinimumSize(720, 520)

        self._build_ui()
        self._restore_geometry()
        self._load_from_config()
        if initial_tab:
            self.select_tab(initial_tab)

    def select_tab(self, tab_key: str) -> None:
        """Switch to the tab matching a widget or section key."""
        idx = self.TAB_KEYS.get(tab_key)
        if idx is not None and 0 <= idx < self.tabs.count():
            self.tabs.setCurrentIndex(idx)

    def _restore_geometry(self) -> None:
        """Restore window position and size if valid on current screens."""
        cfg_w = max(680, self.config.settings_width)
        cfg_h = max(620, self.config.settings_height)
        self.resize(cfg_w, cfg_h)

        if self.config.settings_pos_x >= 0 and self.config.settings_pos_y >= 0:
            target_pt = QPoint(self.config.settings_pos_x, self.config.settings_pos_y)
            target_rect = QRect(target_pt, QSize(cfg_w, cfg_h))
            for screen in QApplication.screens():
                if screen.availableGeometry().intersects(target_rect):
                    self.move(target_pt)
                    return

        primary = QApplication.primaryScreen()
        if primary:
            avail = primary.availableGeometry()
            self.move(
                avail.x() + max(0, (avail.width() - cfg_w) // 2),
                avail.y() + max(0, (avail.height() - cfg_h) // 2),
            )

    def _save_geometry_to_config(self) -> None:
        self.config.settings_pos_x = self.x()
        self.config.settings_pos_y = self.y()
        self.config.settings_width = self.width()
        self.config.settings_height = self.height()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self._save_geometry_to_config()
        self.config.save()
        super().closeEvent(event)

    def hideEvent(self, event: QHideEvent) -> None:  # noqa: N802
        self._save_geometry_to_config()
        super().hideEvent(event)

    @staticmethod
    def _wrap_in_scroll(widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(widget)
        return scroll

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self.tabs.addTab(self._wrap_in_scroll(self._build_general_tab()), "Allgemein")
        self.tabs.addTab(self._wrap_in_scroll(self._build_display_tab()), "Anzeige")
        self.tabs.addTab(self._wrap_in_scroll(self._build_clock_tab()), "Uhrzeit && Datum")
        self.tabs.addTab(self._wrap_in_scroll(self._build_gpu_tab()), "GPU-Monitor")
        self.tabs.addTab(self._wrap_in_scroll(self._build_cpu_tab()), "CPU && System")
        self.tabs.addTab(self._wrap_in_scroll(self._build_storage_tab()), "Datenträger")
        self.tabs.addTab(self._wrap_in_scroll(self._build_theme_tab()), "Design && Themes")
        self.tabs.addTab(self._wrap_in_scroll(self._build_about_tab()), "Über")

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_reset = QPushButton("Reset (Standardwerte)")
        btn_reset.clicked.connect(self._reset_defaults)
        btn_row.addWidget(btn_reset)
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

        # Autostart (aligned with TrafficBox)
        grp_auto = QGroupBox("Systemstart && Autostart")
        a_form = QFormLayout(grp_auto)
        self.chk_autostart = QCheckBox("Autostart mit dem Betriebssystem aktivieren")
        a_form.addRow("", self.chk_autostart)

        self.spn_start_delay = QSpinBox()
        self.spn_start_delay.setRange(0, 60)
        self.spn_start_delay.setSuffix(" Sek.")
        a_form.addRow("Startverzögerung beim Booten:", self.spn_start_delay)
        layout.addWidget(grp_auto)

        # Window behavior & position (aligned with TrafficBox)
        grp_win = QGroupBox("Fenster-Verhalten && Position")
        w_lay = QVBoxLayout(grp_win)
        w_lay.setSpacing(6)
        self.chk_always_on_top = QCheckBox("Alle Widgets immer im Vordergrund halten")
        self.chk_locked_pos = QCheckBox("Positionen aller Widgets sperren")
        self.chk_snap_edges = QCheckBox("Magnetisches Einrasten an Bildschirmrändern && Widgets")
        w_lay.addWidget(self.chk_always_on_top)
        w_lay.addWidget(self.chk_locked_pos)
        w_lay.addWidget(self.chk_snap_edges)
        layout.addWidget(grp_win)

        layout.addStretch(1)
        return tab

    def _build_display_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        # Global appearance
        grp_global = QGroupBox("Globale Darstellung")
        form = QFormLayout(grp_global)

        scale_row = QHBoxLayout()
        # Discrete 5% steps (14..60 -> 70%..300%) aligned with TrafficBox
        self.sld_scale = QSlider(Qt.Orientation.Horizontal)
        self.sld_scale.setRange(14, 60)
        self.sld_scale.setSingleStep(1)
        self.sld_scale.setPageStep(5)
        self.sld_scale.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.sld_scale.setTickInterval(5)

        self.spn_scale = QSpinBox()
        self.spn_scale.setRange(70, 300)
        self.spn_scale.setSingleStep(5)
        self.spn_scale.setSuffix("%")

        self.sld_scale.valueChanged.connect(lambda v: self.spn_scale.setValue(v * 5))
        self.spn_scale.valueChanged.connect(
            lambda v: self.sld_scale.setValue(max(14, min(60, int(round(v / 5.0)))))
        )

        btn_scale_100 = QPushButton("100% (Standard)")
        btn_scale_100.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_scale_100.clicked.connect(lambda: self.spn_scale.setValue(100))

        scale_row.addWidget(self.sld_scale, 1)
        scale_row.addWidget(self.spn_scale, 0)
        scale_row.addWidget(btn_scale_100, 0)
        form.addRow("UI-Skalierung:", scale_row)

        op_row = QHBoxLayout()
        self.sld_opacity = QSlider(Qt.Orientation.Horizontal)
        self.sld_opacity.setRange(20, 100)
        self.lbl_opacity_val = QLabel("85%")
        self.lbl_opacity_val.setMinimumWidth(48)
        self.sld_opacity.valueChanged.connect(lambda v: self.lbl_opacity_val.setText(f"{v}%"))
        op_row.addWidget(self.sld_opacity, 1)
        op_row.addWidget(self.lbl_opacity_val)
        form.addRow("Deckkraft:", op_row)
        layout.addWidget(grp_global)

        # Per-widget toggles & scaling
        grp_widgets = QGroupBox("Einzelne Desktop-Widgets")
        w_form = QFormLayout(grp_widgets)

        self._widget_checks: dict[str, tuple[QCheckBox, QSpinBox]] = {}
        for key, label in (
            ("clock", "Uhrzeit & Datum"),
            ("gpu", "GPU-Monitor"),
            ("cpu", "CPU & System"),
            ("storage", "Datenträger & Speicher"),
        ):
            row = QHBoxLayout()
            chk_en = QCheckBox("Aktiv")
            spn_sc = QSpinBox()
            spn_sc.setRange(0, 300)
            spn_sc.setSingleStep(5)
            spn_sc.setSpecialValueText("Global")
            spn_sc.setSuffix("%")
            spn_sc.setToolTip("Individuelle Skalierung (0 = Global übernehmen)")
            row.addWidget(chk_en)
            row.addStretch(1)
            row.addWidget(QLabel("Skalierung:"))
            row.addWidget(spn_sc)
            w_form.addRow(f"{label}:", row)
            self._widget_checks[key] = (chk_en, spn_sc)

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

        self.chk_gpu_mem_clock = QCheckBox("VRAM-Takt (MHz) anzeigen")
        g_form.addRow("", self.chk_gpu_mem_clock)

        self.chk_gpu_driver = QCheckBox("Treiberversion im Header anzeigen")
        g_form.addRow("", self.chk_gpu_driver)

        self.spn_temp_warn = QSpinBox()
        self.spn_temp_warn.setRange(50, 105)
        self.spn_temp_warn.setSuffix(" °C")
        g_form.addRow("Temperatur-Warnschwelle:", self.spn_temp_warn)
        layout.addWidget(grp_gpu)
        layout.addStretch(1)
        return tab

    def _build_cpu_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        grp_cpu = QGroupBox("CPU, RAM && System-Metriken")
        c_form = QFormLayout(grp_cpu)
        self.chk_cpu_max_core = QCheckBox("Höchsten Einzelkern anzeigen (Max-Kern %)")
        self.chk_cpu_page_faults = QCheckBox("PageFaults/sec (Hard Page Faults) Graph anzeigen")
        self.chk_cpu_disk = QCheckBox("Disk I/O (Lesen/Schreiben MB/s) anzeigen")
        self.cmb_disk = QComboBox()
        self.cmb_disk.addItem("Alle Datenträger (Summe)", "")
        for disk in self._disks:
            self.cmb_disk.addItem(disk, disk)
        self.chk_cpu_disk.toggled.connect(self.cmb_disk.setEnabled)
        c_form.addRow("", self.chk_cpu_max_core)
        c_form.addRow("", self.chk_cpu_page_faults)
        c_form.addRow("", self.chk_cpu_disk)
        c_form.addRow("Disk I/O Laufwerk:", self.cmb_disk)
        layout.addWidget(grp_cpu)
        layout.addStretch(1)
        return tab

    def _build_storage_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        grp_st = QGroupBox("Datenträger && Speicher-Anzeige")
        s_form = QFormLayout(grp_st)

        self.chk_storage_free_first = QCheckBox("Freien Speicher zuerst anzeigen („X GB frei von Y GB“)")
        self.chk_storage_dedup = QCheckBox("Identische Laufwerke / Partitionen zusammenfassen")
        self.chk_storage_boot = QCheckBox("Boot-Partitionen (/boot, /boot/efi) mit anzeigen")
        is_linux = sys.platform.startswith("linux")
        self.chk_storage_dedup.setVisible(is_linux)
        self.chk_storage_boot.setVisible(is_linux)

        self.spn_storage_warn = QSpinBox()
        self.spn_storage_warn.setRange(50, 99)
        self.spn_storage_warn.setSuffix(" %")
        self.spn_storage_warn.setToolTip("Ab dieser Belegung färbt sich der Laufwerksbalken in der Warnfarbe.")

        s_form.addRow("", self.chk_storage_free_first)
        if is_linux:
            s_form.addRow("", self.chk_storage_dedup)
            s_form.addRow("", self.chk_storage_boot)
        s_form.addRow("Warnschwelle Belegung:", self.spn_storage_warn)

        layout.addWidget(grp_st)
        layout.addStretch(1)
        return tab

    def _build_theme_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        grp_preset = QGroupBox("Theme-Schnellauswahl (Farb-Vorlagen)")
        p_row = QHBoxLayout(grp_preset)
        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems(list(THEMES.keys()))
        self.cmb_theme.activated.connect(self._load_preset_colors)
        btn_theme = QPushButton("Theme anwenden")
        btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_theme.clicked.connect(self._apply_preset_theme)
        p_row.addWidget(QLabel("Vorlage:"))
        p_row.addWidget(self.cmb_theme, 1)
        p_row.addWidget(btn_theme)
        layout.addWidget(grp_preset)

        colors_row = QHBoxLayout()
        colors_row.setSpacing(10)

        grp_metrics = QGroupBox("Graphen && Metriken")
        m_form = QFormLayout(grp_metrics)
        m_form.setContentsMargins(10, 10, 10, 10)
        m_form.setVerticalSpacing(6)
        self.btn_col_primary = ColorButton(self.config.primary_color)
        self.btn_col_secondary = ColorButton(self.config.secondary_color)
        self.btn_col_temp = ColorButton(self.config.temp_color)
        self.btn_col_vram = ColorButton(self.config.vram_color)
        m_form.addRow("Primär-Graph (GPU/CPU):", self.btn_col_primary)
        m_form.addRow("Sekundär-Graph (RAM):", self.btn_col_secondary)
        m_form.addRow("Temperatur / Warnung:", self.btn_col_temp)
        m_form.addRow("VRAM / Disk / Wochentag:", self.btn_col_vram)
        colors_row.addWidget(grp_metrics)

        grp_design = QGroupBox("Widget Design")
        d_form = QFormLayout(grp_design)
        d_form.setContentsMargins(10, 10, 10, 10)
        d_form.setVerticalSpacing(6)
        self.btn_col_bg = ColorButton(self.config.background_color)
        self.btn_col_border = ColorButton(self.config.border_color)
        self.btn_col_grid = ColorButton(self.config.grid_color)
        self.btn_col_title = ColorButton(self.config.title_color)
        self.btn_col_muted = ColorButton(self.config.muted_color)
        d_form.addRow("Hintergrund:", self.btn_col_bg)
        d_form.addRow("Rahmen:", self.btn_col_border)
        d_form.addRow("Raster (Grid):", self.btn_col_grid)
        d_form.addRow("Titelfarbe:", self.btn_col_title)
        d_form.addRow("Sekundärtext:", self.btn_col_muted)
        colors_row.addWidget(grp_design)

        layout.addLayout(colors_row)
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
        d_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

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
        lbl_gpu.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lbl_gpu.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        d_form.addRow("Hardware:", lbl_gpu)

        d_form.addRow("Hinweise:", QLabel("Open Source (MIT) • 100 % lokal ohne Telemetrie"))
        layout.addWidget(grp_diag)

        layout.addStretch(1)
        return tab

    def _load_preset_colors(self) -> None:
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

    def _apply_preset_theme(self) -> None:
        self._load_preset_colors()
        self._save_to_config()
        self._on_apply()

    def _load_from_config(self) -> None:
        self.chk_autostart.setChecked(is_autostart_enabled() or self.config.autostart)
        self.spn_start_delay.setValue(self.config.start_delay_sec)
        self.spn_scale.setValue(self.config.ui_scale_percent)
        self.sld_opacity.setValue(self.config.opacity)
        self.chk_always_on_top.setChecked(self.config.always_on_top)
        self.chk_locked_pos.setChecked(self.config.locked_pos)
        self.chk_snap_edges.setChecked(self.config.snap_to_edges)

        for key, (chk_en, spn_sc) in self._widget_checks.items():
            wc = self.config.get_widget(key)
            chk_en.setChecked(wc.enabled)
            spn_sc.setValue(wc.scale_percent if wc.scale_percent is not None else 0)

        self.spn_interval.setValue(self.config.refresh_interval_ms)
        self.spn_history.setValue(self.config.history_seconds)

        idx = self.cmb_gpu.findData(self.config.selected_gpu_index)
        if idx >= 0:
            self.cmb_gpu.setCurrentIndex(idx)

        self.chk_gpu_power_fan.setChecked(self.config.gpu_show_power_fan)
        self.chk_gpu_mem_clock.setChecked(self.config.gpu_show_mem_clock)
        self.chk_gpu_driver.setChecked(self.config.gpu_show_driver_version)
        self.spn_temp_warn.setValue(self.config.gpu_temp_warn_c)
        self.chk_cpu_max_core.setChecked(self.config.cpu_show_max_core)
        self.chk_cpu_page_faults.setChecked(self.config.cpu_show_page_faults)
        self.chk_cpu_disk.setChecked(self.config.cpu_show_disk_io)
        self.cmb_disk.setEnabled(self.config.cpu_show_disk_io)
        if self.config.cpu_disk_device and self.cmb_disk.findData(self.config.cpu_disk_device) < 0:
            self.cmb_disk.addItem(f"{self.config.cpu_disk_device} (nicht verbunden)", self.config.cpu_disk_device)
        d_idx = self.cmb_disk.findData(self.config.cpu_disk_device)
        self.cmb_disk.setCurrentIndex(d_idx if d_idx >= 0 else 0)
        self.chk_clock_sec.setChecked(self.config.clock_show_seconds)
        self.chk_clock_uptime.setChecked(self.config.clock_show_uptime)
        self.chk_clock_24h.setChecked(self.config.clock_24h)
        self.chk_storage_free_first.setChecked(self.config.storage_show_free_first)
        self.chk_storage_dedup.setChecked(self.config.storage_deduplicate_devices)
        self.chk_storage_boot.setChecked(self.config.storage_show_boot)
        self.spn_storage_warn.setValue(self.config.storage_warn_percent)

        t_idx = self.cmb_theme.findText(self.config.theme_name)
        if t_idx >= 0:
            self.cmb_theme.setCurrentIndex(t_idx)

    def _save_to_config(self) -> None:
        self.config.autostart = self.chk_autostart.isChecked()
        self.config.start_delay_sec = self.spn_start_delay.value()
        set_autostart(self.config.autostart)
        self.config.ui_scale_percent = self.spn_scale.value()
        self.config.opacity = self.sld_opacity.value()
        self.config.always_on_top = self.chk_always_on_top.isChecked()
        self.config.locked_pos = self.chk_locked_pos.isChecked()
        self.config.snap_to_edges = self.chk_snap_edges.isChecked()

        for key, (chk_en, spn_sc) in self._widget_checks.items():
            wc = self.config.get_widget(key)
            wc.enabled = chk_en.isChecked()
            sc_val = spn_sc.value()
            wc.scale_percent = sc_val if sc_val >= 70 else None

        self.config.refresh_interval_ms = self.spn_interval.value()
        self.config.history_seconds = self.spn_history.value()
        self.config.selected_gpu_index = int(self.cmb_gpu.currentData() or 0)
        self.config.gpu_show_power_fan = self.chk_gpu_power_fan.isChecked()
        self.config.gpu_show_mem_clock = self.chk_gpu_mem_clock.isChecked()
        self.config.gpu_show_driver_version = self.chk_gpu_driver.isChecked()
        self.config.gpu_temp_warn_c = self.spn_temp_warn.value()
        self.config.cpu_show_max_core = self.chk_cpu_max_core.isChecked()
        self.config.cpu_show_page_faults = self.chk_cpu_page_faults.isChecked()
        self.config.cpu_show_disk_io = self.chk_cpu_disk.isChecked()
        self.config.cpu_disk_device = str(self.cmb_disk.currentData() or "")
        self.config.clock_show_seconds = self.chk_clock_sec.isChecked()
        self.config.clock_show_uptime = self.chk_clock_uptime.isChecked()
        self.config.clock_24h = self.chk_clock_24h.isChecked()
        self.config.storage_show_free_first = self.chk_storage_free_first.isChecked()
        self.config.storage_deduplicate_devices = self.chk_storage_dedup.isChecked()
        self.config.storage_show_boot = self.chk_storage_boot.isChecked()
        self.config.storage_warn_percent = self.spn_storage_warn.value()

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

    def _reset_defaults(self) -> None:
        reply = QMessageBox.question(
            self,
            "Standardwerte wiederherstellen",
            "Möchtest du alle Einstellungen auf die Standardwerte zurücksetzen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        defaults = AppConfig()
        self.chk_autostart.setChecked(defaults.autostart)
        self.spn_start_delay.setValue(defaults.start_delay_sec)
        self.spn_scale.setValue(defaults.ui_scale_percent)
        self.sld_opacity.setValue(defaults.opacity)
        self.chk_always_on_top.setChecked(defaults.always_on_top)
        self.chk_locked_pos.setChecked(defaults.locked_pos)
        self.chk_snap_edges.setChecked(defaults.snap_to_edges)
        for key, (chk_en, spn_sc) in self._widget_checks.items():
            wc = defaults.get_widget(key)
            chk_en.setChecked(wc.enabled)
            spn_sc.setValue(wc.scale_percent if wc.scale_percent is not None else 0)
        self.spn_interval.setValue(defaults.refresh_interval_ms)
        self.spn_history.setValue(defaults.history_seconds)
        self.chk_gpu_power_fan.setChecked(defaults.gpu_show_power_fan)
        self.chk_gpu_mem_clock.setChecked(defaults.gpu_show_mem_clock)
        self.chk_gpu_driver.setChecked(defaults.gpu_show_driver_version)
        self.spn_temp_warn.setValue(defaults.gpu_temp_warn_c)
        self.chk_cpu_max_core.setChecked(defaults.cpu_show_max_core)
        self.chk_cpu_page_faults.setChecked(defaults.cpu_show_page_faults)
        self.chk_cpu_disk.setChecked(defaults.cpu_show_disk_io)
        self.cmb_disk.setCurrentIndex(0)
        self.chk_clock_sec.setChecked(defaults.clock_show_seconds)
        self.chk_clock_uptime.setChecked(defaults.clock_show_uptime)
        self.chk_clock_24h.setChecked(defaults.clock_24h)
        self.chk_storage_free_first.setChecked(defaults.storage_show_free_first)
        self.chk_storage_dedup.setChecked(defaults.storage_deduplicate_devices)
        self.chk_storage_boot.setChecked(defaults.storage_show_boot)
        self.spn_storage_warn.setValue(defaults.storage_warn_percent)
        t_idx = self.cmb_theme.findText(defaults.theme_name)
        if t_idx >= 0:
            self.cmb_theme.setCurrentIndex(t_idx)
        self.btn_col_primary.hex_color = defaults.primary_color
        self.btn_col_secondary.hex_color = defaults.secondary_color
        self.btn_col_temp.hex_color = defaults.temp_color
        self.btn_col_vram.hex_color = defaults.vram_color
        self.btn_col_bg.hex_color = defaults.background_color
        self.btn_col_border.hex_color = defaults.border_color
        self.btn_col_grid.hex_color = defaults.grid_color
        self.btn_col_title.hex_color = defaults.title_color
        self.btn_col_muted.hex_color = defaults.muted_color

    def _apply_changes(self) -> None:
        self._save_to_config()
        self._on_apply()

    def _accept_changes(self) -> None:
        self._apply_changes()
        self.accept()

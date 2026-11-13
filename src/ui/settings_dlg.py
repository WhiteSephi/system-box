"""Central Settings Dialog for SystemBox (aligned with TrafficBox look & feel)."""

from __future__ import annotations

from collections.abc import Callable
import platform
import sys

from PySide6.QtCore import Qt, QUrl, qVersion
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
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
from src.ui.tray import create_systembox_icon


def make_swatch_icon(hex_color: str, size: int = 16) -> QIcon:
    """Generate a clean rounded color chip icon."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(hex_color))
    painter.setPen(QColor("#FFFFFF" if QColor(hex_color).lightness() < 60 else "#222222"))
    painter.drawRoundedRect(1, 1, size - 2, size - 2, 4, 4)
    painter.end()
    return QIcon(pix)


class ModernColorPickerPopup(QDialog):
    """Modern dark-themed color picker popup with curated palette and hex input."""

    PALETTE = [
        ["#00E5FF", "#00E676", "#FFEA00", "#FF9100", "#FF1744", "#FF007F"],
        ["#3D5AFE", "#7C4DFF", "#00B0FF", "#1DE9B6", "#76FF03", "#FFD600"],
        ["#80D8FF", "#A7FFEB", "#CCFF90", "#FFE57F", "#FF8A80", "#EA80FC"],
        ["#FFFFFF", "#CFD8DC", "#78909C", "#455A64", "#263238", "#121212"],
    ]

    def __init__(
        self,
        current_hex: str,
        on_chosen: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.on_chosen = on_chosen

        self.setStyleSheet("""
            QDialog {
                background-color: #1A1E24;
                border: 1px solid #3E4652;
                border-radius: 8px;
            }
            QLabel {
                color: #E0E4E8;
                font-size: 8.5pt;
            }
            QLineEdit {
                background-color: #262C36;
                color: #FFFFFF;
                border: 1px solid #444D5A;
                border-radius: 4px;
                padding: 4px 6px;
                font-family: monospace;
                font-weight: bold;
                font-size: 8.5pt;
            }
            QLineEdit:focus {
                border-color: #00E5FF;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        lbl_title = QLabel("Farbe wählen")
        lbl_title.setStyleSheet("font-weight: bold; font-size: 9pt; color: #FFFFFF;")
        layout.addWidget(lbl_title)

        grid = QGridLayout()
        grid.setSpacing(5)
        for r, row in enumerate(self.PALETTE):
            for c, hex_code in enumerate(row):
                btn = QPushButton()
                btn.setFixedSize(26, 26)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setToolTip(hex_code)
                is_curr = hex_code.lower() == current_hex.lower()
                border = "2px solid #FFFFFF" if is_curr else "1px solid rgba(255,255,255,0.2)"
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {hex_code};
                        border: {border};
                        border-radius: 4px;
                    }}
                    QPushButton:hover {{
                        border: 2px solid #00E5FF;
                    }}
                """)
                btn.clicked.connect(lambda _, h=hex_code: self._select_and_close(h))
                grid.addWidget(btn, r, c)
        layout.addLayout(grid)

        hex_row = QHBoxLayout()
        hex_row.setSpacing(6)
        lbl_hex = QLabel("Hex:")
        self.txt_hex = QLineEdit(current_hex)
        self.txt_hex.setMaxLength(9)

        self.lbl_swatch_preview = QLabel()
        self.lbl_swatch_preview.setFixedSize(22, 22)
        self._update_preview_swatch(current_hex)

        self.txt_hex.textChanged.connect(self._on_hex_text_changed)
        self.txt_hex.returnPressed.connect(lambda: self._select_and_close(self.txt_hex.text()))

        btn_ok = QPushButton("✓")
        btn_ok.setFixedSize(26, 26)
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #2D3748;
                color: #00E5FF;
                border: 1px solid #4A5568;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3A475C;
                border-color: #00E5FF;
            }
        """)
        btn_ok.clicked.connect(lambda: self._select_and_close(self.txt_hex.text()))

        hex_row.addWidget(lbl_hex)
        hex_row.addWidget(self.lbl_swatch_preview)
        hex_row.addWidget(self.txt_hex, 1)
        hex_row.addWidget(btn_ok)
        layout.addLayout(hex_row)

        btn_sys = QPushButton("🎨 Erweiterte Farbauswahl…")
        btn_sys.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sys.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #8E9297;
                font-size: 8pt;
                text-decoration: underline;
                padding-top: 2px;
            }
            QPushButton:hover {
                color: #00E5FF;
            }
        """)
        btn_sys.clicked.connect(self._open_system_picker)
        layout.addWidget(btn_sys)

    def _update_preview_swatch(self, hex_code: str) -> None:
        if not hex_code.startswith("#"):
            hex_code = "#" + hex_code
        col = QColor(hex_code)
        if col.isValid():
            self.lbl_swatch_preview.setStyleSheet(
                f"background-color: {col.name()}; border: 1px solid #666; border-radius: 3px;"
            )

    def _on_hex_text_changed(self, text: str) -> None:
        self._update_preview_swatch(text.strip())

    def _select_and_close(self, hex_val: str) -> None:
        hex_val = hex_val.strip()
        if not hex_val.startswith("#"):
            hex_val = "#" + hex_val
        col = QColor(hex_val)
        if col.isValid():
            self.on_chosen(col.name().upper())
            self.close()

    def _open_system_picker(self) -> None:
        init_col = QColor(self.txt_hex.text().strip())
        if not init_col.isValid():
            init_col = QColor("#00E5FF")
        chosen = QColorDialog.getColor(init_col, self, "Erweiterte Farbe wählen")
        if chosen.isValid():
            self.on_chosen(chosen.name().upper())
            self.close()


class ColorButton(QPushButton):
    """Compact button displaying a color swatch and opening ModernColorPickerPopup."""

    def __init__(self, hex_color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._hex_color = hex_color
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(26)
        self.setMinimumWidth(110)
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
        self.setIcon(make_swatch_icon(self._hex_color, 16))
        self.setText(f" {self._hex_color.upper()}")
        self.setStyleSheet(
            """
            QPushButton {
                background-color: #2A2F38;
                color: #E0E4E8;
                border: 1px solid #444D5A;
                border-radius: 5px;
                padding: 3px 8px;
                text-align: left;
                font-family: monospace;
                font-weight: bold;
                font-size: 8.5pt;
            }
            QPushButton:hover {
                border-color: #00E5FF;
                background-color: #323842;
            }
            """
        )

    def _pick_color(self) -> None:
        popup = ModernColorPickerPopup(self._hex_color, self._on_color_chosen, self)
        pos = self.mapToGlobal(self.rect().bottomLeft())
        popup.move(pos.x(), pos.y() + 4)
        popup.exec()

    def _on_color_chosen(self, hex_val: str) -> None:
        self.hex_color = hex_val


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
        self.setMinimumSize(640, 520)
        self.resize(max(680, self.config.settings_width), max(620, self.config.settings_height))
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
        self.tabs.addTab(self._build_display_tab(), "Anzeige")
        self.tabs.addTab(self._build_clock_tab(), "Uhrzeit && Datum")
        self.tabs.addTab(self._build_gpu_tab(), "GPU-Monitor")
        self.tabs.addTab(self._build_cpu_tab(), "CPU && System")
        self.tabs.addTab(self._build_theme_tab(), "Design && Themes")
        self.tabs.addTab(self._build_about_tab(), "Über")

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
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        scroll.setWidget(tab)

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
        return scroll

    def _build_display_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        scroll.setWidget(tab)

        # Global appearance
        grp_global = QGroupBox("Globale Darstellung")
        form = QFormLayout(grp_global)

        scale_row = QHBoxLayout()
        self.sld_scale = QSlider(Qt.Orientation.Horizontal)
        self.sld_scale.setRange(70, 300)
        self.sld_scale.setSingleStep(5)
        self.lbl_scale_val = QLabel("100%")
        self.lbl_scale_val.setMinimumWidth(48)
        self.sld_scale.valueChanged.connect(lambda v: self.lbl_scale_val.setText(f"{v}%"))
        scale_row.addWidget(self.sld_scale, 1)
        scale_row.addWidget(self.lbl_scale_val)
        form.addRow("Globale Skalierung:", scale_row)

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
        for key, label in (("clock", "Uhrzeit & Datum"), ("gpu", "GPU-Monitor"), ("cpu", "CPU & System")):
            row = QHBoxLayout()
            chk_en = QCheckBox("Aktiv")
            spn_sc = QSpinBox()
            spn_sc.setRange(0, 300)
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
        return scroll

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
        self.chk_cpu_max_core = QCheckBox("Höchsten Einzelkern anzeigen (Max-Kern %)")
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

        grp_preset = QGroupBox("Theme-Schnellauswahl (Farb-Vorlagen)")
        p_row = QHBoxLayout(grp_preset)
        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems(list(THEMES.keys()))
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
        self.chk_autostart.setChecked(is_autostart_enabled() or self.config.autostart)
        self.spn_start_delay.setValue(self.config.start_delay_sec)
        self.sld_scale.setValue(self.config.ui_scale_percent)
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
        self.config.autostart = self.chk_autostart.isChecked()
        self.config.start_delay_sec = self.spn_start_delay.value()
        set_autostart(self.config.autostart)
        self.config.ui_scale_percent = self.sld_scale.value()
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
        self.sld_scale.setValue(defaults.ui_scale_percent)
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
        self.spn_vram_warn.setValue(defaults.gpu_vram_warn_percent)
        self.chk_cpu_max_core.setChecked(defaults.cpu_show_max_core)
        self.chk_cpu_page_faults.setChecked(defaults.cpu_show_page_faults)
        self.chk_cpu_disk.setChecked(defaults.cpu_show_disk_io)
        self.chk_clock_sec.setChecked(defaults.clock_show_seconds)
        self.chk_clock_uptime.setChecked(defaults.clock_show_uptime)
        self.chk_clock_24h.setChecked(defaults.clock_24h)
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

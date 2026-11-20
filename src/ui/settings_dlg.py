"""Central Settings Dialog for SystemBox (aligned with TrafficBox look & feel)."""

from __future__ import annotations

from collections.abc import Callable
import platform
import sys

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QUrl, qVersion
from PySide6.QtGui import QCloseEvent, QDesktopServices, QHideEvent, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src import __version__
from src.autostart import is_autostart_enabled, set_autostart
from src.config import AppConfig
from src.sensors.disk_space import format_storage_size, read_disk_spaces
from src.sensors.models import DiskSpaceInfo, GpuInfo
from src.themes import THEMES
from src.ui.color_picker import ColorButton
from src.ui.tray import create_systembox_icon


class SettingsDialog(QDialog):
    """Tabbed settings dialog for widgets, sensors, scaling and themes."""

    TAB_KEYS = {
        "general": 0,
        "display": 1,
        "theme": 1,
        "clock": 2,
        "gpu": 3,
        "cpu": 4,
        "storage": 5,
        "about": 6,
    }

    def __init__(
        self,
        config: AppConfig,
        gpus: list[GpuInfo],
        on_apply: Callable[[], None],
        parent: QWidget | None = None,
        initial_tab: str = "",
        disks: list[str] | None = None,
        storage_disks: list[DiskSpaceInfo] | None = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self._gpus = gpus
        self._disks = list(disks) if disks is not None else []
        self._storage_disks = (
            list(storage_disks)
            if storage_disks is not None
            else read_disk_spaces(
                deduplicate_devices=self.config.storage_deduplicate_devices,
                show_boot=self.config.storage_show_boot,
            )
        )
        self._storage_drive_checks: dict[str, QCheckBox] = {}
        self._on_apply = on_apply

        self.setWindowTitle("SystemBox Einstellungen")
        self.setWindowIcon(create_systembox_icon(self.config.primary_color))
        self.setMinimumSize(500, 420)

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
            if tab_key == "display":
                self._set_display_subpage(0)
            elif tab_key == "theme":
                self._set_display_subpage(1)

    def _restore_geometry(self) -> None:
        """Restore window position and size if valid on current screens."""
        cfg_w = max(500, self.config.settings_width)
        cfg_h = max(420, self.config.settings_height)
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

    @staticmethod
    def _set_tooltip(widget: QWidget, text: str, form: QFormLayout | None = None) -> None:
        """Assign a concise tooltip to a control and its associated form label."""
        widget.setToolTip(text)
        if form is not None:
            label = form.labelForField(widget)
            if label is not None:
                label.setToolTip(text)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self.tabs.addTab(self._wrap_in_scroll(self._build_general_tab()), "Allgemein")
        self.tabs.addTab(self._build_display_container_tab(), "Anzeige")
        self.tabs.addTab(self._wrap_in_scroll(self._build_clock_tab()), "Uhrzeit")
        self.tabs.addTab(self._wrap_in_scroll(self._build_gpu_tab()), "GPU")
        self.tabs.addTab(self._wrap_in_scroll(self._build_cpu_tab()), "System")
        self.tabs.addTab(self._wrap_in_scroll(self._build_storage_tab()), "Datenträger")
        self.tabs.addTab(self._wrap_in_scroll(self._build_about_tab()), "Über")

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_reset = QPushButton("Reset (Standardwerte)")
        btn_reset.setToolTip("Setzt alle Einstellungen im Dialog auf die Standardwerte zurück.")
        btn_reset.clicked.connect(self._reset_defaults)
        btn_row.addWidget(btn_reset)
        btn_row.addStretch(1)
        btn_apply = QPushButton("Übernehmen")
        btn_apply.setToolTip("Speichert die Änderungen und wendet sie sofort auf alle Widgets an.")
        btn_apply.clicked.connect(self._apply_changes)
        btn_ok = QPushButton("OK")
        btn_ok.setToolTip("Speichert die Änderungen, wendet sie an und schließt den Dialog.")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self._accept_changes)
        btn_cancel = QPushButton("Abbrechen")
        btn_cancel.setToolTip("Verwirft ungespeicherte Änderungen und schließt den Dialog.")
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
        self.chk_autostart = QCheckBox("Mit Systemstart automatisch starten")
        self._set_tooltip(
            self.chk_autostart,
            "Startet SystemBox automatisch nach der Anmeldung am Betriebssystem.",
        )
        a_form.addRow("", self.chk_autostart)

        self.spn_start_delay = QSpinBox()
        self.spn_start_delay.setRange(0, 60)
        self.spn_start_delay.setSuffix(" Sek.")
        a_form.addRow("Startverzögerung:", self.spn_start_delay)
        self._set_tooltip(
            self.spn_start_delay,
            "Wartezeit nach dem Systemstart, bevor die Widgets angezeigt werden (0–60 Sek.).",
            a_form,
        )
        layout.addWidget(grp_auto)

        # Window behavior & position (aligned with TrafficBox)
        grp_win = QGroupBox("Fenster-Verhalten && Position")
        w_lay = QVBoxLayout(grp_win)
        w_lay.setSpacing(6)
        self.chk_always_on_top = QCheckBox("Immer im Vordergrund")
        self._set_tooltip(
            self.chk_always_on_top,
            "Hält alle Desktop-Widgets dauerhaft über anderen Fenstern.",
        )
        self.chk_locked_pos = QCheckBox("Widget-Positionen sperren")
        self._set_tooltip(
            self.chk_locked_pos,
            "Verhindert versehentliches Verschieben der Widgets per Maus.",
        )
        self.chk_snap_edges = QCheckBox("An Rändern && Widgets einrasten")
        self._set_tooltip(
            self.chk_snap_edges,
            "Richtet Widgets beim Verschieben magnetisch an Bildschirmrändern und anderen Widgets aus.",
        )
        w_lay.addWidget(self.chk_always_on_top)
        w_lay.addWidget(self.chk_locked_pos)
        w_lay.addWidget(self.chk_snap_edges)
        layout.addWidget(grp_win)

        grp_poll = QGroupBox("Abfrage && Verlauf")
        p_form = QFormLayout(grp_poll)
        self.spn_interval = QSpinBox()
        self.spn_interval.setRange(500, 5000)
        self.spn_interval.setSingleStep(250)
        self.spn_interval.setSuffix(" ms")
        p_form.addRow("Aktualisierungs-Intervall:", self.spn_interval)
        self._set_tooltip(
            self.spn_interval,
            "Abstand zwischen zwei Sensor-Abfragen in Millisekunden (500–5000 ms).",
            p_form,
        )

        self.spn_history = QSpinBox()
        self.spn_history.setRange(15, 300)
        self.spn_history.setSuffix(" Samples")
        p_form.addRow("Graph-Verlaufslänge:", self.spn_history)
        self._set_tooltip(
            self.spn_history,
            "Anzahl der gespeicherten Messpunkte für die Verlaufsgraphen (15–300 Samples).",
            p_form,
        )
        layout.addWidget(grp_poll)

        layout.addStretch(1)
        return tab

    def _build_display_container_tab(self) -> QWidget:
        """Build the unified Display tab with a segmented subpage switcher."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(4)

        bar_row = QHBoxLayout()
        bar_row.setContentsMargins(9, 0, 9, 0)

        seg_bar = QFrame()
        seg_bar.setObjectName("displaySegmentBar")
        seg_layout = QHBoxLayout(seg_bar)
        seg_layout.setContentsMargins(3, 3, 3, 3)
        seg_layout.setSpacing(3)

        self.btn_sub_display = QPushButton("Darstellung && Widgets")
        self.btn_sub_display.setCheckable(True)
        self.btn_sub_display.setChecked(True)
        self.btn_sub_display.setMinimumWidth(165)
        self.btn_sub_display.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_sub_theme = QPushButton("Themes && Farben")
        self.btn_sub_theme.setCheckable(True)
        self.btn_sub_theme.setMinimumWidth(165)
        self.btn_sub_theme.setCursor(Qt.CursorShape.PointingHandCursor)

        self._display_seg_group = QButtonGroup(self)
        self._display_seg_group.setExclusive(True)
        self._display_seg_group.addButton(self.btn_sub_display, 0)
        self._display_seg_group.addButton(self.btn_sub_theme, 1)
        self._display_seg_group.idClicked.connect(self._set_display_subpage)

        seg_layout.addWidget(self.btn_sub_display)
        seg_layout.addWidget(self.btn_sub_theme)
        self._style_display_segment_bar(seg_bar)

        bar_row.addWidget(seg_bar)
        bar_row.addStretch(1)
        layout.addLayout(bar_row)

        self.display_stack = QStackedWidget()
        self.display_stack.addWidget(self._wrap_in_scroll(self._build_display_tab()))
        self.display_stack.addWidget(self._wrap_in_scroll(self._build_theme_tab()))
        layout.addWidget(self.display_stack, 1)
        return container

    def _style_display_segment_bar(self, bar: QFrame, object_name: str = "displaySegmentBar") -> None:
        """Apply palette-aware high-contrast QSS to a segmented subpage bar."""
        bar.setObjectName(object_name)
        is_dark = self.palette().color(QPalette.ColorRole.Window).lightness() < 128
        if is_dark:
            track_bg = "rgba(255, 255, 255, 12)"
            track_border = "rgba(255, 255, 255, 38)"
            btn_fg = "rgba(255, 255, 255, 195)"
            hover_bg = "rgba(255, 255, 255, 20)"
            checked_bg = "palette(button)"
            checked_fg = "palette(button-text)"
        else:
            track_bg = "rgba(0, 0, 0, 12)"
            track_border = "rgba(0, 0, 0, 35)"
            btn_fg = "rgba(0, 0, 0, 195)"
            hover_bg = "rgba(0, 0, 0, 18)"
            checked_bg = "palette(base)"
            checked_fg = "palette(window-text)"

        bar.setStyleSheet(
            f"""
            QFrame#{object_name} {{
                background-color: {track_bg};
                border: 1px solid {track_border};
                border-radius: 7px;
            }}
            QFrame#{object_name} QPushButton {{
                background: transparent;
                color: {btn_fg};
                border: 1px solid transparent;
                border-radius: 5px;
                padding: 5px 14px;
            }}
            QFrame#{object_name} QPushButton:hover:!checked {{
                background-color: {hover_bg};
                color: palette(window-text);
            }}
            QFrame#{object_name} QPushButton:checked {{
                background-color: {checked_bg};
                color: {checked_fg};
                border: 1px solid palette(highlight);
                font-weight: 600;
            }}
            """
        )

    def _set_display_subpage(self, index: int) -> None:
        """Switch subpage inside the Display tab and sync segmented toggle state."""
        if index not in (0, 1):
            return
        self.display_stack.setCurrentIndex(index)
        if index == 0:
            self.btn_sub_display.setChecked(True)
        else:
            self.btn_sub_theme.setChecked(True)

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
        scale_tip = "Globale Schrift- und Widget-Größe in Prozent (70–300 %)."
        self._set_tooltip(self.sld_scale, scale_tip)
        self._set_tooltip(self.spn_scale, scale_tip)
        self._set_tooltip(btn_scale_100, "Setzt die globale UI-Skalierung auf 100 % zurück.")
        if (lbl_scale := form.labelForField(scale_row)) is not None:
            lbl_scale.setToolTip(scale_tip)

        op_row = QHBoxLayout()
        self.sld_opacity = QSlider(Qt.Orientation.Horizontal)
        self.sld_opacity.setRange(20, 100)
        self.lbl_opacity_val = QLabel("85%")
        self.lbl_opacity_val.setMinimumWidth(48)
        self.sld_opacity.valueChanged.connect(lambda v: self.lbl_opacity_val.setText(f"{v}%"))
        op_row.addWidget(self.sld_opacity, 1)
        op_row.addWidget(self.lbl_opacity_val)
        form.addRow("Deckkraft:", op_row)
        opacity_tip = "Transparenz der Widget-Hintergründe (20–100 %)."
        self._set_tooltip(self.sld_opacity, opacity_tip)
        self._set_tooltip(self.lbl_opacity_val, opacity_tip)
        if (lbl_opacity := form.labelForField(op_row)) is not None:
            lbl_opacity.setToolTip(opacity_tip)
        layout.addWidget(grp_global)

        # Per-widget toggles & scaling
        grp_widgets = QGroupBox("Einzelne Desktop-Widgets")
        w_form = QFormLayout(grp_widgets)

        self._widget_checks: dict[str, tuple[QCheckBox, QSpinBox]] = {}
        for key, label in (
            ("clock", "Uhrzeit & Datum"),
            ("gpu", "GPU-Monitor"),
            ("cpu", "System"),
            ("storage", "Datenträger"),
        ):
            row = QHBoxLayout()
            chk_en = QCheckBox("Aktiv")
            self._set_tooltip(chk_en, f"Blendet das Widget „{label}“ auf dem Desktop ein oder aus.")
            spn_sc = QSpinBox()
            spn_sc.setRange(0, 300)
            spn_sc.setSingleStep(5)
            spn_sc.setSpecialValueText("Global")
            spn_sc.setSuffix("%")
            self._set_tooltip(
                spn_sc,
                "Individuelle Skalierung für dieses Widget (Global = globale UI-Skalierung übernehmen).",
            )
            row.addWidget(chk_en)
            row.addStretch(1)
            row.addWidget(QLabel("Skalierung:"))
            row.addWidget(spn_sc)
            w_form.addRow(f"{label}:", row)
            self._widget_checks[key] = (chk_en, spn_sc)

        layout.addWidget(grp_widgets)

        layout.addStretch(1)
        return tab

    def _build_clock_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        grp_clk = QGroupBox("Anzeige-Optionen (Uhrzeit && Datum)")
        c_form = QFormLayout(grp_clk)
        self.chk_clock_24h = QCheckBox("24-Stunden-Format")
        self._set_tooltip(
            self.chk_clock_24h,
            "Zeigt die Uhrzeit im 24-Stunden-Format statt 12-Stunden-Format (AM/PM) an.",
        )
        self.chk_clock_sec = QCheckBox("Sekunden-Balken anzeigen")
        self._set_tooltip(
            self.chk_clock_sec,
            "Zeigt unter der Uhrzeit einen animierten Fortschrittsbalken für die laufende Minute an.",
        )
        self.chk_clock_uptime = QCheckBox("System-Uptime anzeigen")
        self._set_tooltip(
            self.chk_clock_uptime,
            "Zeigt die Betriebszeit seit dem letzten Systemstart im Uhrzeit-Widget an.",
        )
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
        self._set_tooltip(
            self.cmb_gpu,
            "Wählt die Grafikkarte aus, deren Sensordaten im GPU-Widget angezeigt werden.",
            g_form,
        )

        self.chk_gpu_power_fan = QCheckBox("Lüfter && Leistung (Watt) anzeigen")
        self._set_tooltip(
            self.chk_gpu_power_fan,
            "Zeigt Lüfterdrehzahl (RPM / %) und aktuelle Leistungsaufnahme in Watt an.",
        )
        g_form.addRow("", self.chk_gpu_power_fan)

        self.chk_gpu_mem_clock = QCheckBox("VRAM-Takt (MHz) anzeigen")
        self._set_tooltip(
            self.chk_gpu_mem_clock,
            "Zeigt zusätzlich die aktuelle Speichertaktfrequenz des Grafikspeichers (MHz) an.",
        )
        g_form.addRow("", self.chk_gpu_mem_clock)

        self.chk_gpu_driver = QCheckBox("Treiberversion im Header anzeigen")
        self._set_tooltip(
            self.chk_gpu_driver,
            "Zeigt die installierte GPU-Treiberversion oben im Header des GPU-Widgets an.",
        )
        g_form.addRow("", self.chk_gpu_driver)

        self.spn_temp_warn = QSpinBox()
        self.spn_temp_warn.setRange(50, 105)
        self.spn_temp_warn.setSuffix(" °C")
        g_form.addRow("Temperatur-Warnschwelle:", self.spn_temp_warn)
        self._set_tooltip(
            self.spn_temp_warn,
            "Ab dieser GPU-Temperatur (50–105 °C) wird der Wert in der Warnfarbe hervorgehoben.",
            g_form,
        )
        layout.addWidget(grp_gpu)
        layout.addStretch(1)
        return tab

    @staticmethod
    def _make_viz_combo(options: list[tuple[str, str]]) -> QComboBox:
        cmb = QComboBox()
        for label, key in options:
            cmb.addItem(label, key)
        return cmb

    def _build_cpu_viz_group(self) -> QGroupBox:
        """Build the Visualization group box for CPU, RAM, PageFaults and Disk I/O."""
        grp_viz = QGroupBox("Darstellung")
        v_form = QFormLayout(grp_viz)

        self.cmb_cpu_viz = self._make_viz_combo([
            ("Live-Graph (Standard)", "graph"),
            ("Kerne als Balken (Equalizer)", "core_bars"),
            ("Kern-Heatmap-Grid", "core_heatmap"),
        ])
        self.cmb_ram_viz = self._make_viz_combo([
            ("Live-Graph (Standard)", "graph"),
            ("Speicherblöcke", "grid_blocks"),
            ("Segment-Füllbalken (0–100%)", "segmented_bar"),
        ])
        self.cmb_pf_viz = self._make_viz_combo([
            ("Live-Graph (Standard)", "graph"),
            ("Log-Pulse-Meter (Peak-Hold)", "pulse_meter"),
            ("Impuls-Balken (Spike-Historie)", "impulse_bars"),
        ])
        self.cmb_disk_viz = self._make_viz_combo([
            ("Dual-Live-Graph (Standard)", "graph"),
            ("Dual-R/W-Balken (Peak-Hold)", "dual_meter"),
            ("Retro-HDD-LED-Leiste", "activity_leds"),
        ])

        v_form.addRow("CPU-Auslastung:", self.cmb_cpu_viz)
        self._set_tooltip(self.cmb_cpu_viz, "Wählt zwischen Verlaufsgraph, Einzelkern-Balken oder Kern-Heatmap.", v_form)
        v_form.addRow("Arbeitsspeicher (RAM):", self.cmb_ram_viz)
        self._set_tooltip(self.cmb_ram_viz, "Wählt zwischen Verlaufsgraph, 2er-Potenz-Speicherblöcken oder Segment-Balken.", v_form)
        v_form.addRow("PageFaults/sec:", self.cmb_pf_viz)
        self._set_tooltip(self.cmb_pf_viz, "Wählt zwischen Verlaufsgraph, logarithmischem Peak-Hold-Meter oder Spike-Impulsen.", v_form)
        v_form.addRow("Disk I/O (R/W):", self.cmb_disk_viz)
        self._set_tooltip(self.cmb_disk_viz, "Wählt zwischen Dual-Graph, R/W-Peak-Hold-Balken oder Retro-LED-Leiste.", v_form)
        return grp_viz

    def _build_cpu_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        grp_cpu = QGroupBox("CPU, RAM && System-Metriken")
        c_form = QFormLayout(grp_cpu)
        self.chk_cpu_max_core = QCheckBox("Max-Kern-Auslastung (%) anzeigen")
        self._set_tooltip(
            self.chk_cpu_max_core,
            "Zeigt die Auslastung des am stärksten belasteten CPU-Einzelkerns an.",
        )
        self.chk_cpu_page_faults = QCheckBox("PageFaults/sec-Graph anzeigen")
        self._set_tooltip(
            self.chk_cpu_page_faults,
            "Zeigt einen zusätzlichen Verlaufsgraphen für Hard Page Faults pro Sekunde an.",
        )
        self.chk_cpu_disk = QCheckBox("Disk I/O (MB/s) anzeigen")
        self._set_tooltip(
            self.chk_cpu_disk,
            "Zeigt Lese- und Schreibrate der Festplatte bzw. SSD in MB/s an.",
        )
        self.cmb_disk = QComboBox()
        self.cmb_disk.addItem("Alle Datenträger (Summe)", "")
        for disk in self._disks:
            self.cmb_disk.addItem(disk, disk)
        self.chk_cpu_disk.toggled.connect(self.cmb_disk.setEnabled)
        c_form.addRow("", self.chk_cpu_max_core)
        c_form.addRow("", self.chk_cpu_page_faults)
        c_form.addRow("", self.chk_cpu_disk)
        c_form.addRow("Disk I/O Laufwerk:", self.cmb_disk)
        self._set_tooltip(
            self.cmb_disk,
            "Wählt ein bestimmtes Laufwerk oder die Summe aller Datenträger für Disk I/O aus.",
            c_form,
        )
        layout.addWidget(grp_cpu)
        layout.addWidget(self._build_cpu_viz_group())
        layout.addStretch(1)
        return tab

    def _build_storage_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        grp_st = QGroupBox("Datenträger-Anzeige")
        s_form = QFormLayout(grp_st)

        self.chk_storage_free_first = QCheckBox("Freien Speicher zuerst anzeigen")
        self._set_tooltip(
            self.chk_storage_free_first,
            "Formatiert den Speichertext als „X GB frei von Y GB“ statt belegtem Speicher zuerst.",
        )
        self.chk_storage_dedup = QCheckBox("Identische Laufwerke zusammenfassen")
        self._set_tooltip(
            self.chk_storage_dedup,
            "Fasst mehrfach eingehängte Geräte (z. B. Btrfs-Subvolumes unter Linux) zu einem Eintrag zusammen.",
        )
        self.chk_storage_boot = QCheckBox("Boot-Partitionen mit anzeigen")
        self._set_tooltip(
            self.chk_storage_boot,
            "Zeigt auch System-Boot-Partitionen wie /boot und /boot/efi in der Laufwerksliste an.",
        )
        is_linux = sys.platform.startswith("linux")
        self.chk_storage_dedup.setVisible(is_linux)
        self.chk_storage_boot.setVisible(is_linux)

        self.spn_storage_warn = QSpinBox()
        self.spn_storage_warn.setRange(50, 99)
        self.spn_storage_warn.setSuffix(" %")

        s_form.addRow("", self.chk_storage_free_first)
        if is_linux:
            s_form.addRow("", self.chk_storage_dedup)
            s_form.addRow("", self.chk_storage_boot)
        s_form.addRow("Warnschwelle Belegung:", self.spn_storage_warn)
        self._set_tooltip(
            self.spn_storage_warn,
            "Ab dieser Belegung färbt sich der Laufwerksbalken in der Warnfarbe.",
            s_form,
        )

        layout.addWidget(grp_st)

        grp_drives = QGroupBox("Angezeigte Laufwerke")
        drv_outer = QVBoxLayout(grp_drives)
        drv_outer.setContentsMargins(10, 10, 10, 10)
        drv_scroll = QScrollArea()
        drv_scroll.setWidgetResizable(True)
        drv_scroll.setFrameShape(QFrame.Shape.NoFrame)
        drv_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        drv_inner = QWidget()
        drv_list = QVBoxLayout(drv_inner)
        drv_list.setContentsMargins(0, 0, 0, 0)
        drv_list.setSpacing(6)

        self._storage_drive_checks.clear()
        seen_mounts: set[str] = set()
        for d in self._storage_disks:
            seen_mounts.add(d.mountpoint)
            chk = QCheckBox(f"{d.label}  ({format_storage_size(d.total_gb)})")
            self._set_tooltip(chk, f"Laufwerk „{d.mountpoint}“ im Datenträger-Widget anzeigen oder ausblenden.")
            drv_list.addWidget(chk)
            self._storage_drive_checks[d.mountpoint] = chk

        for mp in self.config.storage_hidden_mountpoints:
            if mp not in seen_mounts:
                chk = QCheckBox(f"{mp} (nicht verbunden)")
                self._set_tooltip(chk, f"Laufwerk „{mp}“ im Datenträger-Widget anzeigen oder ausblenden.")
                drv_list.addWidget(chk)
                self._storage_drive_checks[mp] = chk

        if not self._storage_drive_checks:
            lbl_none = QLabel("Keine Laufwerke erkannt.")
            drv_list.addWidget(lbl_none)

        drv_list.addStretch(1)
        drv_scroll.setWidget(drv_inner)
        drv_outer.addWidget(drv_scroll)
        layout.addWidget(grp_drives, 1)
        return tab

    def _build_theme_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        grp_preset = QGroupBox("Theme-Schnellauswahl")
        p_row = QHBoxLayout(grp_preset)
        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems(list(THEMES.keys()) + ["Benutzerdefiniert"])
        self.cmb_theme.activated.connect(self._load_preset_colors)
        self._set_tooltip(
            self.cmb_theme,
            "Wählt eine Farbvorlage direkt in die Farbfelder darunter. Speichern über „Übernehmen“ oder „OK“.",
        )
        p_row.addWidget(QLabel("Vorlage:"))
        p_row.addWidget(self.cmb_theme, 1)
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
        self._set_tooltip(
            self.btn_col_primary,
            "Hauptfarbe für GPU-/CPU-Auslastung und Akzente.",
            m_form,
        )
        self._set_tooltip(
            self.btn_col_secondary,
            "Farbe für RAM-Auslastung und sekundäre Graphen.",
            m_form,
        )
        self._set_tooltip(
            self.btn_col_temp,
            "Farbe für Temperaturanzeigen und Schwellwert-Warnungen.",
            m_form,
        )
        self._set_tooltip(
            self.btn_col_vram,
            "Farbe für VRAM, Disk I/O und den Wochentag im Uhrzeit-Widget.",
            m_form,
        )
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
        self._set_tooltip(self.btn_col_bg, "Hintergrundfarbe der Widget-Karten.", d_form)
        self._set_tooltip(self.btn_col_border, "Rahmenfarbe der Widget-Karten.", d_form)
        self._set_tooltip(self.btn_col_grid, "Linienfarbe des Hintergrundrasters in Graphen.", d_form)
        self._set_tooltip(self.btn_col_title, "Textfarbe für Widget-Titel und Hauptwerte.", d_form)
        self._set_tooltip(self.btn_col_muted, "Textfarbe für Beschriftungen, Einheiten und Nebentexte.", d_form)
        colors_row.addWidget(grp_design)

        for btn_col in (
            self.btn_col_primary,
            self.btn_col_secondary,
            self.btn_col_temp,
            self.btn_col_vram,
            self.btn_col_bg,
            self.btn_col_border,
            self.btn_col_grid,
            self.btn_col_title,
            self.btn_col_muted,
        ):
            btn_col.color_changed.connect(self._sync_theme_dropdown_from_buttons)

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

        btn_grid = QGridLayout()
        btn_grid.setSpacing(8)
        about_buttons: list[QPushButton] = []
        for text, url in (
            ("🌐 GitHub", repo_url),
            ("🚀 Releases", releases_url),
            ("🐛 Fehler melden", issues_url),
        ):
            btn = QPushButton(text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, u=url: QDesktopServices.openUrl(QUrl(u)))
            about_buttons.append(btn)

        btn_cfg = QPushButton("📁 Konfig-Ordner")
        btn_cfg.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cfg.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(AppConfig.config_path().parent)))
        )
        about_buttons.append(btn_cfg)

        for idx, btn in enumerate(about_buttons):
            btn_grid.addWidget(btn, idx // 2, idx % 2)
        about_layout.addLayout(btn_grid)
        layout.addWidget(grp_about)

        # Group 2: System-Diagnose & Rechtliches
        grp_diag = QGroupBox("System-Diagnose && Rechtliches")
        d_form = QFormLayout(grp_diag)
        d_form.setVerticalSpacing(6)
        d_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        mode_str = "Binary" if getattr(sys, "frozen", False) else "Quellcode"
        os_str = f"{platform.system()} {platform.release()} ({platform.machine()})"
        runtime_str = f"{os_str} • Python {platform.python_version()} • Qt {qVersion()} • {mode_str}"
        lbl_runtime = self._make_wrapping_info_label(runtime_str, selectable=True)
        d_form.addRow("Laufzeit:", lbl_runtime)

        cfg_dir = AppConfig.config_path().parent
        loc_str = f"Portabel ({cfg_dir})" if cfg_dir.name == "local" else f"Systemprofil ({cfg_dir})"
        lbl_loc = self._make_wrapping_info_label(loc_str, selectable=True)
        d_form.addRow("Speicherort:", lbl_loc)

        gpu_str = ", ".join(f"[{g.index}] {g.name} ({g.backend})" for g in self._gpus) or "Keine dedizierte GPU erkannt"
        lbl_gpu = self._make_wrapping_info_label(gpu_str, selectable=True)
        d_form.addRow("Hardware:", lbl_gpu)

        lbl_notes = self._make_wrapping_info_label("Open Source (MIT) • 100 % lokal ohne Telemetrie")
        d_form.addRow("Hinweise:", lbl_notes)
        layout.addWidget(grp_diag)

        layout.addStretch(1)
        return tab

    @staticmethod
    def _make_wrapping_info_label(text: str, selectable: bool = False) -> QLabel:
        """Create a word-wrapping info label that expands cleanly in QFormLayout."""
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        if selectable:
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return lbl

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

    def _sync_theme_dropdown_from_buttons(self) -> None:
        """Select matching theme preset in cmb_theme or 'Benutzerdefiniert'."""
        current = {
            "primary": self.btn_col_primary.hex_color,
            "secondary": self.btn_col_secondary.hex_color,
            "temp": self.btn_col_temp.hex_color,
            "vram": self.btn_col_vram.hex_color,
            "bg": self.btn_col_bg.hex_color,
            "border": self.btn_col_border.hex_color,
            "grid": self.btn_col_grid.hex_color,
            "title": self.btn_col_title.hex_color,
            "muted": self.btn_col_muted.hex_color,
        }
        for name, preset in THEMES.items():
            if all(current[k].upper() == preset[k].upper() for k in current):
                self.cmb_theme.setCurrentText(name)
                return
        self.cmb_theme.setCurrentText("Benutzerdefiniert")

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
        for cmb, attr in (
            (self.cmb_cpu_viz, "cpu_viz_mode"),
            (self.cmb_ram_viz, "ram_viz_mode"),
            (self.cmb_pf_viz, "pf_viz_mode"),
            (self.cmb_disk_viz, "disk_viz_mode"),
        ):
            v_idx = cmb.findData(getattr(self.config, attr))
            cmb.setCurrentIndex(v_idx if v_idx >= 0 else 0)
        self.chk_clock_sec.setChecked(self.config.clock_show_seconds)
        self.chk_clock_uptime.setChecked(self.config.clock_show_uptime)
        self.chk_clock_24h.setChecked(self.config.clock_24h)
        self.chk_storage_free_first.setChecked(self.config.storage_show_free_first)
        self.chk_storage_dedup.setChecked(self.config.storage_deduplicate_devices)
        self.chk_storage_boot.setChecked(self.config.storage_show_boot)
        self.spn_storage_warn.setValue(self.config.storage_warn_percent)
        hidden_mounts = set(self.config.storage_hidden_mountpoints)
        for mp, chk in self._storage_drive_checks.items():
            chk.setChecked(mp not in hidden_mounts)

        self._sync_theme_dropdown_from_buttons()

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
        for cmb, attr in (
            (self.cmb_cpu_viz, "cpu_viz_mode"),
            (self.cmb_ram_viz, "ram_viz_mode"),
            (self.cmb_pf_viz, "pf_viz_mode"),
            (self.cmb_disk_viz, "disk_viz_mode"),
        ):
            setattr(self.config, attr, str(cmb.currentData() or "graph"))
        self.config.clock_show_seconds = self.chk_clock_sec.isChecked()
        self.config.clock_show_uptime = self.chk_clock_uptime.isChecked()
        self.config.clock_24h = self.chk_clock_24h.isChecked()
        self.config.storage_show_free_first = self.chk_storage_free_first.isChecked()
        self.config.storage_deduplicate_devices = self.chk_storage_dedup.isChecked()
        self.config.storage_show_boot = self.chk_storage_boot.isChecked()
        self.config.storage_warn_percent = self.spn_storage_warn.value()
        self.config.storage_hidden_mountpoints = [
            mp for mp, chk in self._storage_drive_checks.items() if not chk.isChecked()
        ]

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
        for cmb in (self.cmb_cpu_viz, self.cmb_ram_viz, self.cmb_pf_viz, self.cmb_disk_viz):
            cmb.setCurrentIndex(0)
        self.chk_clock_sec.setChecked(defaults.clock_show_seconds)
        self.chk_clock_uptime.setChecked(defaults.clock_show_uptime)
        self.chk_clock_24h.setChecked(defaults.clock_24h)
        self.chk_storage_free_first.setChecked(defaults.storage_show_free_first)
        self.chk_storage_dedup.setChecked(defaults.storage_deduplicate_devices)
        self.chk_storage_boot.setChecked(defaults.storage_show_boot)
        self.spn_storage_warn.setValue(defaults.storage_warn_percent)
        for chk in self._storage_drive_checks.values():
            chk.setChecked(True)
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
        self._sync_theme_dropdown_from_buttons()

    def _apply_changes(self) -> None:
        self._save_to_config()
        self._on_apply()

    def _accept_changes(self) -> None:
        self._apply_changes()
        self.accept()

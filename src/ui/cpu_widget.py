"""CPU, RAM & Disk I/O Live Telemetry Widget."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QStackedWidget, QVBoxLayout, QWidget

from src.config import AppConfig, CPU_VIZ_MODES, DISK_VIZ_MODES, PF_VIZ_MODES, RAM_VIZ_MODES
from src.sensors.models import SystemSnapshot
from src.ui.base_widget import BaseDesktopWidget
from src.ui.graph_canvas import MiniLiveGraphWidget
from src.ui.visualizers import (
    ActivityLedsWidget,
    CoreBarsWidget,
    CoreHeatmapWidget,
    DualIoMeterWidget,
    ImpulseBarsWidget,
    PulseMeterWidget,
    RamGridBoxWidget,
    RamSegmentedBarWidget,
)


class CpuSystemWidget(BaseDesktopWidget):
    """Frameless CPU, RAM & Disk I/O monitor with stacked live graphs and compact mode."""

    def __init__(self, config: AppConfig) -> None:
        super().__init__("cpu", "CPU & System", config)
        self._build_ui()
        self.on_apply_config()

    def _build_ui(self) -> None:
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 8, 10, 8)
        self._layout.setSpacing(4)

        # Header
        hdr = QHBoxLayout()
        hdr.setSpacing(6)
        self.lbl_title = QLabel("CPU & System")
        self.lbl_temp_pill = QLabel("")
        self.lbl_temp_pill.setVisible(False)
        self.btn_settings = self.create_gear_button()
        hdr.addWidget(self.lbl_title, 1)
        hdr.addWidget(self.lbl_temp_pill)
        hdr.addWidget(self.btn_settings)
        self._layout.addLayout(hdr)

        self._hdr_line = QFrame()
        self._hdr_line.setFrameShape(QFrame.Shape.HLine)
        self._hdr_line.setFixedHeight(1)
        self._layout.addWidget(self._hdr_line)

        # Section 1: CPU
        self._sec_cpu = QWidget()
        v1 = QVBoxLayout(self._sec_cpu)
        v1.setContentsMargins(0, 0, 0, 0)
        v1.setSpacing(2)
        r1 = QHBoxLayout()
        self.lbl_cpu = QLabel("CPU: --%")
        self.lbl_cpu_clk = QLabel("-- MHz")
        self.lbl_cpu_clk.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        r1.addWidget(self.lbl_cpu)
        r1.addStretch(1)
        r1.addWidget(self.lbl_cpu_clk)
        self.graph_cpu = MiniLiveGraphWidget(self.config.history_seconds, self.config.primary_color, self.config.grid_color, 100.0)
        self.viz_cpu_bars = CoreBarsWidget(self.config.primary_color, self.config.grid_color, self.config.temp_color)
        self.viz_cpu_heatmap = CoreHeatmapWidget(self.config.primary_color, self.config.grid_color, self.config.temp_color)
        self.stack_cpu = QStackedWidget()
        self.stack_cpu.addWidget(self.graph_cpu)
        self.stack_cpu.addWidget(self.viz_cpu_bars)
        self.stack_cpu.addWidget(self.viz_cpu_heatmap)
        v1.addLayout(r1)
        v1.addWidget(self.stack_cpu)
        self._layout.addWidget(self._sec_cpu, 1)

        # Section 2: RAM
        self._sec_ram = QWidget()
        v2 = QVBoxLayout(self._sec_ram)
        v2.setContentsMargins(0, 0, 0, 0)
        v2.setSpacing(2)
        r2 = QHBoxLayout()
        self.lbl_ram = QLabel("RAM: -- GB")
        self.lbl_ram_pct = QLabel("--%")
        self.lbl_ram_pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        r2.addWidget(self.lbl_ram)
        r2.addStretch(1)
        r2.addWidget(self.lbl_ram_pct)
        self.graph_ram = MiniLiveGraphWidget(self.config.history_seconds, self.config.secondary_color, self.config.grid_color, 100.0)
        self.viz_ram_grid = RamGridBoxWidget(self.config.secondary_color, self.config.grid_color)
        self.viz_ram_bar = RamSegmentedBarWidget(self.config.secondary_color, self.config.grid_color, self.config.muted_color)
        self.stack_ram = QStackedWidget()
        self.stack_ram.addWidget(self.graph_ram)
        self.stack_ram.addWidget(self.viz_ram_grid)
        self.stack_ram.addWidget(self.viz_ram_bar)
        v2.addLayout(r2)
        v2.addWidget(self.stack_ram)
        self._layout.addWidget(self._sec_ram, 1)

        # Section 3: Hard Page Faults / sec (optional)
        self._sec_pf = QWidget()
        v_pf = QVBoxLayout(self._sec_pf)
        v_pf.setContentsMargins(0, 0, 0, 0)
        v_pf.setSpacing(2)
        r_pf = QHBoxLayout()
        self.lbl_pf = QLabel("PageFaults/sec: 0")
        self.lbl_pf_max = QLabel("Max: 128")
        self.lbl_pf_max.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        r_pf.addWidget(self.lbl_pf)
        r_pf.addStretch(1)
        r_pf.addWidget(self.lbl_pf_max)
        self.graph_pf = MiniLiveGraphWidget(
            self.config.history_seconds,
            self.config.vram_color,
            self.config.grid_color,
            128.0,
            dynamic_scale=True,
            min_ceiling=128.0,
        )
        self.viz_pf_pulse = PulseMeterWidget(self.config.vram_color, self.config.grid_color, self.config.temp_color)
        self.viz_pf_impulse = ImpulseBarsWidget(self.config.history_seconds, self.config.vram_color, self.config.grid_color, self.config.temp_color)
        self.stack_pf = QStackedWidget()
        self.stack_pf.addWidget(self.graph_pf)
        self.stack_pf.addWidget(self.viz_pf_pulse)
        self.stack_pf.addWidget(self.viz_pf_impulse)
        v_pf.addLayout(r_pf)
        v_pf.addWidget(self.stack_pf)
        self._layout.addWidget(self._sec_pf, 1)

        # Section 4: Disk I/O
        self._sec_disk = QWidget()
        v3 = QVBoxLayout(self._sec_disk)
        v3.setContentsMargins(0, 0, 0, 0)
        v3.setSpacing(2)
        r3 = QHBoxLayout()
        self.lbl_disk_r = QLabel("Disk R: 0.0 MB/s")
        self.lbl_disk_w = QLabel("W: 0.0 MB/s")
        self.lbl_disk_w.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        r3.addWidget(self.lbl_disk_r)
        r3.addStretch(1)
        r3.addWidget(self.lbl_disk_w)
        self.graph_disk = MiniLiveGraphWidget(
            self.config.history_seconds,
            self.config.vram_color,
            self.config.grid_color,
            100.0,
            dynamic_scale=True,
        )
        self.viz_disk_meter = DualIoMeterWidget(self.config.vram_color, self.config.secondary_color, self.config.grid_color)
        self.viz_disk_leds = ActivityLedsWidget(self.config.vram_color, self.config.secondary_color, self.config.grid_color)
        self.stack_disk = QStackedWidget()
        self.stack_disk.addWidget(self.graph_disk)
        self.stack_disk.addWidget(self.viz_disk_meter)
        self.stack_disk.addWidget(self.viz_disk_leds)
        v3.addLayout(r3)
        v3.addWidget(self.stack_disk)
        self._layout.addWidget(self._sec_disk, 1)

    def on_apply_config(self) -> None:
        m = self.sc(9)
        self._layout.setContentsMargins(m, self.sc(7), m, self.sc(7))
        self._layout.setSpacing(self.sc(4))

        self.lbl_title.setFont(self.make_font(10.0, bold=True))
        self.lbl_title.setStyleSheet(f"color: {self.config.title_color};")
        self.style_gear_button(self.btn_settings)

        line_col = QColor(self.config.border_color)
        self._hdr_line.setStyleSheet(
            f"background-color: rgba({line_col.red()}, {line_col.green()}, {line_col.blue()}, 95); border: none;"
        )

        self.lbl_temp_pill.setFont(self.make_font(8.5, bold=True))
        self.lbl_temp_pill.setStyleSheet(
            f"color: {self.config.temp_color}; border: 1px solid {self.config.temp_color}; border-radius: {self.sc(4)}px; padding: 1px {self.sc(5)}px;"
        )

        val_font = self.make_font(9.0, bold=True)
        sub_font = self.make_font(8.5, bold=False)
        for lbl in (self.lbl_cpu, self.lbl_ram, self.lbl_pf, self.lbl_disk_r):
            lbl.setFont(val_font)
            lbl.setStyleSheet(f"color: {self.config.title_color};")
        for lbl in (self.lbl_cpu_clk, self.lbl_ram_pct, self.lbl_pf_max):
            lbl.setFont(sub_font)
            lbl.setStyleSheet(f"color: {self.config.muted_color};")
        self.lbl_disk_w.setFont(sub_font)
        self.lbl_disk_w.setStyleSheet(f"color: {self.config.secondary_color};")

        self.graph_cpu.set_colors(self.config.primary_color, self.config.grid_color)
        self.viz_cpu_bars.set_colors(self.config.primary_color, self.config.grid_color, accent_color=self.config.temp_color)
        self.viz_cpu_heatmap.set_colors(self.config.primary_color, self.config.grid_color, accent_color=self.config.temp_color)

        self.graph_ram.set_colors(self.config.secondary_color, self.config.grid_color)
        self.viz_ram_grid.set_colors(self.config.secondary_color, self.config.grid_color)
        self.viz_ram_bar.set_colors(self.config.secondary_color, self.config.grid_color, muted_color=self.config.muted_color)

        self.graph_pf.set_colors(self.config.vram_color, self.config.grid_color)
        self.viz_pf_pulse.set_colors(self.config.vram_color, self.config.grid_color, accent_color=self.config.temp_color)
        self.viz_pf_impulse.set_colors(self.config.vram_color, self.config.grid_color, accent_color=self.config.temp_color)

        self.graph_disk.set_colors(self.config.vram_color, self.config.grid_color, self.config.secondary_color)
        self.viz_disk_meter.set_colors(self.config.vram_color, self.config.grid_color, secondary_color=self.config.secondary_color)
        self.viz_disk_leds.set_colors(self.config.vram_color, self.config.grid_color, secondary_color=self.config.secondary_color)

        for g in (self.graph_cpu, self.graph_ram, self.graph_pf, self.graph_disk, self.viz_pf_impulse):
            g.set_history_length(self.config.history_seconds)

        for w in (
            self.graph_cpu,
            self.viz_cpu_bars,
            self.viz_cpu_heatmap,
            self.graph_ram,
            self.viz_ram_grid,
            self.viz_ram_bar,
            self.graph_pf,
            self.viz_pf_pulse,
            self.viz_pf_impulse,
            self.graph_disk,
            self.viz_disk_meter,
            self.viz_disk_leds,
        ):
            w.set_ui_scale(self.ui_scale)

        self.stack_cpu.setCurrentIndex(CPU_VIZ_MODES.index(self.config.cpu_viz_mode) if self.config.cpu_viz_mode in CPU_VIZ_MODES else 0)
        self.stack_ram.setCurrentIndex(RAM_VIZ_MODES.index(self.config.ram_viz_mode) if self.config.ram_viz_mode in RAM_VIZ_MODES else 0)
        self.stack_pf.setCurrentIndex(PF_VIZ_MODES.index(self.config.pf_viz_mode) if self.config.pf_viz_mode in PF_VIZ_MODES else 0)
        self.stack_disk.setCurrentIndex(DISK_VIZ_MODES.index(self.config.disk_viz_mode) if self.config.disk_viz_mode in DISK_VIZ_MODES else 0)

        self._sec_pf.setVisible(self.config.cpu_show_page_faults)
        self._sec_disk.setVisible(self.config.cpu_show_disk_io)
        disk_label = self.config.cpu_disk_device or "Alle Datenträger (Summe)"
        self.lbl_disk_r.setToolTip(f"Überwachtes Laufwerk: {disk_label}")

        active_sections = 2 + int(self.config.cpu_show_page_faults) + int(self.config.cpu_show_disk_io)
        self.setMinimumSize(self.sc(220), self.sc(44 + active_sections * 46))

    def update_snapshot(self, snapshot: SystemSnapshot) -> None:
        """Render the latest CPU, RAM and Disk I/O telemetry."""
        cpu = snapshot.cpu

        if cpu.cpu_temp_c is not None:
            self.lbl_temp_pill.setText(f"{cpu.cpu_temp_c:.0f} °C")
            self.lbl_temp_pill.setVisible(True)
        else:
            self.lbl_temp_pill.setVisible(False)

        cpu_txt = f"CPU: {cpu.cpu_percent:.1f}%"
        if self.config.cpu_show_max_core:
            cpu_txt += f" (Max-Kern {cpu.cpu_max_core_percent:.0f}%)"
        self.lbl_cpu.setText(cpu_txt)
        self.lbl_cpu_clk.setText(f"{cpu.cpu_freq_mhz:.0f} MHz" if cpu.cpu_freq_mhz else "")
        self.graph_cpu.push_value(cpu.cpu_percent, 100.0)
        self.viz_cpu_bars.push_cores(cpu.cpu_cores, cpu.cpu_percent)
        self.viz_cpu_heatmap.push_cores(cpu.cpu_cores, cpu.cpu_percent)

        self.lbl_ram.setText(f"RAM: {cpu.ram_used_gb:.1f} / {cpu.ram_total_gb:.1f} GB")
        self.lbl_ram_pct.setText(f"{cpu.ram_percent:.1f}%")
        self.graph_ram.push_value(cpu.ram_percent, 100.0)
        self.viz_ram_grid.push_memory(cpu.ram_percent, cpu.ram_total_gb)
        self.viz_ram_bar.push_memory(cpu.ram_percent, cpu.ram_total_gb)

        if self.config.cpu_show_page_faults:
            pf_val = cpu.page_faults_per_sec if cpu.page_faults_per_sec is not None else 0.0
            self.graph_pf.push_value(pf_val)
            self.viz_pf_pulse.push_value(pf_val)
            self.viz_pf_impulse.push_value(pf_val)
            self.lbl_pf.setText(f"PageFaults/sec: {pf_val:.0f}")
            active_pf = self.stack_pf.currentWidget()
            ceiling = active_pf.current_ceiling() if hasattr(active_pf, "current_ceiling") else self.graph_pf.current_ceiling()
            self.lbl_pf_max.setText(f"Max: {ceiling:.0f}")

        if self.config.cpu_show_disk_io:
            self.lbl_disk_r.setText(f"Disk R: {cpu.disk_read_mb_s:.1f} MB/s")
            self.lbl_disk_w.setText(f"W: {cpu.disk_write_mb_s:.1f} MB/s")
            self.graph_disk.push_value(cpu.disk_read_mb_s, secondary_value=cpu.disk_write_mb_s)
            self.viz_disk_meter.push_io(cpu.disk_read_mb_s, cpu.disk_write_mb_s)
            self.viz_disk_leds.push_io(cpu.disk_read_mb_s, cpu.disk_write_mb_s)

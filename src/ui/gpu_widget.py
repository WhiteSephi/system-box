"""GPU Live Telemetry Widget (Utilization, Clocks, Temp/Fan/Power, VRAM & Throttle status)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.config import AppConfig
from src.sensors.models import GpuSample, SystemSnapshot
from src.ui.base_widget import BaseDesktopWidget
from src.ui.graph_canvas import MiniLiveGraphWidget


class GpuWidget(BaseDesktopWidget):
    """Frameless GPU monitor with stacked live graphs and compact mode."""

    def __init__(self, config: AppConfig) -> None:
        super().__init__("gpu", "GPU-Monitor", config)
        self._last_gpu = GpuSample()
        self._build_ui()
        self.on_apply_config()

    def _build_ui(self) -> None:
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 8, 10, 8)
        self._layout.setSpacing(4)

        # Header
        hdr = QHBoxLayout()
        hdr.setSpacing(6)
        self.lbl_title = QLabel("GPU")
        self.lbl_throttle = QLabel("")
        self.lbl_throttle.setVisible(False)
        hdr.addWidget(self.lbl_title, 1)
        hdr.addWidget(self.lbl_throttle)
        self._layout.addLayout(hdr)

        # Compact single-line summary
        self.lbl_compact = QLabel("GPU: --")
        self.lbl_compact.setWordWrap(True)
        self.lbl_compact.setVisible(False)
        self._layout.addWidget(self.lbl_compact)

        # Section 1: Utilization & Clock
        self._sec_util = QWidget()
        v1 = QVBoxLayout(self._sec_util)
        v1.setContentsMargins(0, 0, 0, 0)
        v1.setSpacing(2)
        r1 = QHBoxLayout()
        self.lbl_util = QLabel("GPU: -- %")
        self.lbl_clock = QLabel("-- MHz")
        self.lbl_clock.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        r1.addWidget(self.lbl_util)
        r1.addStretch(1)
        r1.addWidget(self.lbl_clock)
        self.graph_util = MiniLiveGraphWidget(self.config.history_seconds, self.config.primary_color, self.config.grid_color, 100.0)
        v1.addLayout(r1)
        v1.addWidget(self.graph_util)
        self._layout.addWidget(self._sec_util, 1)

        # Section 2: Temperature, Fan & Power
        self._sec_temp = QWidget()
        v2 = QVBoxLayout(self._sec_temp)
        v2.setContentsMargins(0, 0, 0, 0)
        v2.setSpacing(2)
        r2 = QHBoxLayout()
        r2.setSpacing(6)
        self.lbl_temp = QLabel("-- °C")
        self.lbl_fan_pwr = QLabel("")
        self.lbl_fan_pwr.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_power = QLabel("")
        self.lbl_power.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        r2.addWidget(self.lbl_temp)
        r2.addStretch(1)
        r2.addWidget(self.lbl_fan_pwr)
        r2.addWidget(self.lbl_power)
        self.graph_temp = MiniLiveGraphWidget(self.config.history_seconds, self.config.temp_color, self.config.grid_color, 100.0)
        v2.addLayout(r2)
        v2.addWidget(self.graph_temp)
        self._layout.addWidget(self._sec_temp, 1)

        # Section 3: VRAM
        self._sec_vram = QWidget()
        v3 = QVBoxLayout(self._sec_vram)
        v3.setContentsMargins(0, 0, 0, 0)
        v3.setSpacing(2)
        r3 = QHBoxLayout()
        self.lbl_vram_used = QLabel("VRAM: --")
        self.lbl_vram_total = QLabel("")
        self.lbl_vram_total.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        r3.addWidget(self.lbl_vram_used)
        r3.addStretch(1)
        r3.addWidget(self.lbl_vram_total)
        self.graph_vram = MiniLiveGraphWidget(self.config.history_seconds, self.config.vram_color, self.config.grid_color, 100.0)
        v3.addLayout(r3)
        v3.addWidget(self.graph_vram)
        self._layout.addWidget(self._sec_vram, 1)

    def on_apply_config(self) -> None:
        compact = self.config.get_widget("gpu").compact_mode
        m = self.sc(9)
        self._layout.setContentsMargins(m, self.sc(7), m, self.sc(7))
        self._layout.setSpacing(self.sc(4))

        self.lbl_title.setFont(self.make_font(10.0, bold=True))
        self.lbl_title.setStyleSheet(f"color: {self.config.title_color};")

        self.lbl_throttle.setFont(self.make_font(7.5, bold=True))
        self.lbl_throttle.setStyleSheet(
            f"color: #FFFFFF; background-color: {self.config.temp_color}; border-radius: {self.sc(3)}px; padding: 1px {self.sc(4)}px;"
        )

        val_font = self.make_font(9.0, bold=True)
        sub_font = self.make_font(8.5, bold=False)
        for lbl in (self.lbl_util, self.lbl_temp, self.lbl_vram_used):
            lbl.setFont(val_font)
            lbl.setStyleSheet(f"color: {self.config.title_color};")
        for lbl in (self.lbl_clock, self.lbl_fan_pwr, self.lbl_vram_total):
            lbl.setFont(sub_font)
            lbl.setStyleSheet(f"color: {self.config.muted_color};")

        self.lbl_power.setFont(val_font)
        self.lbl_power.setStyleSheet(f"color: {self.config.secondary_color};")

        self.lbl_compact.setFont(self.make_font(9.5, bold=True))
        self.lbl_compact.setStyleSheet(f"color: {self.config.title_color};")

        self.graph_util.set_colors(self.config.primary_color, self.config.grid_color)
        self.graph_temp.set_colors(self.config.temp_color, self.config.grid_color, self.config.secondary_color)
        self.graph_vram.set_colors(self.config.vram_color, self.config.grid_color)

        for g in (self.graph_util, self.graph_temp, self.graph_vram):
            g.set_ui_scale(self.ui_scale)
            g.set_history_length(self.config.history_seconds)

        self.lbl_compact.setVisible(compact)
        self._sec_util.setVisible(not compact)
        self._sec_temp.setVisible(not compact)
        self._sec_vram.setVisible(not compact)

        if compact:
            self.setMinimumSize(self.sc(180), self.sc(62))
        else:
            self.setMinimumSize(self.sc(220), self.sc(175))

    def update_snapshot(self, snapshot: SystemSnapshot) -> None:
        """Render the latest GPU telemetry sample."""
        gpu = snapshot.active_gpu
        self._last_gpu = gpu
        self.lbl_title.setText(gpu.name)

        if not gpu.available:
            self.lbl_util.setText("GPU: nicht verfügbar")
            self.lbl_clock.setText("")
            self.lbl_temp.setText("--")
            self.lbl_fan_pwr.setText("")
            self.lbl_power.setText("")
            self.lbl_vram_used.setText("VRAM: --")
            self.lbl_vram_total.setText("")
            self.lbl_compact.setText("Keine GPU-Sensoren verfügbar")
            self.lbl_throttle.setVisible(False)
            return

        if gpu.throttle_reasons:
            self.lbl_throttle.setText(" / ".join(gpu.throttle_reasons))
            self.lbl_throttle.setVisible(True)
        else:
            self.lbl_throttle.setVisible(False)

        util_txt = f"{gpu.util_percent:.0f} %" if gpu.util_percent is not None else "-- %"
        clk_txt = f"{gpu.clock_mhz} MHz" if gpu.clock_mhz is not None else ""
        self.lbl_util.setText(f"GPU: {util_txt}")
        self.lbl_clock.setText(clk_txt)
        if gpu.util_percent is not None:
            self.graph_util.push_value(gpu.util_percent, 100.0)

        temp_txt = f"{gpu.temp_c:.0f} °C" if gpu.temp_c is not None else "Temp: --"
        self.lbl_temp.setText(temp_txt)

        pwr_pct: float | None = None
        if self.config.gpu_show_power_fan and gpu.power_watts is not None:
            if gpu.power_limit_watts and gpu.power_limit_watts > 0:
                pwr_pct = min(100.0, (gpu.power_watts / gpu.power_limit_watts) * 100.0)
                self.lbl_power.setText(f"{gpu.power_watts:.0f}/{gpu.power_limit_watts:.0f} W")
            else:
                self.lbl_power.setText(f"{gpu.power_watts:.0f} W")
            self.lbl_power.setVisible(True)
        else:
            self.lbl_power.setText("")
            self.lbl_power.setVisible(False)

        if gpu.temp_c is not None:
            self.graph_temp.push_value(gpu.temp_c, 100.0, secondary_value=pwr_pct)

        fan_txt = ""
        if self.config.gpu_show_power_fan:
            if gpu.fan_rpm is not None:
                fan_txt = f"{gpu.fan_rpm} RPM"
                if gpu.fan_percent is not None:
                    fan_txt += f" ({gpu.fan_percent}%)"
            elif gpu.fan_percent is not None:
                fan_txt = f"Lüfter {gpu.fan_percent}%"
        self.lbl_fan_pwr.setText(fan_txt)

        vram_pct = 0.0
        if gpu.vram_used_mb is not None and gpu.vram_total_mb:
            vram_pct = (gpu.vram_used_mb / gpu.vram_total_mb) * 100.0
            self.lbl_vram_used.setText(f"VRAM: {gpu.vram_used_mb / 1024.0:.1f} GB ({vram_pct:.0f}%)")
            self.lbl_vram_total.setText(f"{gpu.vram_total_mb / 1024.0:.1f} GB")
            vram_col = self.config.temp_color if vram_pct >= self.config.gpu_vram_warn_percent else self.config.vram_color
            self.graph_vram.set_colors(vram_col, self.config.grid_color)
            self.graph_vram.push_value(vram_pct, 100.0)
        elif gpu.vram_used_mb is not None:
            self.lbl_vram_used.setText(f"VRAM: {gpu.vram_used_mb:.0f} MB")
            self.lbl_vram_total.setText("")
        else:
            self.lbl_vram_used.setText("VRAM: --")
            self.lbl_vram_total.setText("")

        # Compact text
        parts = [f"GPU {util_txt}"]
        if gpu.temp_c is not None:
            parts.append(f"{gpu.temp_c:.0f}°C")
        if gpu.vram_used_mb is not None and gpu.vram_total_mb:
            parts.append(f"{gpu.vram_used_mb / 1024.0:.1f}/{gpu.vram_total_mb / 1024.0:.1f} GB")
        if self.config.gpu_show_power_fan and gpu.power_watts is not None:
            parts.append(f"{gpu.power_watts:.0f}W")
        self.lbl_compact.setText(" • ".join(parts))

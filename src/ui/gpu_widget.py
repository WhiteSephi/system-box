"""GPU Live Telemetry Widget (Utilization, Clocks, Temp/Fan/Power, VRAM & Throttle status)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from src.config import AppConfig
from src.sensors.models import GpuSample, SystemSnapshot
from src.ui.base_widget import BaseDesktopWidget
from src.ui.graph_canvas import MiniLiveGraphWidget


class FanIconWidget(QWidget):
    """Crisp vector-drawn 3-blade fan icon scaled to widget font size."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = QColor("#9AA0A6")
        self.setFixedSize(12, 12)

    def set_color(self, hex_color: str) -> None:
        self._color = QColor(hex_color)
        self.update()

    def set_icon_size(self, px: int) -> None:
        size = max(10, px)
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._color)

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        r = min(self.width(), self.height()) * 0.46

        blade = QPainterPath()
        blade.moveTo(0.0, -r * 0.16)
        blade.cubicTo(r * 0.58, -r * 0.28, r * 0.56, -r * 0.88, 0.0, -r)
        blade.cubicTo(-r * 0.34, -r * 0.84, -r * 0.28, -r * 0.36, 0.0, -r * 0.16)

        for angle in (0, 120, 240):
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(angle)
            painter.drawPath(blade)
            painter.restore()

        hub_r = max(1.3, r * 0.22)
        painter.drawEllipse(QPointF(cx, cy), hub_r, hub_r)


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
        self.lbl_title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.lbl_throttle = QLabel("")
        self.lbl_throttle.setVisible(False)
        self.btn_settings = self.create_gear_button()
        hdr.addWidget(self.lbl_title, 1)
        hdr.addWidget(self.lbl_throttle)
        hdr.addWidget(self.btn_settings)
        self._layout.addLayout(hdr)

        self._hdr_line = QFrame()
        self._hdr_line.setFrameShape(QFrame.Shape.HLine)
        self._hdr_line.setFixedHeight(1)
        self._layout.addWidget(self._hdr_line)

        # Section 1: Utilization & Clock
        self._sec_util = QWidget()
        v1 = QVBoxLayout(self._sec_util)
        v1.setContentsMargins(0, 0, 0, 0)
        v1.setSpacing(2)
        r1 = QHBoxLayout()
        self.lbl_util = QLabel("GPU: --%")
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
        self._r2 = QHBoxLayout()
        self._r2.setSpacing(4)

        self._temp_box = QWidget()
        self._temp_box.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        l_temp = QHBoxLayout(self._temp_box)
        l_temp.setContentsMargins(0, 0, 0, 0)
        self.lbl_temp = QLabel("-- °C")
        l_temp.addWidget(self.lbl_temp)
        l_temp.addStretch(1)

        self._fan_box = QWidget()
        self._fan_box.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self._fan_layout = QHBoxLayout(self._fan_box)
        self._fan_layout.setContentsMargins(0, 0, 0, 0)
        self._fan_layout.setSpacing(4)
        self.fan_icon = FanIconWidget(self._fan_box)
        self.lbl_fan_pwr = QLabel("")
        self.lbl_fan_pwr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._fan_layout.addWidget(self.fan_icon)
        self._fan_layout.addWidget(self.lbl_fan_pwr)

        self._pwr_box = QWidget()
        self._pwr_box.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._pwr_layout = QHBoxLayout(self._pwr_box)
        self._pwr_layout.setContentsMargins(0, 0, 0, 0)
        self._pwr_layout.setSpacing(4)
        self.lbl_power_max = QLabel("")
        self.lbl_power_max.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_power = QLabel("")
        self.lbl_power.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._pwr_layout.addStretch(1)
        self._pwr_layout.addWidget(self.lbl_power_max)
        self._pwr_layout.addWidget(self.lbl_power)

        self._r2.addWidget(self._temp_box, 1)
        self._r2.addWidget(self._fan_box, 0)
        self._r2.addWidget(self._pwr_box, 1)
        self.graph_temp = MiniLiveGraphWidget(self.config.history_seconds, self.config.temp_color, self.config.grid_color, 100.0)
        v2.addLayout(self._r2)
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

        self.lbl_throttle.setFont(self.make_font(7.5, bold=True))
        self.lbl_throttle.setStyleSheet(
            f"color: #FFFFFF; background-color: {self.config.temp_color}; border-radius: {self.sc(3)}px; padding: 1px {self.sc(4)}px;"
        )

        val_font = self.make_font(9.0, bold=True)
        sub_font = self.make_font(8.5, bold=False)
        for lbl in (self.lbl_util, self.lbl_vram_used):
            lbl.setFont(val_font)
            lbl.setStyleSheet(f"color: {self.config.title_color};")
        self.lbl_temp.setFont(val_font)
        self.lbl_temp.setStyleSheet(f"color: {self.config.temp_color};")
        for lbl in (self.lbl_clock, self.lbl_fan_pwr, self.lbl_power_max, self.lbl_vram_total):
            lbl.setFont(sub_font)
            lbl.setStyleSheet(f"color: {self.config.muted_color};")

        self.fan_icon.set_color(self.config.muted_color)
        self.fan_icon.set_icon_size(self.sc(12))
        self._fan_layout.setSpacing(self.sc(4))

        self.lbl_power.setFont(val_font)
        self.lbl_power.setStyleSheet(f"color: {self.config.secondary_color};")

        self.graph_util.set_colors(self.config.primary_color, self.config.grid_color)
        self.graph_temp.set_colors(self.config.temp_color, self.config.grid_color, self.config.secondary_color)
        if not self.config.gpu_show_power_fan:
            self.graph_temp.set_secondary_enabled(False)
        self.graph_vram.set_colors(self.config.vram_color, self.config.grid_color)

        for g in (self.graph_util, self.graph_temp, self.graph_vram):
            g.set_ui_scale(self.ui_scale)
            g.set_history_length(self.config.history_seconds)

        self.setMinimumSize(self.sc(220), self.sc(175))
        self._apply_row2_responsive()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._apply_row2_responsive()

    def _apply_row2_responsive(self) -> None:
        """Progressively trim optional Row 2 details when widget width is narrow."""
        gpu = self._last_gpu
        if not gpu.available or not self.config.gpu_show_power_fan:
            self.lbl_power_max.setVisible(False)
            self._fan_box.setVisible(False)
            return

        has_pwr = gpu.power_watts is not None
        has_limit = has_pwr and bool(gpu.power_limit_watts and gpu.power_limit_watts > 0)
        pwr_max_full = f"max {gpu.power_limit_watts:.0f} /" if has_limit else ""

        fan_full = ""
        fan_rpm_only = ""
        fan_pct_only = ""
        if gpu.fan_rpm is not None:
            fan_rpm_only = f"{gpu.fan_rpm} RPM"
            fan_full = f"{fan_rpm_only} ({gpu.fan_percent}%)" if gpu.fan_percent is not None else fan_rpm_only
            if gpu.fan_percent is not None:
                fan_pct_only = f"{gpu.fan_percent}%"
        elif gpu.fan_percent is not None:
            fan_full = fan_pct_only = f"{gpu.fan_percent}%"

        candidates = [
            (fan_full, pwr_max_full),
            (fan_rpm_only or fan_full, pwr_max_full),
            (fan_rpm_only or fan_full, ""),
            (fan_pct_only, ""),
            ("", ""),
        ]

        margins = self._layout.contentsMargins()
        row_w = max(1, self.width() - margins.left() - margins.right())

        fm_sub = self.lbl_fan_pwr.fontMetrics()
        fm_val = self.lbl_power.fontMetrics()
        need_left = self.lbl_temp.fontMetrics().horizontalAdvance(self.lbl_temp.text())
        pwr_w = fm_val.horizontalAdvance(self.lbl_power.text()) if has_pwr else 0

        chosen_fan, chosen_max = candidates[-1]
        for cand_fan, cand_max in candidates:
            fan_w = (self.fan_icon.width() + self._fan_layout.spacing() + fm_sub.horizontalAdvance(cand_fan)) if cand_fan else 0
            max_w = (fm_sub.horizontalAdvance(cand_max) + self._pwr_layout.spacing()) if cand_max else 0
            need_right = max_w + pwr_w
            side_w = (row_w - fan_w - 2 * self._r2.spacing()) / 2.0
            if need_left <= side_w and need_right <= side_w:
                chosen_fan, chosen_max = cand_fan, cand_max
                break

        self.lbl_fan_pwr.setText(chosen_fan)
        self._fan_box.setVisible(bool(chosen_fan))
        self.lbl_power_max.setText(chosen_max)
        self.lbl_power_max.setVisible(bool(chosen_max))
        self._fan_box.updateGeometry()
        self._r2.invalidate()

    def update_snapshot(self, snapshot: SystemSnapshot) -> None:
        """Render the latest GPU telemetry sample."""
        gpu = snapshot.active_gpu
        self._last_gpu = gpu
        if self.config.gpu_show_driver_version and gpu.driver_version:
            self.lbl_title.setText(f"{gpu.name} (v{gpu.driver_version})")
            self.lbl_title.setToolTip(f"{gpu.name} · Treiber {gpu.driver_version}")
        else:
            self.lbl_title.setText(gpu.name)
            self.lbl_title.setToolTip("")

        if not gpu.available:
            self.lbl_util.setText("GPU: nicht verfügbar")
            self.lbl_clock.setText("")
            self.lbl_temp.setText("--")
            self.lbl_fan_pwr.setText("")
            self._fan_box.setVisible(False)
            self.lbl_power_max.setText("")
            self.lbl_power_max.setVisible(False)
            self.lbl_power.setText("")
            self.lbl_vram_used.setText("VRAM: --")
            self.lbl_vram_total.setText("")
            self.lbl_throttle.setVisible(False)
            return

        warnings: list[str] = []
        tooltips: list[str] = []
        if gpu.temp_c is not None and gpu.temp_c >= self.config.gpu_temp_warn_c:
            warnings.append(f"TEMP {gpu.temp_c:.0f}°C")
            tooltips.append(f"Temperatur-Warnschwelle ({self.config.gpu_temp_warn_c} °C) erreicht")
        if gpu.throttle_reasons:
            warnings.extend(gpu.throttle_reasons)
            tooltips.append("Drosselung: " + ", ".join(gpu.throttle_reasons))

        if warnings:
            self.lbl_throttle.setText(" / ".join(warnings))
            self.lbl_throttle.setToolTip("\n".join(tooltips))
            self.lbl_throttle.setVisible(True)
        else:
            self.lbl_throttle.setToolTip("")
            self.lbl_throttle.setVisible(False)

        util_txt = f"{gpu.util_percent:.0f}%" if gpu.util_percent is not None else "--%"
        clk_txt = f"{gpu.clock_mhz} MHz" if gpu.clock_mhz is not None else ""
        self.lbl_util.setText(f"GPU: {util_txt}")
        self.lbl_clock.setText(clk_txt)
        if gpu.util_percent is not None:
            self.graph_util.push_value(gpu.util_percent, 100.0)

        temp_txt = f"{gpu.temp_c:.0f} °C" if gpu.temp_c is not None else "Temp: --"
        self.lbl_temp.setText(temp_txt)

        pwr_pct: float | None = None
        if self.config.gpu_show_power_fan and gpu.power_watts is not None:
            self.lbl_power.setText(f"{gpu.power_watts:.0f} W")
            self.lbl_power.setVisible(True)
            if gpu.power_limit_watts and gpu.power_limit_watts > 0:
                pwr_pct = min(100.0, (gpu.power_watts / gpu.power_limit_watts) * 100.0)
        else:
            self.lbl_power.setText("")
            self.lbl_power.setVisible(False)

        if gpu.temp_c is not None:
            self.graph_temp.push_value(gpu.temp_c, 100.0, secondary_value=pwr_pct)

        self._apply_row2_responsive()

        vram_pct = 0.0
        mem_clk_txt = f"{gpu.mem_clock_mhz} MHz" if (self.config.gpu_show_mem_clock and gpu.mem_clock_mhz is not None) else ""
        if gpu.vram_used_mb is not None and gpu.vram_total_mb:
            vram_pct = (gpu.vram_used_mb / gpu.vram_total_mb) * 100.0
            self.lbl_vram_used.setText(f"VRAM: {gpu.vram_used_mb / 1024.0:.1f} GB ({vram_pct:.0f}%)")
            total_txt = f"{gpu.vram_total_mb / 1024.0:.1f} GB"
            self.lbl_vram_total.setText(f"{mem_clk_txt} · {total_txt}" if mem_clk_txt else total_txt)
            self.graph_vram.set_colors(self.config.vram_color, self.config.grid_color)
            self.graph_vram.push_value(vram_pct, 100.0)
        elif gpu.vram_used_mb is not None:
            self.lbl_vram_used.setText(f"VRAM: {gpu.vram_used_mb:.0f} MB")
            self.lbl_vram_total.setText(mem_clk_txt)
        else:
            self.lbl_vram_used.setText("VRAM: --")
            self.lbl_vram_total.setText(mem_clk_txt)

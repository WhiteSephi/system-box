"""PageFault and Disk I/O visualizers (pulse meters, impulse bars, dual I/O bars, LED rows)."""

from __future__ import annotations

from collections import deque
import math

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter

from src.ui.visualizers.base import BaseVisualizerWidget


def _log_ratio(value: float, max_ref: float = 4096.0) -> float:
    """Map a non-negative spike value logarithmically into [0.0, 1.0]."""
    if value <= 0.0:
        return 0.0
    return min(1.0, math.log1p(value) / math.log1p(max_ref))


def _sqrt_ratio(value: float, max_ref: float = 1000.0) -> float:
    """Map MB/s throughput with sqrt curve so both 0.4 MB/s and 500+ MB/s are visible."""
    if value <= 0.0:
        return 0.0
    return min(1.0, math.sqrt(value) / math.sqrt(max_ref))


class PulseMeterWidget(BaseVisualizerWidget):
    """Logarithmic 16-LED meter with slowly decaying peak-hold marker for PageFaults/sec."""

    def __init__(self, primary_color: str = "#3FB950", grid_color: str = "#32383D", accent_color: str = "#F85149") -> None:
        super().__init__(primary_color=primary_color, grid_color=grid_color, accent_color=accent_color)
        self._current = 0.0
        self._peak_ratio = 0.0
        self._peak_raw = 0.0

    def push_value(self, value: float) -> None:
        """Push latest PageFaults/sec sample and update decaying peak-hold."""
        self._current = max(0.0, float(value))
        ratio = _log_ratio(self._current)
        if ratio >= self._peak_ratio:
            self._peak_ratio = ratio
        else:
            self._peak_ratio = max(ratio, self._peak_ratio * 0.88)
        self._peak_raw = max(128.0, self._current, self._peak_raw * 0.96)
        self.update()

    def current_ceiling(self) -> float:
        """Return recent dynamic ceiling for display in header label."""
        return max(128.0, self._peak_raw)

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        inner = self._begin_frame(painter)

        segments = 16
        ratio = _log_ratio(self._current)
        lit = int(round(ratio * segments))
        peak_idx = int(round(self._peak_ratio * (segments - 1))) if self._peak_ratio > 0.03 else None
        bar_h = min(inner.height(), max(12.0, 18.0 * self._ui_scale))
        y = inner.center().y() - bar_h * 0.5
        self._draw_led_row(painter, QRectF(inner.left(), y, inner.width(), bar_h), segments, lit, self._primary_color, peak_idx)
        painter.end()


class ImpulseBarsWidget(BaseVisualizerWidget):
    """Renders spike history (PageFaults/sec) as crisp vertical impulse needles."""

    def __init__(self, history_len: int = 60, primary_color: str = "#3FB950", grid_color: str = "#32383D", accent_color: str = "#F85149") -> None:
        super().__init__(primary_color=primary_color, grid_color=grid_color, accent_color=accent_color)
        self._history: deque[float] = deque([0.0] * max(15, history_len), maxlen=max(15, history_len))

    def set_history_length(self, length: int) -> None:
        """Resize rolling sample buffer."""
        target = max(15, length)
        if self._history.maxlen != target:
            items = list(self._history)[-target:]
            pad = [0.0] * max(0, target - len(items))
            self._history = deque(pad + items, maxlen=target)
            self.update()

    def push_value(self, value: float) -> None:
        """Append latest sample and trigger repaint."""
        self._history.append(max(0.0, float(value)))
        self.update()

    def current_ceiling(self) -> float:
        """Return dynamic Y-axis ceiling (minimum 128)."""
        peak = max(self._history) if self._history else 0.0
        return max(128.0, peak * 1.2)

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        inner = self._begin_frame(painter)

        samples = list(self._history)
        n = len(samples)
        if n == 0:
            painter.end()
            return
        ceiling = self.current_ceiling()
        step = inner.width() / n
        bar_w = max(1.5, step * 0.62)

        painter.setPen(Qt.PenStyle.NoPen)
        for i, val in enumerate(samples):
            x = inner.left() + i * step
            ratio = min(1.0, val / ceiling)
            h = max(1.0, inner.height() * ratio) if val > 0.0 else 1.0
            col = self._accent_color if ratio >= 0.75 else self._primary_color
            if val <= 0.0:
                col = QColor(self._grid_color)
                col.setAlpha(150)
            painter.setBrush(col)
            painter.drawRoundedRect(QRectF(x, inner.bottom() - h, bar_w, h), 1.0, 1.0)
        painter.end()


class DualIoMeterWidget(BaseVisualizerWidget):
    """Dual horizontal Read/Write throughput bars with sqrt scaling and peak-hold markers."""

    def __init__(self, read_color: str = "#3FB950", write_color: str = "#FFEA00", grid_color: str = "#32383D") -> None:
        super().__init__(primary_color=read_color, grid_color=grid_color, secondary_color=write_color)
        self._read = 0.0
        self._write = 0.0
        self._read_peak = 0.0
        self._write_peak = 0.0

    def push_io(self, read_mb_s: float, write_mb_s: float) -> None:
        """Update Read/Write MB/s values and decaying peak markers."""
        self._read = max(0.0, float(read_mb_s))
        self._write = max(0.0, float(write_mb_s))
        r_ratio = _sqrt_ratio(self._read)
        w_ratio = _sqrt_ratio(self._write)
        self._read_peak = r_ratio if r_ratio >= self._read_peak else max(r_ratio, self._read_peak * 0.88)
        self._write_peak = w_ratio if w_ratio >= self._write_peak else max(w_ratio, self._write_peak * 0.88)
        self.update()

    def _draw_meter_row(self, painter: QPainter, row_rect: QRectF, tag: str, ratio: float, peak: float, color: QColor) -> None:
        tag_w = max(12.0, 14.0 * self._ui_scale)
        font = QFont("Segoe UI", max(6, int(round(7.5 * self._ui_scale))), QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(color)
        painter.drawText(QRectF(row_rect.left(), row_rect.top(), tag_w, row_rect.height()), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, tag)

        track = QRectF(row_rect.left() + tag_w + 2.0, row_rect.top() + 1.0, max(10.0, row_rect.width() - tag_w - 2.0), max(4.0, row_rect.height() - 2.0))
        track_col = QColor(self._grid_color)
        track_col.setAlpha(135)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_col)
        radius = max(1.5, 2.5 * self._ui_scale)
        painter.drawRoundedRect(track, radius, radius)

        if ratio > 0.01:
            fill_w = max(3.0, track.width() * ratio)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(track.left(), track.top(), fill_w, track.height()), radius, radius)

        if peak > 0.02:
            px = min(track.right() - 2.0, track.left() + track.width() * peak)
            painter.setBrush(QColor("#F0F6FC"))
            painter.drawRect(QRectF(px, track.top(), max(1.5, 2.0 * self._ui_scale), track.height()))

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        inner = self._begin_frame(painter)

        gap = max(2.0, 3.0 * self._ui_scale)
        row_h = max(8.0, (inner.height() - gap) * 0.5)
        self._draw_meter_row(painter, QRectF(inner.left(), inner.top(), inner.width(), row_h), "R", _sqrt_ratio(self._read), self._read_peak, self._primary_color)
        self._draw_meter_row(painter, QRectF(inner.left(), inner.top() + row_h + gap, inner.width(), row_h), "W", _sqrt_ratio(self._write), self._write_peak, self._secondary_color)
        painter.end()


class ActivityLedsWidget(BaseVisualizerWidget):
    """Retro dual R/W LED strips for Disk I/O activity."""

    def __init__(self, read_color: str = "#3FB950", write_color: str = "#FFEA00", grid_color: str = "#32383D") -> None:
        super().__init__(primary_color=read_color, grid_color=grid_color, secondary_color=write_color)
        self._read = 0.0
        self._write = 0.0

    def push_io(self, read_mb_s: float, write_mb_s: float) -> None:
        """Update Read/Write MB/s values."""
        self._read = max(0.0, float(read_mb_s))
        self._write = max(0.0, float(write_mb_s))
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        inner = self._begin_frame(painter)

        gap = max(2.0, 3.0 * self._ui_scale)
        row_h = max(8.0, (inner.height() - gap) * 0.5)
        tag_w = max(12.0, 14.0 * self._ui_scale)
        font = QFont("Segoe UI", max(6, int(round(7.5 * self._ui_scale))), QFont.Weight.Bold)
        painter.setFont(font)

        segments = 12
        for idx, (tag, val, col) in enumerate((("R", self._read, self._primary_color), ("W", self._write, self._secondary_color))):
            y = inner.top() + idx * (row_h + gap)
            painter.setPen(col)
            painter.drawText(QRectF(inner.left(), y, tag_w, row_h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, tag)
            lit = int(round(_sqrt_ratio(val) * segments))
            if val > 0.05 and lit == 0:
                lit = 1
            led_area = QRectF(inner.left() + tag_w + 2.0, y + 1.0, max(10.0, inner.width() - tag_w - 2.0), max(4.0, row_h - 2.0))
            self._draw_led_row(painter, led_area, segments, lit, col)
        painter.end()

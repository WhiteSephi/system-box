"""PageFault and Disk I/O visualizers (page matrix, dual R/W meter, mirror graph)."""

from __future__ import annotations

from collections import deque
import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen

from src.ui.visualizers.base import BaseVisualizerWidget


def _log_ratio(value: float, max_ref: float = 4096.0) -> float:
    """Map a non-negative spike value logarithmically into [0.0, 1.0]."""
    if value <= 0.0:
        return 0.0
    return min(1.0, math.log1p(value) / math.log1p(max_ref))


def _io_log_ratio(value: float) -> float:
    """Map MB/s throughput logarithmically so 0.1-10 MB/s and 500+ MB/s are both clear."""
    if value <= 0.0:
        return 0.0
    return min(1.0, math.log1p(value * 4.0) / math.log1p(2000.0))


class PageMatrixWidget(BaseVisualizerWidget):
    """20x3 memory-page chip matrix that sparks and softly fades out on PageFaults."""

    _COLS = 20
    _ROWS = 3

    def __init__(self, primary_color: str = "#3FB950", grid_color: str = "#32383D", accent_color: str = "#F85149") -> None:
        super().__init__(primary_color=primary_color, grid_color=grid_color, accent_color=accent_color)
        total = self._COLS * self._ROWS
        self._intensity: list[float] = [0.0] * total
        self._is_hot: list[bool] = [False] * total
        self._peak_raw = 128.0
        self._fade_timer = QTimer(self)
        self._fade_timer.setInterval(85)
        self._fade_timer.timeout.connect(self._on_fade_tick)

    def push_value(self, value: float) -> None:
        """Spark random memory cells proportional to PageFaults/sec."""
        val = max(0.0, float(value))
        self._peak_raw = max(128.0, val, self._peak_raw * 0.96)
        if val > 0.0:
            ratio = _log_ratio(val)
            sparks = max(1, min(32, int(round(ratio * 32))))
            hot_spike = ratio >= 0.65
            total = len(self._intensity)
            for _ in range(sparks):
                idx = random.randrange(total)
                self._intensity[idx] = 1.0
                self._is_hot[idx] = hot_spike and random.random() < 0.75
            if not self._fade_timer.isActive():
                self._fade_timer.start()
        self.update()

    def current_ceiling(self) -> float:
        """Return recent dynamic ceiling for display in header label."""
        return max(128.0, self._peak_raw)

    def _on_fade_tick(self) -> None:
        any_lit = False
        for i, v in enumerate(self._intensity):
            if v > 0.03:
                nxt = v * 0.83
                if nxt <= 0.03:
                    self._intensity[i] = 0.0
                    self._is_hot[i] = False
                else:
                    self._intensity[i] = nxt
                    any_lit = True
            else:
                self._intensity[i] = 0.0
                self._is_hot[i] = False
        if not any_lit:
            self._fade_timer.stop()
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        inner = self._begin_frame(painter)

        gap = max(1.5, 2.0 * self._ui_scale)
        cw = max(2.5, (inner.width() - gap * (self._COLS - 1)) / self._COLS)
        ch = max(2.5, (inner.height() - gap * (self._ROWS - 1)) / self._ROWS)
        radius = max(1.0, 1.8 * self._ui_scale)

        base_col = QColor(self._grid_color)
        base_col.setAlpha(120)
        painter.setPen(Qt.PenStyle.NoPen)

        for r in range(self._ROWS):
            for c in range(self._COLS):
                idx = r * self._COLS + c
                cell = QRectF(inner.left() + c * (cw + gap), inner.top() + r * (ch + gap), cw, ch)
                painter.setBrush(base_col)
                painter.drawRoundedRect(cell, radius, radius)

                glow = self._intensity[idx]
                if glow > 0.03:
                    col = QColor(self._accent_color if self._is_hot[idx] else self._primary_color)
                    col.setAlpha(int(round(max(20.0, min(255.0, glow * 255.0)))))
                    painter.setBrush(col)
                    painter.drawRoundedRect(cell, radius, radius)
        painter.end()


class DualIoMeterWidget(BaseVisualizerWidget):
    """Dual horizontal Read/Write throughput bars with log scaling and peak-hold markers."""

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
        r_ratio = _io_log_ratio(self._read)
        w_ratio = _io_log_ratio(self._write)
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
        self._draw_meter_row(painter, QRectF(inner.left(), inner.top(), inner.width(), row_h), "R", _io_log_ratio(self._read), self._read_peak, self._primary_color)
        self._draw_meter_row(painter, QRectF(inner.left(), inner.top() + row_h + gap, inner.width(), row_h), "W", _io_log_ratio(self._write), self._write_peak, self._secondary_color)
        painter.end()


class MirrorGraphWidget(BaseVisualizerWidget):
    """Bidirectional Disk I/O waveform: Read plots upward, Write plots downward from center."""

    def __init__(self, history_len: int = 60, read_color: str = "#3FB950", write_color: str = "#FFEA00", grid_color: str = "#32383D") -> None:
        super().__init__(primary_color=read_color, grid_color=grid_color, secondary_color=write_color)
        maxlen = max(15, history_len)
        self._read_hist: deque[float] = deque([0.0] * maxlen, maxlen=maxlen)
        self._write_hist: deque[float] = deque([0.0] * maxlen, maxlen=maxlen)

    def set_history_length(self, length: int) -> None:
        """Resize rolling Read/Write sample buffers."""
        target = max(15, length)
        if self._read_hist.maxlen != target:
            r_items = list(self._read_hist)[-target:]
            w_items = list(self._write_hist)[-target:]
            self._read_hist = deque([0.0] * max(0, target - len(r_items)) + r_items, maxlen=target)
            self._write_hist = deque([0.0] * max(0, target - len(w_items)) + w_items, maxlen=target)
            self.update()

    def push_io(self, read_mb_s: float, write_mb_s: float) -> None:
        """Append Read and Write MB/s samples and trigger repaint."""
        self._read_hist.append(max(0.0, float(read_mb_s)))
        self._write_hist.append(max(0.0, float(write_mb_s)))
        self.update()

    def _draw_half(self, painter: QPainter, samples: list[float], inner: QRectF, mid_y: float, half_h: float, ceiling: float, color: QColor, upward: bool) -> None:
        n = len(samples)
        if n < 2:
            return
        line_path = QPainterPath()
        area_path = QPainterPath()
        area_path.moveTo(inner.left(), mid_y)
        for i, val in enumerate(samples):
            x = inner.left() + (inner.width() * i) / (n - 1)
            ratio = min(1.0, val / ceiling)
            offset = ratio * half_h
            y = mid_y - offset if upward else mid_y + offset
            if i == 0:
                line_path.moveTo(x, y)
            else:
                line_path.lineTo(x, y)
            area_path.lineTo(x, y)
        area_path.lineTo(inner.right(), mid_y)
        area_path.closeSubpath()

        fill_col = QColor(color)
        fill_col.setAlpha(65)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill_col)
        painter.drawPath(area_path)

        painter.setPen(QPen(color, max(1.2, 1.5 * self._ui_scale)))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(line_path)

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        inner = self._begin_frame(painter)

        mid_y = inner.center().y()
        half_h = max(4.0, inner.height() * 0.5 - 1.0)
        painter.setPen(QPen(self._grid_color, max(0.8, 0.9 * self._ui_scale)))
        painter.drawLine(QPointF(inner.left(), mid_y), QPointF(inner.right(), mid_y))

        r_samples = list(self._read_hist)
        w_samples = list(self._write_hist)
        ceiling = max(5.0, max(r_samples or [0.0]) * 1.2, max(w_samples or [0.0]) * 1.2)
        self._draw_half(painter, r_samples, inner, mid_y, half_h, ceiling, self._primary_color, upward=True)
        self._draw_half(painter, w_samples, inner, mid_y, half_h, ceiling, self._secondary_color, upward=False)
        painter.end()

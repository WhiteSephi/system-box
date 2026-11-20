"""CPU per-core visualizers (equalizer bars and heatmap grid)."""

from __future__ import annotations

import math

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter

from src.ui.visualizers.base import BaseVisualizerWidget


class CoreBarsWidget(BaseVisualizerWidget):
    """Renders per-core CPU utilization as vertical equalizer bars."""

    def __init__(self, primary_color: str = "#4A9EFF", grid_color: str = "#32383D", accent_color: str = "#FF6D00") -> None:
        super().__init__(primary_color=primary_color, grid_color=grid_color, accent_color=accent_color)
        self._cores: list[float] = [0.0]

    def push_cores(self, cores: list[float], fallback_total: float = 0.0) -> None:
        """Update per-core utilization percentages and trigger repaint."""
        self._cores = [max(0.0, min(100.0, float(v))) for v in cores] if cores else [max(0.0, min(100.0, fallback_total))]
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        inner = self._begin_frame(painter)

        cores = self._cores or [0.0]
        n = len(cores)
        gap = max(1.0, (2.0 if n <= 24 else 1.0) * self._ui_scale)
        bar_w = max(2.0, (inner.width() - gap * (n - 1)) / n)
        radius = max(1.0, min(2.5, bar_w * 0.25))

        track_col = QColor(self._grid_color)
        track_col.setAlpha(110)

        for i, pct in enumerate(cores):
            x = inner.left() + i * (bar_w + gap)
            track = QRectF(x, inner.top(), bar_w, inner.height())
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(track_col)
            painter.drawRoundedRect(track, radius, radius)

            fill_h = max(1.5, inner.height() * (pct / 100.0)) if pct > 0.5 else 0.0
            if fill_h > 0.0:
                fill_rect = QRectF(x, inner.bottom() - fill_h, bar_w, fill_h)
                col = self._accent_color if pct >= 85.0 else self._primary_color
                painter.setBrush(col)
                painter.drawRoundedRect(fill_rect, radius, radius)
        painter.end()


class CoreHeatmapWidget(BaseVisualizerWidget):
    """Renders per-core CPU utilization as a compact 2D tile heatmap."""

    def __init__(self, primary_color: str = "#4A9EFF", grid_color: str = "#32383D", accent_color: str = "#FF6D00") -> None:
        super().__init__(primary_color=primary_color, grid_color=grid_color, accent_color=accent_color)
        self._cores: list[float] = [0.0]

    def push_cores(self, cores: list[float], fallback_total: float = 0.0) -> None:
        """Update per-core utilization percentages and trigger repaint."""
        self._cores = [max(0.0, min(100.0, float(v))) for v in cores] if cores else [max(0.0, min(100.0, fallback_total))]
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        inner = self._begin_frame(painter)

        cores = self._cores or [0.0]
        n = len(cores)
        rows = 1 if n <= 4 else (2 if n <= 16 else (3 if n <= 24 else 4))
        cols = max(1, math.ceil(n / rows))

        gap = max(1.5, 2.0 * self._ui_scale)
        cell_w = max(3.0, (inner.width() - gap * (cols - 1)) / cols)
        cell_h = max(3.0, (inner.height() - gap * (rows - 1)) / rows)
        radius = max(1.0, 2.0 * self._ui_scale)

        base_bg = QColor(self._grid_color)
        base_bg.setAlpha(120)

        for idx, pct in enumerate(cores):
            r = idx // cols
            c = idx % cols
            x = inner.left() + c * (cell_w + gap)
            y = inner.top() + r * (cell_h + gap)
            cell = QRectF(x, y, cell_w, cell_h)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(base_bg)
            painter.drawRoundedRect(cell, radius, radius)

            if pct > 0.5:
                col = QColor(self._accent_color if pct >= 85.0 else self._primary_color)
                alpha = int(round(38 + (pct / 100.0) * 217))
                col.setAlpha(max(30, min(255, alpha)))
                painter.setBrush(col)
                painter.drawRoundedRect(cell, radius, radius)
        painter.end()

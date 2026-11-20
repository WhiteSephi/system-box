"""Shared base widget and drawing helpers for SystemBox visualizers."""

from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class BaseVisualizerWidget(QWidget):
    """Base class for alternative telemetry visualizers matching MiniLiveGraphWidget geometry."""

    def __init__(
        self,
        primary_color: str = "#4A9EFF",
        grid_color: str = "#32383D",
        secondary_color: str = "#FFEA00",
        accent_color: str = "#FF6D00",
        muted_color: str = "#9E9E9E",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._primary_color = QColor(primary_color)
        self._grid_color = QColor(grid_color)
        self._secondary_color = QColor(secondary_color)
        self._accent_color = QColor(accent_color)
        self._muted_color = QColor(muted_color)
        self._ui_scale = 1.0
        self.setMinimumHeight(34)

    def set_colors(
        self,
        primary_color: str,
        grid_color: str,
        secondary_color: str | None = None,
        accent_color: str | None = None,
        muted_color: str | None = None,
    ) -> None:
        """Update theme colors and trigger repaint."""
        self._primary_color = QColor(primary_color)
        self._grid_color = QColor(grid_color)
        if secondary_color is not None:
            self._secondary_color = QColor(secondary_color)
        if accent_color is not None:
            self._accent_color = QColor(accent_color)
        if muted_color is not None:
            self._muted_color = QColor(muted_color)
        self.update()

    def set_ui_scale(self, scale: float) -> None:
        """Update UI scaling factor and minimum height."""
        self._ui_scale = max(0.7, min(3.0, scale))
        self.setMinimumHeight(max(24, int(round(36.0 * self._ui_scale))))
        self.update()

    def _begin_frame(self, painter: QPainter) -> QRectF:
        """Draw the standard rounded border frame and return the inner content rect."""
        rect = QRectF(0.5, 0.5, max(1.0, self.width() - 1.0), max(1.0, self.height() - 1.0))
        grid_pen = QPen(self._grid_color, max(0.8, 1.0 * self._ui_scale * 0.8))
        painter.setPen(grid_pen)
        painter.setBrush(self._grid_color.darker(220))
        radius = 4.0 * self._ui_scale
        painter.drawRoundedRect(rect, radius, radius)
        painter.setClipRect(rect.adjusted(1.0, 1.0, -1.0, -1.0))
        pad = max(3.0, 4.0 * self._ui_scale)
        return rect.adjusted(pad, pad, -pad, -pad)

    def _draw_led_row(
        self,
        painter: QPainter,
        area: QRectF,
        count: int,
        lit_count: int,
        lit_color: QColor,
        peak_index: int | None = None,
    ) -> None:
        """Draw a horizontal row of discrete LED segments with an optional peak-hold marker."""
        if count <= 0 or area.width() <= 0 or area.height() <= 0:
            return
        gap = max(1.5, 2.5 * self._ui_scale)
        seg_w = max(2.0, (area.width() - gap * (count - 1)) / count)
        radius = max(1.0, 1.8 * self._ui_scale)

        inactive = QColor(self._grid_color)
        inactive.setAlpha(140)
        painter.setPen(lit_color.darker(150))

        for i in range(count):
            x = area.left() + i * (seg_w + gap)
            cell = QRectF(x, area.top(), seg_w, area.height())
            if peak_index is not None and i == peak_index and peak_index >= lit_count:
                painter.setPen(self._accent_color)
                painter.setBrush(self._accent_color)
            elif i < lit_count:
                painter.setPen(lit_color)
                painter.setBrush(lit_color)
            else:
                painter.setPen(inactive)
                painter.setBrush(inactive)
            painter.drawRoundedRect(cell, radius, radius)

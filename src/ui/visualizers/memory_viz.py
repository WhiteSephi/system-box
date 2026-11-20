"""RAM memory visualizers (power-of-two block grid and segmented bar)."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter

from src.ui.visualizers.base import BaseVisualizerWidget


def power_of_two_grid(total_gb: float) -> tuple[int, int, int]:
    """Return (blocks, cols, rows) as a power of two scaled to installed RAM."""
    if total_gb <= 8.5:
        return 8, 8, 1
    if total_gb <= 16.5:
        return 16, 8, 2
    if total_gb <= 32.5:
        return 32, 8, 4
    return 64, 16, 4


class RamGridBoxWidget(BaseVisualizerWidget):
    """Renders RAM utilization as a power-of-two grid of memory blocks."""

    def __init__(self, primary_color: str = "#FFEA00", grid_color: str = "#32383D") -> None:
        super().__init__(primary_color=primary_color, grid_color=grid_color)
        self._percent = 0.0
        self._total_gb = 16.0

    def push_memory(self, percent: float, total_gb: float) -> None:
        """Update RAM usage percentage and total capacity in GB."""
        self._percent = max(0.0, min(100.0, float(percent)))
        self._total_gb = max(1.0, float(total_gb))
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        inner = self._begin_frame(painter)

        blocks, cols, rows = power_of_two_grid(self._total_gb)
        gap = max(1.5, 2.0 * self._ui_scale)
        cell_w = max(3.0, (inner.width() - gap * (cols - 1)) / cols)
        cell_h = max(3.0, (inner.height() - gap * (rows - 1)) / rows)
        radius = max(1.0, 1.8 * self._ui_scale)

        exact_filled = (self._percent / 100.0) * blocks
        full_blocks = int(exact_filled)
        partial = exact_filled - full_blocks

        empty_col = QColor(self._grid_color)
        empty_col.setAlpha(135)

        for idx in range(blocks):
            r = idx // cols
            c = idx % cols
            x = inner.left() + c * (cell_w + gap)
            y = inner.top() + r * (cell_h + gap)
            cell = QRectF(x, y, cell_w, cell_h)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(empty_col)
            painter.drawRoundedRect(cell, radius, radius)

            if idx < full_blocks:
                painter.setBrush(self._primary_color)
                painter.drawRoundedRect(cell, radius, radius)
            elif idx == full_blocks and partial > 0.05:
                part_col = QColor(self._primary_color)
                part_col.setAlpha(int(round(65 + partial * 185)))
                painter.setBrush(part_col)
                painter.drawRoundedRect(cell, radius, radius)
        painter.end()


class RamSegmentedBarWidget(BaseVisualizerWidget):
    """Renders RAM utilization as a 20-segment horizontal bar with scale markers."""

    def __init__(self, primary_color: str = "#FFEA00", grid_color: str = "#32383D", muted_color: str = "#9E9E9E") -> None:
        super().__init__(primary_color=primary_color, grid_color=grid_color, muted_color=muted_color)
        self._percent = 0.0

    def push_memory(self, percent: float, _total_gb: float = 0.0) -> None:
        """Update RAM usage percentage."""
        self._percent = max(0.0, min(100.0, float(percent)))
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        inner = self._begin_frame(painter)

        bar_h = max(8.0, inner.height() * 0.52)
        bar_rect = QRectF(inner.left(), inner.top() + 1.0, inner.width(), bar_h)
        segments = 20
        lit = int(round((self._percent / 100.0) * segments))
        self._draw_led_row(painter, bar_rect, segments, lit, self._primary_color)

        # Scale ticks: 0%, 50%, 100%
        label_top = bar_rect.bottom() + max(1.0, 2.0 * self._ui_scale)
        label_h = max(8.0, inner.bottom() - label_top)
        font = QFont("Segoe UI", max(6, int(round(7.5 * self._ui_scale))))
        painter.setFont(font)
        painter.setPen(self._muted_color)
        painter.drawText(QRectF(inner.left(), label_top, 36, label_h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "0%")
        painter.drawText(QRectF(inner.left(), label_top, inner.width(), label_h), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, "50%")
        painter.drawText(QRectF(inner.right() - 40, label_top, 40, label_h), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "100%")
        painter.end()

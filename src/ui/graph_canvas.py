"""Vector-scaled real-time live graph widget using Qt6 QPainter."""

from __future__ import annotations

from collections import deque

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class MiniLiveGraphWidget(QWidget):
    """Renders a crisp, HiDPI-scalable real-time area/line graph with background grid."""

    def __init__(
        self,
        history_len: int = 60,
        line_color: str = "#4A9EFF",
        grid_color: str = "#32383D",
        max_value: float = 100.0,
        dynamic_scale: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._history: deque[float] = deque([0.0] * max(15, history_len), maxlen=max(15, history_len))
        self._secondary_history: deque[float] = deque([0.0] * max(15, history_len), maxlen=max(15, history_len))
        self._has_secondary = False
        self._line_color = QColor(line_color)
        self._secondary_color = QColor("#FFEA00")
        self._grid_color = QColor(grid_color)
        self._max_value = max(1.0, max_value)
        self._dynamic_scale = dynamic_scale
        self._ui_scale = 1.0
        self.setMinimumHeight(34)

    def set_colors(self, line_color: str, grid_color: str, secondary_color: str | None = None) -> None:
        """Update primary/secondary line and grid colors."""
        self._line_color = QColor(line_color)
        self._grid_color = QColor(grid_color)
        if secondary_color is not None:
            self._secondary_color = QColor(secondary_color)
        self.update()

    def set_ui_scale(self, scale: float) -> None:
        """Update UI scaling factor for stroke widths and minimum height."""
        self._ui_scale = max(0.7, min(3.0, scale))
        self.setMinimumHeight(max(24, int(round(36.0 * self._ui_scale))))
        self.update()

    def set_history_length(self, length: int) -> None:
        """Resize rolling sample buffers."""
        target = max(15, length)
        if self._history.maxlen != target:
            items = list(self._history)[-target:]
            pad = [0.0] * max(0, target - len(items))
            self._history = deque(pad + items, maxlen=target)

            sec_items = list(self._secondary_history)[-target:]
            sec_pad = [0.0] * max(0, target - len(sec_items))
            self._secondary_history = deque(sec_pad + sec_items, maxlen=target)
            self.update()

    def push_value(
        self,
        value: float,
        max_value: float | None = None,
        secondary_value: float | None = None,
    ) -> None:
        """Append a new sample value (and optional secondary overlay) and trigger a repaint."""
        if max_value is not None and max_value > 0:
            self._max_value = max_value
        self._history.append(max(0.0, float(value)))
        if secondary_value is not None:
            self._has_secondary = True
            self._secondary_history.append(max(0.0, float(secondary_value)))
        else:
            self._secondary_history.append(0.0)
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(0.5, 0.5, max(1.0, self.width() - 1.0), max(1.0, self.height() - 1.0))

        # Subtle frame & grid
        grid_pen = QPen(self._grid_color, max(0.8, 1.0 * self._ui_scale * 0.8))
        painter.setPen(grid_pen)
        painter.drawRoundedRect(rect, 4.0 * self._ui_scale, 4.0 * self._ui_scale)

        mid_y = rect.top() + rect.height() * 0.5
        painter.drawLine(QPointF(rect.left() + 1, mid_y), QPointF(rect.right() - 1, mid_y))

        samples = list(self._history)
        if len(samples) < 2:
            painter.end()
            return

        if self._dynamic_scale:
            peak = max(samples) if samples else 0.0
            if self._has_secondary and self._secondary_history:
                peak = max(peak, max(self._secondary_history))
            ceiling = max(1.0, peak * 1.2)
        else:
            ceiling = max(1.0, self._max_value)

        painter.setClipRect(rect.adjusted(1, 1, -1, -1))
        n = len(samples)
        w = rect.width()
        h = rect.height() - 2.0

        line_path = QPainterPath()
        area_path = QPainterPath()
        bottom_y = rect.bottom() - 1.0

        for i, val in enumerate(samples):
            x = rect.left() + (w * i / (n - 1))
            ratio = min(1.0, max(0.0, val / ceiling))
            y = bottom_y - (ratio * h)
            if i == 0:
                line_path.moveTo(x, y)
                area_path.moveTo(x, bottom_y)
                area_path.lineTo(x, y)
            else:
                line_path.lineTo(x, y)
                area_path.lineTo(x, y)

        area_path.lineTo(rect.right(), bottom_y)
        area_path.closeSubpath()

        grad = QLinearGradient(0, rect.top(), 0, bottom_y)
        top_col = QColor(self._line_color)
        top_col.setAlpha(95)
        bot_col = QColor(self._line_color)
        bot_col.setAlpha(10)
        grad.setColorAt(0.0, top_col)
        grad.setColorAt(1.0, bot_col)
        painter.fillPath(area_path, grad)

        stroke_w = max(1.2, 1.6 * self._ui_scale)
        painter.setPen(QPen(self._line_color, stroke_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(line_path)

        if self._has_secondary:
            sec_samples = list(self._secondary_history)
            if len(sec_samples) == n:
                sec_path = QPainterPath()
                for i, val in enumerate(sec_samples):
                    x = rect.left() + (w * i / (n - 1))
                    ratio = min(1.0, max(0.0, val / ceiling))
                    y = bottom_y - (ratio * h)
                    if i == 0:
                        sec_path.moveTo(x, y)
                    else:
                        sec_path.lineTo(x, y)
                sec_w = max(1.0, 1.3 * self._ui_scale)
                painter.setPen(
                    QPen(
                        self._secondary_color,
                        sec_w,
                        Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap,
                        Qt.PenJoinStyle.RoundJoin,
                    )
                )
                painter.drawPath(sec_path)

        painter.end()

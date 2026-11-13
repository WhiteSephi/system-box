"""System Tray icon and shared context menu for SystemBox."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPolygonF, QPixmap


def render_systembox_pixmap(size: int = 64, accent_hex: str = "#4A9EFF") -> QPixmap:
    """Render the programmatic chip/pulse icon at any square pixel size."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.scale(size / 64.0, size / 64.0)

    # Outer chip body
    body = QRectF(10, 10, 44, 44)
    painter.setBrush(QColor("#1C2428"))
    painter.setPen(QPen(QColor("#8C96A0"), 2.8))
    painter.drawRoundedRect(body, 9, 9)

    # Chip pins (top/bottom/left/right)
    painter.setPen(QPen(QColor("#8C96A0"), 2.4))
    for offset in (22, 32, 42):
        painter.drawLine(QPointF(offset, 4), QPointF(offset, 10))
        painter.drawLine(QPointF(offset, 54), QPointF(offset, 60))
        painter.drawLine(QPointF(4, offset), QPointF(10, offset))
        painter.drawLine(QPointF(54, offset), QPointF(60, offset))

    # Inner pulse waveform
    pulse = QPolygonF(
        [
            QPointF(16, 34),
            QPointF(23, 34),
            QPointF(27, 22),
            QPointF(33, 43),
            QPointF(38, 28),
            QPointF(42, 34),
            QPointF(48, 34),
        ]
    )
    painter.setPen(QPen(QColor(accent_hex), 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.drawPolyline(pulse)

    painter.end()
    return pix


def create_systembox_icon(accent_hex: str = "#4A9EFF") -> QIcon:
    """Create a crisp multi-resolution chip/pulse icon for tray and windows."""
    icon = QIcon()
    for sz in (32, 64, 128):
        icon.addPixmap(render_systembox_pixmap(sz, accent_hex))
    return icon

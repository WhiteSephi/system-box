"""Vector icon utilities for the SystemBox UI."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap


def create_ui_icon(
    icon_type: str,
    color: str | QColor,
    size: int = 14,
) -> QPixmap:
    """Generate clean monochrome vector icons for UI buttons (github, etc.).

    :param icon_type: 'github'.
    :param color: Hex string or QColor for the icon stroke/fill.
    :param size: Dimension in pixels.
    :return: Transparent QPixmap.
    """
    col = QColor(color) if isinstance(color, str) else color
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    if icon_type == "github":
        scale = size / 24.0
        painter.scale(scale, scale)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(col)
        # Standard GitHub Octocat mark in 24x24 viewBox
        gh = QPainterPath()
        gh.moveTo(12.0, 0.5)
        gh.cubicTo(5.65, 0.5, 0.5, 5.65, 0.5, 12.0)
        gh.cubicTo(0.5, 17.08, 3.79, 21.39, 8.36, 22.91)
        gh.cubicTo(8.94, 23.02, 9.15, 22.66, 9.15, 22.36)
        gh.cubicTo(9.15, 22.09, 9.14, 21.37, 9.13, 20.42)
        gh.cubicTo(5.94, 21.11, 5.27, 18.88, 5.27, 18.88)
        gh.cubicTo(4.75, 17.55, 4.0, 17.2, 4.0, 17.2)
        gh.cubicTo(2.96, 16.49, 4.08, 16.5, 4.08, 16.5)
        gh.cubicTo(5.23, 16.58, 5.84, 17.68, 5.84, 17.68)
        gh.cubicTo(6.86, 19.44, 8.53, 18.93, 9.18, 18.64)
        gh.cubicTo(9.28, 17.9, 9.58, 17.39, 9.91, 17.1)
        gh.cubicTo(7.36, 16.81, 4.68, 15.82, 4.68, 11.42)
        gh.cubicTo(4.68, 10.17, 5.13, 9.15, 5.86, 8.35)
        gh.cubicTo(5.74, 8.06, 5.35, 6.89, 5.97, 5.31)
        gh.cubicTo(5.97, 5.31, 6.93, 5.0, 9.13, 6.49)
        gh.cubicTo(10.05, 6.23, 11.03, 6.11, 12.0, 6.1)
        gh.cubicTo(12.97, 6.11, 13.95, 6.23, 14.87, 6.49)
        gh.cubicTo(17.07, 5.0, 18.03, 5.31, 18.03, 5.31)
        gh.cubicTo(18.65, 6.89, 18.26, 8.06, 18.14, 8.35)
        gh.cubicTo(18.87, 9.15, 19.32, 10.17, 19.32, 11.42)
        gh.cubicTo(19.32, 15.83, 16.63, 16.81, 14.07, 17.09)
        gh.cubicTo(14.48, 17.45, 14.85, 18.15, 14.85, 19.23)
        gh.cubicTo(14.85, 20.77, 14.84, 22.02, 14.84, 22.36)
        gh.cubicTo(14.84, 22.67, 15.05, 23.03, 15.63, 22.91)
        gh.cubicTo(20.21, 21.39, 23.5, 17.08, 23.5, 12.0)
        gh.cubicTo(23.5, 5.65, 18.35, 0.5, 12.0, 0.5)
        gh.closeSubpath()
        painter.drawPath(gh)

    painter.end()
    return pix

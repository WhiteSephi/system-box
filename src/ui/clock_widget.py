"""Vector-rendered Clock, Date & Uptime desktop widget inspired by Rainmeter."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from src.config import AppConfig
from src.sensors.models import SystemSnapshot
from src.ui.base_widget import BaseDesktopWidget

_MONTHS_DE = ("JAN", "FEB", "MÄR", "APR", "MAI", "JUN", "JUL", "AUG", "SEP", "OKT", "NOV", "DEZ")
_WEEKDAYS_DE = ("MO", "DI", "MI", "DO", "FR", "SA", "SO")


def format_uptime(seconds: int) -> str:
    """Format uptime seconds into a concise human-readable string."""
    secs = max(0, int(seconds))
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    mins, _ = divmod(rem, 60)
    if days > 0:
        return f"{days}d {hours}h {mins:02d}m"
    if hours > 0:
        return f"{hours}h {mins:02d}m"
    return f"{mins}m"


class ClockWidget(BaseDesktopWidget):
    """Frameless Clock & Date widget with seconds progress bar and block date."""

    def __init__(self, config: AppConfig) -> None:
        self._uptime_seconds: int = 0
        super().__init__("clock", "Uhrzeit & Datum", config)
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self.update)
        self._tick_timer.start(1000)

    def update_snapshot(self, snapshot: SystemSnapshot) -> None:
        """Update uptime from the latest system snapshot."""
        self._uptime_seconds = snapshot.cpu.uptime_seconds
        if self.config.clock_show_uptime:
            self.update()

    def on_apply_config(self) -> None:
        self.setMinimumSize(self.sc(150), self.sc(75))

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        now = datetime.now()
        w = float(self.width())
        h = float(self.height())
        pad = float(self.sc(12))

        title_col = QColor(self.config.title_color)
        muted_col = QColor(self.config.muted_color)
        primary_col = QColor(self.config.primary_color)
        temp_col = QColor(self.config.temp_color)
        vram_col = QColor(self.config.vram_color)
        grid_col = QColor(self.config.grid_color)

        time_str = now.strftime("%H:%M") if self.config.clock_24h else now.strftime("%I:%M %p")

        # 1. Big Time (auto-fitted to available width so 12h AM/PM never clips)
        time_h = h * 0.40
        avail_w = max(40.0, w - 2 * pad)
        pt = max(14.0, min(time_h * 0.72, w * 0.24))
        time_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        time_font.setPointSizeF(pt)
        fm = QFontMetricsF(time_font)
        text_w = fm.horizontalAdvance(time_str)
        if text_w > avail_w:
            pt = max(10.0, pt * (avail_w / text_w) * 0.96)
            time_font.setPointSizeF(pt)
        painter.setFont(time_font)
        painter.setPen(title_col)
        painter.drawText(QRectF(pad, pad * 0.4, avail_w, time_h), Qt.AlignmentFlag.AlignCenter, time_str)

        # 2. Seconds progress bar
        bar_y = pad * 0.4 + time_h + self.sc(2)
        bar_w = w - 2 * pad
        bar_h = max(2.0, 2.5 * self.ui_scale)
        if self.config.clock_show_seconds:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(grid_col)
            painter.drawRoundedRect(QRectF(pad, bar_y, bar_w, bar_h), bar_h * 0.5, bar_h * 0.5)

            sec_ratio = max(0.02, now.second / 59.0)
            painter.setBrush(primary_col)
            painter.drawRoundedRect(QRectF(pad, bar_y, bar_w * sec_ratio, bar_h), bar_h * 0.5, bar_h * 0.5)

        # 3. Date Block (Day + Month badge | Weekday badge + Year)
        block_top = bar_y + self.sc(8)
        footer_h = self.sc(18) if self.config.clock_show_uptime else 0
        block_h = max(30.0, h - block_top - pad * 0.6 - footer_h)
        mid_x = w * 0.48

        # Left side: Day number + Month badge
        day_rect = QRectF(pad, block_top, mid_x - pad - self.sc(6), block_h * 0.62)
        day_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        day_font.setPointSizeF(max(11.0, min(day_rect.height() * 0.75, 36.0 * self.ui_scale)))
        painter.setFont(day_font)
        painter.setPen(title_col)
        painter.drawText(day_rect, Qt.AlignmentFlag.AlignCenter, f"{now.day:02d}")

        month_badge_rect = QRectF(pad + self.sc(4), block_top + block_h * 0.64, mid_x - pad - self.sc(14), block_h * 0.32)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(temp_col)
        painter.drawRoundedRect(month_badge_rect, self.sc(3), self.sc(3))
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(self.make_font(9.0, bold=True))
        painter.drawText(month_badge_rect, Qt.AlignmentFlag.AlignCenter, _MONTHS_DE[now.month - 1])

        # Vertical divider
        painter.setPen(QPen(grid_col, max(1.0, 1.5 * self.ui_scale)))
        painter.drawLine(QPointF(mid_x, block_top + self.sc(4)), QPointF(mid_x, block_top + block_h - self.sc(4)))

        # Right side: Weekday badge + Year
        right_x = mid_x + self.sc(8)
        right_w = w - pad - right_x
        wd_rect = QRectF(right_x, block_top + self.sc(2), right_w, block_h * 0.42)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(vram_col)
        painter.drawRoundedRect(wd_rect, self.sc(3), self.sc(3))
        painter.setPen(QColor("#0D1117"))
        painter.setFont(self.make_font(10.0, bold=True))
        painter.drawText(wd_rect, Qt.AlignmentFlag.AlignCenter, _WEEKDAYS_DE[now.weekday()])

        year_rect = QRectF(right_x, block_top + block_h * 0.50, right_w, block_h * 0.45)
        painter.setFont(self.make_font(12.5, bold=True))
        painter.setPen(title_col)
        painter.drawText(year_rect, Qt.AlignmentFlag.AlignCenter, str(now.year))

        # 4. Optional Uptime footer
        if self.config.clock_show_uptime:
            up_rect = QRectF(pad, h - footer_h - self.sc(4), w - 2 * pad, footer_h)
            painter.setFont(self.make_font(8.0, bold=False))
            painter.setPen(muted_col)
            painter.drawText(up_rect, Qt.AlignmentFlag.AlignCenter, f"Uptime: {format_uptime(self._uptime_seconds)}")

        painter.end()

"""Shared frameless, translucent, HiDPI-scalable base widget for SystemBox."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QContextMenuEvent,
    QFont,
    QMouseEvent,
    QMoveEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QResizeEvent,
)
from PySide6.QtWidgets import QApplication, QMenu, QSizeGrip, QWidget

from src.config import AppConfig
from src.ui.tray import create_systembox_icon


class VisualSizeGrip(QSizeGrip):
    """QSizeGrip with custom diagonal grip dots visible across all themes."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(14, 14)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setToolTip("Größe anpassen (Ziehen)")

    def update_scale(self, scale: float) -> None:
        """Adjust physical grip area to match UI scaling factor."""
        sz = max(12, int(round(14.0 * scale)))
        self.setFixedSize(sz, sz)

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        w, h = self.width(), self.height()
        pen_shadow = QColor(0, 0, 0, 180)
        pen_fg = QColor(255, 255, 255, 140)
        scale = max(1.0, w / 14.0)
        base_dots = [(3, 3), (7, 3), (3, 7), (11, 3), (7, 7), (3, 11)]
        for bx, by in base_dots:
            dx = int(round(bx * scale))
            dy = int(round(by * scale))
            painter.setPen(pen_shadow)
            painter.drawPoint(w - dx + 1, h - dy + 1)
            painter.setPen(pen_fg)
            painter.drawPoint(w - dx, h - dy)
        painter.end()


class BaseDesktopWidget(QWidget):
    """Frameless floating desktop widget with Drag & Drop, scaling, and context menu."""

    settings_requested = Signal()
    quit_requested = Signal()
    config_changed = Signal()

    def __init__(self, widget_key: str, display_name: str, config: AppConfig) -> None:
        super().__init__()
        self.widget_key = widget_key
        self.display_name = display_name
        self.config = config

        self._drag_start_pos = QPoint()
        self._drag_offset: QPoint | None = None
        self._restoring_geometry = False

        self._save_geo_timer = QTimer(self)
        self._save_geo_timer.setSingleShot(True)
        self._save_geo_timer.timeout.connect(self._persist_geometry)

        self.size_grip = VisualSizeGrip(self)
        self._configure_window_flags()
        self._restore_geometry()

    @property
    def ui_scale(self) -> float:
        """Return effective UI scale factor for this widget."""
        return self.config.effective_scale(self.widget_key)

    def sc(self, px: float) -> int:
        """Scale a base pixel value by the widget's effective UI scale."""
        return max(1, int(round(px * self.ui_scale)))

    def make_font(self, pt_size: float, bold: bool = False, family: str = "Segoe UI") -> QFont:
        """Create a scaled QFont (point sizes scale cleanly on HiDPI displays)."""
        font = QFont(family)
        font.setPointSizeF(max(6.0, pt_size * self.ui_scale))
        font.setBold(bold)
        return font

    def _configure_window_flags(self) -> None:
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.config.effective_always_on_top(self.widget_key):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        was_visible = self.isVisible()
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle(f"SystemBox – {self.display_name}")
        self.setWindowIcon(create_systembox_icon(self.config.primary_color))
        if was_visible and self.config.get_widget(self.widget_key).enabled:
            self.show()

    def _restore_geometry(self) -> None:
        wc = self.config.get_widget(self.widget_key)
        self._restoring_geometry = True
        try:
            self.resize(wc.width, wc.height)
            if wc.pos_x >= 0 and wc.pos_y >= 0:
                self.move(wc.pos_x, wc.pos_y)
            else:
                self._place_default_position()
        finally:
            self._restoring_geometry = False

    def _place_default_position(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        avail = screen.availableGeometry()
        offsets = {"clock": 0, "gpu": 1, "cpu": 2}
        slot = offsets.get(self.widget_key, 0)
        x = avail.right() - self.width() - 28
        y = avail.top() + 28 + slot * (self.height() + 16)
        if y + self.height() > avail.bottom():
            y = avail.top() + 28
            x = max(avail.left() + 20, x - self.width() - 20)
        self.move(x, y)

    def _persist_geometry(self) -> None:
        if self._restoring_geometry:
            return
        wc = self.config.get_widget(self.widget_key)
        wc.pos_x = self.x()
        wc.pos_y = self.y()
        wc.width = self.width()
        wc.height = self.height()
        self.config.save()

    def apply_config(self) -> None:
        """Apply updated configuration (flags, scale, colors, compact mode)."""
        want_top = self.config.effective_always_on_top(self.widget_key)
        is_top = bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        if want_top != is_top:
            self._configure_window_flags()

        self.size_grip.update_scale(self.ui_scale)
        self._position_size_grip()
        self.on_apply_config()
        self.update()

    def on_apply_config(self) -> None:
        """Hook for subclasses to refresh fonts, colors, and compact visibility."""

    def _position_size_grip(self) -> None:
        gw, gh = self.size_grip.width(), self.size_grip.height()
        margin = max(2, self.sc(3))
        self.size_grip.move(self.width() - gw - margin, self.height() - gh - margin)
        self.size_grip.raise_()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._position_size_grip()
        if not self._restoring_geometry:
            self._save_geo_timer.start(300)

    def moveEvent(self, event: QMoveEvent) -> None:
        super().moveEvent(event)
        if not self._restoring_geometry:
            self._save_geo_timer.start(300)

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        bg = QColor(self.config.background_color)
        alpha = int(self.config.effective_opacity(self.widget_key) * 2.55)
        bg.setAlpha(alpha)

        border = QColor(self.config.border_color)
        border.setAlpha(min(255, alpha + 35))

        radius = max(4.0, 8.0 * self.ui_scale)
        rect = QRectF(0.5, 0.5, max(1.0, self.width() - 1.0), max(1.0, self.height() - 1.0))
        painter.setBrush(bg)
        painter.setPen(QPen(border, max(1.0, 1.2 * self.ui_scale)))
        painter.drawRoundedRect(rect, radius, radius)
        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        locked = self.config.effective_locked_pos(self.widget_key)
        if event.button() == Qt.MouseButton.LeftButton and not locked:
            self._drag_start_pos = event.globalPosition().toPoint()
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        locked = self.config.effective_locked_pos(self.widget_key)
        if self._drag_offset is not None and (event.buttons() & Qt.MouseButton.LeftButton) and not locked:
            delta = (event.globalPosition().toPoint() - self._drag_start_pos).manhattanLength()
            if delta >= 3:
                app = QApplication.instance()
                if app is not None and app.platformName() == "wayland":
                    handle = self.windowHandle()
                    if handle is not None and hasattr(handle, "startSystemMove") and handle.startSystemMove():
                        self._drag_offset = None
                        event.accept()
                        return
                self.move(event.globalPosition().toPoint() - self._drag_offset)
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.settings_requested.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = QMenu(self)

        act_lock = QAction("Position sperren", menu, checkable=True)
        act_lock.setChecked(self.config.effective_locked_pos(self.widget_key))
        act_lock.triggered.connect(self._toggle_lock)
        menu.addAction(act_lock)

        act_top = QAction("Immer im Vordergrund", menu, checkable=True)
        act_top.setChecked(self.config.effective_always_on_top(self.widget_key))
        act_top.triggered.connect(self._toggle_top)
        menu.addAction(act_top)

        menu.addSeparator()

        act_hide = QAction(f"{self.display_name} ausblenden", menu)
        act_hide.triggered.connect(self._hide_widget)
        menu.addAction(act_hide)

        act_settings = QAction("Einstellungen...", menu)
        act_settings.triggered.connect(self.settings_requested.emit)
        menu.addAction(act_settings)

        menu.addSeparator()

        act_quit = QAction("SystemBox beenden", menu)
        act_quit.triggered.connect(self.quit_requested.emit)
        menu.addAction(act_quit)

        menu.exec(event.globalPos())

    def _toggle_lock(self, checked: bool) -> None:
        self.config.get_widget(self.widget_key).locked_pos = checked
        self.config.save()
        self.config_changed.emit()

    def _toggle_top(self, checked: bool) -> None:
        self.config.get_widget(self.widget_key).always_on_top = checked
        self.config.save()
        self.apply_config()
        self.config_changed.emit()

    def _hide_widget(self) -> None:
        self.config.get_widget(self.widget_key).enabled = False
        self.config.save()
        self.hide()
        self.config_changed.emit()

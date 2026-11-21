"""Shared frameless, translucent, HiDPI-scalable base widget for SystemBox."""

from __future__ import annotations

import logging
import math
import shutil
import subprocess
import sys

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QContextMenuEvent,
    QFont,
    QIcon,
    QMouseEvent,
    QMoveEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QPixmap,
    QResizeEvent,
    QShowEvent,
)
from PySide6.QtWidgets import QApplication, QMenu, QPushButton, QSizeGrip, QWidget

from src.config import AppConfig
from src.ui.linux_x11 import set_x11_skip_taskbar_libx11
from src.ui.tray import create_systembox_icon

logger = logging.getLogger(__name__)


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

    settings_requested = Signal(str)
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

    @staticmethod
    def _render_gear_icon(color: str, size: int) -> QIcon:
        """Render a crisp 6-tooth vector gear icon scaled to the button size."""
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))

        cx = size / 2.0
        cy = size / 2.0
        r_out = size * 0.42
        r_in = size * 0.305
        r_hole = size * 0.135
        path = QPainterPath()
        teeth = 6
        for i in range(teeth):
            angle = i * (2.0 * math.pi / teeth)
            half_step = math.pi / teeth
            a1 = angle - half_step * 0.35
            a2 = angle + half_step * 0.35
            a3 = angle + half_step * 0.70
            a4 = angle + half_step * 1.30
            if i == 0:
                path.moveTo(cx + r_out * math.cos(a1), cy + r_out * math.sin(a1))
            else:
                path.lineTo(cx + r_out * math.cos(a1), cy + r_out * math.sin(a1))
            path.lineTo(cx + r_out * math.cos(a2), cy + r_out * math.sin(a2))
            path.lineTo(cx + r_in * math.cos(a3), cy + r_in * math.sin(a3))
            path.lineTo(cx + r_in * math.cos(a4), cy + r_in * math.sin(a4))
        path.closeSubpath()
        hole = QPainterPath()
        hole.addEllipse(QPointF(cx, cy), r_hole, r_hole)
        painter.drawPath(path.subtracted(hole))
        painter.end()
        return QIcon(pix)

    def create_gear_button(self) -> QPushButton:
        """Create a compact header gear button opening this widget's settings tab."""
        btn = QPushButton(self)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(f"{self.display_name}-Einstellungen öffnen")
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.clicked.connect(lambda: self.settings_requested.emit(self.widget_key))
        return btn

    def style_gear_button(self, btn: QPushButton) -> None:
        """Apply HiDPI scaling and theme-aware styling to a header gear button."""
        btn_sz = self.sc(18)
        icon_sz = self.sc(12)
        btn.setFixedSize(btn_sz, btn_sz)
        btn.setIcon(self._render_gear_icon(self.config.muted_color, icon_sz))
        btn.setIconSize(QSize(icon_sz, icon_sz))
        b_col = QColor(self.config.border_color)
        p_col = QColor(self.config.primary_color)
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: rgba({b_col.red()}, {b_col.green()}, {b_col.blue()}, 45);
                border: 1px solid rgba({b_col.red()}, {b_col.green()}, {b_col.blue()}, 110);
                border-radius: {self.sc(4)}px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: rgba({p_col.red()}, {p_col.green()}, {p_col.blue()}, 55);
                border-color: {self.config.primary_color};
            }}
            """
        )

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

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._apply_x11_skip_taskbar()
        if sys.platform.startswith("linux"):
            QTimer.singleShot(50, self._apply_x11_skip_taskbar)
            QTimer.singleShot(250, self._apply_x11_skip_taskbar)

    def _apply_x11_skip_taskbar(self) -> None:
        """Ensure _NET_WM_STATE_SKIP_TASKBAR is set on X11/XWayland surfaces to hide from taskbars."""
        if not sys.platform.startswith("linux"):
            return
        app = QApplication.instance()
        if app is not None and app.platformName() not in ("xcb", ""):
            return
        wid = self.winId()
        if not wid:
            return
        if self._set_x11_skip_taskbar_libx11(int(wid)):
            return
        self._set_x11_skip_taskbar_xprop(int(wid))

    @staticmethod
    def _set_x11_skip_taskbar_libx11(wid: int) -> bool:
        """Set _NET_WM_STATE_SKIP_TASKBAR and _NET_WM_STATE_SKIP_PAGER directly via libX11."""
        return set_x11_skip_taskbar_libx11(wid)

    @staticmethod
    def _set_x11_skip_taskbar_xprop(wid: int) -> None:
        """Fallback: set _NET_WM_STATE_SKIP_TASKBAR via xprop CLI if available."""
        xprop_bin = shutil.which("xprop")
        if not xprop_bin:
            logger.debug("Neither libX11 nor xprop available; cannot set _NET_WM_STATE_SKIP_TASKBAR")
            return
        try:
            subprocess.run(
                [
                    xprop_bin,
                    "-id",
                    str(wid),
                    "-f",
                    "_NET_WM_STATE",
                    "32a",
                    "-set",
                    "_NET_WM_STATE",
                    "_NET_WM_STATE_SKIP_TASKBAR, _NET_WM_STATE_SKIP_PAGER",
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=0.5,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning("Failed to apply _NET_WM_STATE_SKIP_TASKBAR via xprop: %s", exc)

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
                raw_pos = event.globalPosition().toPoint() - self._drag_offset
                if self.config.snap_to_edges:
                    raw_pos = self._snap_position(raw_pos)
                self.move(raw_pos)
                event.accept()
                return
        super().mouseMoveEvent(event)

    def _snap_position(self, pos: QPoint, snap_dist: int = 14, widget_gap: int = 8) -> QPoint:
        """Snap widget position magnetically to screen edges and other visible widgets."""
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        center = QPoint(x + w // 2, y + h // 2)
        screen = QApplication.screenAt(center) or QApplication.primaryScreen()

        candidates_x: list[tuple[int, int]] = []  # (distance, snapped_x)
        candidates_y: list[tuple[int, int]] = []  # (distance, snapped_y)

        if screen is not None:
            avail = screen.availableGeometry()
            left_edge = avail.x()
            right_edge = avail.x() + avail.width() - w
            top_edge = avail.y()
            bottom_edge = avail.y() + avail.height() - h

            for edge_x in (left_edge, right_edge):
                d = abs(x - edge_x)
                if d <= snap_dist:
                    candidates_x.append((d, edge_x))
            for edge_y in (top_edge, bottom_edge):
                d = abs(y - edge_y)
                if d <= snap_dist:
                    candidates_y.append((d, edge_y))

        # Snap to other visible SystemBox widgets (edge alignment & clean gap docking)
        for other in QApplication.topLevelWidgets():
            if other is self or not isinstance(other, BaseDesktopWidget) or not other.isVisible():
                continue
            ox, oy, ow, oh = other.x(), other.y(), other.width(), other.height()
            for target_x in (ox, ox + ow - w, ox + ow + widget_gap, ox - w - widget_gap):
                d = abs(x - target_x)
                if d <= snap_dist:
                    candidates_x.append((d, target_x))
            for target_y in (oy, oy + oh - h, oy + oh + widget_gap, oy - h - widget_gap):
                d = abs(y - target_y)
                if d <= snap_dist:
                    candidates_y.append((d, target_y))

        if candidates_x:
            x = min(candidates_x, key=lambda item: item[0])[1]
        if candidates_y:
            y = min(candidates_y, key=lambda item: item[0])[1]
        return QPoint(x, y)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.settings_requested.emit(self.widget_key)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = QMenu(self)

        act_settings = QAction("Einstellungen...", menu)
        act_settings.triggered.connect(lambda: self.settings_requested.emit(self.widget_key))
        menu.addAction(act_settings)

        menu.addSeparator()

        act_top = QAction("Immer im Vordergrund", menu, checkable=True)
        act_top.setChecked(self.config.effective_always_on_top(self.widget_key))
        act_top.triggered.connect(self._toggle_top)
        menu.addAction(act_top)

        act_lock = QAction("Position sperren", menu, checkable=True)
        act_lock.setChecked(self.config.effective_locked_pos(self.widget_key))
        act_lock.triggered.connect(self._toggle_lock)
        menu.addAction(act_lock)

        menu.addSeparator()

        act_hide = QAction("Widget ausblenden", menu)
        act_hide.triggered.connect(self._hide_widget)
        menu.addAction(act_hide)

        menu.addSeparator()

        act_about = QAction("Über SystemBox...", menu)
        act_about.triggered.connect(lambda: self.settings_requested.emit("about"))
        menu.addAction(act_about)

        act_quit = QAction("Beenden", menu)
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

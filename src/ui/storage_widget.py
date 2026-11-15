"""Storage / Disk capacity live desktop widget (Windows 'This PC' style for Windows & Linux)."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QMouseEvent, QPainter
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from src.config import AppConfig
from src.sensors.disk_space import format_storage_size
from src.sensors.models import DiskSpaceInfo, SystemSnapshot
from src.ui.base_widget import BaseDesktopWidget


class _DiskUsageBar(QWidget):
    """Slim rounded progress bar rendered with current theme colors."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._percent = 0.0
        self._fill_color = QColor("#4A9EFF")
        self._track_color = QColor("#32383D")
        self._radius = 3.0
        self.setFixedHeight(7)

    def set_bar_state(self, percent: float, fill_color: str, track_color: str, ui_scale: float) -> None:
        self._percent = max(0.0, min(100.0, percent))
        self._fill_color = QColor(fill_color)
        self._track_color = QColor(track_color)
        h = max(5, int(round(7.0 * ui_scale)))
        self._radius = h / 2.0
        self.setFixedHeight(h)
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)

        rect = QRectF(0.0, 0.0, float(self.width()), float(self.height()))
        track = QColor(self._track_color)
        track.setAlpha(180)
        painter.setBrush(track)
        painter.drawRoundedRect(rect, self._radius, self._radius)

        if self._percent > 0.0:
            fill_w = max(float(self.height()), rect.width() * (self._percent / 100.0))
            fill_w = min(rect.width(), fill_w)
            fill_rect = QRectF(0.0, 0.0, fill_w, rect.height())
            painter.setBrush(self._fill_color)
            painter.drawRoundedRect(fill_rect, self._radius, self._radius)


class _DiskRowWidget(QWidget):
    """Single drive/mountpoint card with label, percentage, progress bar, and capacity line."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mountpoint = ""

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        top = QHBoxLayout()
        top.setSpacing(6)
        self.lbl_name = QLabel("")
        self.lbl_pct = QLabel("")
        self.lbl_pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top.addWidget(self.lbl_name, 1)
        top.addWidget(self.lbl_pct)
        lay.addLayout(top)

        self.bar = _DiskUsageBar(self)
        lay.addWidget(self.bar)

        self.lbl_sub = QLabel("")
        lay.addWidget(self.lbl_sub)

    def update_item(
        self,
        disk: DiskSpaceInfo,
        config: AppConfig,
        ui_scale: float,
        name_font,
        sub_font,
    ) -> None:
        self._mountpoint = disk.mountpoint
        is_warn = disk.percent >= config.storage_warn_percent
        fill_col = config.temp_color if is_warn else config.primary_color

        self.lbl_name.setFont(name_font)
        self.lbl_name.setStyleSheet(f"color: {config.title_color};")
        self.lbl_name.setText(disk.label or disk.mountpoint)

        self.lbl_pct.setFont(name_font)
        pct_col = config.temp_color if is_warn else config.secondary_color
        self.lbl_pct.setStyleSheet(f"color: {pct_col};")
        self.lbl_pct.setText(f"{disk.percent:.0f}%")

        self.bar.set_bar_state(disk.percent, fill_col, config.grid_color, ui_scale)

        self.lbl_sub.setFont(sub_font)
        self.lbl_sub.setStyleSheet(f"color: {config.muted_color};")
        total_txt = format_storage_size(disk.total_gb)
        if config.storage_show_free_first:
            free_txt = format_storage_size(disk.free_gb)
            self.lbl_sub.setText(f"{free_txt} frei von {total_txt}")
        else:
            used_txt = format_storage_size(disk.used_gb)
            self.lbl_sub.setText(f"{used_txt} / {total_txt} belegt")

        self.setToolTip(
            f"{disk.label}\nGerät: {disk.device}\nTyp: {disk.fstype or 'unbekannt'}\nDoppelklick zum Öffnen"
        )

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._mountpoint:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._mountpoint))
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class StorageWidget(BaseDesktopWidget):
    """Frameless storage capacity widget showing drives and mountpoints cleanly."""

    def __init__(self, config: AppConfig) -> None:
        super().__init__("storage", "Datenträger & Speicher", config)
        self._rows: list[_DiskRowWidget] = []
        self._last_disks: list[DiskSpaceInfo] = []
        self._build_ui()
        self.on_apply_config()

    def _build_ui(self) -> None:
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 8, 10, 8)
        self._layout.setSpacing(4)

        hdr = QHBoxLayout()
        hdr.setSpacing(6)
        self.lbl_title = QLabel("Datenträger & Speicher")
        self.btn_settings = self.create_gear_button()
        hdr.addWidget(self.lbl_title, 1)
        hdr.addWidget(self.btn_settings)
        self._layout.addLayout(hdr)

        self._hdr_line = QFrame()
        self._hdr_line.setFrameShape(QFrame.Shape.HLine)
        self._hdr_line.setFixedHeight(1)
        self._layout.addWidget(self._hdr_line)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }")

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 2, 0, 2)
        self._list_layout.setSpacing(8)
        self._list_layout.addStretch(1)

        self._scroll.setWidget(self._list_container)
        self._layout.addWidget(self._scroll, 1)

        self.lbl_empty = QLabel("Keine Laufwerke erkannt")
        self.lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._list_layout.insertWidget(0, self.lbl_empty)

    def on_apply_config(self) -> None:
        m = self.sc(9)
        self._layout.setContentsMargins(m, self.sc(7), m, self.sc(7))
        self._layout.setSpacing(self.sc(4))
        self._list_layout.setSpacing(self.sc(7))

        self.lbl_title.setFont(self.make_font(10.0, bold=True))
        self.lbl_title.setStyleSheet(f"color: {self.config.title_color};")
        self.style_gear_button(self.btn_settings)

        line_col = QColor(self.config.border_color)
        self._hdr_line.setStyleSheet(
            f"background-color: rgba({line_col.red()}, {line_col.green()}, {line_col.blue()}, 95); border: none;"
        )
        self.lbl_empty.setFont(self.make_font(8.5))
        self.lbl_empty.setStyleSheet(f"color: {self.config.muted_color};")

        self.setMinimumSize(self.sc(220), self.sc(110))
        self._render_disks(self._last_disks)

    def update_snapshot(self, snapshot: SystemSnapshot) -> None:
        """Update visible drive bars from the latest SystemSnapshot."""
        self._last_disks = list(snapshot.disks)
        self._render_disks(self._last_disks)

    def _render_disks(self, disks: list[DiskSpaceInfo]) -> None:
        hidden = set(self.config.storage_hidden_mountpoints)
        visible_disks = [d for d in disks if d.mountpoint not in hidden]
        self.lbl_empty.setVisible(len(visible_disks) == 0)

        while len(self._rows) < len(visible_disks):
            row = _DiskRowWidget(self._list_container)
            # Insert before the trailing stretch
            self._list_layout.insertWidget(self._list_layout.count() - 1, row)
            self._rows.append(row)

        name_font = self.make_font(9.0, bold=True)
        sub_font = self.make_font(8.0, bold=False)

        for idx, row in enumerate(self._rows):
            if idx < len(visible_disks):
                row.setVisible(True)
                row.update_item(visible_disks[idx], self.config, self.ui_scale, name_font, sub_font)
            else:
                row.setVisible(False)

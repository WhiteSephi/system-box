"""Reusable dark-themed color picker popup and swatch button for SystemBox."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def make_swatch_icon(hex_color: str, size: int = 16) -> QIcon:
    """Generate a clean rounded color chip icon."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(hex_color))
    painter.setPen(QColor("#FFFFFF" if QColor(hex_color).lightness() < 60 else "#222222"))
    painter.drawRoundedRect(1, 1, size - 2, size - 2, 4, 4)
    painter.end()
    return QIcon(pix)


class ModernColorPickerPopup(QDialog):
    """Modern dark-themed color picker popup with curated palette and hex input."""

    PALETTE = [
        ["#00E5FF", "#00E676", "#FFEA00", "#FF9100", "#FF1744", "#FF007F"],
        ["#3D5AFE", "#7C4DFF", "#00B0FF", "#1DE9B6", "#76FF03", "#FFD600"],
        ["#80D8FF", "#A7FFEB", "#CCFF90", "#FFE57F", "#FF8A80", "#EA80FC"],
        ["#FFFFFF", "#CFD8DC", "#78909C", "#455A64", "#263238", "#121212"],
    ]

    def __init__(
        self,
        current_hex: str,
        on_chosen: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.on_chosen = on_chosen

        self.setStyleSheet("""
            QDialog {
                background-color: #1A1E24;
                border: 1px solid #3E4652;
                border-radius: 8px;
            }
            QLabel {
                color: #E0E4E8;
                font-size: 8.5pt;
            }
            QLineEdit {
                background-color: #262C36;
                color: #FFFFFF;
                border: 1px solid #444D5A;
                border-radius: 4px;
                padding: 4px 6px;
                font-family: monospace;
                font-weight: bold;
                font-size: 8.5pt;
            }
            QLineEdit:focus {
                border-color: #00E5FF;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        lbl_title = QLabel("Farbe wählen")
        lbl_title.setStyleSheet("font-weight: bold; font-size: 9pt; color: #FFFFFF;")
        layout.addWidget(lbl_title)

        grid = QGridLayout()
        grid.setSpacing(5)
        for r, row in enumerate(self.PALETTE):
            for c, hex_code in enumerate(row):
                btn = QPushButton()
                btn.setFixedSize(26, 26)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setToolTip(hex_code)
                is_curr = hex_code.lower() == current_hex.lower()
                border = "2px solid #FFFFFF" if is_curr else "1px solid rgba(255,255,255,0.2)"
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {hex_code};
                        border: {border};
                        border-radius: 4px;
                    }}
                    QPushButton:hover {{
                        border: 2px solid #00E5FF;
                    }}
                """)
                btn.clicked.connect(lambda _, h=hex_code: self._select_and_close(h))
                grid.addWidget(btn, r, c)
        layout.addLayout(grid)

        hex_row = QHBoxLayout()
        hex_row.setSpacing(6)
        lbl_hex = QLabel("Hex:")
        self.txt_hex = QLineEdit(current_hex)
        self.txt_hex.setMaxLength(9)

        self.lbl_swatch_preview = QLabel()
        self.lbl_swatch_preview.setFixedSize(22, 22)
        self._update_preview_swatch(current_hex)

        self.txt_hex.textChanged.connect(self._on_hex_text_changed)
        self.txt_hex.returnPressed.connect(lambda: self._select_and_close(self.txt_hex.text()))

        btn_ok = QPushButton("✓")
        btn_ok.setFixedSize(26, 26)
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #2D3748;
                color: #00E5FF;
                border: 1px solid #4A5568;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3A475C;
                border-color: #00E5FF;
            }
        """)
        btn_ok.clicked.connect(lambda: self._select_and_close(self.txt_hex.text()))

        hex_row.addWidget(lbl_hex)
        hex_row.addWidget(self.lbl_swatch_preview)
        hex_row.addWidget(self.txt_hex, 1)
        hex_row.addWidget(btn_ok)
        layout.addLayout(hex_row)

        btn_sys = QPushButton("🎨 Erweiterte Farbauswahl…")
        btn_sys.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sys.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #8E9297;
                font-size: 8pt;
                text-decoration: underline;
                padding-top: 2px;
            }
            QPushButton:hover {
                color: #00E5FF;
            }
        """)
        btn_sys.clicked.connect(self._open_system_picker)
        layout.addWidget(btn_sys)

    def _update_preview_swatch(self, hex_code: str) -> None:
        if not hex_code.startswith("#"):
            hex_code = "#" + hex_code
        col = QColor(hex_code)
        if col.isValid():
            self.lbl_swatch_preview.setStyleSheet(
                f"background-color: {col.name()}; border: 1px solid #666; border-radius: 3px;"
            )

    def _on_hex_text_changed(self, text: str) -> None:
        self._update_preview_swatch(text.strip())

    def _select_and_close(self, hex_val: str) -> None:
        hex_val = hex_val.strip()
        if not hex_val.startswith("#"):
            hex_val = "#" + hex_val
        col = QColor(hex_val)
        if col.isValid():
            self.on_chosen(col.name().upper())
            self.close()

    def _open_system_picker(self) -> None:
        init_col = QColor(self.txt_hex.text().strip())
        if not init_col.isValid():
            init_col = QColor("#00E5FF")
        chosen = QColorDialog.getColor(init_col, self, "Erweiterte Farbe wählen")
        if chosen.isValid():
            self.on_chosen(chosen.name().upper())
            self.close()


class ColorButton(QPushButton):
    """Compact button displaying a color swatch and opening ModernColorPickerPopup."""

    def __init__(self, hex_color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._hex_color = hex_color
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(26)
        self.setMinimumWidth(110)
        self.clicked.connect(self._pick_color)
        self._update_style()

    @property
    def hex_color(self) -> str:
        return self._hex_color

    @hex_color.setter
    def hex_color(self, value: str) -> None:
        self._hex_color = value
        self._update_style()

    def _update_style(self) -> None:
        self.setIcon(make_swatch_icon(self._hex_color, 16))
        self.setText(f" {self._hex_color.upper()}")
        self.setStyleSheet(
            """
            QPushButton {
                background-color: #2A2F38;
                color: #E0E4E8;
                border: 1px solid #444D5A;
                border-radius: 5px;
                padding: 3px 8px;
                text-align: left;
                font-family: monospace;
                font-weight: bold;
                font-size: 8.5pt;
            }
            QPushButton:hover {
                border-color: #00E5FF;
                background-color: #323842;
            }
            """
        )

    def _pick_color(self) -> None:
        popup = ModernColorPickerPopup(self._hex_color, self._on_color_chosen, self)
        pos = self.mapToGlobal(self.rect().bottomLeft())
        popup.move(pos.x(), pos.y() + 4)
        popup.exec()

    def _on_color_chosen(self, hex_val: str) -> None:
        self.hex_color = hex_val

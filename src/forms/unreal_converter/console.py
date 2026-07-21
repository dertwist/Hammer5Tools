"""Colored console/log widget for conversion feedback."""

from datetime import datetime
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QTextEdit

_LEVEL_COLORS = {
    "info":    "#b8b8b8",
    "warn":    "#e0a030",
    "error":   "#e05656",
    "success": "#5fb96a",
    "header":  "#5aa0e0",
}


class ConsoleWidget(QTextEdit):
    """Read-only rich-text console with leveled, timestamped output."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.NoWrap)
        self.document().setMaximumBlockCount(5000)
        self.setStyleSheet(
            "QTextEdit {\n"
            "    font: 580 10pt \"Segoe UI\";\n"
            "    border: 2px solid black;\n"
            "    border-radius: 4px;\n"
            "    border-color: rgba(80, 80, 80, 255);\n"
            "    padding: 4px;\n"
            "    padding-left: 6px;\n"
            "    padding-right: 6px;\n"
            "    color: #E3E3E3;\n"
            "    background-color: #1C1C1C;\n"
            "}"
        )

    def _emit(self, message: str, level: str, timestamp: bool):
        color = _LEVEL_COLORS.get(level, _LEVEL_COLORS["info"])
        ts = f'<span style="color:#808080;">[{datetime.now():%H:%M:%S}]</span> ' if timestamp else ""
        safe = (message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        self.append(f'{ts}<span style="color:{color}">{safe}</span>')
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())

    def info(self, message):    self._emit(message, "info", True)
    def warn(self, message):    self._emit(message, "warn", True)
    def error(self, message):   self._emit(message, "error", True)
    def success(self, message): self._emit(message, "success", True)

    def header(self, message):
        self._emit("", "info", False)
        self._emit(f"-- {message} --", "header", False)

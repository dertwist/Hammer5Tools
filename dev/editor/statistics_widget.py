from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt


class StatisticsWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignTop)
        self.setText("Statistics will be shown here.")

    def update_statistics(self, data):
        if isinstance(data, dict):
            count = len(data)
        elif isinstance(data, list):
            count = len(data)
        else:
            count = 1
        self.setText(f"Item count: {count}")
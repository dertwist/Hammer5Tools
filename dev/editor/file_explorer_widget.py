import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem
from PySide6.QtCore import Signal


class FileExplorerWidget(QWidget):
    file_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)

    def set_directory(self, directory):
        self.list_widget.clear()
        if not os.path.isdir(directory):
            return
        for filename in os.listdir(directory):
            item = QListWidgetItem(filename)
            item.setData(0, os.path.join(directory, filename))
            self.list_widget.addItem(item)

    def on_item_double_clicked(self, item):
        file_path = item.data(0)
        self.file_selected.emit(file_path)
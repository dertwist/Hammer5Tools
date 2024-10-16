from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox

class ComboboxChoiceClass(QComboBox):
    signal = Signal(str)  # Define a signal that emits a string when the variable changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet('padding:4px')
        self.items = ['1', '2', '65']
        self.addItems(self.items)
        self.signal.connect(self.updateItems)

    def type(self):
        print('clicked')

    def updateItems(self, new_items):
        self.clear()  # Clear existing items
        self.addItems(new_items)  # Add new items to the QComboBox
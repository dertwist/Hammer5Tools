from PySide6.QtWidgets import QComboBox

class ComboboxDynamicItems(QComboBox):

    def __init__(self, parent=None, items=None):
        super().__init__(parent)
        self.setStyleSheet('padding:4px')
        self.items = items

    def updateItems(self):
        current = self.currentText()
        self.clear()
        self.addItems(self.items)
        if current in self.items:
            self.setCurrentText(current)

    def showPopup(self):
        self.updateItems()
        super().showPopup()


    def wheelEvent(self, event):
        event.ignore()
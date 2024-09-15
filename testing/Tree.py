import sys
import json
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

class TreeViewExample(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("TreeView Example")
        self.setGeometry(100, 100, 600, 400)

        self.tree_view = QTreeWidget()
        self.tree_view.setHeaderLabels(['Label', 'ComboBox'])

        self.setup_tree()

        self.status_bar = QStatusBar()
        self.tree_view.clicked.connect(lambda: self.update_status_bar(message='lol'))
        self.tree_view.itemChanged.connect(lambda: self.update_status_bar(message='lol'))

        self.plain_text = QPlainTextEdit()
        dock_widget = QDockWidget("Plain Text Dock")
        dock_widget.setWidget(self.plain_text)
        self.addDockWidget(Qt.RightDockWidgetArea, dock_widget)

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(self.tree_view)
        layout.addWidget(self.status_bar)
        self.setCentralWidget(central_widget)

    def setup_tree(self):
        for i in range(1):
            parent_item = QTreeWidgetItem(self.tree_view, ['Parent'])
            for _ in range(4):
                child_item = QTreeWidgetItem(parent_item, ['Child'])
                combo_box = QComboBox()
                combo_box.currentIndexChanged.connect(lambda: self.update_status_bar(message='combo'))
                combo_box.addItems(['Doublespinbox', 'Editline'])
                combo_box.currentIndexChanged.connect(lambda state, combo_box=combo_box, child_item=child_item: self.handle_combo_box(combo_box, child_item))
                self.tree_view.setItemWidget(child_item, 0, combo_box)

    def handle_combo_box(self, combo_box, child_item):
        if combo_box.currentText() == 'Editline':
            edit_line = QLineEdit()
            edit_line.textChanged.connect(lambda: self.update_status_bar(message='text'))
            self.tree_view.setItemWidget(child_item, 1, edit_line)
            self.update_status_bar('Editline selected')
        elif combo_box.currentText() == 'Doublespinbox':
            double_spin_box = QDoubleSpinBox()
            double_spin_box.valueChanged.connect(lambda: self.update_status_bar(message='double'))
            self.tree_view.setItemWidget(child_item, 1, double_spin_box)
            self.update_status_bar('Doublespinbox selected')

    def update_status_bar(self, message):
        self.status_bar.showMessage(message)
        json_data = self.modelToJson()
        self.plain_text.setPlainText(json_data)

    def modelToJson(self):
        json_data = self.modelToJsonRecursive(self.tree_view.invisibleRootItem())
        return json.dumps(json_data)

    def modelToJsonRecursive(self, item):
        item_data = {}
        if item is not None:
            item_data['label'] = item.text(0)

            # Save the value from the QDoubleSpinBox (assuming it's in the second column)
            widget = self.tree_view.itemWidget(item, 1)
            if isinstance(widget, QLineEdit):
                print('Editline widget found', widget.text())
                item_data['value'] = widget.text()
            if isinstance(widget, QDoubleSpinBox):
                item_data['value'] = widget.value()
            # print(widget.value())

            if item.childCount() > 0:
                item_data['children'] = [self.modelToJsonRecursive(item.child(i)) for i in range(item.childCount())]
        return item_data
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TreeViewExample()
    window.show()
    sys.exit(app.exec())
import sys
from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem

app = QApplication(sys.argv)

tree = QTreeWidget()
tree.setColumnCount(2)
tree.setHeaderLabels(['Name', 'Value'])

parent = QTreeWidgetItem(tree, ['Parent'])
child1 = QTreeWidgetItem(parent, ['Child 1', 'Value 1'])
child2 = QTreeWidgetItem(parent, ['Child 2', 'Value 2'])

tree.addTopLevelItem(parent)

tree.show()

sys.exit(app.exec())
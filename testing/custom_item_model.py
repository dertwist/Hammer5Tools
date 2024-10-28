from PySide6.QtWidgets import QApplication, QTreeView
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem


class CustomStandardItemModel(QStandardItemModel):
    def flags(self, index):
        # Get the default flags for the item
        default_flags = super().flags(index)

        # Check if the column is the one you want to make non-editable
        if index.column() == 1:  # Example: make the second column non-editable
            # Remove the ItemIsEditable flag
            return default_flags & ~Qt.ItemIsEditable

        # Return the default flags for other columns
        return default_flags


app = QApplication([])

# Create the model
model = CustomStandardItemModel()
model.setHorizontalHeaderLabels(['Editable Column', 'Non-Editable Column'])

# Add some items
for i in range(5):
    item1 = QStandardItem(f"Editable {i}")
    item2 = QStandardItem(f"Non-Editable {i}")
    model.appendRow([item1, item2])

# Create the view
view = QTreeView()
view.setModel(model)
view.show()

app.exec()
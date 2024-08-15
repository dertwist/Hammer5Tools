
def add_items(parent, data):
    for key, value in data.items():
        key_item = QStandardItem(key)
        if isinstance(value, dict):
            value_item = QStandardItem("")
            parent.appendRow([key_item, value_item])
            add_items(key_item, value)
        else:
            value_item = QStandardItem(str(value))
            parent.appendRow([key_item, value_item])

app = QApplication(sys.argv)
window = QMainWindow()
window.setWindowTitle("Data Tree View")

# Create the central widget and layout
central_widget = QWidget()
layout = QVBoxLayout(central_widget)

# Create the tree view and model
tree_view = QTreeView()
model = QStandardItemModel()
model.setHorizontalHeaderLabels(["Key", "Value"])
root_item = model.invisibleRootItem()

# Populate the model with data
add_items(root_item, data)

# Set the model to the tree view
tree_view.setModel(model)
tree_view.expandAll()

# Add the tree view to the layout
layout.addWidget(tree_view)
window.setCentralWidget(central_widget)

# Show the window
window.resize(800, 600)
window.show()

sys.exit(app.exec())
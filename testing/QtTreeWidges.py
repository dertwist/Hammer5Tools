from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem, QGroupBox, QVBoxLayout, QLineEdit, QPushButton, QWidget, QCheckBox

app = QApplication([])

# Create the main window
main_window = QWidget()
main_layout = QVBoxLayout()
main_window.setLayout(main_layout)

# Create the tree widget
tree_widget = QTreeWidget()
tree_widget.setColumnCount(2)
main_layout.addWidget(tree_widget)

# Create parent item with buttons and checkboxes
parent_item = QTreeWidgetItem(tree_widget)
parent_item.setText(0, "Parent Item")

# Add checkboxes and buttons to the parent item
for i in range(4):
    checkbox = QCheckBox()  # Create a checkbox
    tree_widget.setItemWidget(parent_item, 0, checkbox)

    button = QPushButton(f"Button {i+1}")
    tree_widget.setItemWidget(parent_item, 1, button)

# Create child item with group box and edit lines
child_item = QTreeWidgetItem(parent_item)
child_item.setText(0, "Child Item")

# Add child items "value", "min value", "max value" with checkboxes
group_box = QGroupBox()
group_layout = QVBoxLayout()
group_box.setLayout(group_layout)

for i in range(3):
    checkbox = QCheckBox()  # Create a checkbox
    group_layout.addWidget(checkbox)

    edit_line = QLineEdit()
    group_layout.addWidget(edit_line)

tree_widget.setItemWidget(child_item, 1, group_box)

# Add separate child items for "value", "min value", "max value" with checkboxes
for item_name in ["value", "min value", "max value"]:
    new_child_item = QTreeWidgetItem(child_item)
    new_child_item.setText(0, item_name)

    new_group_box = QGroupBox()  # Create a new group box for each item
    new_group_layout = QVBoxLayout()
    new_group_box.setLayout(new_group_layout)

    checkbox = QCheckBox()  # Create a checkbox
    new_group_layout.addWidget(checkbox)

    edit_line = QLineEdit()
    new_group_layout.addWidget(edit_line)

    tree_widget.setItemWidget(new_child_item, 1, new_group_box)

main_window.show()
app.exec()
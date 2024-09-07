from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem, QGroupBox, QVBoxLayout, QLineEdit, QPushButton, QWidget, QCheckBox, QStatusBar, QHBoxLayout

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
parent_item.setText(0, "")

group_box = QGroupBox()
group_layout = QHBoxLayout()
group_box.setLayout(group_layout)

checkbox = QCheckBox()  # Create a checkbox
group_layout.addWidget(checkbox)

edit_line = QLineEdit()
group_layout.addWidget(edit_line)

tree_widget.setItemWidget(parent_item, 0, group_box)

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

# Add status bar
status_bar = QStatusBar()
main_layout.addWidget(status_bar)

# Create a button to print inputs to status bar
button_print = QPushButton("Print Inputs to Status Bar")

def print_inputs_to_status_bar():
    inputs = []
    for i in range(group_layout.count()):
        widget = group_layout.itemAt(i).widget()
        if isinstance(widget, QCheckBox):
            inputs.append(f"Checkbox {i+1}: {'Checked' if widget.isChecked() else 'Unchecked'}")
        elif isinstance(widget, QLineEdit):
            inputs.append(f"Edit Line {i+1}: {widget.text()}")
    status_bar.showMessage(", ".join(inputs))

button_print.clicked.connect(print_inputs_to_status_bar)
main_layout.addWidget(button_print)

main_window.show()
app.exec()
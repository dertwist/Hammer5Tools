from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QScrollArea, QLabel, QLineEdit,
    QCheckBox, QSpinBox, QDoubleSpinBox, QPushButton
)
from PySide6.QtCore import Qt


class JsonEditorWidget(QWidget):
    def __init__(self, document, parent=None):
        super().__init__(parent)
        self.document = document
        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.form_container = QWidget()
        self.form_layout = QFormLayout(self.form_container)
        scroll.setWidget(self.form_container)
        layout.addWidget(scroll)

        # Connect document signals to refresh the editor display
        self.document.content_changed.connect(self.refresh_editor)
        self.document.selection_changed.connect(self.edit_selected_item)
        self.refresh_editor()

    def refresh_editor(self):
        # Remove all rows
        while self.form_layout.rowCount() > 0:
            self.form_layout.removeRow(0)

        if self.document.selected_item:
            self.edit_selected_item(self.document.selected_item)
        else:
            label = QLabel("Select an item in the hierarchy to edit its properties")
            label.setAlignment(Qt.AlignCenter)
            self.form_layout.addRow(label)

    def edit_selected_item(self, item_data):
        while self.form_layout.rowCount() > 0:
            self.form_layout.removeRow(0)
        if not item_data:
            return
        title = QLabel(f"<h3>Editing: {item_data.get('_class', item_data.get('name', 'Selected Item'))}</h3>")
        title.setAlignment(Qt.AlignCenter)
        self.form_layout.addRow(title)
        if isinstance(item_data, dict):
            for key, value in item_data.items():
                self.add_property_field(key, value)
        elif isinstance(item_data, list):
            for i, value in enumerate(item_data):
                if isinstance(value, (dict, list)):
                    btn = QPushButton(f"Edit item {i}")
                    self.form_layout.addRow(f"Item {i}:", btn)
                else:
                    self.add_property_field(str(i), value)
        else:
            self.add_property_field("Value", item_data)
        apply_btn = QPushButton("Apply Changes")
        apply_btn.clicked.connect(self.apply_changes)
        self.form_layout.addRow(apply_btn)

    def add_property_field(self, key, value):
        if isinstance(value, bool):
            field = QCheckBox()
            field.setChecked(value)
        elif isinstance(value, int):
            field = QSpinBox()
            field.setRange(-1000000, 1000000)
            field.setValue(value)
        elif isinstance(value, float):
            field = QDoubleSpinBox()
            field.setRange(-1000000, 1000000)
            field.setDecimals(6)
            field.setValue(value)
        elif isinstance(value, str):
            field = QLineEdit(value)
        else:
            field = QLineEdit(str(value))
        field.setProperty("key", key)
        self.form_layout.addRow(key, field)

    def apply_changes(self):
        # This method would gather changes from form fields and update the document.
        # For brevity, we print a message.
        print("Apply changes clicked.")
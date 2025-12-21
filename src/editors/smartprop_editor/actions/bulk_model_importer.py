import os
import copy
import uuid

from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QCheckBox, QFileDialog
from PySide6.QtCore import Signal
from src.styles.common import apply_stylesheets

class BulkModelImporterDialog(QDialog):
    accepted_data = Signal(list, bool, int)

    def __init__(self, parent=None, current_folder=None):
        super().__init__(parent)
        self.setWindowTitle("Bulk Model Importer")
        self.resize(400, 300)
        self.files = []
        self.current_folder = current_folder

        layout = QVBoxLayout(self)
        self.list_widget = QListWidget(self)
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)
        layout.addWidget(self.list_widget)

        browse_btn = QPushButton("Browse Files", self)
        browse_btn.clicked.connect(self.browse_files)
        layout.addWidget(browse_btn)

        self.ref_checkbox = QCheckBox("Create ref element?", self)
        self.ref_checkbox.setChecked(True)
        layout.addWidget(self.ref_checkbox)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK", self)
        ok_btn.clicked.connect(self.on_ok)
        cancel_btn = QPushButton("Cancel", self)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        apply_stylesheets(self)

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select vmdl Files", self.current_folder, "vmdl Files (*.vmdl)")
        if files:
            self.files = files
            self.list_widget.clear()
            for f in files:
                item = QListWidgetItem(f)
                self.list_widget.addItem(item)
            if self.list_widget.count() > 0:
                self.list_widget.setCurrentRow(0)

    def on_ok(self):
        if not self.files:
            self.reject()
            return
        ref_index = self.list_widget.currentRow() if self.list_widget.currentRow() >= 0 else 0
        self.accepted_data.emit(self.files, self.ref_checkbox.isChecked(), ref_index)
        self.accept()
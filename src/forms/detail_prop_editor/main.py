"""
Detail Prop Editor — edits an addon's scripts/detail_prop_types.vdata.

Layout mirrors the SmartProp editor: a hierarchy of detail types and their
models on the left, a compact property editor for the selected item on the
right, and a save bar along the bottom.
"""

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QPushButton, QLabel,
    QScrollArea, QMessageBox, QInputDialog,
)

from src.common import enable_dark_title_bar
from src.styles.common import apply_stylesheets
from src.settings.common import get_addon_dir, get_addon_name
from src.editors.smartprop_editor.property import compact

from .hierarchy import DetailPropTree, KIND_TYPE, payload
from .rows import ModelRow, SectionHeader, build_row, apply_zebra
from .schema import MODEL_FIELDS_BY_KEY, MODEL_FIELD_GROUPS, TYPE_FIELDS
from .vdata_io import get_vdata_path, load_vdata, save_vdata


class DetailPropEditorWidget(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detail Prop Editor")
        self.resize(1180, 780)
        self.setMinimumSize(880, 520)
        enable_dark_title_bar(self)
        self.setStyleSheet("background-color: #151515;")

        self.addon_dir = get_addon_dir()
        self.vdata_path = get_vdata_path(self.addon_dir)

        self._build_ui()
        apply_stylesheets(self)
        self._load()

    # ------------------------------------------------------------------ UI --

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_hierarchy_panel())
        splitter.addWidget(self._build_property_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([380, 800])
        root.addWidget(splitter, 1)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self.save_button = QPushButton("Save")
        self.save_button.setMinimumWidth(140)
        self.save_button.setMinimumHeight(30)
        self.save_button.clicked.connect(self.save)
        bottom.addWidget(self.save_button)
        root.addLayout(bottom)

    def _build_hierarchy_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.hierarchy = DetailPropTree()
        self.hierarchy.selection_changed.connect(self._on_selection_changed)
        layout.addWidget(self.hierarchy, 1)

        buttons = QHBoxLayout()
        buttons.setSpacing(4)
        for text, icon, tooltip, handler in (
            ("Type", "add", "Add a new detail prop type", self.add_type),
            ("Model", "add", "Add a model to the selected type", self.hierarchy.add_model),
            ("Duplicate", "copy", "Duplicate the selected type or model",
             self.hierarchy.duplicate_current),
            ("Delete", "delete", "Delete the selected type or model", self.delete_selected),
        ):
            button = QPushButton(text)
            button.setIcon(compact.cs2_icon(icon))
            button.setToolTip(tooltip)
            button.clicked.connect(handler)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        return panel

    def _build_property_panel(self) -> QWidget:
        self.property_area = QScrollArea()
        self.property_area.setWidgetResizable(True)
        self.property_area.setFrameShape(QScrollArea.NoFrame)

        self.property_host = QWidget()
        self.property_host.setStyleSheet(compact.widget_qss())
        self.property_layout = QVBoxLayout(self.property_host)
        self.property_layout.setContentsMargins(0, 0, 0, 8)
        self.property_layout.setSpacing(0)
        self.property_layout.setAlignment(Qt.AlignTop)
        self.property_area.setWidget(self.property_host)
        return self.property_area

    # ---------------------------------------------------------------- data --

    def _set_title(self, suffix: str = ""):
        """The file being edited lives in the title bar rather than a top row."""
        self.setWindowTitle(f"Detail Prop Editor — {get_addon_name()}{suffix}")

    def _load(self):
        if not self.vdata_path:
            self.setWindowTitle("Detail Prop Editor — no addon selected")
            self.save_button.setEnabled(False)
            QMessageBox.warning(
                self, "No Addon Selected",
                "Select an addon before editing detail props."
            )
            return
        existed = os.path.exists(self.vdata_path)
        self.hierarchy.load(load_vdata(self.vdata_path))
        self.setToolTip(self.vdata_path)
        self._set_title("" if existed else "   (new file, not saved yet)")

    def add_type(self):
        name, ok = QInputDialog.getText(self, "Add Detail Type", "Type name:")
        name = (name or "").strip()
        if ok and name:
            self.hierarchy.add_type(name)

    def delete_selected(self):
        item = self.hierarchy.tree.currentItem()
        if item is None:
            return
        if self.hierarchy.kind_of(item) == KIND_TYPE:
            if QMessageBox.question(
                self, "Delete Detail Type",
                f"Delete detail type '{item.text(0)}' and all of its models?"
            ) != QMessageBox.Yes:
                return
        error = self.hierarchy.remove_current()
        if error:
            QMessageBox.information(self, "Cannot Delete", error)

    # --------------------------------------------------- property rendering --

    def _clear_properties(self):
        while self.property_layout.count():
            child = self.property_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _on_selection_changed(self, item):
        self._clear_properties()
        self.current_item = item
        if item is None:
            return
        data = payload(item)
        if self.hierarchy.kind_of(item) == KIND_TYPE:
            self._render_type(item, data)
        else:
            self._render_model(item, data)
        apply_zebra(self.property_layout)

    def _add_row(self, row, item, key):
        """Wire a row so edits write straight into the item's dict."""
        def commit():
            data = payload(item)
            data[key] = row.value()
            self.hierarchy.set_payload(item, data)
            self.hierarchy.refresh_item(item)

        row.edited.connect(commit)
        self.property_layout.addWidget(row)

    def _render_type(self, item, data):
        self.property_layout.addWidget(SectionHeader(f"Detail Type — {item.text(0)}"))
        for field in TYPE_FIELDS:
            row = build_row(field, data.get(field.key, field.default))
            self._add_row(row, item, field.key)

        count = item.childCount()
        total = sum(float(payload(item.child(j)).get("m_flWeight", 1.0))
                    for j in range(count)) or 1.0
        summary = QLabel(f"  {count} model(s), total weight {total:g}")
        summary.setStyleSheet("color: #999; font: 8pt 'Segoe UI'; padding: 8px 6px;")
        self.property_layout.addWidget(summary)

    def _render_model(self, item, data):
        for group_name, keys in MODEL_FIELD_GROUPS:
            self.property_layout.addWidget(SectionHeader(group_name))
            for key in keys:
                field = MODEL_FIELDS_BY_KEY[key]
                row = build_row(field, data.get(key, field.default))
                if isinstance(row, ModelRow):
                    row.browse_requested.connect(lambda r=row: self._browse_model(r))
                self._add_row(row, item, key)

    # -------------------------------------------------------------- browse --

    def _browse_model(self, row: ModelRow):
        # The browser already yields addon-relative resource paths, so no
        # _to_addon_relative() round-trip is needed here.
        from src.widgets.model_browser import pick_model
        path = pick_model(self, current_path=row.value())
        if path:
            row.set_value(path)

    # ---------------------------------------------------------------- save --

    def save(self):
        if not self.vdata_path:
            return
        try:
            save_vdata(self.vdata_path, self.hierarchy.to_types())
        except Exception as error:
            QMessageBox.critical(self, "Save Failed", f"Could not write:\n{self.vdata_path}\n\n{error}")
            return
        self._set_title()
        parent = self.parent()
        if parent is not None and hasattr(parent, "update_title"):
            parent.update_title(text="Detail prop types saved")

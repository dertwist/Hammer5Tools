"""
Detail Prop Editor — edits an addon's scripts/detail_prop_types.vdata.

Layout mirrors the SmartProp editor: a hierarchy of detail types and their
models on the left, a compact property editor for the selected item on the
right, and a save bar along the bottom.
"""

import os

from PySide6.QtCore import Qt, QEvent
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QPushButton, QLabel,
    QScrollArea, QMessageBox, QInputDialog, QDockWidget, QUndoView, QMenu,
)
from PySide6.QtGui import (
    QUndoStack, QUndoCommand, QShortcut, QKeySequence,
)

from src.common import enable_dark_title_bar, fast_deepcopy, set_qdock_tab_style
from src.styles.common import apply_stylesheets
from src.settings.common import get_addon_dir, get_addon_name
from src.editors.smartprop_editor.property import compact

from .hierarchy import (
    DetailPropTree, KIND_TYPE, payload,
    get_selection_path, find_item_by_path, restore_selection_path,
)
from .rows import ModelRow, SectionHeader, build_row, apply_zebra, FloatRow, pretty_name
from .schema import MODEL_FIELDS_BY_KEY, MODEL_FIELD_GROUPS, TYPE_FIELDS
from .vdata_io import get_vdata_path, load_vdata, save_vdata


class DetailPropTreeSnapshotCommand(QUndoCommand):
    def __init__(self, editor, description, old_types, new_types, old_selection_path=None, new_selection_path=None):
        super().__init__(description)
        self.editor = editor
        self.old_types = fast_deepcopy(old_types)
        self.new_types = fast_deepcopy(new_types)
        self.old_selection_path = old_selection_path
        self.new_selection_path = new_selection_path
        self._first_redo = True

    def redo(self):
        if self._first_redo:
            self._first_redo = False
            return
        self.editor._restore_tree_state(self.new_types, self.new_selection_path)

    def undo(self):
        self.editor._restore_tree_state(self.old_types, self.old_selection_path)


class DetailPropPropertySnapshotCommand(QUndoCommand):
    _MERGE_ID = 3001

    def __init__(self, editor, item, key, old_value, new_value):
        super().__init__(f"Edit {pretty_name(key)}")
        self.editor = editor
        self.item = item
        self.key = key
        self.old_value = fast_deepcopy(old_value)
        self.new_value = fast_deepcopy(new_value)
        self._item_path = get_selection_path(editor.hierarchy.tree, item)
        self._first_redo = True

    def id(self):
        return self._MERGE_ID

    def mergeWith(self, other):
        if not isinstance(other, DetailPropPropertySnapshotCommand):
            return False
        if self._item_path != other._item_path:
            return False
        if self.key != other.key:
            return False
        self.new_value = other.new_value
        return True

    def _apply_value(self, val):
        item = find_item_by_path(self.editor.hierarchy.tree, self._item_path)
        if item is None:
            return

        data = payload(item)
        data[self.key] = val
        self.editor.hierarchy.set_payload(item, data)
        self.editor.hierarchy.refresh_item(item)

        if self.editor.hierarchy.tree.currentItem() is item:
            self.editor._on_selection_changed(item)

    def redo(self):
        if self._first_redo:
            self._first_redo = False
            return
        self._apply_value(self.new_value)
        self.editor._mark_modified()

    def undo(self):
        self._apply_value(self.old_value)
        self.editor._mark_modified()


class DetailPropEditorWidget(QMainWindow):
    DetailPropTreeSnapshotCommand = DetailPropTreeSnapshotCommand

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detail Prop Editor")
        self.resize(1180, 780)
        self.setMinimumSize(880, 520)
        enable_dark_title_bar(self)
        self.setStyleSheet("background-color: #151515;")

        self.addon_dir = get_addon_dir()
        self.vdata_path = get_vdata_path(self.addon_dir)
        self._modified = False

        self.undo_stack = QUndoStack(self)
        self.undo_stack.setUndoLimit(400)
        self.undo_stack.cleanChanged.connect(self._on_clean_changed)

        self._slider_dragging = False
        self._slider_pre_drag_value = None

        self._build_ui()
        self._setup_history_dock()

        # Window-level shortcuts
        _undo_sc = QShortcut(QKeySequence.Undo, self)
        _undo_sc.activated.connect(self.undo_stack.undo)
        _redo_sc = QShortcut(QKeySequence.Redo, self)
        _redo_sc.activated.connect(self.undo_stack.redo)
        _redo_sc2 = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        _redo_sc2.activated.connect(self.undo_stack.redo)
        _save_sc = QShortcut(QKeySequence.Save, self)
        _save_sc.activated.connect(self.save)

        # Context menu policy & event filter
        self.hierarchy.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.hierarchy.tree.customContextMenuRequested.connect(self.open_context_menu)
        self.hierarchy.tree.installEventFilter(self)

        apply_stylesheets(self)
        self._load()

        set_qdock_tab_style(self.findChildren)

    # ------------------------------------------------------------------ UI --

    def _build_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root = QVBoxLayout(central_widget)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_hierarchy_panel())
        splitter.addWidget(self._build_property_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([380, 800])
        root.addWidget(splitter, 1)

    def _build_hierarchy_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.hierarchy = DetailPropTree(editor=self)
        self.hierarchy.selection_changed.connect(self._on_selection_changed)
        layout.addWidget(self.hierarchy, 1)

        buttons = QHBoxLayout()
        buttons.setSpacing(4)

        type_btn = QPushButton("Type")
        type_btn.setIcon(compact.cs2_icon("add"))
        type_btn.setToolTip("Add a new detail prop type")
        type_btn.clicked.connect(self.add_type)
        buttons.addWidget(type_btn)

        model_btn = QPushButton("Model")
        model_btn.setIcon(compact.cs2_icon("add"))
        model_btn.setToolTip("Add a model to the selected type")
        model_btn.clicked.connect(self.hierarchy.add_model)
        buttons.addWidget(model_btn)

        from PySide6.QtGui import QIcon
        self.save_button = QPushButton("Save")
        self.save_button.setIcon(QIcon(":/icons/save_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg"))
        self.save_button.setToolTip("Save detail prop types (Ctrl+S)")
        self.save_button.clicked.connect(self.save)
        buttons.addWidget(self.save_button)

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

    def _setup_history_dock(self):
        self._history_dock = QDockWidget("History", self)
        self._history_dock.setObjectName("DPE_history_dock")
        self._history_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea  |
            Qt.DockWidgetArea.RightDockWidgetArea |
            Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self._history_dock.setMinimumWidth(160)
        history_view = QUndoView(self.undo_stack, self._history_dock)
        self._history_dock.setWidget(history_view)
        self._history_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._history_dock)

    # ----------------------------------------------------------- shortcuts & events --

    def eventFilter(self, source, event):
        if event.type() == QEvent.KeyPress:
            if source == self.hierarchy.tree:
                if event.key() == Qt.Key_Delete:
                    self.delete_selected()
                    return True
                if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_D:
                    self.hierarchy.duplicate_current()
                    return True
        return super().eventFilter(source, event)

    def open_context_menu(self, position):
        menu = QMenu(self)

        # Add Type
        add_type_action = menu.addAction("Add Detail Type")
        add_type_action.triggered.connect(self.add_type)

        # Add Model
        add_model_action = menu.addAction("Add Model")
        add_model_action.triggered.connect(self.hierarchy.add_model)

        menu.addSeparator()

        # Duplicate
        duplicate_action = menu.addAction("Duplicate")
        duplicate_action.triggered.connect(self.hierarchy.duplicate_current)

        # Delete
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(self.delete_selected)

        # Enable/disable based on selection
        current_item = self.hierarchy.tree.currentItem()
        if current_item is None:
            add_model_action.setEnabled(False)
            duplicate_action.setEnabled(False)
            delete_action.setEnabled(False)

        menu.exec(self.hierarchy.tree.mapToGlobal(position))

    # ---------------------------------------------------------------- data --

    def _set_title(self, suffix: str = ""):
        """The file being edited lives in the title bar rather than a top row."""
        self.setWindowTitle(f"Detail Prop Editor — {get_addon_name()}{suffix}")

    def _mark_modified(self):
        self._modified = True
        self._set_title(" *")

    def _on_clean_changed(self, clean):
        self._modified = not clean
        self._set_title("" if clean else " *")

    def _restore_tree_state(self, types, selection_path):
        self.hierarchy.load(types)
        restore_selection_path(self.hierarchy.tree, selection_path)

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
        self.undo_stack.clear()
        self._set_title("" if existed else " *")
        if not existed:
            self._modified = True

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

    def _on_slider_pressed(self, row, item, key):
        self._slider_dragging = True
        data = payload(item)
        self._slider_pre_drag_value = data.get(key, row.field.default)

    def _on_slider_committed(self, row, item, key):
        self._slider_dragging = False
        old_val = self._slider_pre_drag_value
        new_val = row.value()
        if old_val != new_val:
            cmd = DetailPropPropertySnapshotCommand(self, item, key, old_val, new_val)
            self.undo_stack.push(cmd)
            self._mark_modified()

    def _on_row_edited(self, row, item, key):
        if self._slider_dragging:
            data = payload(item)
            data[key] = row.value()
            self.hierarchy.set_payload(item, data)
            self.hierarchy.refresh_item(item)
            return

        data = payload(item)
        old_val = data.get(key, row.field.default)
        new_val = row.value()
        if old_val != new_val:
            cmd = DetailPropPropertySnapshotCommand(self, item, key, old_val, new_val)
            self.undo_stack.push(cmd)

            data[key] = new_val
            self.hierarchy.set_payload(item, data)
            self.hierarchy.refresh_item(item)
            self._mark_modified()

    def _add_row(self, row, item, key):
        """Wire a row so edits write straight into the item's dict with Undo support."""
        row.edited.connect(lambda: self._on_row_edited(row, item, key))
        if isinstance(row, FloatRow):
            row.float_widget.slider_pressed.connect(lambda: self._on_slider_pressed(row, item, key))
            row.float_widget.committed.connect(lambda: self._on_slider_committed(row, item, key))
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

    # ---------------------------------------------------------------- save & close --

    def save(self):
        if not self.vdata_path:
            return
        try:
            save_vdata(self.vdata_path, self.hierarchy.to_types())
        except Exception as error:
            QMessageBox.critical(self, "Save Failed", f"Could not write:\n{self.vdata_path}\n\n{error}")
            return
        self.undo_stack.setClean()
        parent = self.parent()
        if parent is not None and hasattr(parent, "update_title"):
            parent.update_title(text="Detail prop types saved")

    def closeEvent(self, event):
        if self._modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save them before closing?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Yes:
                self.save()
                event.accept()
            elif reply == QMessageBox.No:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

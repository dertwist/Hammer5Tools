import os
import json
from PySide6.QtWidgets import QTabWidget, QWidget, QVBoxLayout, QMessageBox
from PySide6.QtCore import QObject, Signal

from json_editor import JsonEditorWidget


class Document(QObject):
    content_changed = Signal()
    selection_changed = Signal(object)

    def __init__(self, file_path=None):
        super().__init__()
        self.file_path = file_path
        self.data = {}
        self.modified = False
        self.undo_stack = []
        self.redo_stack = []
        self.selected_item = None
        if not file_path:
            # Initialize with a default data example
            self.data = {
                "generic_data_type": "CSmartPropRoot",
                "editor_info": {
                    "name": "Hammer 5 Tools",
                    "version": "4.5.0",
                    "m_nElementID": 8
                },
                "m_Variables": [
                    {
                        "_class": "CSmartPropVariable_CoordinateSpace",
                        "m_VariableName": "new_var",
                        "m_bExposeAsParameter": False,
                        "m_DefaultValue": "",
                        "m_nElementID": 1
                    },
                    {
                        "_class": "CSmartPropVariable_CoordinateSpace",
                        "m_VariableName": "new_var_1",
                        "m_bExposeAsParameter": False,
                        "m_DefaultValue": "",
                        "m_nElementID": 2
                    },
                    {
                        "_class": "CSmartPropVariable_CoordinateSpace",
                        "m_VariableName": "new_var_2",
                        "m_bExposeAsParameter": False,
                        "m_DefaultValue": "",
                        "m_nElementID": 3
                    }
                ],
                "m_Choices": [],
                "m_Children": [
                    {
                        "_class": "CSmartPropElement_Group",
                        "m_bEnabled": True,
                        "m_nElementID": 4,
                        "m_Modifiers": [],
                        "m_SelectionCriteria": [],
                        "m_sLabel": "Group_04",
                        "m_Children": [
                            {
                                "_class": "CSmartPropElement_PlaceInSphere",
                                "m_bEnabled": True,
                                "m_nElementID": 5,
                                "m_bAlignOrientation": False,
                                "m_flPositionRadiusOuter": 0.0,
                                "m_flPositionRadiusInner": 0.0,
                                "m_nCountMax": 0,
                                "m_nCountMin": 0,
                                "m_Modifiers": [],
                                "m_SelectionCriteria": [],
                                "m_sLabel": "PlaceInSphere_05",
                                "m_Children": [
                                    {
                                        "_class": "CSmartPropElement_PlaceMultiple",
                                        "m_bEnabled": True,
                                        "m_nElementID": 6,
                                        "m_Expression": {"m_Expression": ""},
                                        "m_Modifiers": [],
                                        "m_SelectionCriteria": [],
                                        "m_sLabel": "PlaceMultiple_06",
                                        "m_Children": [
                                            {
                                                "_class": "CSmartPropElement_PlaceMultiple",
                                                "m_bEnabled": True,
                                                "m_nElementID": 7,
                                                "m_Expression": {"m_Expression": ""},
                                                "m_Modifiers": [],
                                                "m_SelectionCriteria": [],
                                                "m_sLabel": "PlaceMultiple_07"
                                            },
                                            {
                                                "_class": "CSmartPropElement_PlaceOnPath",
                                                "m_bEnabled": True,
                                                "m_nElementID": 8,
                                                "m_DefaultPath": None,
                                                "m_PathName": "path",
                                                "m_Modifiers": [],
                                                "m_SelectionCriteria": [],
                                                "m_sLabel": "PlaceOnPath_08"
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }

    @property
    def display_name(self):
        return os.path.basename(self.file_path) if self.file_path else "Untitled"

    def set_content(self, content):
        try:
            self.data = json.loads(content)
            self.modified = False
            self.undo_stack = []
            self.redo_stack = []
            self.content_changed.emit()
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {str(e)}")

    def get_content(self):
        return json.dumps(self.data, indent=2)

    def is_modified(self):
        return self.modified

    def set_modified(self, modified=True):
        self.modified = modified
        self.content_changed.emit()

    def update_data(self, new_data):
        self.undo_stack.append(json.dumps(self.data))
        self.redo_stack = []
        self.data = new_data
        self.set_modified(True)
        self.content_changed.emit()

    def update_selected_item(self, path, new_value):
        self.undo_stack.append(json.dumps(self.data))
        self.redo_stack = []
        # A simple dot-separated path traversal
        current = self.data
        path_parts = path.split('.')
        for part in path_parts[:-1]:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
                current = current[int(part)]
            else:
                raise ValueError(f"Invalid path: {path}")
        last_part = path_parts[-1]
        if isinstance(current, dict) and last_part in current:
            current[last_part] = new_value
        elif isinstance(current, list) and last_part.isdigit() and int(last_part) < len(current):
            current[int(last_part)] = new_value
        else:
            raise ValueError(f"Invalid path: {path}")
        self.set_modified(True)
        self.content_changed.emit()

    def select_item(self, item_data):
        self.selected_item = item_data
        self.selection_changed.emit(item_data)

    def can_undo(self):
        return len(self.undo_stack) > 0

    def can_redo(self):
        return len(self.redo_stack) > 0

    def undo(self):
        if not self.can_undo():
            return
        self.redo_stack.append(json.dumps(self.data))
        previous_state = self.undo_stack.pop()
        self.data = json.loads(previous_state)
        self.set_modified(bool(self.undo_stack))
        self.content_changed.emit()

    def redo(self):
        if not self.can_redo():
            return
        self.undo_stack.append(json.dumps(self.data))
        next_state = self.redo_stack.pop()
        self.data = json.loads(next_state)
        self.set_modified(True)
        self.content_changed.emit()


class DocumentTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.tabCloseRequested.connect(self.close_tab)
        self.currentChanged.connect(self.on_current_changed)

    def add_document(self, document):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        editor = JsonEditorWidget(document)
        layout.addWidget(editor)
        index = self.addTab(container, document.display_name)
        self.setCurrentIndex(index)
        # Connect document changed signal to update the tab text when modified.
        document.content_changed.connect(lambda: self.update_tab_text(document))

    def update_tab_text(self, document):
        for i in range(self.count()):
            if self.document_at(i) == document:
                text = document.display_name
                if document.is_modified():
                    text = f"*{text}"
                self.setTabText(i, text)
                break

    def document_at(self, index):
        if 0 <= index < self.count():
            container = self.widget(index)
            # Assuming the first widget in the layout is the JSON editor
            editor = container.layout().itemAt(0).widget()
            return editor.document
        return None

    def current_document(self):
        return self.document_at(self.currentIndex())

    def close_tab(self, index):
        document = self.document_at(index)
        if not document:
            return
        if document.is_modified():
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                f"Document '{document.display_name}' has unsaved changes. Save?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if reply == QMessageBox.Save:
                self.setCurrentIndex(index)
                self.parent().save_document()
            elif reply == QMessageBox.Cancel:
                return
        self.removeTab(index)

    def has_unsaved_changes(self):
        for i in range(self.count()):
            doc = self.document_at(i)
            if doc and doc.is_modified():
                return True
        return False

    def on_current_changed(self, index):
        # Notify the main window to update the UI in response to tab change.
        if self.parent() is not None and hasattr(self.parent(), "update_ui"):
            self.parent().update_ui()
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

def process_bulk_models(document, files, create_ref, ref_index):
    from src.settings.main import get_addon_dir
    from src.editors.smartprop_editor._common import get_clean_class_name_value, get_label_id_from_value, get_ElementID_key
    from src.editors.smartprop_editor.element_id import update_value_ElementID
    from src.widgets import HierarchyItemModel

    addon_path = get_addon_dir()
    ref_id = None

    if not hasattr(document, "reference_objects"):
        document.reference_objects = {}

    parent_item = document.ui.tree_hierarchy_widget.currentItem()
    if parent_item is None:
        parent_item = document.ui.tree_hierarchy_widget.invisibleRootItem()

    for index, file_path in enumerate(files):
        rel_path = os.path.relpath(file_path, addon_path).replace(os.path.sep, '/')
        base_name, _ = os.path.splitext(os.path.basename(file_path))
        element_dict = {
            "_class": "CSmartPropElement_Model",
            "m_sModelName": rel_path,
            "m_vModelScale": None,
            "m_MaterialGroupName": None,
            "m_Modifiers": [],
            "m_SelectionCriteria": []
        }
        is_reference = create_ref and (index == ref_index)
        if is_reference:
            element_dict["m_sLabel"] = f"{base_name}_REF"
        else:
            element_dict["m_sLabel"] = base_name
            if create_ref and ref_id is not None:
                element_dict["m_nReferenceID"] = ref_id
                element_dict["m_sReferenceObjectID"] = str(uuid.uuid4())
        element_value = copy.deepcopy(element_dict)
        update_value_ElementID(element_value)
        label = element_value.get("m_sLabel", get_label_id_from_value(element_value))
        new_item = HierarchyItemModel(
            _name=label,
            _data=element_value,
            _class=get_clean_class_name_value(element_value),
            _id=get_ElementID_key(element_value)
        )
        parent_item.addChild(new_item)
        if is_reference:
            try:
                ref_id = element_value.get("m_nElementID")
            except Exception:
                ref_id = None
        else:
            if create_ref and ref_id is not None and "m_sReferenceObjectID" in element_value:
                document.reference_objects[element_value["m_sReferenceObjectID"]] = copy.deepcopy(element_value)

    apply_stylesheets(document.ui.tree_hierarchy_widget)
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QRadioButton, QDialogButtonBox, QMessageBox, QAbstractItemView, QCheckBox,
    QSizePolicy
)
from PySide6.QtCore import Qt
from src.editors.smartprop_editor.vmap_vsmart_converter import scan_vmap_for_props, convert_vmap_props_to_vsmart
from src.common import get_cs2_path
from src.settings.common import get_addon_name

class VMapToVSmartConverterDialog(QDialog):
    """
    Dialog wizard to parse a VMAP, select placed props, and compile them into a VSMART.
    """
    def __init__(self, parent=None, initial_vmap=None):
        super().__init__(parent)
        self.setWindowTitle("Convert VMAP Props to SmartProp")
        self.resize(800, 600)
        self.setMinimumSize(600, 450)
        
        self.scanned_entities = []
        self.init_ui()
        
        if initial_vmap:
            self.vmap_input.setText(initial_vmap)
            self.scan_vmap()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)
        
        # 1. VMAP Selection
        vmap_layout = QHBoxLayout()
        vmap_layout.addWidget(QLabel("Map File (.vmap):"))
        self.vmap_input = QLineEdit()
        self.vmap_input.setPlaceholderText("Select Hammer 5 map file...")
        self.vmap_input.textChanged.connect(self.on_vmap_path_changed)
        vmap_layout.addWidget(self.vmap_input)
        
        vmap_browse = QPushButton("Browse...")
        vmap_browse.clicked.connect(self.browse_vmap)
        vmap_layout.addWidget(vmap_browse)
        main_layout.addLayout(vmap_layout)
        
        # 2. Table and Filters
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter Props:"))
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Search by model name or classname...")
        self.filter_input.textChanged.connect(self.filter_table)
        filter_layout.addWidget(self.filter_input)
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(lambda: self.set_all_selection(True))
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(lambda: self.set_all_selection(False))
        
        filter_layout.addWidget(select_all_btn)
        filter_layout.addWidget(deselect_all_btn)
        main_layout.addLayout(filter_layout)
        
        # Table widget
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Select", "Classname", "Model Path", "Origin", "Scale"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        main_layout.addWidget(self.table)
        
        # Status Label
        self.status_label = QLabel("Please select a VMAP file to scan.")
        main_layout.addWidget(self.status_label)
        
        # 3. Pivot Strategy Group Box
        pivot_group = QGroupBox("Pivot Position Strategy")
        pivot_layout = QHBoxLayout(pivot_group)
        
        self.pivot_center = QRadioButton("Center of Selection (Recommended)")
        self.pivot_center.setChecked(True)
        self.pivot_first = QRadioButton("First Selected Prop")
        self.pivot_origin = QRadioButton("Map Origin [0, 0, 0]")
        
        pivot_layout.addWidget(self.pivot_center)
        pivot_layout.addWidget(self.pivot_first)
        pivot_layout.addWidget(self.pivot_origin)
        main_layout.addWidget(pivot_group)
        
        # 4. Output VSMART Selection
        vsmart_layout = QHBoxLayout()
        vsmart_layout.addWidget(QLabel("Output SmartProp (.vsmart):"))
        self.vsmart_input = QLineEdit()
        self.vsmart_input.setPlaceholderText("Output SmartProp path...")
        vsmart_layout.addWidget(self.vsmart_input)
        
        vsmart_browse = QPushButton("Browse...")
        vsmart_browse.clicked.connect(self.browse_vsmart)
        vsmart_layout.addWidget(vsmart_browse)
        main_layout.addLayout(vsmart_layout)
        
        # 5. Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText("Convert")
        self.button_box.accepted.connect(self.perform_conversion)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)
        
        # Keep Convert button disabled until we have selection
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)

    def browse_vmap(self):
        cs2_path = get_cs2_path()
        addon_name = get_addon_name() or "addon"
        start_dir = os.path.join(cs2_path, "content", "csgo_addons", addon_name, "maps") if cs2_path else ""
        if not os.path.exists(start_dir):
            start_dir = ""
            
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select VMAP File", start_dir, "VMAP Files (*.vmap)"
        )
        if file_path:
            self.vmap_input.setText(file_path)
            self.scan_vmap()

    def browse_vsmart(self):
        cs2_path = get_cs2_path()
        addon_name = get_addon_name() or "addon"
        start_dir = os.path.join(cs2_path, "content", "csgo_addons", addon_name, "smartprops") if cs2_path else ""
        os.makedirs(start_dir, exist_ok=True)
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save SmartProp", start_dir, "SmartProp Files (*.vsmart)"
        )
        if file_path:
            if not file_path.endswith(".vsmart"):
                file_path += ".vsmart"
            self.vsmart_input.setText(file_path)

    def on_vmap_path_changed(self):
        # Reset output path if vmap changes
        vmap_path = self.vmap_input.text()
        if vmap_path and vmap_path.endswith(".vmap"):
            # Set a default output smartprop path based on VMAP name
            vmap_dir = os.path.dirname(vmap_path)
            # Find smartprops folder relative to content addon
            addon_dir = os.path.dirname(vmap_dir)
            vsmart_dir = os.path.join(addon_dir, "smartprops")
            basename = os.path.splitext(os.path.basename(vmap_path))[0]
            default_vsmart = os.path.join(vsmart_dir, f"{basename}_group.vsmart")
            self.vsmart_input.setText(default_vsmart)

    def scan_vmap(self):
        vmap_path = self.vmap_input.text()
        if not os.path.exists(vmap_path):
            self.status_label.setText("Error: Map file does not exist.")
            return
            
        self.status_label.setText("Scanning map for props...")
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
        self.table.setRowCount(0)
        
        # Scan props
        self.scanned_entities = scan_vmap_for_props(vmap_path)
        
        self.table.setRowCount(len(self.scanned_entities))
        for idx, ent in enumerate(self.scanned_entities):
            # Checkbox item
            chk_widget = QCheckBox()
            chk_widget.setStyleSheet("margin-left:5px;")
            chk_widget.stateChanged.connect(self.update_convert_button_state)
            
            # Align checkbox center
            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.addWidget(chk_widget)
            cell_layout.setAlignment(Qt.AlignCenter)
            cell_layout.setContentsMargins(0,0,0,0)
            self.table.setCellWidget(idx, 0, cell_widget)
            
            # Text fields
            self.table.setItem(idx, 1, QTableWidgetItem(ent["classname"]))
            self.table.setItem(idx, 2, QTableWidgetItem(ent["model"]))
            
            org_str = f"{round(ent['origin'][0],1)}, {round(ent['origin'][1],1)}, {round(ent['origin'][2],1)}"
            self.table.setItem(idx, 3, QTableWidgetItem(org_str))
            
            scale_str = f"{round(ent['scales'][0],2)}, {round(ent['scales'][1],2)}, {round(ent['scales'][2],2)}"
            self.table.setItem(idx, 4, QTableWidgetItem(scale_str))
            
        self.status_label.setText(f"Found {len(self.scanned_entities)} prop entities in map.")
        self.update_convert_button_state()

    def set_all_selection(self, select: bool):
        for idx in range(self.table.rowCount()):
            cell = self.table.cellWidget(idx, 0)
            if cell:
                chk = cell.findChild(QCheckBox)
                if chk:
                    chk.setChecked(select)
        self.update_convert_button_state()

    def update_convert_button_state(self):
        selected_count = len(self.get_selected_indices())
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(selected_count > 0)
        if len(self.scanned_entities) > 0:
            self.status_label.setText(f"Scanned {len(self.scanned_entities)} props. Selected {selected_count} for conversion.")

    def get_selected_indices(self) -> list:
        indices = []
        for idx in range(self.table.rowCount()):
            cell = self.table.cellWidget(idx, 0)
            if cell:
                chk = cell.findChild(QCheckBox)
                if chk and chk.isChecked():
                    indices.append(idx)
        return indices

    def filter_table(self):
        query = self.filter_input.text().lower()
        for idx in range(self.table.rowCount()):
            match = False
            for col in [1, 2]:
                item = self.table.item(idx, col)
                if item and query in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(idx, not match)

    def perform_conversion(self):
        vmap_path = self.vmap_input.text()
        vsmart_path = self.vsmart_input.text()
        selected_indices = self.get_selected_indices()
        
        # 1. Validation
        if not vmap_path or not os.path.exists(vmap_path):
            QMessageBox.critical(self, "Error", "A valid VMAP file must be specified.")
            return
            
        if not vsmart_path:
            QMessageBox.critical(self, "Error", "A target VSMART output path must be specified.")
            return
            
        if not selected_indices:
            QMessageBox.critical(self, "Error", "No props have been selected for conversion.")
            return
            
        # 2. Check for Hammer running
        import psutil
        hammer_running = False
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and 'hammer' in proc.info['name'].lower():
                hammer_running = True
                break
                
        if hammer_running:
            reply = QMessageBox.warning(
                self,
                "Hammer Editor Running",
                "The Hammer Editor seems to be running. If the map is currently loaded in Hammer, saving external changes "
                "might cause conflicts or data loss.\n\nAre you sure you want to proceed with conversion?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        # 3. Determine pivot strategy
        strategy = "center"
        if self.pivot_first.isChecked():
            strategy = "first"
        elif self.pivot_origin.isChecked():
            strategy = "origin"
            
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
        self.status_label.setText("Performing map conversion and generating smartprop...")
        
        # Execute
        success = convert_vmap_props_to_vsmart(
            vmap_path=vmap_path,
            selected_indices=selected_indices,
            output_vsmart_path=vsmart_path,
            pivot_strategy=strategy
        )
        
        if success:
            QMessageBox.information(
                self,
                "Conversion Success",
                f"Successfully converted {len(selected_indices)} props to {os.path.basename(vsmart_path)}.\n\nThe original props in the map have been replaced by a smart prop entity."
            )
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Conversion Failed",
                "An error occurred during map parsing or write operation. Please check log console."
            )
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(True)
            self.status_label.setText("Conversion failed.")

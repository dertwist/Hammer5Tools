import os
from PySide6.QtWidgets import QDialog, QFileDialog, QListWidgetItem, QMessageBox
from PySide6.QtCore import Qt, Slot
from .ui_main import Ui_UE2SourceMaterialsWidget
from .converter import scan_and_group, UE2SourceWorker
from src.settings.main import get_addon_dir, get_addon_name

class UE2SourceMaterialsWidget(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_UE2SourceMaterialsWidget()
        self.ui.setupUi(self)
        self.setWindowTitle("Material Importer (UE -> Source 2)")
        
        # Set layout stretches: GroupBox=0, Buttons=0, Splitter=1, Progress=0
        self.ui.verticalLayout.setStretch(0, 0)
        self.ui.verticalLayout.setStretch(1, 0)
        self.ui.verticalLayout.setStretch(2, 1)
        self.ui.verticalLayout.setStretch(3, 0)
        
        self.groups = {}
        self.worker = None
        
        # Default paths
        addon_dir = get_addon_dir()
        if addon_dir:
            from src.settings.main import get_settings_value
            default_sub = get_settings_value('UE2Source', 'default_subfolder') or get_addon_name()
            
            # Use forward slashes for the edit fields, converter will handle the rest
            self.ui.output_folder_edit.setText(os.path.join(addon_dir, "materials", default_sub).replace("\\", "/"))
            
            
        # Connections
        self.ui.browse_input_button.clicked.connect(self.browse_input)
        self.ui.browse_output_button.clicked.connect(self.browse_output)
        self.ui.scan_button.clicked.connect(self.scan_folder)
        self.ui.convert_button.clicked.connect(self.start_conversion)
        self.ui.clear_log_button.clicked.connect(self.ui.log_edit.clear)
        
    def browse_input(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Unreal Textures Folder")
        if folder:
            self.ui.input_folder_edit.setText(folder)
            
    def browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.ui.output_folder_edit.setText(folder)

    def get_calculated_rel_path(self):
        path = self.ui.output_folder_edit.text().replace("\\", "/")
        parts = path.split("/")
        try:
            # Find the last occurrence of 'materials' in the path parts
            m_idx = -1
            for i, p in enumerate(parts):
                if p.lower() == "materials":
                    m_idx = i
            
            if m_idx != -1:
                return "/".join(parts[m_idx:])
        except:
            pass
        return ""
            
    def scan_folder(self):
        input_dir = self.ui.input_folder_edit.text()
        if not os.path.exists(input_dir):
            QMessageBox.warning(self, "Error", "Input folder does not exist.")
            return
            
        self.groups = scan_and_group(input_dir)
        self.ui.group_list.clear()
        
        for base_name in sorted(self.groups.keys()):
            item = QListWidgetItem(base_name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.ui.group_list.addItem(item)
            
        self.ui.convert_button.setEnabled(len(self.groups) > 0)
        self.log(f"Scanned {len(self.groups)} groups.")
        
    def log(self, message):
        self.ui.log_edit.append(message)
        
    def start_conversion(self):
        input_dir = self.ui.input_folder_edit.text()
        output_dir = self.ui.output_folder_edit.text()
        rel_path = self.get_calculated_rel_path()
        
        selected_groups = {}
        for i in range(self.ui.group_list.count()):
            item = self.ui.group_list.item(i)
            if item.checkState() == Qt.Checked:
                base_name = item.text()
                selected_groups[base_name] = self.groups[base_name]
                
        if not selected_groups:
            QMessageBox.warning(self, "Error", "No groups selected.")
            return
            
        self.ui.convert_button.setEnabled(False)
        self.ui.scan_button.setEnabled(False)
        self.ui.progress_bar.setValue(0)
        
        self.worker = UE2SourceWorker(input_dir, output_dir, rel_path, selected_groups)
        self.worker.progress.connect(self.on_progress)
        self.worker.file_done.connect(self.on_file_done)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()
        
    @Slot(int, int)
    def on_progress(self, current, total):
        self.ui.progress_bar.setMaximum(total)
        self.ui.progress_bar.setValue(current)
        
    @Slot(str, bool, str)
    def on_file_done(self, name, success, message):
        status = "✔" if success else "❌"
        self.log(f"{status} {name}: {message}")
        
    @Slot(list, list)
    def on_finished(self, created, skipped):
        self.log(f"Finished. Created: {len(created)}, Skipped: {len(skipped)}")
        self.ui.convert_button.setEnabled(True)
        self.ui.scan_button.setEnabled(True)
        QMessageBox.information(self, "Done", f"Conversion complete.\nCreated: {len(created)}\nSkipped: {len(skipped)}")

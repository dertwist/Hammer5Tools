import os
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton
from src.common import JsonToKv3

class QuickCreateDialog(QDialog):
    def __init__(self, folder_path, file_type, parent=None):
        super().__init__(parent)
        self.folder_path = folder_path
        self.file_type = file_type # 'vmdl' or 'vmat'
        self.setWindowTitle(f"Quick Create {file_type.upper()}")
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Enter name for new {file_type.upper()}:"))
        
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)
        
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        
    def accept(self):
        filename = self.name_edit.text().strip()
        if not filename:
            return
        if not filename.endswith(f".{self.file_type}"):
            filename += f".{self.file_type}"
            
        full_path = os.path.join(self.folder_path, filename)
        
        # Create minimal template
        data = {}
        if self.file_type == 'vmdl':
            data = {"m_sMDLFilename": ""}
        elif self.file_type == 'vmat':
            data = {"shader": "create_version_2.vfx"}
            
        kv3_content = JsonToKv3(data, format=self.file_type)
        
        try:
            with open(full_path, 'w') as f:
                f.write(kv3_content)
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to create file: {e}")
            return
            
        super().accept()

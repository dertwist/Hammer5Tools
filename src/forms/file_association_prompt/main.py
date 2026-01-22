"""
First-launch file association prompt dialog.
Asks user if they want to associate .vsmart files with Hammer5Tools.
"""
import os
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QWidget,
    QFrame
)
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt

from src.settings.main import get_settings_bool, set_settings_bool, get_cs2_path
from src.file_associations.icon_converter import get_vsmart_icon_path, extract_cs2_icon


class FileAssociationPromptDialog(QDialog):
    """
    Dialog prompting user to register .vsmart file associations.
    Shown on first launch of the application.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("File Association Setup")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(350)
        
        self.dont_ask_again = False
        
        self._setup_ui()
        self._apply_stylesheet()
    
    def _setup_ui(self):
        """Setup the dialog UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title_label = QLabel("Associate .vsmart Files?")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Icon display
        icon_widget = self._create_icon_widget()
        layout.addWidget(icon_widget)
        
        # Description
        description = QLabel(
            "<b>Hammer5Tools</b> can be set as the default program for SmartProp files (.vsmart).<br><br>"
            "<b>Benefits:</b><br>"
            "• Double-click .vsmart files to open them directly<br>"
            "• Seamless integration with Windows Explorer<br>"
            "• Custom icon for easy file identification<br><br>"
            "You can change this later in Settings."
        )
        description.setWordWrap(True)
        description.setObjectName("descriptionLabel")
        layout.addWidget(description)
        
        layout.addStretch()
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setObjectName("separator")
        layout.addWidget(separator)
        
        # "Don't ask again" checkbox
        self.dont_ask_checkbox = QCheckBox("Don't ask me again")
        self.dont_ask_checkbox.setObjectName("dontAskCheckbox")
        layout.addWidget(self.dont_ask_checkbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.not_now_button = QPushButton("Not Now")
        self.not_now_button.setObjectName("secondaryButton")
        self.not_now_button.setMinimumHeight(35)
        self.not_now_button.clicked.connect(self._on_not_now)
        button_layout.addWidget(self.not_now_button)
        
        button_layout.addStretch()
        
        self.register_button = QPushButton("Yes, Register .vsmart Files")
        self.register_button.setObjectName("primaryButton")
        self.register_button.setMinimumHeight(35)
        self.register_button.setDefault(True)
        self.register_button.clicked.connect(self._on_register)
        button_layout.addWidget(self.register_button)
        
        layout.addLayout(button_layout)
    
    def _create_icon_widget(self) -> QWidget:
        """Create widget displaying the icon that will be used."""
        widget = QWidget()
        widget.setObjectName("iconWidget")
        widget_layout = QVBoxLayout(widget)
        widget_layout.setContentsMargins(0, 10, 0, 10)
        
        # Try to get CS2 smart_prop icon
        cs2_path = get_cs2_path()
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        
        # Try to load the PNG icon for preview
        icon_path = None
        if cs2_path:
            png_path = extract_cs2_icon(cs2_path)
            if png_path and os.path.exists(png_path):
                icon_path = png_path
        
        # Load and display icon
        if icon_path:
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                # Scale to reasonable size for display
                scaled_pixmap = pixmap.scaled(
                    128, 128,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                icon_label.setPixmap(scaled_pixmap)
        else:
            # Fallback text if icon not available
            icon_label.setText("[SmartProp Icon]")
            icon_label.setStyleSheet("color: #888; font-size: 14px;")
        
        widget_layout.addWidget(icon_label)
        
        caption = QLabel("This icon will appear for .vsmart files")
        caption.setAlignment(Qt.AlignCenter)
        caption.setObjectName("captionLabel")
        widget_layout.addWidget(caption)
        
        return widget
    
    def _on_register(self):
        """Handle register button click."""
        self.dont_ask_again = self.dont_ask_checkbox.isChecked()
        self.accept()
    
    def _on_not_now(self):
        """Handle not now button click."""
        self.dont_ask_again = self.dont_ask_checkbox.isChecked()
        self.reject()
    
    def _apply_stylesheet(self):
        """Apply custom stylesheet to the dialog."""
        stylesheet = """
            QDialog {
                background-color: #2b2b2b;
            }
            
            #titleLabel {
                font-size: 20px;
                font-weight: bold;
                color: #ffffff;
                padding: 10px;
            }
            
            #descriptionLabel {
                font-size: 13px;
                color: #cccccc;
                padding: 10px;
            }
            
            #iconWidget {
                background-color: #353535;
                border-radius: 8px;
                padding: 15px;
            }
            
            #captionLabel {
                font-size: 11px;
                color: #999999;
                padding-top: 5px;
            }
            
            #separator {
                color: #555555;
                margin: 5px 0;
            }
            
            #dontAskCheckbox {
                color: #aaaaaa;
                font-size: 12px;
            }
            
            #dontAskCheckbox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 2px solid #555555;
                background-color: #3a3a3a;
            }
            
            #dontAskCheckbox::indicator:checked {
                background-color: #4a9eff;
                border-color: #4a9eff;
            }
            
            #primaryButton {
                background-color: #4a9eff;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            
            #primaryButton:hover {
                background-color: #5aafff;
            }
            
            #primaryButton:pressed {
                background-color: #3a8eef;
            }
            
            #secondaryButton {
                background-color: #454545;
                color: #cccccc;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 13px;
            }
            
            #secondaryButton:hover {
                background-color: #505050;
                border-color: #666666;
            }
            
            #secondaryButton:pressed {
                background-color: #3a3a3a;
            }
        """
        self.setStyleSheet(stylesheet)

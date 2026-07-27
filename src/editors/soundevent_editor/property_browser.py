import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QSplitter, QPushButton, QStyle
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from src.editors.soundevent_editor.objects import soundevent_editor_properties
from src.common import (
    get_all_presets, SoundEventEditor_Preset_Path, SoundEventEditor_Internal_Preset_Path,
    Kv3ToJson
)

class PropertyBrowserWidget(QWidget):
    """
    Property Browser panel containing:
    1. Properties list & search filter (top section)
    2. Templates list & search filter (bottom section)
    """
    add_property_requested = Signal(str, object)  # (property_name, value_dict)
    create_event_from_template_requested = Signal(str, str)  # (template_name, template_path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.load_properties()
        self.load_templates()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        splitter = QSplitter(Qt.Vertical, self)
        main_layout.addWidget(splitter)

        # -------------------------------------------------------------
        # TOP SECTION: Properties
        # -------------------------------------------------------------
        properties_container = QWidget()
        prop_layout = QVBoxLayout(properties_container)
        prop_layout.setContentsMargins(0, 0, 0, 0)
        prop_layout.setSpacing(4)

        # Header label
        prop_header = QLabel("Properties", properties_container)
        prop_header.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 11px;
                color: #CCCCCC;
                padding-left: 2px;
            }
        """)
        prop_layout.addWidget(prop_header)

        # Search bar
        self.prop_filter_edit = QLineEdit(properties_container)
        self.prop_filter_edit.setPlaceholderText("Filter properties...")
        self.prop_filter_edit.setClearButtonEnabled(True)
        self.prop_filter_edit.textChanged.connect(self.filter_properties)
        prop_layout.addWidget(self.prop_filter_edit)

        # Properties List
        self.prop_list_widget = QListWidget(properties_container)
        self.prop_list_widget.setAlternatingRowColors(True)
        self.prop_list_widget.setStyleSheet("""
            QListWidget {
                background-color: #1C1C1C;
                alternate-background-color: #242424;
                border: 1px solid #333333;
                border-radius: 2px;
                color: #E0E0E0;
                font: 580 10pt "Segoe UI";
            }
            QListWidget::item {
                padding: 2px 6px;
            }
            QListWidget::item:hover {
                background-color: #2D333B;
            }
            QListWidget::item:selected {
                background-color: #3E4B5E;
                color: white;
            }
        """)
        self.prop_list_widget.itemDoubleClicked.connect(self._on_property_double_clicked)
        prop_layout.addWidget(self.prop_list_widget)

        splitter.addWidget(properties_container)

        # -------------------------------------------------------------
        # BOTTOM SECTION: Templates
        # -------------------------------------------------------------
        templates_container = QWidget()
        tmpl_layout = QVBoxLayout(templates_container)
        tmpl_layout.setContentsMargins(0, 0, 0, 0)
        tmpl_layout.setSpacing(4)

        # Templates Bar (Header + Refresh button)
        tmpl_bar_layout = QHBoxLayout()
        tmpl_bar_layout.setContentsMargins(0, 0, 0, 0)

        tmpl_header = QLabel("Templates", templates_container)
        tmpl_header.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 11px;
                color: #CCCCCC;
                padding-left: 2px;
            }
        """)
        tmpl_bar_layout.addWidget(tmpl_header)
        tmpl_bar_layout.addStretch()

        open_folder_icon = QIcon(":/valve_common/icons/tools/common/open.png")
        if open_folder_icon.isNull():
            open_folder_icon = self.style().standardIcon(QStyle.SP_DialogOpenButton)
        open_folder_btn = QPushButton(templates_container)
        open_folder_btn.setToolTip("Open User Templates Folder")
        open_folder_btn.setFlat(True)
        open_folder_btn.setFixedSize(20, 20)
        open_folder_btn.setIcon(open_folder_icon)
        open_folder_btn.clicked.connect(self._open_templates_folder)
        tmpl_bar_layout.addWidget(open_folder_btn)

        refresh_icon = QIcon(":/valve_common/icons/tools/common/refresh.png")
        if refresh_icon.isNull():
            refresh_icon = self.style().standardIcon(QStyle.SP_BrowserReload)
        refresh_btn = QPushButton(templates_container)
        refresh_btn.setToolTip("Refresh Templates")
        refresh_btn.setFlat(True)
        refresh_btn.setFixedSize(20, 20)
        refresh_btn.setIcon(refresh_icon)
        refresh_btn.clicked.connect(self.load_templates)
        tmpl_bar_layout.addWidget(refresh_btn)

        tmpl_layout.addLayout(tmpl_bar_layout)

        # Search bar
        self.tmpl_filter_edit = QLineEdit(templates_container)
        self.tmpl_filter_edit.setPlaceholderText("Filter templates...")
        self.tmpl_filter_edit.setClearButtonEnabled(True)
        self.tmpl_filter_edit.textChanged.connect(self.filter_templates)
        tmpl_layout.addWidget(self.tmpl_filter_edit)

        # Templates List
        self.tmpl_list_widget = QListWidget(templates_container)
        self.tmpl_list_widget.setAlternatingRowColors(True)
        self.tmpl_list_widget.setStyleSheet("""
            QListWidget {
                background-color: #1C1C1C;
                alternate-background-color: #242424;
                border: 1px solid #333333;
                border-radius: 2px;
                color: #E0E0E0;
                font: 580 10pt "Segoe UI";
            }
            QListWidget::item {
                padding: 2px 6px;
            }
            QListWidget::item:hover {
                background-color: #2D333B;
            }
            QListWidget::item:selected {
                background-color: #3E4B5E;
                color: white;
            }
        """)
        self.tmpl_list_widget.itemClicked.connect(self._on_template_clicked)
        self.tmpl_list_widget.itemDoubleClicked.connect(self._on_template_clicked)
        tmpl_layout.addWidget(self.tmpl_list_widget)

        splitter.addWidget(templates_container)
        splitter.setSizes([450, 180])

    def load_properties(self):
        """Populate property list from soundevent_editor_properties."""
        self.prop_list_widget.clear()
        for dict_value in soundevent_editor_properties:
            for display_name, val_dict in dict_value.items():
                item = QListWidgetItem(display_name)
                item.setData(Qt.UserRole, (display_name, val_dict))
                self.prop_list_widget.addItem(item)

    def filter_properties(self, text: str):
        search = text.strip().lower()
        for i in range(self.prop_list_widget.count()):
            item = self.prop_list_widget.item(i)
            item.setHidden(bool(search and search not in item.text().lower()))

    def _on_property_double_clicked(self, item: QListWidgetItem):
        if not (item.flags() & Qt.ItemIsEnabled):
            return
        data = item.data(Qt.UserRole)
        if data:
            display_name, val_dict = data
            self.add_property_requested.emit(display_name, val_dict)

    def update_property_states(self, existing_properties=None):
        """
        Check existing properties in active sound event.
        Deactivate single-add properties if they already exist.
        All properties except 'comment' can be added only once.
        """
        if existing_properties is None:
            existing_properties = set()

        if isinstance(existing_properties, (dict, list)):
            existing_keys = set(existing_properties)
        elif isinstance(existing_properties, set):
            existing_keys = existing_properties
        else:
            existing_keys = set()

        existing_keys_lower = {str(k).lower() for k in existing_keys}

        for i in range(self.prop_list_widget.count()):
            item = self.prop_list_widget.item(i)
            data = item.data(Qt.UserRole)
            if not data:
                continue
            display_name, val_dict = data

            prop_key = next(iter(val_dict.keys())) if (isinstance(val_dict, dict) and val_dict) else ""
            prop_key_lower = prop_key.lower()

            # All properties except 'comment' can only be added once
            is_single_add = (prop_key_lower != "comment")
            already_exists = prop_key_lower in existing_keys_lower

            if is_single_add and already_exists:
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                item.setForeground(Qt.darkGray)
                item.setToolTip(f"'{display_name}' already exists in active sound event")
            else:
                item.setFlags(item.flags() | Qt.ItemIsEnabled)
                item.setForeground(Qt.NoBrush)
                item.setToolTip(f"Double-click to add {display_name}")

    def load_templates(self):
        """Populate templates list from user and software template directories."""
        self.tmpl_list_widget.clear()
        presets = get_all_presets(SoundEventEditor_Internal_Preset_Path, SoundEventEditor_Preset_Path)
        for preset_entry in presets:
            for display_name, file_path in preset_entry.items():
                item = QListWidgetItem(display_name)
                item.setData(Qt.UserRole, (display_name, file_path))
                item.setToolTip(file_path)
                self.tmpl_list_widget.addItem(item)

    def filter_templates(self, text: str):
        search = text.strip().lower()
        for i in range(self.tmpl_list_widget.count()):
            item = self.tmpl_list_widget.item(i)
            item.setHidden(bool(search and search not in item.text().lower()))

    def _on_template_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.UserRole)
        if data:
            display_name, file_path = data
            # Extract clean template name
            template_name = Path(file_path).stem
            self.create_event_from_template_requested.emit(template_name, file_path)

    def _open_templates_folder(self):
        if os.path.exists(SoundEventEditor_Preset_Path):
            os.startfile(SoundEventEditor_Preset_Path)

"""
Custom widgets for build settings UI.
Auto-generates UI elements from BuildSettings dataclass.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QSpinBox, QLineEdit, QComboBox,
    QToolButton, QFrame, QSizePolicy, QPushButton,
    QScrollArea
)
import os
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon
from dataclasses import fields
from typing import Any, Dict, Optional
from src.forms.mapbuilder.preset_manager import BuildSettings
from PySide6.QtWidgets import QPushButton, QLabel, QGridLayout, QFileDialog, QMessageBox
from PySide6.QtCore import Qt, QSize, Signal

from src.settings.common import get_addon_dir, get_addon_name
from src.widgets.common import Button


class SettingWidget(QWidget):
    """Base class for setting widgets"""
    valueChanged = Signal(object)

    def __init__(self, field_name: str, field_type: type, default_value: Any, parent=None):
        super().__init__(parent)
        self.field_name = field_name
        self.field_type = field_type
        self.default_value = default_value

        # Convert field name to display name (e.g., "build_world" -> "Build World")
        self.display_name = self._field_name_to_display(field_name)

        self.setup_ui()

    def _field_name_to_display(self, name: str) -> str:
        """Convert field_name to Display Name"""
        # Replace underscores with spaces and capitalize
        words = name.replace('_', ' ').split()
        return ' '.join(word.capitalize() for word in words)

    def setup_ui(self):
        """Override in subclasses"""
        pass

    def get_value(self) -> Any:
        """Override in subclasses"""
        return self.default_value

    def set_value(self, value: Any):
        """Override in subclasses"""
        pass


class BoolSettingWidget(SettingWidget):
    """Checkbox for boolean settings"""

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("border: none; padding: 0px;")

        self.checkbox = QCheckBox(self.display_name)
        self.checkbox.setChecked(self.default_value)
        self.checkbox.stateChanged.connect(lambda: self.valueChanged.emit(self.get_value()))

        layout.addWidget(self.checkbox)
        layout.addStretch()

    def get_value(self) -> bool:
        return self.checkbox.isChecked()

    def set_value(self, value: bool):
        self.checkbox.setChecked(value)


class IntSettingWidget(SettingWidget):
    """SpinBox for integer settings"""

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(self.display_name)
        self.spinbox = QSpinBox()
        self.spinbox.setMinimum(-1)
        self.spinbox.setMaximum(9999)
        self.spinbox.setValue(self.default_value)
        self.spinbox.valueChanged.connect(lambda: self.valueChanged.emit(self.get_value()))

        layout.addWidget(label)
        layout.addStretch()
        layout.addWidget(self.spinbox)

    def get_value(self) -> int:
        return self.spinbox.value()

    def set_value(self, value: int):
        self.spinbox.setValue(value)


class StringSettingWidget(SettingWidget):
    """LineEdit for string settings"""

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(self.display_name)
        self.lineedit = QLineEdit()
        self.lineedit.setText(str(self.default_value))
        self.lineedit.textChanged.connect(lambda: self.valueChanged.emit(self.get_value()))

        layout.addWidget(label)
        layout.addWidget(self.lineedit)

    def get_value(self) -> str:
        return self.lineedit.text()

    def set_value(self, value: str):
        self.lineedit.setText(value)

class EnumSettingWidget(SettingWidget):
    """ComboBox for enumerated settings (supports (label,value) or raw values)"""

    def __init__(self, field_name: str, field_type: type, default_value: Any, options: list, cast: type = str, parent=None):
        self.options = options
        self.cast = cast
        super().__init__(field_name, field_type, default_value, parent)

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(self.display_name)
        self.combobox = QComboBox()
        # Populate options (support (label, value) tuples)
        self._values = []
        for opt in self.options:
            if isinstance(opt, tuple) and len(opt) == 2:
                display, value = opt
            else:
                display, value = str(opt), opt
            self.combobox.addItem(str(display), userData=value)
            self._values.append(value)
        # Set current by matching default value to value list
        try:
            idx = self._values.index(self.default_value)
        except ValueError:
            idx = 0
        self.combobox.setCurrentIndex(idx)
        self.combobox.currentIndexChanged.connect(lambda: self.valueChanged.emit(self.get_value()))

        layout.addWidget(label)
        layout.addWidget(self.combobox)

    def get_value(self) -> Any:
        value = self.combobox.currentData()
        try:
            return self.cast(value)
        except Exception:
            return value

    def set_value(self, value: Any):
        try:
            # Cast for comparison consistency
            cast_val = self.cast(value)
            idx = self._values.index(cast_val)
            self.combobox.setCurrentIndex(idx)
        except ValueError:
            pass

class FolderSettingWidget(SettingWidget):
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(self.display_name)
        self.lineedit = QLineEdit()
        self.lineedit.setPlaceholderText(self.find_default_vmap())
        self.lineedit.setText(str(self.default_value))
        self.lineedit.textChanged.connect(lambda: self.valueChanged.emit(self.get_value()))

        self.browse_vmap_path = Button()
        self.browse_vmap_path.set_icon_folder_open()
        self.browse_vmap_path.clicked.connect(self.browse_path)

        layout.addWidget(label)
        layout.addWidget(self.lineedit)
        layout.addWidget(self.browse_vmap_path)

    def get_value(self) -> str:
        if self.lineedit.text() == '':
            return self.find_default_vmap()
        else:
            return self.lineedit.text()

    def set_value(self, value: str):
        self.lineedit.setText(value)
    def find_default_vmap(self):
        return os.path.relpath(os.path.join(get_addon_dir(), 'maps', f'{get_addon_name()}.vmap'), get_addon_dir())

    def browse_path(self):
        addon_dir = get_addon_dir()
        maps_dir = os.path.join(addon_dir, 'maps')

        # Ensure maps directory exists
        os.makedirs(maps_dir, exist_ok=True)

        selected_file, _ = QFileDialog.getOpenFileName(
            self,
            "Select Vmap file",
            maps_dir,
            "Vmap files (*.vmap);;All files (*)"
        )

        if selected_file:
            if not selected_file.endswith('.vmap'):
                QMessageBox.warning(self, "Invalid File", "Please select a .vmap file.")
                return

            rel_path = os.path.relpath(selected_file, addon_dir)
            if rel_path.startswith('..'):
                QMessageBox.warning(self, "Invalid Location",
                                    "Please select a file within the addon's directory.")
                return

            self.set_value(rel_path)


class SettingsGroup(QWidget):
    """Collapsible group of settings"""

    def __init__(self, group_name: str, parent=None):
        super().__init__(parent)
        self.group_name = group_name
        self.collapsed = False
        self.setting_widgets: Dict[str, SettingWidget] = {}

        self.setup_ui()

    def setup_ui(self):
        self.setContentsMargins(0, 0, 0, 0)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        # Header
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.StyledPanel)
        header_frame.setMaximumHeight(32)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_frame.setStyleSheet('background-color: #1D1D1F;')

        self.collapse_button = QToolButton()
        self.collapse_button.setIcon(QIcon(":/icons/arrow_drop_down_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg"))
        self.collapse_button.setIconSize(QSize(24, 24))
        self.collapse_button.setStyleSheet('padding: 0px; margin: 0px;')
        self.collapse_button.setFixedSize(24, 24)
        self.collapse_button.clicked.connect(self.toggle_collapse)

        self.group_label = QLabel(self.group_name)
        self.group_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.group_label.setStyleSheet("font-weight: 500; font-size: 16px;")

        header_layout.addStretch()
        header_layout.addWidget(self.group_label)
        header_layout.addStretch()
        header_layout.addWidget(self.collapse_button)


        # Content
        self.content_frame = QFrame()
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(12, 8, 12, 8)
        self.content_layout.setSpacing(6)

        main_layout.addWidget(header_frame)
        main_layout.addWidget(self.content_frame)

    def add_setting(self, field_name: str, widget: SettingWidget):
        """Add a setting widget to this group"""
        self.setting_widgets[field_name] = widget
        self.content_layout.addWidget(widget)

    def add_row(self, field_names: list[str]):
        """Group existing field widgets into a single horizontal row."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        container = QWidget()
        container.setLayout(row)
        # collect widgets in order
        widgets = []
        for name in field_names:
            w = self.setting_widgets.get(name)
            if w is not None:
                widgets.append(w)
        if not widgets:
            return
        # remove widgets from current parent layout and add to row
        for w in widgets:
            self.content_layout.removeWidget(w)
            row.addWidget(w)
        row.addStretch()
        self.content_layout.addWidget(container)

    def toggle_collapse(self):
        """Collapse/expand the group"""
        self.collapsed = not self.collapsed
        self.content_frame.setVisible(not self.collapsed)

        if self.collapsed:
            self.collapse_button.setIcon(QIcon(":/icons/arrow_drop_up_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg"))
        else:
            self.collapse_button.setIcon(QIcon(":/icons/arrow_drop_down_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg"))

    def get_values(self) -> Dict[str, Any]:
        """Get all setting values from this group"""
        return {name: widget.get_value() for name, widget in self.setting_widgets.items()}

    def set_values(self, values: Dict[str, Any]):
        """Set all setting values in this group"""
        for name, value in values.items():
            if name in self.setting_widgets:
                self.setting_widgets[name].set_value(value)


class SettingsPanel(QWidget):
    """Complete settings panel with auto-generated UI"""

    # Define which fields go in which groups
    FIELD_GROUPS = {
        "Common": ["mappath", "threads"],
        "World": ["build_world", "entities_only",
                  "skip_aux_files", "no_settle",
                  "tile_mesh_base_geometry"],
        "Lightmapping": ["bake_lighting", "lightmap_max_resolution", "lightmap_quality",
                         "lightmap_do_weld", "lightmap_compression", "lightmap_cpu",
                         "lightmap_filtering", "no_light_calculations",
                         "lightmap_deterministic_charts", "write_debug_path_trace",
                         "vrad3_large_block_size", "lightmap_local_compile"],
        "Physics": ["build_physics", "legacy_compile_collision_mesh"],
        "Visibility": ["build_vis", "debug_vis_geo", "build_vis_geometry"],
        "Navigation": ["build_nav", "nav_debug", "grid_nav"],
        "Audio": ["build_reverb", "build_paths", "bake_custom_audio", "audio_threads"],
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.groups: Dict[str, SettingsGroup] = {}
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create groups and widgets
        for group_name, field_names in self.FIELD_GROUPS.items():
            group = SettingsGroup(group_name)
            self.groups[group_name] = group

            # Add setting widgets for each field
            for field_name in field_names:
                widget = self._create_widget_for_field(field_name)
                if widget:
                    group.add_setting(field_name, widget)

            # Horizontal groupings
            if group_name == "Lightmapping":
                group.add_row(["lightmap_max_resolution", "lightmap_quality", "lightmap_compression"])
            if group_name == "Audio":
                group.add_row(["build_reverb", "build_paths", "audio_threads"])

            main_layout.addWidget(group)

        main_layout.addStretch()

    def _create_widget_for_field(self, field_name: str) -> Optional[SettingWidget]:
        """Create appropriate widget for a field"""
        # Get field info from BuildSettings dataclass
        for field in fields(BuildSettings):
            if field.name == field_name:
                field_type = field.type
                default_value = field.default

                # Create widget based on type
                if field_name == "lightmap_filtering":
                    return BoolSettingWidget("Noise removal", field_type, default_value)
                elif field_name == "lightmap_compression":
                    return BoolSettingWidget("Compression", field_type, default_value)
                elif field_type == bool:
                    return BoolSettingWidget(field_name, field_type, default_value)
                elif field_type == int:
                    # Special cases for enum-like ints
                    if field_name == "lightmap_max_resolution":
                        return EnumSettingWidget("Resolution", field_type, default_value,
                                                 [256, 512, 1024, 2048, 4096, 8192], cast=int)
                    elif field_name == "lightmap_quality":
                        # Display friendly names while keeping internal int mapping 0/1/2
                        return EnumSettingWidget("Quality", field_type, default_value,
                                                 [("Fast", 0), ("Standard", 1), ("Final", 2)], cast=int)
                    else:
                        return IntSettingWidget(field_name, field_type, default_value)
                elif field_type == str and field_name == "mappath":
                    return FolderSettingWidget(field_name, field_type, default_value)
                elif field_type == str:
                    return StringSettingWidget(field_name, field_type, default_value)

        return None

    def get_settings(self) -> BuildSettings:
        """Get current settings as BuildSettings object"""
        values = {}
        for group in self.groups.values():
            values.update(group.get_values())
        return BuildSettings(**values)

    def set_settings(self, settings: BuildSettings):
        """Set all settings from BuildSettings object"""
        settings_dict = {f.name: getattr(settings, f.name) for f in fields(settings)}
        for group in self.groups.values():
            group.set_values(settings_dict)


class PresetButton(QPushButton):
    """Button representing a build preset"""

    presetClicked = Signal(str)  # preset name
    contextMenuRequested = Signal(object)

    def __init__(self, preset_name: str, is_default: bool, parent=None):
        super().__init__(parent)
        self.preset_name = preset_name
        self.is_default = is_default
        self.is_active = False

        self.setMinimumSize(QSize(64, 64))
        self.setMaximumSize(QSize(64, 64))

        layout = QGridLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        self.label = QLabel(preset_name)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignCenter)

        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.label.setStyleSheet("font-size: 10px; background-color: transparent; color: white;")

        layout.addWidget(self.label, 0, 0)

        self.setCheckable(True)
        self.clicked.connect(lambda: self.presetClicked.emit(self.preset_name))

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)

        self.update_style()
    def on_context_menu(self, pos):
        """Emit context menu signal with position"""
        self.contextMenuRequested.emit((self, pos))

    def set_active(self, active: bool):
        """Set active state"""
        self.is_active = active
        self.setChecked(active)
        self.update_style()

    def update_style(self):
        """Update button style based on state"""
        if self.is_active:
            self.setStyleSheet("""
                QPushButton {
                    font-size: 12px;
                    background-color: #2a82da;
                    color: white;
                    border: 2px solid #1a5fb4;
                    border-radius: 2px;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    font-size: 12px;
                    background-color: #1D1D1F;
                    color: #c0c0c0;
                    border: 1px solid #606060;
                    border-radius: 2px;
                }
                QPushButton:hover {
                    background-color: #505050;
                }
            """)

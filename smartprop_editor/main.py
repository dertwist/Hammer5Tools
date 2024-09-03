import os.path
import sys
import time

from qt_material import apply_stylesheet
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QListWidgetItem, QMenu, QScrollArea
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction,QCursor
from smartprop_editor.ui_main import Ui_MainWindow
from preferences import get_config_value, get_cs2_path, get_addon_name, set_config_value
from soudevent_editor.soundevent_editor_mini_windows_explorer import SoundEvent_Editor_MiniWindowsExplorer
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QListWidgetItem, QMenu, QScrollArea, QInputDialog
from PySide6.QtWidgets import QSpacerItem, QSizePolicy
from PySide6.QtWidgets import QProgressBar
from popup_menu.popup_menu_main import PopupMenu


import keyvalues3 as kv3


# Import necessary modules
from PySide6.QtCore import QPoint, QSize

# Save positions and sizes of dock widgets
def save_dock_widget_positions_sizes(dock_widgets):
    positions_sizes = {}
    for dock_widget in dock_widgets:
        widget_name = dock_widget.objectName()
        positions_sizes[widget_name] = {
            'position': str(dock_widget.pos()),  # Convert position to string
            'size': str(dock_widget.size())  # Convert size to string
        }
    # Save positions and sizes to configuration
    set_config_value('DOCK_WIDGETS', 'positions_sizes', str(positions_sizes))  # Convert positions_sizes to string

# Restore positions and sizes of dock widgets
# Restore positions and sizes of dock widgets
def restore_dock_widget_positions_sizes(dock_widgets):
    positions_sizes = get_config_value('DOCK_WIDGETS', 'positions_sizes')
    if positions_sizes:
        for dock_widget in dock_widgets:
            widget_name = dock_widget.objectName()
            if widget_name in positions_sizes:
                position = eval(positions_sizes[widget_name]['position'])  # Convert string to tuple
                size = eval(positions_sizes[widget_name]['size'])  # Convert string to tuple
                dock_widget.move(*position)  # Unpack tuple for move
                dock_widget.resize(*size)  # Unpack tuple for resize

# In your SmartPropEditorMainWindow class
class SmartPropEditorMainWindow(QMainWindow):
    def __init__(self, version="1", parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.version_label.setText(version)

        # Call functions to restore positions and sizes
        dock_widgets = [self.ui.dockWidget_2, self.ui.dockWidget_3]  # Add all dock widgets here
        self.ui.dockWidget_2.titleBarWidget()
        # restore_dock_widget_positions_sizes(dock_widgets)

    def closeEvent(self, event):
        print('Close event')
        dock_widgets = [self.ui.dockWidget_2, self.ui.dockWidget_3]  # Add all dock widgets here
        save_dock_widget_positions_sizes(dock_widgets)
        # event.accept()

# Main block remains the same
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SmartPropEditorMainWindow()
    apply_stylesheet('darak')
    window.show()
    sys.exit(app.exec())
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
import json

import keyvalues3 as kv3


# Import necessary modules
from PySide6.QtCore import QPoint, QSize

# Save positions and sizes of dock widgets
def save_dock_widget_positions_sizes(dock_widgets):
    positions_sizes = {}
    for dock_widget in dock_widgets:
        widget_name = dock_widget.objectName()
        position = [(dock_widget.pos()).x(), (dock_widget.pos()).y()]
        print('position', position)
        size = [dock_widget.size().width(), dock_widget.size().height()]
        print('size', size)
        positions_sizes[widget_name] = {
            'position': str(position),
            'size': str(size)
        }
    # Save positions and sizes to configuration
    set_config_value('SMARTPROPS_DOCK_WIDGETS', 'positions_sizes', str(positions_sizes))  # Convert positions_sizes to string

# Restore positions and sizes of dock widgets
# Restore positions and sizes of dock widgets
def restore_dock_widget_positions_sizes(dock_widgets):
    positions_sizes = get_config_value('SMARTPROPS_DOCK_WIDGETS', 'positions_sizes')
    print(type(positions_sizes), positions_sizes)
    import ast

    if positions_sizes:
        positions_sizes = ast.literal_eval(positions_sizes)
        print(type(positions_sizes), positions_sizes)
        print((positions_sizes.items()))
        for item in positions_sizes.items():
            print(item)
        for dock_widget in dock_widgets:

            widget_name = dock_widget.objectName()
            position = positions_sizes[widget_name]['position']
            position = ast.literal_eval(position)
            size = positions_sizes[widget_name]['size']
            size = ast.literal_eval(size)
            print(type(position), position)
            print(widget_name, position, size)
            dock_widget.move(position[0],position[1])
            dock_widget.resize(size[0],size[1])


# In your SmartPropEditorMainWindow class
class SmartPropEditorMainWindow(QMainWindow):
    def __init__(self, version="1", parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.version_label.setText(version)

        # Call functions to restore positions and sizes
        dock_widgets = [self.ui.dockWidget_2, self.ui.dockWidget_3]  # Add all dock widgets here
        # self.ui.dockWidget_2.titleBarWidget()
        restore_dock_widget_positions_sizes(dock_widgets)

    def closeEvent(self, event):
        dock_widgets = [self.ui.dockWidget_2, self.ui.dockWidget_3]  # Add all dock widgets here
        save_dock_widget_positions_sizes(dock_widgets)
        # event.accept()

# Main block remains the same
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SmartPropEditorMainWindow()
    apply_stylesheet(app, theme='dark_yellow.xml')
    window.show()
    sys.exit(app.exec())
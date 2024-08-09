import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QScrollBar, QWidget, QLabel, QScrollArea, \
    QListWidgetItem, QSizePolicy
from PySide6.QtCore import Qt, QMimeData, QPropertyAnimation, QPoint
from PySide6.QtGui import QDrag, QPixmap
from soudevent_editor.ui_soundevenet_editor_mainwindow import Ui_SoundEvent_Editor_MainWindow
from soudevent_editor.soundevent_editor_viewport import SoundEventEditor_Viewport_Window
from preferences import get_config_value, get_cs2_path, get_addon_name
from soudevent_editor.soundevent_editor_mini_windows_explorer import SoundEvent_Editor_MiniWindowsExplorer


class SoundEventEditorMainWidget(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_SoundEvent_Editor_MainWindow()
        self.ui.setupUi(self)

        # Set up the custom file system model
        counter_strike_2_path = get_cs2_path()
        addon_name = get_addon_name()
        tree_directory = rf"{counter_strike_2_path}\content\csgo_addons\{addon_name}\sounds"

        # Initialize the mini windows explorer
        self.mini_explorer = SoundEvent_Editor_MiniWindowsExplorer(self.ui.audio_files_explorer, tree_directory)

        # Set up the layout for the audio_files_explorer widget
        self.audio_files_explorer_layout = QVBoxLayout(self.ui.audio_files_explorer)
        self.audio_files_explorer_layout.addWidget(self.mini_explorer.tree)
        self.audio_files_explorer_layout.setContentsMargins(0, 0, 0, 0)


        layout = self.ui.sound_event_editor_viewport_widget
        self.editor_viewport = SoundEventEditor_Viewport_Window()
        layout.addWidget(self.editor_viewport)

        # Instead of creating a new container, set the central widget directly
        container = QWidget()
        container.setLayout(self.ui.horizontalLayout)  # Use the existing layout
        self.setCentralWidget(container)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SoundEventEditorMainWidget()
    window.show()
    sys.exit(app.exec())
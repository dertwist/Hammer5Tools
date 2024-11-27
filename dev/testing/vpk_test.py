import os
import vpk
from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, QMessageBox
from PySide6.QtCore import Qt
from src.preferences import get_cs2_path
from PySide6.QtWidgets import QMainWindow, QTreeView, QVBoxLayout, QFileSystemModel, QStyledItemDelegate, QHeaderView, QMenu, QInputDialog, QMessageBox, QLineEdit, QTreeWidgetItem, QPushButton, QHBoxLayout
from PySide6.QtGui import QIcon, QAction, QDesktopServices, QMouseEvent, QKeyEvent, QGuiApplication
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl
from PySide6.QtCore import Qt, QDir, QMimeData, QUrl, QFile, QFileInfo, QItemSelectionModel
from src.preferences import get_config_value, set_config_value, get_cs2_path, get_addon_name, debug
from PySide6.QtCore import QModelIndex
from src.common import *

def _play_audio_file(file_path):
    print(f'Playing audio {file_path}')
    audio_player = None
    try:
        if audio_player is not None:
            audio_player.deleteLater()
        audio_player = QMediaPlayer()
        audio_output = QAudioOutput()
        audio_player.setAudioOutput(audio_output)
        audio_player.setSource(QUrl.fromLocalFile(file_path))
        audio_player.play()
    except Exception as e:
        print(f"Error playing audio: {e}")
def play_audio_file(path):
    iternal_audiopath = 'sounds\\' + (path.replace('vsnd', 'vsnd_c')).replace('/', '\\')
    local_audiopath = (os.path.join(SoundEventEditor_sounds_path, path.replace('vsnd', 'wav'))).replace('/', '\\')
    local_audiopath = os.path.abspath(local_audiopath)
    print(f'local {local_audiopath}')
    if os.path.exists(local_audiopath):
        _play_audio_file(local_audiopath)
    else:
        decompile_audio(iternal_audiopath)
        _play_audio_file(local_audiopath)
def decompile_audio(path):
    """"""
    pak1 = os.path.join(get_cs2_path(), 'game', 'csgo', 'pak01_dir.vpk')
    subprocess.Popen([
        Decompiler_path,
        '-i', pak1,
        '--output', SoundEventEditor_path,
        '--vpk_filepath', path,
        '-d'
    ])


def create_tree_widget():
    app = QApplication([])

    window = QWidget()
    window.setWindowTitle("Sound Files Tree")
    layout = QVBoxLayout(window)

    tree_widget = QTreeWidget()
    tree_widget.setHeaderLabels(["Category", "File"])
    layout.addWidget(tree_widget)

    def on_item_clicked(item, column):
        # Assemble the path from the clicked item to the root
        path_elements = []
        current_item = item
        while current_item is not None:
            path_elements.insert(0, current_item.text(0))
            current_item = current_item.parent()
        assembled_path = '/'.join(path_elements)
        if 'vsnd' in assembled_path:
            print(f"Assembled Path: {assembled_path}")
            play_audio_file(assembled_path)


    tree_widget.itemClicked.connect(on_item_clicked)

    try:
        path = os.path.join(get_cs2_path(), 'game', 'csgo', 'pak01_dir.vpk')
        with vpk.open(path) as pak1:
            folders = []
            for filepath in pak1:
                if 'vsnd_c' in filepath and 'sounds' in filepath:
                    filepath = filepath.replace('vsnd_c', 'vsnd')
                    element = filepath.split('/')[1:]
                    folders.append(element)

            for path_elements in folders:
                parent_item = None
                for element in path_elements:
                    if parent_item is None:
                        found_items = tree_widget.findItems(element, Qt.MatchExactly, 0)
                    else:
                        found_items = [child for child in (parent_item.child(i) for i in range(parent_item.childCount())) if child.text(0) == element]

                    if found_items:
                        parent_item = found_items[0]
                    else:
                        new_item = QTreeWidgetItem([element])
                        if parent_item is None:
                            tree_widget.addTopLevelItem(new_item)
                        else:
                            parent_item.addChild(new_item)
                        parent_item = new_item

    except FileNotFoundError:
        QMessageBox.critical(window, "Error", "VPK file not found.")
    except Exception as e:
        QMessageBox.critical(window, "Error", f"Failed to load VPK file: {e}")

    window.show()
    app.exec()

if __name__ == "__main__":
    create_tree_widget()
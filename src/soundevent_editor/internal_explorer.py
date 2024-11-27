import os
import vpk
import subprocess
from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, QMessageBox
from PySide6.QtCore import Qt, QUrl, QMimeData
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from src.preferences import get_cs2_path, get_addon_dir, debug
from src.common import SoundEventEditor_sounds_path, Decompiler_path, SoundEventEditor_path
from src.property.methods import *

class InternalSoundFileExplorer(QTreeWidget):
    def __init__(self):
        super().__init__()
        self.setHeaderHidden(True)  # Hide the header
        self.setDragEnabled(True)   # Enable dragging
        self.setAcceptDrops(True)   # Enable dropping
        self.setDragDropMode(QTreeWidget.InternalMove)  # Set drag-and-drop mode
        self.itemClicked.connect(self.on_item_clicked)
        self.audio_player = None
        self.load_vpk_files()

    def _play_audio_file(self, file_path):
        debug(f'Playing audio {file_path}')
        try:
            if self.audio_player is not None:
                self.audio_player.deleteLater()
            self.audio_player = QMediaPlayer()
            self.audio_output = QAudioOutput()
            self.audio_player.setAudioOutput(self.audio_output)
            self.audio_player.setSource(QUrl.fromLocalFile(file_path))
            self.audio_player.play()
        except Exception as e:
            print(f"Error playing audio: {e}")

    def play_audio_file(self, path):
        internal_audiopath = 'sounds\\' + (path.replace('vsnd', 'vsnd_c')).replace('/', '\\')
        local_audiopath = (os.path.join(SoundEventEditor_sounds_path, path.replace('vsnd', 'wav'))).replace('/', '\\')
        local_audiopath = os.path.abspath(local_audiopath)
        debug(f'local {local_audiopath}')
        if os.path.exists(local_audiopath):
            self._play_audio_file(local_audiopath)
        else:
            self._play_audio_file(self.decompile_audio(internal_audiopath, local_audiopath))

    def decompile_audio(self, path, path_l):
        pak1 = os.path.join(get_cs2_path(), 'game', 'csgo', 'pak01_dir.vpk')
        subprocess.run([
            Decompiler_path,
            '-i', pak1,
            '--output', SoundEventEditor_path,
            '--vpk_filepath', path,
            '-d'
        ], check=True)
        return path_l

    def assemble_path(self, item):
        path_elements = []
        current_item = item
        while current_item is not None:
            path_elements.insert(0, current_item.text(0))
            current_item = current_item.parent()
        return '/'.join(path_elements)

    def on_item_clicked(self, item, column):
        assembled_path = self.assemble_path(item)
        if 'vsnd' in assembled_path:
            debug(f"Assembled Path: {assembled_path}")
            self.play_audio_file(assembled_path)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()

            # Assuming you want to get the path of the currently selected item
            current_item = self.currentItem()
            if current_item is not None:
                path = self.assemble_path(current_item)
                if 'vsnd' in path:
                    path = "file:///" + get_addon_dir() + '/' + 'sounds/' + path
                    path = path.replace('\\', '/')
                    path = path.replace('vsnd', 'wav')

                    # Create a QUrl object for the path
                    url = QUrl(path)

                    # Set the text and URLs for the mime data
                    mime_data.setText(path)
                    mime_data.setUrls([url])
            drag.setMimeData(mime_data)
            drag.exec()

    def dragEnterEvent(self, event):
        event.accept()

    def load_vpk_files(self):
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
                            found_items = self.findItems(element, Qt.MatchExactly, 0)
                        else:
                            found_items = [child for child in (parent_item.child(i) for i in range(parent_item.childCount())) if child.text(0) == element]

                        if found_items:
                            parent_item = found_items[0]
                        else:
                            new_item = QTreeWidgetItem([element])
                            if parent_item is None:
                                self.addTopLevelItem(new_item)
                            else:
                                parent_item.addChild(new_item)
                            parent_item = new_item

        except FileNotFoundError:
            QMessageBox.critical(self, "Error", "VPK file not found.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load VPK file: {e}")

if __name__ == "__main__":
    app = QApplication([])
    explorer = InternalSoundFileExplorer()
    explorer.show()
    app.exec()
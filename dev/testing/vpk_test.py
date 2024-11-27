import os
import vpk
import subprocess
from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, QMessageBox
from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from src.preferences import get_cs2_path
from src.common import SoundEventEditor_sounds_path, Decompiler_path, SoundEventEditor_path

class SoundFileExplorer:
    def __init__(self):
        self.app = QApplication([])
        self.window = QWidget()
        self.window.setWindowTitle("Sound Files Tree")
        self.layout = QVBoxLayout(self.window)
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Category", "File"])
        self.layout.addWidget(self.tree_widget)
        self.tree_widget.itemClicked.connect(self.on_item_clicked)
        self.audio_player = None

    def _play_audio_file(self, file_path):
        print(f'Playing audio {file_path}')
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
        print(f'local {local_audiopath}')
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

    def on_item_clicked(self, item, column):
        path_elements = []
        current_item = item
        while current_item is not None:
            path_elements.insert(0, current_item.text(0))
            current_item = current_item.parent()
        assembled_path = '/'.join(path_elements)
        if 'vsnd' in assembled_path:
            print(f"Assembled Path: {assembled_path}")
            self.play_audio_file(assembled_path)

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
                            found_items = self.tree_widget.findItems(element, Qt.MatchExactly, 0)
                        else:
                            found_items = [child for child in (parent_item.child(i) for i in range(parent_item.childCount())) if child.text(0) == element]

                        if found_items:
                            parent_item = found_items[0]
                        else:
                            new_item = QTreeWidgetItem([element])
                            if parent_item is None:
                                self.tree_widget.addTopLevelItem(new_item)
                            else:
                                parent_item.addChild(new_item)
                            parent_item = new_item

        except FileNotFoundError:
            QMessageBox.critical(self.window, "Error", "VPK file not found.")
        except Exception as e:
            QMessageBox.critical(self.window, "Error", f"Failed to load VPK file: {e}")

    def run(self):
        self.load_vpk_files()
        self.window.show()
        self.app.exec()

if __name__ == "__main__":
    explorer = SoundFileExplorer()
    explorer.run()
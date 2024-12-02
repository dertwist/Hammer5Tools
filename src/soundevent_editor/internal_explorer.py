from src.property.methods import QDrag
import os
import vpk
from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem, QMessageBox
from PySide6.QtCore import Qt, QUrl, QMimeData, QProcess, QThread, Signal
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from src.preferences import get_cs2_path, get_addon_dir, debug
from src.common import SoundEventEditor_sounds_path, Decompiler_path, SoundEventEditor_path

class VPKLoaderThread(QThread):
    vpk_loaded = Signal(list)

    def run(self):
        try:
            path = os.path.join(get_cs2_path(), 'game', 'csgo', 'pak01_dir.vpk')
            with vpk.open(path) as pak1:
                folders = []
                for filepath in pak1:
                    if 'vsnd_c' in filepath and 'sounds' in filepath:
                        filepath = filepath.replace('vsnd_c', 'vsnd')
                        element = filepath.split('/')[1:]
                        folders.append(element)
                self.vpk_loaded.emit(folders)
        except Exception as e:
            self.vpk_loaded.emit([])

class InternalSoundFileExplorer(QTreeWidget):
    def __init__(self):
        super().__init__()
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.InternalMove)
        self.itemClicked.connect(self.on_item_clicked)
        self.audio_player = None
        self.vpk_loader_thread = VPKLoaderThread()
        self.vpk_loader_thread.vpk_loaded.connect(self.populate_tree)
        self.vpk_loader_thread.start()

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
            pass

    def play_audio_file(self, path):
        internal_audiopath = os.path.join('sounds', path.replace('vsnd', 'vsnd_c')).replace('/', '\\')

        # Define paths for WAV and MP3 formats
        local_audiopath_wav = os.path.join(SoundEventEditor_sounds_path, path.replace('vsnd', 'wav')).replace('/', '\\')
        local_audiopath_mp3 = os.path.join(SoundEventEditor_sounds_path, path.replace('vsnd', 'mp3')).replace('/', '\\')

        local_audiopath_wav = os.path.abspath(local_audiopath_wav)
        local_audiopath_mp3 = os.path.abspath(local_audiopath_mp3)

        if os.path.exists(local_audiopath_wav):
            self._play_audio_file(local_audiopath_wav)
        elif os.path.exists(local_audiopath_mp3):
            self._play_audio_file(local_audiopath_mp3)
        else:
            self.decompile_audio(internal_audiopath, local_audiopath_wav)

    def decompile_audio(self, internal_path, local_path):
        pak1 = os.path.join(get_cs2_path(), 'game', 'csgo', 'pak01_dir.vpk')
        process = QProcess(self)

        process.finished.connect(lambda exit_code, exit_status: self.on_process_finished(exit_code, exit_status, process, local_path))
        process.errorOccurred.connect(lambda error: self.on_process_error(error, process))

        try:
            process.start(
                Decompiler_path,
                [
                    '-i', pak1,
                    '--output', SoundEventEditor_path,
                    '--vpk_filepath', internal_path,
                    '-d'
                ]
            )
        except Exception as e:
            pass

        return local_path

    def on_process_finished(self, exit_code, exit_status, process, path):
        if exit_code != 0:
            stderr = process.readAllStandardError().data().decode()
        else:
            self._play_audio_file(path)

    def on_process_error(self, error, process):
        pass

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

            current_item = self.currentItem()
            if current_item is not None:
                path = self.assemble_path(current_item)
                if 'vsnd' in path:
                    path = "file:///" + get_addon_dir() + '/' + 'sounds/' + path
                    path = path.replace('\\', '/')
                    path = path.replace('vsnd', 'wav')

                    url = QUrl(path)
                    mime_data.setText(path)
                    mime_data.setUrls([url])
            drag.setMimeData(mime_data)
            drag.exec()

    def dragEnterEvent(self, event):
        event.accept()

    def populate_tree(self, folders):
        if not folders:
            QMessageBox.critical(self, "Error", "Failed to load VPK file.")
            return

        self.setUpdatesEnabled(False)

        path_mapping = {}

        for path_elements in folders:
            parent_key = ""
            parent_item = None

            for element in path_elements:
                current_key = f"{parent_key}/{element}" if parent_key else element

                if current_key in path_mapping:
                    parent_item = path_mapping[current_key]
                else:
                    new_item = QTreeWidgetItem([element])
                    if parent_item is None:
                        self.addTopLevelItem(new_item)
                    else:
                        parent_item.addChild(new_item)

                    path_mapping[current_key] = new_item
                    parent_item = new_item

                parent_key = current_key

        self.setUpdatesEnabled(True)

if __name__ == "__main__":
    app = QApplication([])
    explorer = InternalSoundFileExplorer()
    explorer.show()
    app.exec()
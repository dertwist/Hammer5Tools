from src.property.methods import QDrag
import os
import vpk
import time
from PySide6.QtWidgets import (
    QApplication, QTreeWidget, QTreeWidgetItem, QMessageBox,
    QTreeWidgetItemIterator, QMenu
)
from PySide6.QtCore import Qt, QUrl, QMimeData, QProcess, QThread, Signal
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtGui import QGuiApplication
from src.settings.main import get_cs2_path, get_addon_dir, debug, get_settings_value
from src.common import SoundEventEditor_sounds_path, SoundEventEditor_path
from src.widgets import exception_handler
from src.dotnet import extract_vsnd_file


@exception_handler
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


@exception_handler
class InternalSoundFileExplorer(QTreeWidget):
    play_sound = Signal(str)

    def __init__(self, audio_player: QMediaPlayer):
        super().__init__()
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.InternalMove)

        # ── Multi-select: Ctrl+Click and Shift+Click ──
        self.setSelectionMode(QTreeWidget.ExtendedSelection)

        self.itemClicked.connect(self.on_item_clicked)
        self.audio_player = audio_player
        self.vpk_loader_thread = VPKLoaderThread()
        self.vpk_loader_thread.vpk_loaded.connect(self.populate_tree)
        self.vpk_loader_thread.start()

    # ──────────────────────────────────────────────
    #  Filter
    # ──────────────────────────────────────────────

    def filter_tree(self, filter_text):
        """Filter tree items based on search text and expand matching items"""
        filter_text = filter_text.lower().strip()

        if not filter_text:
            # Show all items and collapse all
            iterator = QTreeWidgetItemIterator(self)
            while iterator.value():
                item = iterator.value()
                item.setHidden(False)
                iterator += 1
            self.collapseAll()
            return

        # First pass: hide all items
        iterator = QTreeWidgetItemIterator(self)
        while iterator.value():
            item = iterator.value()
            item.setHidden(True)
            iterator += 1

        # Second pass: find matches and show them with their parents
        iterator = QTreeWidgetItemIterator(self)
        found_items = []
        while iterator.value():
            item = iterator.value()
            if filter_text in item.text(0).lower():
                found_items.append(item)
                # Show this item and all its parents
                current = item
                while current is not None:
                    current.setHidden(False)
                    current = current.parent()
            iterator += 1

        # Expand all parent items of found items
        for item in found_items:
            current = item.parent()
            while current is not None:
                self.expandItem(current)
                current = current.parent()

    # ──────────────────────────────────────────────
    #  Audio playback helpers
    # ──────────────────────────────────────────────

    def _play_audio_file(self, file_path):
        debug(f'Playing audio {file_path}')
        self.play_sound.emit(file_path)

    def maintain_cache_size(self, cache_path, max_cache_bytes):
        """
        Check if cache folder exceeds the allowed size and delete oldest files if necessary.
        """
        if not os.path.isdir(cache_path):
            return
        total_size = 0
        file_list = []
        for root, dirs, files in os.walk(cache_path):
            for file in files:
                full_path = os.path.join(root, file)
                try:
                    file_size = os.path.getsize(full_path)
                    total_size += file_size
                    mod_time = os.path.getmtime(full_path)
                    file_list.append((full_path, mod_time, file_size))
                except Exception:
                    continue
        if total_size <= max_cache_bytes:
            return
        # Sort files by modification time (oldest first)
        file_list.sort(key=lambda x: x[1])
        while total_size > max_cache_bytes and file_list:
            file_to_remove, mod_time, file_size = file_list.pop(0)
            try:
                os.remove(file_to_remove)
                total_size -= file_size
                debug(f"Removed cached file: {file_to_remove}")
            except Exception as e:
                debug(f"Failed to remove {file_to_remove}: {e}")

    def play_audio_file(self, path):
        internal_audiopath = os.path.join(
            'sounds', path.replace('vsnd', 'vsnd_c')
        ).replace('/', '\\')

        local_audiopath_wav = os.path.join(
            SoundEventEditor_sounds_path, path.replace('vsnd', 'wav')
        ).replace('/', '\\')
        local_audiopath_mp3 = os.path.join(
            SoundEventEditor_sounds_path, path.replace('vsnd', 'mp3')
        ).replace('/', '\\')

        local_audiopath_wav = os.path.abspath(local_audiopath_wav)
        local_audiopath_mp3 = os.path.abspath(local_audiopath_mp3)

        try:
            max_cache_mb = float(
                get_settings_value('SoundEventEditor', 'max_cache_size', 4000)
            )
        except ValueError:
            max_cache_mb = 4000
        max_cache_bytes = max_cache_mb * 1024 * 1024

        # Before using the cache, ensure the cache folder size is maintained.
        self.maintain_cache_size(SoundEventEditor_sounds_path, max_cache_bytes)

        if os.path.exists(local_audiopath_wav):
            self._play_audio_file(local_audiopath_wav)
        elif os.path.exists(local_audiopath_mp3):
            self._play_audio_file(local_audiopath_mp3)
        else:
            self.decompile_audio(internal_audiopath, local_audiopath_wav, path)

    def decompile_audio(self, internal_path, local_path, assembled_path):
        pak1 = os.path.join(get_cs2_path(), 'game', 'csgo', 'pak01_dir.vpk')
        extract_vsnd_file(
            vpk_path=pak1,
            vpk_file=internal_path,
            output_folder=SoundEventEditor_path,
            export=True,
        )
        self.play_audio_file(assembled_path)

    # ──────────────────────────────────────────────
    #  Path helpers
    # ──────────────────────────────────────────────

    def assemble_path(self, item):
        """Build the full relative vsnd path from a tree item's hierarchy."""
        path_elements = []
        current_item = item
        while current_item is not None:
            path_elements.insert(0, current_item.text(0))
            current_item = current_item.parent()
        return '/'.join(path_elements)

    def _is_vsnd_item(self, item):
        """Return True if the item represents a .vsnd leaf file."""
        return 'vsnd' in self.assemble_path(item)

    def _get_selected_vsnd_items(self):
        """Return only the selected items that are actual .vsnd leaf files."""
        return [item for item in self.selectedItems() if self._is_vsnd_item(item)]

    # ──────────────────────────────────────────────
    #  Click handler  (single-select plays audio,
    #                   multi-select does NOT)
    # ──────────────────────────────────────────────

    def on_item_clicked(self, item, column):
        """
        Play audio only when exactly ONE vsnd item is selected.
        Prevents playing N sounds simultaneously on multi-select.
        """
        selected_vsnd = self._get_selected_vsnd_items()
        if len(selected_vsnd) == 1:
            assembled_path = self.assemble_path(selected_vsnd[0])
            if 'vsnd' in assembled_path:
                debug(f"Assembled Path: {assembled_path}")
                self.play_audio_file(assembled_path)

    # ──────────────────────────────────────────────
    #  Context menu  — "Copy N Asset Names"
    # ──────────────────────────────────────────────

    def contextMenuEvent(self, event):
        """
        Right-click context menu matching Valve's asset browser UX.
        Shows "Copy N Asset Name(s)" for selected .vsnd items.
        Clipboard format: one path per line with sounds/ prefix.
        """
        vsnd_items = self._get_selected_vsnd_items()

        if not vsnd_items:
            return

        menu = QMenu(self)

        count = len(vsnd_items)
        label = f"Copy {count} Asset Name{'s' if count > 1 else ''}"
        copy_action = menu.addAction(label)
        copy_action.triggered.connect(lambda: self._copy_asset_names(vsnd_items))

        menu.exec(event.globalPos())

    def _copy_asset_names(self, items):
        """
        Copy assembled vsnd paths to the system clipboard, one per line.

        Output format (matches Valve's "Copy N Asset Names"):
            sounds/ambient/common/materials/metal_str1.vsnd
            sounds/ambient/common/materials/metal_str2.vsnd
        """
        paths = []
        for item in items:
            path = self.assemble_path(item)
            if 'vsnd' in path:
                # Ensure the sounds/ prefix is present
                if not path.startswith('sounds/'):
                    path = 'sounds/' + path
                paths.append(path)

        if paths:
            clipboard_text = '\n'.join(paths)
            QGuiApplication.clipboard().setText(clipboard_text)
            debug(f"Copied {len(paths)} asset name(s) to clipboard")

    # ──────────────────────────────────────────────
    #  Drag-and-drop  (supports multi-select)
    # ──────────────────────────────────────────────

    def mouseMoveEvent(self, event):
        """
        Drag handler that supports multiple selected items.
        Sets both plain text (newline-separated paths) and URL list
        on the mime data so the drop target can use either format.
        """
        if event.buttons() & Qt.LeftButton:
            selected_items = self._get_selected_vsnd_items()

            # Fall back to current item for single-item compat
            if not selected_items:
                current = self.currentItem()
                if current and self._is_vsnd_item(current):
                    selected_items = [current]

            if not selected_items:
                return

            drag = QDrag(self)
            mime_data = QMimeData()

            urls = []
            text_paths = []

            addon_dir = get_addon_dir()

            for item in selected_items:
                path = self.assemble_path(item)
                if 'vsnd' not in path:
                    continue

                # Build the full sounds/ prefixed path for clipboard text
                vsnd_path = path
                if not vsnd_path.startswith('sounds/'):
                    vsnd_path = 'sounds/' + vsnd_path
                text_paths.append(vsnd_path)

                # Build file URL (wav) for drag-drop into file properties
                url_path = (
                    "file:///" + addon_dir + '/sounds/' + path
                ).replace('\\', '/').replace('vsnd', 'wav')
                urls.append(QUrl(url_path))

            if text_paths:
                mime_data.setText('\n'.join(text_paths))
                mime_data.setUrls(urls)

            drag.setMimeData(mime_data)
            drag.exec()

    def dragEnterEvent(self, event):
        event.accept()

    # ──────────────────────────────────────────────
    #  Tree population
    # ──────────────────────────────────────────────

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
    # QMediaPlayer instance required for audio playback.
    player = QMediaPlayer()
    explorer = InternalSoundFileExplorer(player)
    explorer.show()
    app.exec()

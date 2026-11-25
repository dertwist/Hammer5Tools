from gui.widgets.property_methods import QDrag
import os
import time
from PySide6.QtWidgets import (
    QApplication, QTreeWidget, QTreeWidgetItem, QMessageBox,
    QTreeWidgetItemIterator, QMenu
)
from PySide6.QtCore import Qt, QUrl, QMimeData, QProcess, QThread, Signal
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtGui import QGuiApplication
from gui.settings.common import get_cs2_path, get_addon_dir
from gui.common import SoundEventEditor_path
from gui.widgets import exception_handler
from core.bridge.core import CoreBridge
from gui.editors.soundevent_editor.thread_parking import park

# pak01_dir.vpk is global CS2 content, identical for every addon. Scan it once
# and reuse the result so switching addons neither re-walks ~130k VPK entries
# nor spawns a second scanner thread that races the editor teardown.
_VSND_FOLDERS_CACHE = None


class VPKLoaderThread(QThread):
    vpk_loaded = Signal(list)
    vpk_load_failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stopped = False

    def stop(self):
        self._stopped = True

    def run(self):
        try:
            cs2_path = get_cs2_path()
            if not cs2_path:
                self.vpk_load_failed.emit(
                    "CS2 installation not configured.\nSet the CS2 path in Preferences."
                )
                return
            path = os.path.join(cs2_path, 'game', 'csgo', 'pak01_dir.vpk')
            if not os.path.isfile(path):
                self.vpk_load_failed.emit(
                    f"CS2 installation not found (looked for {path}).\n"
                    "Set the CS2 path in Preferences."
                )
                return
            with CoreBridge.instance().create_vpk_index() as index:
                index.mount(path)
                folders = []
                for filepath, _ in index.entries((".vsnd",)):
                    if self._stopped or self.isInterruptionRequested():
                        return
                    if 'sounds' in filepath:
                        element = filepath.split('/')[1:]
                        folders.append(element)
                self.vpk_loaded.emit(folders)
        except Exception as e:
            self.vpk_load_failed.emit(str(e))


class VSNDDecodeThread(QThread):
    decoded = Signal(int, object, str)

    def __init__(self, pak_path: str, internal_path: str, generation: int = 0, parent=None):
        super().__init__(parent)
        self.pak_path = pak_path
        self.internal_path = internal_path
        self.generation = generation
        self._stopped = False

    def stop(self):
        self._stopped = True

    def run(self):
        try:
            if self._stopped or self.isInterruptionRequested():
                return
            result = CoreBridge.instance().read_compiled_resource(self.pak_path, self.internal_path)
            if self._stopped or self.isInterruptionRequested():
                return
            if result is not None and result.format in ('wav', 'mp3'):
                self.decoded.emit(self.generation, result.data, result.format)
        except Exception:
            pass


class InternalSoundFileExplorer(QTreeWidget):
    play_audio_data = Signal(object, str)

    def __init__(self, audio_player=None):
        super().__init__()
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.InternalMove)

        self.setSelectionMode(QTreeWidget.ExtendedSelection)

        self.itemClicked.connect(self.on_item_clicked)
        self.audio_player = audio_player
        self.vpk_loader_thread = None
        self._decode_thread = None
        self._decode_generation = 0
        if _VSND_FOLDERS_CACHE is not None:
            self.populate_tree(_VSND_FOLDERS_CACHE)
        else:
            # Unparented and parked: an addon switch deletes this tree while the
            # scan is still walking the VPK, and a running QThread destroyed with
            # its parent aborts the process. See thread_parking.
            self.vpk_loader_thread = park(VPKLoaderThread())
            self.vpk_loader_thread.vpk_loaded.connect(self.populate_tree)
            self.vpk_loader_thread.vpk_load_failed.connect(self.on_vpk_load_failed)
            self.vpk_loader_thread.start()

    #  Filter

    def filter_tree(self, filter_text):
        """Filter tree items based on search text and expand matching items"""
        filter_text = filter_text.lower().strip()

        if not filter_text:
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

    #  Audio playback helpers

    def _to_compiled_vsnd_path(self, rel_path: str) -> str:
        compiled = rel_path[:-5] + '.vsnd_c' if rel_path.lower().endswith('.vsnd') else rel_path
        return os.path.join('sounds', compiled).replace('/', '\\')

    def _on_decoded(self, generation: int, data: object, fmt: str) -> None:
        if generation != self._decode_generation:
            return
        self.play_audio_data.emit(data, fmt)

    def play_audio_file(self, path):
        cs2_path = get_cs2_path()
        if not cs2_path:
            return
        if self._decode_thread is not None and self._decode_thread.isRunning():
            self._decode_thread.stop()
            self._decode_thread.requestInterruption()

        self._decode_generation += 1
        gen = self._decode_generation
        internal_audiopath = self._to_compiled_vsnd_path(path)
        pak1 = os.path.join(cs2_path, 'game', 'csgo', 'pak01_dir.vpk')
        thread = park(VSNDDecodeThread(pak1, internal_audiopath, generation=gen))
        self._decode_thread = thread
        thread.decoded.connect(self._on_decoded)
        thread.start()

    #  Path helpers

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
        return self.assemble_path(item).lower().endswith('.vsnd')

    def _get_selected_vsnd_items(self):
        """Return only the selected items that are actual .vsnd leaf files."""
        return [item for item in self.selectedItems() if self._is_vsnd_item(item)]

    #  Click handler  (single-select plays audio,
    #                   multi-select does NOT)

    def on_item_clicked(self, item, column):
        """
        Play audio only when exactly ONE vsnd item is selected.
        Prevents playing N sounds simultaneously on multi-select.
        """
        selected_vsnd = self._get_selected_vsnd_items()
        if len(selected_vsnd) == 1:
            assembled_path = self.assemble_path(selected_vsnd[0])
            if 'vsnd' in assembled_path:
                self.play_audio_file(assembled_path)

    #  Context menu  — "Copy N Asset Names"

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

        menu.addSeparator()
        decompile_action = menu.addAction(
            f"Decompile {count} file{'s' if count > 1 else ''} to Addon"
        )
        decompile_action.triggered.connect(lambda: self._decompile_to_addon(vsnd_items))

        menu.exec(event.globalPos())

    def _decompile_to_addon(self, items):
        """Decompile the selected .vsnd assets to the current addon content folder.

        Core decoding recreates the sounds/ path under it, writing .wav or .mp3 depending on the source.
        Decoding is synchronous and displays a wait cursor.
        """
        dest = get_addon_dir()
        if not dest:
            QMessageBox.warning(self, "Decompile to Addon", "No active addon directory set.")
            return
        cs2_path = get_cs2_path()
        if not cs2_path:
            return
        pak1 = os.path.join(cs2_path, 'game', 'csgo', 'pak01_dir.vpk')
        QApplication.setOverrideCursor(Qt.WaitCursor)
        done = 0
        try:
            for item in items:
                rel = self.assemble_path(item)
                internal_path = self._to_compiled_vsnd_path(rel)
                result = CoreBridge.instance().read_compiled_resource(pak1, internal_path)
                if result is not None:
                    output_path = os.path.join(dest, internal_path.replace('\\', os.sep))
                    if output_path.lower().endswith('_c'):
                        output_path = output_path[:-2]
                    output_path = os.path.splitext(output_path)[0] + '.' + result.format
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with open(output_path, 'wb') as stream:
                        stream.write(result.data)
                    done += 1
        finally:
            QApplication.restoreOverrideCursor()
        QMessageBox.information(
            self, "Decompile to Addon",
            f"Decompiled {done}/{len(items)} file(s) to:\n{dest}"
        )

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

    #  Drag-and-drop  (supports multi-select)

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

    #  Tree population

    def on_vpk_load_failed(self, reason):
        QMessageBox.critical(self, "Error", f"Failed to load VPK file:\n{reason}")

    def populate_tree(self, folders):
        if not folders:
            return

        global _VSND_FOLDERS_CACHE
        if _VSND_FOLDERS_CACHE is None:
            _VSND_FOLDERS_CACHE = folders

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

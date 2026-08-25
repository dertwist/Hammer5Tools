from gui.property.methods import QDrag
import os
import time
from PySide6.QtWidgets import (
    QApplication, QTreeWidget, QTreeWidgetItem, QMessageBox,
    QTreeWidgetItemIterator, QMenu
)
from PySide6.QtCore import Qt, QUrl, QMimeData, QProcess, QThread, Signal
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtGui import QGuiApplication
from gui.settings.main import get_cs2_path, get_addon_dir, debug
from gui.common import SoundEventEditor_path
from gui.widgets import exception_handler
from hammer5tools_core.bridge.core import CoreBridge
from gui.editors.soundevent_editor.thread_parking import park

# pak01_dir.vpk is global CS2 content, identical for every addon. Scan it once
# and reuse the result so switching addons neither re-walks ~130k VPK entries
# nor spawns a second scanner thread that races the editor teardown.
_VSND_FOLDERS_CACHE = None


@exception_handler
class VPKLoaderThread(QThread):
    vpk_loaded = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stopped = False

    def stop(self):
        self._stopped = True

    def run(self):
        try:
            path = os.path.join(get_cs2_path(), 'game', 'csgo', 'pak01_dir.vpk')
            with CoreBridge.instance().create_vpk_index() as index:
                index.mount(path)
                folders = []
                for filepath, _ in index.entries((".vsnd",)):
                    if self._stopped:
                        return
                    if 'vsnd_c' in filepath and 'sounds' in filepath:
                        filepath = filepath.replace('vsnd_c', 'vsnd')
                        element = filepath.split('/')[1:]
                        folders.append(element)
                self.vpk_loaded.emit(folders)
        except Exception as e:
            self.vpk_loaded.emit([])


@exception_handler
class VSNDDecodeThread(QThread):
    decoded = Signal(object, str)

    def __init__(self, pak_path: str, internal_path: str, parent=None):
        super().__init__(parent)
        self.pak_path = pak_path
        self.internal_path = internal_path

    def run(self):
        try:
            result = CoreBridge.instance().read_compiled_resource(self.pak_path, self.internal_path)
            if result is not None:
                self.decoded.emit(result.data, result.format)
            else:
                debug(f"Failed to decode {self.internal_path}")
        except Exception as e:
            debug(f"Error decoding {self.internal_path}: {e}")


@exception_handler
class InternalSoundFileExplorer(QTreeWidget):
    play_audio_data = Signal(object, str)

    def __init__(self, audio_player=None):
        super().__init__()
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.InternalMove)

        # ── Multi-select: Ctrl+Click and Shift+Click ──
        self.setSelectionMode(QTreeWidget.ExtendedSelection)

        self.itemClicked.connect(self.on_item_clicked)
        self.audio_player = audio_player
        self.vpk_loader_thread = None
        self._decode_thread = None
        if _VSND_FOLDERS_CACHE is not None:
            self.populate_tree(_VSND_FOLDERS_CACHE)
        else:
            # Unparented and parked: an addon switch deletes this tree while the
            # scan is still walking the VPK, and a running QThread destroyed with
            # its parent aborts the process. See thread_parking.
            self.vpk_loader_thread = park(VPKLoaderThread())
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

    def play_audio_file(self, path):
        if self._decode_thread is not None and self._decode_thread.isRunning():
            self._decode_thread.quit()
            self._decode_thread.wait()
            self._decode_thread = None

        internal_audiopath = os.path.join(
            'sounds', path.replace('vsnd', 'vsnd_c')
        ).replace('/', '\\')
        pak1 = os.path.join(get_cs2_path(), 'game', 'csgo', 'pak01_dir.vpk')
        self._decode_thread = park(VSNDDecodeThread(pak1, internal_audiopath))
        self._decode_thread.decoded.connect(self.play_audio_data.emit)
        self._decode_thread.start()

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

        menu.addSeparator()
        decompile_action = menu.addAction(
            f"Decompile {count} file{'s' if count > 1 else ''} to Addon"
        )
        decompile_action.triggered.connect(lambda: self._decompile_to_addon(vsnd_items))

        menu.exec(event.globalPos())

    def _decompile_to_addon(self, items):
        """Decompile the selected .vsnd assets to the current addon content folder.

        Core decoding recreates the sounds/ path under it, writing .wav or .mp3 depending on the source.
        ponytail: synchronous with a wait cursor — fine for a handful of files;
        move to a QThread if bulk decompiles get slow.
        """
        dest = get_addon_dir()
        if not dest:
            QMessageBox.warning(self, "Decompile to Addon", "No active addon directory set.")
            return
        pak1 = os.path.join(get_cs2_path(), 'game', 'csgo', 'pak01_dir.vpk')
        QApplication.setOverrideCursor(Qt.WaitCursor)
        done = 0
        try:
            for item in items:
                rel = self.assemble_path(item)
                internal_path = os.path.join(
                    'sounds', rel.replace('vsnd', 'vsnd_c')
                ).replace('/', '\\')
                result = CoreBridge.instance().read_compiled_resource(pak1, internal_path)
                if result is not None:
                    output_path = os.path.join(dest, internal_path.replace('\\', os.sep))[:-2]
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

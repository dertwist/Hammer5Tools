"""Pick which local changes go into this sync.

Committing everything is wrong more often than not in a map repo: one finished
.vmap sits next to half-imported models and a test material nobody wants
published. So the sync button asks first, and only the ticked paths are staged.

Unticked changes stay local and are not uploaded. When the server has no newer
work, the controller pushes the selected commit without touching them. Only a
required pull temporarily stashes and restores them; the note at the bottom of
the dialog explains that exceptional path.
"""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHeaderView, QHBoxLayout, QLabel, QLineEdit,
    QMenu, QMessageBox, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
)

from gui.forms.git_sync import git_icon
from gui.forms.git_sync.commit_msg import generate

_PATH_ROLE = Qt.UserRole
_COUNT_ROLE = Qt.UserRole + 1
_SIZE_ROLE = Qt.UserRole + 2


def human_size(nbytes):
    """"12.3 MB". Bytes and KB stay whole; anything larger gets one decimal."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if nbytes < 1024 or unit == "TB":
            return ("%.0f %s" if unit in ("B", "KB") else "%.1f %s") % (nbytes, unit)
        nbytes /= 1024


def leftover_note(left_out, behind=0):
    """The warning under the list, or "" when nothing is being left behind.

    Split out from the widget so the wording is testable without a QApplication.
    """
    if not left_out:
        return ""
    text = ("%d unticked change%s will stay local and will not be uploaded."
            % (len(left_out), "" if len(left_out) == 1 else "s"))
    if behind:
        text += (" The server has newer work, so these changes will be backed up "
                 "while Git merges it. If the same file changed on both sides, "
                 "you may have to merge it by hand.")
    return text


class ChangesDialog(QDialog):
    """Checklist of local changes plus the commit message for the ticked ones.

    `entries` is [(change word, path, size in bytes)] as produced by
    GitRepo.entries(); `behind` is how many commits the server is ahead, used
    only to sharpen the warning text. `suggest` is the GitSync preference: off
    means the message box starts empty and the user has to write one.
    """

    def __init__(self, entries, behind=0, suggest=True, repo=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sync changes")
        self.setWindowIcon(git_icon())
        self.resize(720, 480)
        self._entries = list(entries)
        self._repo = repo
        self._suggest = suggest
        self._message_edited = False
        self._updating_checks = False
        self._leaf_items = []

        outer = QVBoxLayout(self)
        header = QLabel(
            "Tick the changes you want to send. Everything else stays on your "
            "machine, exactly as it is now.")
        header.setWordWrap(True)
        outer.addWidget(header)

        picker = QHBoxLayout()
        for label, action in (("All", self._select_all),
                              ("None", self._select_none),
                              ("Maps only", self._select_maps)):
            button = QPushButton(label)
            button.clicked.connect(action)
            picker.addWidget(button)
        self.discard_btn = QPushButton("Discard")
        self.discard_btn.setToolTip(
            "Permanently discard the selected change, restoring the file to "
            "its last committed state.")
        self.discard_btn.setEnabled(False)
        self.discard_btn.clicked.connect(self._discard_selected)
        picker.addWidget(self.discard_btn)
        picker.addStretch(1)
        self.count_label = QLabel()
        picker.addWidget(self.count_label)
        outer.addLayout(picker)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["File", "Change", "Size"])
        self.tree.setRootIsDecorated(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.tree.header().setStretchLastSection(False)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        self._populate_tree()
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tree.itemChanged.connect(self._on_item_changed)
        if len(self._entries) <= 100:
            self.tree.expandAll()
        else:
            for index in range(self.tree.topLevelItemCount()):
                self.tree.topLevelItem(index).setExpanded(True)
        outer.addWidget(self.tree, 1)

        self.note_label = QLabel()
        self.note_label.setWordWrap(True)
        self.note_label.setProperty("h5Component", "gitLeftoverNote")
        outer.addWidget(self.note_label)

        message_row = QHBoxLayout()
        message_row.addWidget(QLabel("Message"))
        self.message_edit = QLineEdit()
        self.message_edit.setPlaceholderText("Describe what changed")
        self.message_edit.textEdited.connect(self._on_message_edited)
        message_row.addWidget(self.message_edit, 1)
        outer.addLayout(message_row)

        buttons = QDialogButtonBox()
        self.sync_btn = buttons.addButton("Sync", QDialogButtonBox.AcceptRole)
        buttons.addButton(QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        self._behind = behind
        self._refresh()

    # selection
    def _populate_tree(self):
        """Build folder nodes while keeping leaf order identical to Git status."""
        folders = {}
        root = self.tree.invisibleRootItem()
        for word, path, size in self._entries:
            parts = [part for part in path.replace("\\", "/").split("/") if part]
            if not parts:
                continue
            parent = root
            folder_path = []
            for name in parts[:-1]:
                folder_path.append(name)
                key = tuple(folder_path)
                folder = folders.get(key)
                if folder is None:
                    folder = QTreeWidgetItem(parent, [name, "", ""])
                    folder.setFlags(
                        folder.flags() | Qt.ItemIsUserCheckable |
                        Qt.ItemIsAutoTristate)
                    folder.setCheckState(0, Qt.Checked)
                    folder.setToolTip(0, "/".join(folder_path))
                    folder.setData(0, _COUNT_ROLE, 0)
                    folder.setData(0, _SIZE_ROLE, 0)
                    folders[key] = folder
                folder.setData(0, _COUNT_ROLE, folder.data(0, _COUNT_ROLE) + 1)
                folder.setData(0, _SIZE_ROLE, folder.data(0, _SIZE_ROLE) + size)
                parent = folder

            item = QTreeWidgetItem(
                parent, [parts[-1], word, human_size(size) if size else ""])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setData(0, _PATH_ROLE, path)
            item.setToolTip(0, path)
            item.setCheckState(0, Qt.Checked)
            self._leaf_items.append(item)

        for folder in folders.values():
            count = folder.data(0, _COUNT_ROLE)
            size = folder.data(0, _SIZE_ROLE)
            folder.setText(1, "%d change%s" % (count, "" if count == 1 else "s"))
            folder.setText(2, human_size(size) if size else "")

    def _items(self):
        return self._leaf_items

    @staticmethod
    def _descendants(item):
        for index in range(item.childCount()):
            child = item.child(index)
            yield child
            yield from ChangesDialog._descendants(child)

    def _sync_folder_states(self):
        """Recompute folder checks from leaves after a bulk or leaf change."""
        def visit(item):
            if not item.childCount():
                return item.checkState(0)
            states = [visit(item.child(index)) for index in range(item.childCount())]
            if all(state == Qt.Checked for state in states):
                state = Qt.Checked
            elif all(state == Qt.Unchecked for state in states):
                state = Qt.Unchecked
            else:
                state = Qt.PartiallyChecked
            item.setCheckState(0, state)
            return state

        self._updating_checks = True
        try:
            root = self.tree.invisibleRootItem()
            for index in range(root.childCount()):
                visit(root.child(index))
        finally:
            self._updating_checks = False

    def _on_item_changed(self, item, column):
        if self._updating_checks or column != 0:
            return
        self._updating_checks = True
        try:
            if item.childCount() and item.checkState(0) != Qt.PartiallyChecked:
                state = item.checkState(0)
                for child in self._descendants(item):
                    child.setCheckState(0, state)
        finally:
            self._updating_checks = False
        self._sync_folder_states()
        self._refresh()

    def _set_all(self, predicate):
        self._updating_checks = True
        try:
            for item in self._items():
                item.setCheckState(
                    0, Qt.Checked
                    if predicate(item.data(0, _PATH_ROLE)) else Qt.Unchecked)
        finally:
            self._updating_checks = False
        self._sync_folder_states()
        self._refresh()

    def _select_all(self):
        self._set_all(lambda _path: True)

    def _select_none(self):
        self._set_all(lambda _path: False)

    def _select_maps(self):
        self._set_all(lambda path: path.lower().endswith(".vmap"))

    def _on_message_edited(self, text):
        # Once the user types their own message, stop overwriting it when the
        # ticked set changes.
        self._message_edited = bool(text.strip())
        self._refresh()

    # discard
    def _leaf_items_for_selection(self):
        """Unique leaf items under the current tree selection, including folder descendants."""
        seen = set()
        leaves = []
        for item in self.tree.selectedItems():
            if item.data(0, _PATH_ROLE) is not None:
                # Leaf item (file).
                path = item.data(0, _PATH_ROLE)
                if path not in seen:
                    seen.add(path)
                    leaves.append(item)
            else:
                # Folder item — collect all leaf descendants.
                for child in self._descendants(item):
                    if child.data(0, _PATH_ROLE) is not None:
                        path = child.data(0, _PATH_ROLE)
                        if path not in seen:
                            seen.add(path)
                            leaves.append(child)
        return leaves

    def _on_selection_changed(self):
        has_selection = bool(self._leaf_items_for_selection()) and self._repo is not None
        self.discard_btn.setEnabled(has_selection)

    def _show_context_menu(self, pos):
        items = self._leaf_items_for_selection()
        if not items or self._repo is None:
            return
        menu = QMenu(self)
        label = ("Discard change" if len(items) == 1
                 else "Discard %d changes" % len(items))
        menu.addAction(label, self._discard_selected)
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _discard_selected(self):
        items = self._leaf_items_for_selection()
        if not items or self._repo is None:
            return
        paths = [item.data(0, _PATH_ROLE) for item in items]
        noun = "this change" if len(paths) == 1 else "%d changes" % len(paths)
        r = QMessageBox.question(
            self, "Discard",
            "Permanently discard %s?\n\n%s\n\n"
            "This cannot be undone." % (noun, "\n".join(paths)),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if r != QMessageBox.Yes:
            return
        succeeded = []
        for item in items:
            path = item.data(0, _PATH_ROLE)
            word = item.text(1)
            if not self._discard_path(path, word):
                break
            succeeded.append(item)
        self._remove_discarded_items(succeeded)

    def _discard_path(self, path, word):
        """Revert one path. Returns True on success."""
        if word == "New":
            full = os.path.join(self._repo.dir, path) if self._repo.dir else path
            try:
                os.remove(full)
            except OSError:
                pass
            return True
        code, _out, err = self._repo._run("checkout", "--", path)
        if code != 0:
            QMessageBox.warning(
                self, "Discard failed",
                "Could not discard %s:\n\n%s" % (path, err.strip() or "Unknown error"))
            return False
        return True

    def _remove_discarded_items(self, items):
        """Remove successfully discarded items from the tree and the entry list."""
        if not items:
            return
        discarded = set()
        for item in items:
            path = item.data(0, _PATH_ROLE)
            discarded.add(path)
            parent = item.parent() or self.tree.invisibleRootItem()
            parent.removeChild(item)
        self._entries = [(w, p, s) for w, p, s in self._entries if p not in discarded]
        self._leaf_items = [i for i in self._leaf_items if i.data(0, _PATH_ROLE) not in discarded]
        self._prune_empty_folders()
        self._sync_folder_states()
        self._refresh()

    def _prune_empty_folders(self):
        """Recursively remove folder nodes that have no children left."""
        def prune(parent):
            for index in range(parent.childCount() - 1, -1, -1):
                child = parent.child(index)
                if child.data(0, _PATH_ROLE) is None:  # folder node
                    prune(child)
                    if child.childCount() == 0:
                        parent.removeChild(child)
        prune(self.tree.invisibleRootItem())

    # results
    def selected_paths(self):
        return [item.data(0, _PATH_ROLE) for item in self._items()
                if item.checkState(0) == Qt.Checked]

    def left_out_paths(self):
        return [item.data(0, _PATH_ROLE) for item in self._items()
                if item.checkState(0) != Qt.Checked]

    def message(self):
        typed = self.message_edit.text().strip()
        if typed or not self._suggest:
            return typed
        return self._suggested(set(self.selected_paths()))

    def _suggested(self, selected):
        """Reuse the commit-message generator, fed only the ticked paths."""
        porcelain = "\n".join(
            "%s %s" % ("??" if word == "New" else " M", path)
            for word, path, _size in self._entries if path in selected)
        return generate(porcelain)

    def _refresh(self):
        selected = self.selected_paths()
        left_out = self.left_out_paths()
        total = sum(size for _w, path, size in self._entries if path in set(selected))
        self.count_label.setText(
            "%d of %d selected%s" % (len(selected), len(self._entries),
                                     " — " + human_size(total) if total else ""))
        note = leftover_note(left_out, self._behind)
        self.note_label.setText(note)
        self.note_label.setVisible(bool(note))
        self.message_edit.setEnabled(bool(selected))
        if not self._message_edited and self._suggest:
            self.message_edit.setText(self._suggested(set(selected)) if selected else "")
        # Nothing ticked is still a valid sync — it means "just get the server's
        # changes" — so Sync stays available. A commit with no message is not:
        # git rejects it, and only the "write it yourself" preference can get here.
        self.sync_btn.setText("Sync" if selected else "Pull only")
        self.sync_btn.setEnabled(not selected or bool(self.message()))


def _demo():
    assert human_size(0) == "0 B"
    assert human_size(2048) == "2 KB"
    assert human_size(300 * 1024 * 1024) == "300.0 MB"
    assert leftover_note([]) == ""
    assert leftover_note(["a"]).startswith("1 unticked change will stay local")
    assert "changes will stay local" in leftover_note(["a", "b"])
    assert "merge it by hand" in leftover_note(["a"], behind=2)
    assert "merge it by hand" not in leftover_note(["a"], behind=0)
    print("changes_dialog self-check OK")


if __name__ == "__main__":
    _demo()

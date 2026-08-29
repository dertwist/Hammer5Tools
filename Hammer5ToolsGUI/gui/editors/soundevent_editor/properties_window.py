import ast
import logging

from gui.common import fast_deepcopy

from gui.editors.soundevent_editor.ui_properties_window import Ui_MainWindow
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QTimer
from gui.settings.common import settings
from gui.editors.soundevent_editor.property.frame import SoundEventEditorPropertyFrame
from gui.widgets.popup_menu.main import PopupMenu
from gui.editors.soundevent_editor.objects import soundevent_editor_properties
from gui.widgets import ErrorInfo
from PySide6.QtWidgets import QMainWindow, QMenu, QApplication, QTreeWidget
from PySide6.QtGui import QKeySequence, QKeyEvent, QUndoStack, QUndoCommand, QShortcut
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QFrame, QHBoxLayout
from gui.editors.soundevent_editor.property_schema import (
    COLLAPSED_BY_DEFAULT,
    GROUP_ORDER,
    GROUP_TITLES,
    PAIRED,
    TOGGLE_DEPENDENTS,
    get_spec,
    sort_key,
)

log = logging.getLogger(__name__)


class PropertyGroupHeader(QFrame):
    """Collapsible bar above the properties of one schema group.

    Membership is read off the layout rather than tracked: everything after the
    header whose ``display_order`` names the same group belongs to it, so
    adding or deleting a property needs no bookkeeping here. Collapsing only
    hides widgets, so hidden properties still serialize.
    """

    def __init__(self, group: str, layout, expanded: bool = True, parent=None):
        super().__init__(parent)
        self.group = group
        self.group_index = GROUP_ORDER[group]
        self.display_order = (self.group_index, -1)
        self._layout = layout

        self.setProperty("h5Component", "soundeventGroupHeader")
        self.setFrameShape(QFrame.NoFrame)
        self.setMinimumHeight(24)
        self.setMaximumHeight(24)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        self.show_child = QCheckBox(self)
        self.show_child.setObjectName("show_child")
        self.show_child.setFocusPolicy(Qt.NoFocus)
        self.show_child.setText(GROUP_TITLES[group])
        self.show_child.setChecked(expanded)
        self.show_child.clicked.connect(self.apply)
        row.addWidget(self.show_child)

    def apply(self):
        """Show or hide every property that follows this header in its group."""
        visible = self.show_child.isChecked()
        start = self._layout.indexOf(self)
        if start < 0:
            return
        for index in range(start + 1, self._layout.count()):
            item = self._layout.itemAt(index)
            widget = item.widget() if item is not None else None
            order = getattr(widget, "display_order", None)
            if order is None or order[0] != self.group_index:
                break
            widget.setVisible(visible)

class PropertyStateCommand(QUndoCommand):
    """
    Snapshots the full properties dict before and after a change.
    Undo restores the before-state, redo restores the after-state.

    This command is element-aware: it stores a target element key (m_nElementID or name)
    so that undo/redo can switch the tree selection to the element whose state it restores,
    and also updates the tree item's stored data accordingly.
    """
    def __init__(self, window, target_key, before: dict, after: dict, description="Edit Property"):
        super().__init__(description)
        self.window = window
        self.target_key = target_key
        self.before = fast_deepcopy(before)
        self.after = fast_deepcopy(after)

    def _find_item_for_key(self):
        """Attempt to find a QTreeWidgetItem in the associated tree matching the target_key.
        Two strategies are tried:
          - If target_key is an int, match against stored data['m_nElementID']
          - Otherwise, match by item text (name)
        Returns the QTreeWidgetItem or None if not found.
        """
        try:
            tree = self.window.tree
            if tree is None:
                return None
            root = tree.invisibleRootItem()
            for i in range(root.childCount()):
                child = root.child(i)
                try:
                    data = self.window._data_for_item(child)
                    if isinstance(self.target_key, int):
                        if isinstance(data, dict) and data.get('m_nElementID') == self.target_key:
                            return child
                    else:
                        # fallback: match by visible name
                        if child.text(0) == str(self.target_key):
                            return child
                except Exception:
                    continue
        except Exception:
            return None
        return None

    def _apply_state(self, state: dict):
        """Switch to the target tree item (if needed) and restore the given state."""
        item = self._find_item_for_key()

        # Block the normal currentItemChanged handler so switch_to_item is not
        # called twice (once from the signal, once from _restore_state).
        self.window._restoring_from_undo = True
        try:
            if item is not None:
                try:
                    self.window.tree.setCurrentItem(item)
                except Exception:
                    pass
            # Rebuild the properties UI from the snapshot
            self.window._restore_state(state)
            # Write the restored data back into the tree item so tree stays in sync
            if item is not None:
                try:
                    self.window._set_data_for_item(item, self.window.value)
                except Exception:
                    pass
        finally:
            self.window._restoring_from_undo = False

    def undo(self):
        self._apply_state(self.before)

    def redo(self):
        # On first push Qt calls redo() immediately — skip to avoid double-apply
        if getattr(self, '_first_redo_done', False):
            self._apply_state(self.after)
        self._first_redo_done = True

class SoundEventEditorPropertiesWindow(QMainWindow):
    edited = Signal()
    def __init__(self, parent=None, value: str = None, tree:QTreeWidget = None, undo_stack:QUndoStack = None):
        """
        The properties window is supposed to store property frame instances in the layout.
        When any of the frames are edited, the value updates and
        sends a signal that can be used to save the file or update the tree item in the hierarchy.
        """

        super().__init__(parent)

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Init QT settings variable from preferences
        self.settings = settings

        # Read-only flag for internal/game events
        self.readonly_mode: bool = False

        # Init common state variables
        self.realtime_save = False

        # Init value variable:
        self.value = self.load_value(value)

        # Init undo/redo system. Allow injection of a global undo stack (recommended).
        if undo_stack is not None:
            self.undo_stack = undo_stack
        else:
            self.undo_stack = QUndoStack(self)
        self._undo_enabled = False   # suppress pushes during load/clear
        self._slider_dragging = False          # True while a slider is being dragged
        self._pre_commit_snapshot = None       # value snapshot taken at sliderPressed
        self._restoring_from_undo = False      # True while undo/redo is restoring state
        self._populating = False               # True while populating properties
        self._next_undo_desc = None            # optional label for the next undo push

        # Init variables
        self.tree = tree

        # Display order is grouped, but the file keeps its original key order:
        # re-saving an untouched event must not reshuffle the .vsndevts.
        self._source_order: list[str] = []
        self._frames_by_key: dict = {}
        self._frames_by_entry: dict = {}
        self._group_headers: dict = {}


        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_context_menu)
        self._context_menu_connected = True

        self.ui.centralwidget.setFocusPolicy(Qt.StrongFocus)

        # Setup undo/redo keyboard shortcuts
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self.undo_stack.undo)

        redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self)
        redo_shortcut.activated.connect(self.undo_stack.redo)

        redo_shortcut_alt = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        redo_shortcut_alt.activated.connect(self.undo_stack.redo)

        self.properties_groups_hide()

    def _data_for_item(self, item) -> dict:
        if item is None or self.tree is None:
            return {}
        document = getattr(self.tree, "soundevent_document", None)
        if document is not None:
            return document.events.get(item.text(0), {})
        value = item.data(0, Qt.UserRole)
        return value if isinstance(value, dict) else {}

    def _set_data_for_item(self, item, value: dict) -> None:
        if item is None:
            return
        document = getattr(self.tree, "soundevent_document", None)
        if document is not None:
            document.events[item.text(0)] = fast_deepcopy(value)
        item.setData(0, Qt.UserRole, fast_deepcopy(value))

    def load_value(self, value):
        if isinstance(value, str):
            return ast.literal_eval(value)
        elif isinstance(value, dict):
            return value
    # Comment keys

    def _unique_comment_key(self):
        """Return the next free comment key: 'comment', then 'comment_2', 'comment_3', ...

        Comments are regular properties now, but unlike the others they can be added
        any number of times. Each new comment gets a unique key so it round-trips
        through the flat properties dict without colliding.
        """
        existing = set(self.get_properties_value().keys())
        if 'comment' not in existing:
            return 'comment'
        index = 2
        while f'comment_{index}' in existing:
            index += 1
        return f'comment_{index}'

    # Properties Actions

    def new_property_popup(self):
        """Call popup menu with all properties"""
        existing_items = set()
        __properties = self.get_properties_value()
        for item in __properties:
            existing_items.add(item)

        soundevent_editor_properties_filtered = []
        # Assuming soundevent_editor_properties is a list of tuples or a dictionary
        for dict_value in soundevent_editor_properties:
            for key, value in dict_value.items():
                key_value = next(iter(value.items()))[0]
                # 'comment' is always offered — it can be added multiple times
                if key_value == 'comment' or key_value not in existing_items:
                    soundevent_editor_properties_filtered.append({key:value})
        self.popup_menu = PopupMenu(soundevent_editor_properties_filtered, add_once=True, help_url="SoundEvent_Editor", window_name='soundevent_editor_properties_filtered')
        self.popup_menu.add_property_signal.connect(lambda name, value: self.new_property(name, value))
        self.popup_menu.show()

    def new_property(self, name:str = None, value:dict  = None):
        """Creates new property in Properties Window"""
        if name is None:
            name = 'Name'
        if value is None:
            value = {}

        # Getting key and value from dict value (single dict value that contains only one key and value)

        # Check if value is a string and convert it to a dictionary if necessary
        if isinstance(value, str):
            try:
                value = ast.literal_eval(value)
            except (ValueError, SyntaxError) as e:
                value = {}

        # Ensure value is a dictionary and has at least one item
        if isinstance(value, dict) and value:
            key, val = next(iter(value.items()))
            # Comments can coexist — give each one a unique key
            if key == 'comment':
                key = self._unique_comment_key()
            self._next_undo_desc = f"Add property '{key}'"
            self.create_property(key, val)
        else:
            pass
        self.on_update()

    def paste_property(self):
        """Creates new property from clipboard using new_property function"""
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text()

        try:
            data = ast.literal_eval(clipboard_text)
            key = next(iter(data))
            val = data[key]
            existing_items = set(self.get_properties_value().keys())
            # Comments can coexist — a pasted comment gets a fresh unique key
            if isinstance(key, str) and (key == 'comment' or key.startswith('comment_')):
                key = self._unique_comment_key()
            if key not in existing_items:
                self._next_undo_desc = f"Paste property '{key}'"
                self.create_property(key, val)
            else:
                ErrorInfo(
                    text='It seems a property with this name already exists in the sound event. Please remove the existing property to create a new one.').exec()
        except (ValueError, SyntaxError) as e:
            ErrorInfo("Error parsing clipboard content").exec()
        self.on_update()
    # Filter

    def eventFilter(self, source, event):
        """Handle keyboard and shortcut events for various widgets."""

        if event.type() == QKeyEvent.KeyPress:
            # Handle events for the specific widget, e.g., tree_hierarchy_widget
            if source == self.ui.centralwidget:
                if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
                    self.new_property_popup()
                    return True
                if event.key() == Qt.Key_V and event.modifiers() == Qt.ControlModifier:
                    self.paste_property()
                    return True

        return super().eventFilter(source, event)
    # Properties widget

    def properties_groups_hide(self):
        """Hide properties and show placeholder"""
        self.ui.properties_spacer.hide()
        self.ui.properties_placeholder.show()

        # Unset Filter
        self.ui.centralwidget.removeEventFilter(self)

        self.setContextMenuPolicy(Qt.NoContextMenu)
        if self._context_menu_connected:
            self.customContextMenuRequested.disconnect(self.open_context_menu)
            self._context_menu_connected = False


        try:
            self.play_button.setEnabled(True)
        except Exception:
            pass
    def properties_groups_show(self):
        """Show properties and hide placeholder"""
        self.ui.properties_placeholder.hide()
        self.ui.properties_spacer.show()

        self.ui.centralwidget.installEventFilter(self)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        # Every event switch calls this; connecting again would stack duplicate
        # handlers and pop the context menu once per switch made.
        if not self._context_menu_connected:
            self.customContextMenuRequested.connect(self.open_context_menu)
            self._context_menu_connected = True

        self.apply_readonly_mode()
    
    def _set_all_groups_expanded(self, expanded: bool):
        for header in self._group_headers.values():
            header.show_child.setChecked(expanded)
            header.apply()

    def collapse_all_properties(self):
        """Collapse all property frames and their group bars"""
        self._set_all_groups_expanded(False)
        for index in range(self.ui.properties_layout.count()):
            widget = self.ui.properties_layout.itemAt(index).widget()
            if isinstance(widget, SoundEventEditorPropertyFrame):
                if hasattr(widget, 'ui') and hasattr(widget.ui, 'show_child'):
                    widget.ui.show_child.setChecked(False)
                    widget.show_child_action()
    
    def expand_all_properties(self):
        """Expand all property frames and their group bars"""
        self._set_all_groups_expanded(True)
        for index in range(self.ui.properties_layout.count()):
            widget = self.ui.properties_layout.itemAt(index).widget()
            if isinstance(widget, SoundEventEditorPropertyFrame):
                if hasattr(widget, 'ui') and hasattr(widget.ui, 'show_child'):
                    widget.ui.show_child.setChecked(True)
                    widget.show_child_action()
    def properties_clear(self):
        self._undo_enabled = False   # prevent clear from pushing a command
        i = 0
        while i < self.ui.properties_layout.count():
            widget = self.ui.properties_layout.itemAt(i).widget()
            if isinstance(widget, (SoundEventEditorPropertyFrame, PropertyGroupHeader)):
                self.ui.properties_layout.takeAt(i)
                widget.deleteLater()
            else:
                i += 1
        self._frames_by_key.clear()
        self._frames_by_entry.clear()
        self._group_headers.clear()
        self._source_order = []

    def populate_properties(self, _data):
        """Loading properties from given data, grouped into schema order.

        Both event switching and undo/redo land here, and both normally differ
        from what is already on screen by a value or two. Frames whose property
        is unchanged are therefore refreshed in place and only the difference is
        built or destroyed — a rebuild costs a .ui load per property, which is
        what made undo and switching stutter.
        """
        if not isinstance(_data, dict):
            log.error("Wrong input data format: %s (%s)", _data, type(_data))
            return

        keys = [key for key in _data if key != 'm_sLabel']
        self._source_order = list(keys)

        container = self.ui.properties_layout.parentWidget()
        if container is not None:
            container.setUpdatesEnabled(False)
        try:
            reusable = self._frames_by_entry
            self._frames_by_entry = {}
            self._frames_by_key = {}
            for entry in self._display_entries(keys):
                data = {key: _data[key] for key in entry}
                frame = reusable.pop(entry, None)
                if frame is not None:
                    if frame.set_values(data):
                        self._register_frame(entry, frame)
                        continue
                    self._discard_frame(frame)
                self.create_property_entry(data)
            for frame in reusable.values():
                self._discard_frame(frame)
            self._prune_group_headers()
        finally:
            if container is not None:
                container.setUpdatesEnabled(True)

        # Ensure readonly mode applied after population
        self.apply_readonly_mode()

        # Sync self.value so callers can read it immediately after populate_properties()
        self.update_value()

    def _register_frame(self, entry: tuple, frame) -> None:
        self._frames_by_entry[entry] = frame
        for key in entry:
            self._frames_by_key[key] = frame

    def _discard_frame(self, frame) -> None:
        """Drop a frame that no longer has a property to show."""
        try:
            self.ui.properties_layout.removeWidget(frame)
            frame.setParent(None)
            frame.deleteLater()
        except RuntimeError:
            pass  # already destroyed (e.g. by its own delete button)

    def _prune_group_headers(self) -> None:
        """Remove the bars of groups that no longer hold any property."""
        groups = {get_spec(key).group for key in self._frames_by_key}
        for group in [g for g in self._group_headers if g not in groups]:
            header = self._group_headers.pop(group)
            self.ui.properties_layout.removeWidget(header)
            header.setParent(None)
            header.deleteLater()

    def _display_entries(self, keys) -> list:
        """Keys in display order, with min/max pairs merged into one entry."""
        present = set(keys)
        merged = {}
        absorbed = set()
        for low, high, _title in PAIRED:
            if low in present and high in present:
                merged[low] = (low, high)
                absorbed.add(high)
        standalone = [key for key in keys if key not in absorbed]
        standalone.sort(key=sort_key)
        return [merged.get(key, (key,)) for key in standalone]


    # Property
    def create_property(self, key, value):
        """Create frame widget instance"""
        self.create_property_entry({key: value})

    def create_property_entry(self, data: dict):
        """Create one frame for a property, or for a merged min/max pair."""
        widget_instance = SoundEventEditorPropertyFrame(_data=data, widget_list=self.ui.properties_layout, tree=self.tree)
        widget_instance.edited.connect(self.on_update)
        widget_instance.deleted.connect(
            lambda name, frame=widget_instance: self._on_property_deleted(name, frame)
        )
        widget_instance.slider_pressed.connect(self._capture_pre_commit_snapshot)
        widget_instance.committed.connect(self.on_commit)

        keys = list(data)
        first = keys[0]
        widget_instance.display_order = sort_key(first)
        if len(keys) > 1:
            title = next((t for low, _high, t in PAIRED if low == first), None)
            if title:
                widget_instance.ui.property_class.setText(title)

        header = self._ensure_group_header(get_spec(first).group)
        index = self._insert_index_for(widget_instance.display_order)
        self.ui.properties_layout.insertWidget(index, widget_instance)
        self._register_frame(tuple(keys), widget_instance)
        if header is not None and not header.show_child.isChecked():
            widget_instance.setVisible(False)
        return widget_instance

    def _insert_index_for(self, order: tuple) -> int:
        """Layout index that keeps the grouped display order."""
        layout = self.ui.properties_layout
        for index in range(layout.count()):
            item = layout.itemAt(index)
            widget = item.widget() if item is not None else None
            other = getattr(widget, 'display_order', None)
            if other is not None and other > order:
                return index
        return layout.count() - 1

    def _ensure_group_header(self, group: str):
        """Header bar for a group, created in display order on first use."""
        header = self._group_headers.get(group)
        if header is not None:
            return header
        header = PropertyGroupHeader(
            group,
            self.ui.properties_layout,
            expanded=group not in COLLAPSED_BY_DEFAULT,
            parent=self.ui.scrollAreaWidgetContents,
        )
        self.ui.properties_layout.insertWidget(self._insert_index_for(header.display_order), header)
        self._group_headers[group] = header
        return header

    def _apply_toggle_dependencies(self):
        """Disable properties whose governing toggle is off."""
        if self.readonly_mode:
            return
        for toggle, dependents in TOGGLE_DEPENDENTS.items():
            frame = self._frames_by_key.get(toggle)
            if frame is None:
                continue
            value = frame.value.get(toggle) if isinstance(frame.value, dict) else None
            for key in dependents:
                dependent = self._frames_by_key.get(key)
                if dependent is not None and dependent is not frame:
                    dependent.setEnabled(bool(value))

    def _on_property_deleted(self, prop_name: str, frame=None):
        """Called just before a property frame destroys itself — sets the undo
        label and forgets the frame, which is about to become a dead reference."""
        self._next_undo_desc = f"Delete property '{prop_name}'"
        for entry, existing in list(self._frames_by_entry.items()):
            if existing is frame:
                del self._frames_by_entry[entry]
                for key in entry:
                    self._frames_by_key.pop(key, None)
        self._prune_group_headers()

    def get_property_value(self, index):
        """Getting dict value from widget instance frame"""
        widget_instance = self.ui.properties_layout.itemAt(index).widget()
        if isinstance(widget_instance, SoundEventEditorPropertyFrame):
            return widget_instance.value
        else:
            return {}
    def get_properties_value(self):
        """All frame values, in the key order the event was loaded with.

        Display order is grouped, but reordering the UI must not reorder the
        saved file, so keys already on the event keep their original position
        and only new ones are appended.
        """
        collected: dict = {}
        for index in range(self.ui.properties_layout.count()):
            try:
                collected.update(self.get_property_value(index))
            except Exception:
                pass
        ordered = {key: collected.pop(key) for key in self._source_order if key in collected}
        ordered.update(collected)
        return ordered

    def _restore_state(self, state: dict):
        """Rebuild the properties UI from a full state snapshot."""
        self._undo_enabled = False       # don't push a new command while restoring
        self._populating = True
        self.properties_groups_show()
        self.populate_properties(state)

        # Update per-frame context labels for the current tree item
        try:
            current_item = self.tree.currentItem()
            if current_item is not None:
                element_name = current_item.text(0)
                for idx in range(self.ui.properties_layout.count()):
                    widget = self.ui.properties_layout.itemAt(idx).widget()
                    if hasattr(widget, 'set_context_element'):
                        try:
                            widget.set_context_element(element_name)
                        except Exception:
                            pass
        except Exception:
            pass

        self.update_value()
        self._populating = False
        self._undo_enabled = True
        self.edited.emit()

    # Updating
    def _get_current_element_key_and_name(self):
        """Return (element_key, element_name) for the currently selected tree item."""
        element_key = None
        element_name = None
        try:
            current_item = self.tree.currentItem()
            if current_item is not None:
                element_name = current_item.text(0)
                data = self._data_for_item(current_item)
                if isinstance(data, dict) and 'm_nElementID' in data:
                    element_key = data.get('m_nElementID')
                else:
                    element_key = element_name
        except Exception:
            pass
        return element_key, element_name

    def on_update(self):
        if self._populating:
            return
        """Updating dict value and send signal.
        For slider drags this is called on every tick — only real-time save, NO undo push.
        Undo is pushed once in on_commit() when the slider is released.
        For discrete widgets (bool, text, combobox) the slider is never pressed so
        _slider_dragging is False and we push to the undo stack as normal.
        """
        if self._undo_enabled and not self._slider_dragging:
            before = fast_deepcopy(self.value)
            self.update_value()
            after = fast_deepcopy(self.value)
            if before != after:
                element_key, element_name = self._get_current_element_key_and_name()
                if self._next_undo_desc:
                    desc = self._next_undo_desc
                    self._next_undo_desc = None
                else:
                    desc = f"Edit '{element_name}'" if element_name else "Edit Property"
                self.undo_stack.push(PropertyStateCommand(self, element_key, before, after, desc))
        else:
            self.update_value()
        self._apply_toggle_dependencies()
        self.edited.emit()

    def _capture_pre_commit_snapshot(self):
        """Called at sliderPressed — snapshot the value BEFORE the drag begins."""
        if self._undo_enabled:
            self._pre_commit_snapshot = fast_deepcopy(self.value)
        self._slider_dragging = True

    def on_commit(self):
        """Called at sliderReleased — push a single undo entry for the whole drag."""
        # update_value() first so self.value reflects the final slider position
        self.update_value()
        if self._undo_enabled and self._pre_commit_snapshot is not None:
            after = fast_deepcopy(self.value)
            if self._pre_commit_snapshot != after:
                element_key, element_name = self._get_current_element_key_and_name()
                desc = f"Edit '{element_name}'" if element_name else "Edit Property"
                self.undo_stack.push(PropertyStateCommand(self, element_key, self._pre_commit_snapshot, after, desc))
        self._pre_commit_snapshot = None
        # Clear the dragging flag LAST so any late valueChanged that arrives
        # during this method is still suppressed by on_update().
        self._slider_dragging = False
    def update_value(self):
        self.value = self.get_properties_value()
    # Context menu
    def open_context_menu(self, position):
        """Layout context menu"""
        menu = QMenu()

        undo_action = menu.addAction("Undo")
        undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        undo_action.setEnabled(self.undo_stack.canUndo())
        undo_action.triggered.connect(self.undo_stack.undo)

        redo_action = menu.addAction("Redo")
        redo_action.setShortcut(QKeySequence("Ctrl+Y"))
        redo_action.setEnabled(self.undo_stack.canRedo())
        redo_action.triggered.connect(self.undo_stack.redo)

        menu.addSeparator()
        new_property = menu.addAction("New Property")
        new_property.triggered.connect(self.new_property_popup)
        new_property.setShortcut(QKeySequence("Ctrl+F"))
        paste = menu.addAction("Paste")
        paste.triggered.connect(self.paste_property)
        paste.setShortcut(QKeySequence("Ctrl+V"))
        
        menu.addSeparator()
        
        collapse_all = menu.addAction("Collapse All")
        collapse_all.triggered.connect(self.collapse_all_properties)
        
        expand_all = menu.addAction("Expand All")
        expand_all.triggered.connect(self.expand_all_properties)
        
        menu.exec(self.ui.scrollArea.viewport().mapToGlobal(position))

    def set_readonly_mode(self, enabled: bool):
        """Public API to toggle read-only mode without affecting Play button."""
        self.readonly_mode = bool(enabled)
        self.apply_readonly_mode()

    def apply_readonly_mode(self):
        """Apply read-only state to all property frames, keep Play enabled."""
        try:
            # Toggle badge
            if hasattr(self, 'readonly_badge'):
                self.readonly_badge.setVisible(self.readonly_mode)
            # Toggle property frames (comments are ordinary frames now)
            for index in range(self.ui.properties_layout.count()):
                widget = self.ui.properties_layout.itemAt(index).widget()
                if isinstance(widget, SoundEventEditorPropertyFrame):
                    try:
                        widget.setEnabled(not self.readonly_mode)
                    except Exception:
                        pass
            # Play button always enabled
            try:
                self.play_button.setEnabled(True)
            except Exception:
                pass
            self._apply_toggle_dependencies()
        except Exception:
            pass

    def switch_to_item(self, item):
        """Centralized switching logic for when the active tree item changes.

        This method suppresses undo pushes while populating the properties UI
        and also updates child property frames with the active element name.

        When an undo/redo command is in progress (_restoring_from_undo is True),
        we skip this method entirely because the command itself handles the UI rebuild.
        """
        # If undo/redo is driving the tree selection, don't interfere
        if self._restoring_from_undo:
            return
        # Ensure any UI-changing logic we perform does not push undo entries
        self._undo_enabled = False
        self._populating = True        # ← block on_update mid-populate

        if item is None:
            self.properties_clear()
            self.properties_groups_hide()
            self._undo_enabled = True
            self.edited.emit()
            return

        # Try to get a dict value for the item
        try:
            data = self._data_for_item(item)
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}

        self.properties_groups_show()
        self.populate_properties(data)

        # Update per-frame context labels if frames expose set_context_element
        element_name = item.text(0)
        for idx in range(self.ui.properties_layout.count()):
            widget = self.ui.properties_layout.itemAt(idx).widget()
            try:
                if hasattr(widget, 'set_context_element'):
                    widget.set_context_element(element_name)
            except Exception:
                pass

        # Re-enable undo pushes and notify listeners
        self._populating = False       # ← clear BEFORE re-enabling undo
        self._undo_enabled = True
        self.edited.emit()

    def find_tree_item_by_element_key(self, key):
        """Public helper to find a tree item by element key (m_nElementID or name)."""
        try:
            root = self.tree.invisibleRootItem()
            for i in range(root.childCount()):
                child = root.child(i)
                data = self._data_for_item(child)
                if isinstance(key, int):
                    if isinstance(data, dict) and data.get('m_nElementID') == key:
                        return child
                else:
                    if child.text(0) == str(key):
                        return child
        except Exception:
            pass
        return None

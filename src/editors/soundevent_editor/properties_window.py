import ast
import copy

from src.editors.soundevent_editor.ui_properties_window import Ui_MainWindow
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QTimer
from src.settings.main import settings, debug
from src.editors.soundevent_editor.property.frame import SoundEventEditorPropertyFrame
from src.widgets.popup_menu.main import PopupMenu
from src.editors.soundevent_editor.objects import *
from src.widgets import ErrorInfo
from PySide6.QtWidgets import QMainWindow, QMenu, QPlainTextEdit, QApplication, QTreeWidget
from PySide6.QtGui import QKeySequence, QKeyEvent, QUndoStack, QUndoCommand, QShortcut
from PySide6.QtCore import Qt, Signal

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
        self.before = copy.deepcopy(before)
        self.after = copy.deepcopy(after)

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
                    data = child.data(0, Qt.UserRole)
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
                    item.setData(0, Qt.UserRole, copy.deepcopy(self.window.value))
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

        # Load ui file
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

        # Init variables
        self.tree = tree


        # Init context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_context_menu)

        self.ui.centralwidget.setFocusPolicy(Qt.StrongFocus)

        # Setup undo/redo keyboard shortcuts
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self.undo_stack.undo)

        redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self)
        redo_shortcut.activated.connect(self.undo_stack.redo)

        redo_shortcut_alt = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        redo_shortcut_alt.activated.connect(self.undo_stack.redo)

        # Hide properties on start
        self.properties_groups_hide()

    #=============================================================<  Load value  >==========================================================
    def load_value(self, value):
        if isinstance(value, str):
            return ast.literal_eval(value)
        elif isinstance(value, dict):
            return value
    #===========================================================<  Comment Widget  >========================================================

    def get_comment(self):
        try:
            return self.comment_widget.toPlainText()
        except:
            return ""
    def init_comment(self, value):
        self.comment_widget = QPlainTextEdit()
        self.comment_widget.setPlainText(value)
        self.ui.groupBox_2.layout().addWidget(self.comment_widget)
        self.comment_widget.textChanged.connect(self.on_update)
    def delete_comment(self):
        try:
            self.comment_widget.deleteLater()
        except:
            pass

    # =========================================================<  Properties Actions  >======================================================

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
                if key_value not in existing_items:
                    soundevent_editor_properties_filtered.append({key:value})
        # Use the filtered properties for the popup menu
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
                debug(f"Error converting string to dictionary: {e}")
                value = {}

        # Ensure value is a dictionary and has at least one item
        if isinstance(value, dict) and value:
            key, val = next(iter(value.items()))
            self.create_property(key, val)
        else:
            debug("Value is not a valid dictionary or is empty.")
        self.on_update()

    def paste_property(self):
        """Creates new property from clipboard using new_property function"""
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text()

        try:
            data = ast.literal_eval(clipboard_text)
            key = next(iter(data))
            existing_items = set()
            __properties = self.get_properties_value()
            for item in __properties:
                existing_items.add(item)
            if key not in existing_items:
                self.create_property(key, data[key])
            else:
                ErrorInfo(
                    text='It seems a property with this name already exists in the sound event. Please remove the existing property to create a new one.').exec()
        except (ValueError, SyntaxError) as e:
            ErrorInfo("Error parsing clipboard content").exec()
        self.on_update()
    #===============================================================<  Filter  >============================================================

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
    #=======================================================<  Properties widget  >=====================================================

    def properties_groups_hide(self):
        """Hide properties and show placeholder"""
        self.ui.properties_spacer.hide()
        self.ui.properties_placeholder.show()
        self.ui.CommetSeciton.hide()

        # Unset Filter
        self.ui.centralwidget.removeEventFilter(self)

        # Remove context menu connection
        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.customContextMenuRequested.disconnect(self.open_context_menu)
        
        # Keep Play button accessible in hidden state
        try:
            self.play_button.setEnabled(True)
        except Exception:
            pass
    def properties_groups_show(self):
        """Show properties and hide placeholder"""
        self.ui.properties_placeholder.hide()
        self.ui.properties_spacer.show()
        self.ui.CommetSeciton.show()

        # Set Filter
        self.ui.centralwidget.installEventFilter(self)

        # Add context menu connection
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_context_menu)

        # Apply read-only state to widgets
        self.apply_readonly_mode()
    
    def collapse_all_properties(self):
        """Collapse all property frames"""
        for index in range(self.ui.properties_layout.count()):
            widget = self.ui.properties_layout.itemAt(index).widget()
            if isinstance(widget, SoundEventEditorPropertyFrame):
                if hasattr(widget, 'ui') and hasattr(widget.ui, 'show_child'):
                    widget.ui.show_child.setChecked(False)
                    widget.show_child_action()
    
    def expand_all_properties(self):
        """Expand all property frames"""
        for index in range(self.ui.properties_layout.count()):
            widget = self.ui.properties_layout.itemAt(index).widget()
            if isinstance(widget, SoundEventEditorPropertyFrame):
                if hasattr(widget, 'ui') and hasattr(widget.ui, 'show_child'):
                    widget.ui.show_child.setChecked(True)
                    widget.show_child_action()
    def properties_clear(self):
        self._undo_enabled = False   # prevent clear from pushing a command
        for i in range(self.ui.properties_layout.count()):
            widget = self.ui.properties_layout.itemAt(i).widget()
            if isinstance(widget, SoundEventEditorPropertyFrame):
                widget.deleteLater()

        self.delete_comment()
        # keep play button and badge intact
    def populate_properties(self, _data):
        """Loading properties from given data"""
        if isinstance(_data, dict):
            # Reverse input data and use insertWidget with index 0 because in that way all widgets will be upper spacer
            debug(f"populate_properties _data \n {_data}")
            # If there is no comment in data init comment widget
            if 'comment' in _data:
                pass
            else:
                self.init_comment("")

            for item, value in _data.items():
                if item == 'comment':
                    self.init_comment(value)
                elif item == 'm_sLabel':
                    pass
                else:
                    self.create_property(item,value)

            # Ensure readonly mode applied after population
            self.apply_readonly_mode()

            # Sync self.value so callers can read it immediately after populate_properties()
            self.update_value()

            # Enable undo/redo after population so initial load doesn't pollute stack
            self._undo_enabled = True
        else:
            print(f"[SoundEventEditorProperties]: Wrong input data format. Given data: \n {_data} \n {type(_data)}")


    #=============================================================<  Property  >==========================================================
    def create_property(self, key, value):
        """Create frame widget instance"""
        widget_instance = SoundEventEditorPropertyFrame(_data={key: value}, widget_list=self.ui.properties_layout, tree=self.tree)
        widget_instance.edited.connect(self.on_update)
        widget_instance.slider_pressed.connect(self._capture_pre_commit_snapshot)
        widget_instance.committed.connect(self.on_commit)
        index = self.ui.properties_layout.count() - 1
        self.ui.properties_layout.insertWidget(index, widget_instance)

    def get_property_value(self, index):
        """Getting dict value from widget instance frame"""
        widget_instance = self.ui.properties_layout.itemAt(index).widget()
        if isinstance(widget_instance, SoundEventEditorPropertyFrame):
            value = widget_instance.value
            debug(f"Getting SoundEventEditorPropertyFrame Value: \n {value}")
            return value
        else:
            return {}
    def get_properties_value(self):
        """Getting all values from frame widget which in layout"""
        _data: dict = {}
        for index in range(self.ui.properties_layout.count()):
            if index is not None:
                try:
                    _data.update(self.get_property_value(index))
                except:
                    pass
        return _data

    def _restore_state(self, state: dict):
        """Rebuild the properties UI from a full state snapshot."""
        self._undo_enabled = False       # don't push a new command while restoring
        self.properties_clear()
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
        self._undo_enabled = True
        self.edited.emit()

    #==============================================================<  Updating  >===========================================================
    def _get_current_element_key_and_name(self):
        """Return (element_key, element_name) for the currently selected tree item."""
        element_key = None
        element_name = None
        try:
            current_item = self.tree.currentItem()
            if current_item is not None:
                element_name = current_item.text(0)
                data = current_item.data(0, Qt.UserRole)
                if isinstance(data, dict) and 'm_nElementID' in data:
                    element_key = data.get('m_nElementID')
                else:
                    element_key = element_name
        except Exception:
            pass
        return element_key, element_name

    def on_update(self):
        """Updating dict value and send signal.
        For slider drags this is called on every tick — only real-time save, NO undo push.
        Undo is pushed once in on_commit() when the slider is released.
        For discrete widgets (bool, text, combobox) the slider is never pressed so
        _slider_dragging is False and we push to the undo stack as normal.
        """
        if self._undo_enabled and not self._slider_dragging:
            before = copy.deepcopy(self.value)
            self.update_value()
            after = copy.deepcopy(self.value)
            if before != after:
                element_key, element_name = self._get_current_element_key_and_name()
                desc = f"Edit '{element_name}'" if element_name else "Edit Property"
                self.undo_stack.push(PropertyStateCommand(self, element_key, before, after, desc))
        else:
            self.update_value()
        self.edited.emit()

    def _capture_pre_commit_snapshot(self):
        """Called at sliderPressed — snapshot the value BEFORE the drag begins."""
        if self._undo_enabled:
            self._pre_commit_snapshot = copy.deepcopy(self.value)
        self._slider_dragging = True

    def on_commit(self):
        """Called at sliderReleased — push a single undo entry for the whole drag."""
        # update_value() first so self.value reflects the final slider position
        self.update_value()
        if self._undo_enabled and self._pre_commit_snapshot is not None:
            after = copy.deepcopy(self.value)
            if self._pre_commit_snapshot != after:
                element_key, element_name = self._get_current_element_key_and_name()
                desc = f"Edit '{element_name}'" if element_name else "Edit Property"
                self.undo_stack.push(PropertyStateCommand(self, element_key, self._pre_commit_snapshot, after, desc))
        self._pre_commit_snapshot = None
        # Clear the dragging flag LAST so any late valueChanged that arrives
        # during this method is still suppressed by on_update().
        self._slider_dragging = False
    def clean_comment(self, text):
        return text.replace('"', "''")
    def update_value(self):
        _data = self.get_properties_value()
        comment = self.get_comment()
        if comment != "":
            _data.update({'comment': self.clean_comment(comment)})
        self.value = _data
    #============================================================<  Context menu  >=========================================================
    def open_context_menu(self, position):
        """Layout context menu"""
        menu = QMenu()

        # Undo action
        undo_action = menu.addAction("Undo")
        undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        undo_action.setEnabled(self.undo_stack.canUndo())
        undo_action.triggered.connect(self.undo_stack.undo)

        # Redo action
        redo_action = menu.addAction("Redo")
        redo_action.setShortcut(QKeySequence("Ctrl+Y"))
        redo_action.setEnabled(self.undo_stack.canRedo())
        redo_action.triggered.connect(self.undo_stack.redo)

        menu.addSeparator()
        # New Property action
        new_property = menu.addAction("New Property")
        new_property.triggered.connect(self.new_property_popup)
        new_property.setShortcut(QKeySequence("Ctrl+F"))
        # Paste action
        paste = menu.addAction("Paste")
        paste.triggered.connect(self.paste_property)
        paste.setShortcut(QKeySequence("Ctrl+V"))
        
        menu.addSeparator()
        
        # Collapse all action
        collapse_all = menu.addAction("Collapse All")
        collapse_all.triggered.connect(self.collapse_all_properties)
        
        # Expand all action
        expand_all = menu.addAction("Expand All")
        expand_all.triggered.connect(self.expand_all_properties)
        
        menu.exec(self.ui.scrollArea.viewport().mapToGlobal(position))

    def set_readonly_mode(self, enabled: bool):
        """Public API to toggle read-only mode without affecting Play button."""
        self.readonly_mode = bool(enabled)
        self.apply_readonly_mode()

    def apply_readonly_mode(self):
        """Apply read-only state to all property frames and comment widget, keep Play enabled."""
        try:
            # Toggle badge
            if hasattr(self, 'readonly_badge'):
                self.readonly_badge.setVisible(self.readonly_mode)
            # Toggle property frames
            for index in range(self.ui.properties_layout.count()):
                widget = self.ui.properties_layout.itemAt(index).widget()
                if isinstance(widget, SoundEventEditorPropertyFrame):
                    try:
                        widget.setEnabled(not self.readonly_mode)
                    except Exception:
                        pass
            # Toggle comment widget
            try:
                if hasattr(self, 'comment_widget') and self.comment_widget is not None:
                    self.comment_widget.setReadOnly(self.readonly_mode)
            except Exception:
                pass
            # Play button always enabled
            try:
                self.play_button.setEnabled(True)
            except Exception:
                pass
        except Exception:
            pass

    # ------------------------------------------------------------------
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

        if item is None:
            self.properties_clear()
            self.properties_groups_hide()
            self._undo_enabled = True
            self.edited.emit()
            return

        # Try to get a dict value for the item
        try:
            data = item.data(0, Qt.UserRole)
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}

        # Populate UI from the item's data
        self.properties_clear()
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
        self._undo_enabled = True
        self.edited.emit()

    def find_tree_item_by_element_key(self, key):
        """Public helper to find a tree item by element key (m_nElementID or name)."""
        try:
            root = self.tree.invisibleRootItem()
            for i in range(root.childCount()):
                child = root.child(i)
                data = child.data(0, Qt.UserRole)
                if isinstance(key, int):
                    if isinstance(data, dict) and data.get('m_nElementID') == key:
                        return child
                else:
                    if child.text(0) == str(key):
                        return child
        except Exception:
            pass
        return None

import os.path
import re
import ast
from gui.common import fast_deepcopy

from PySide6.QtWidgets import (
    QMainWindow,
    QTreeWidgetItem,
    QFileDialog,
    QMenu,
    QApplication,
    QHeaderView,
    QTreeWidget,
    QSpinBox,
    QHBoxLayout,
    QLabel,
    QWidget,
    QDockWidget,
    QUndoView,
    QTabWidget,
    QPushButton,
    QSizePolicy,
)
from PySide6.QtGui import (
    QAction,
    QKeyEvent,
    QUndoStack,
    QKeySequence,
    QShortcut,
    QIcon,
)
import uuid
import traceback, ctypes
from PySide6.QtCore import Qt, QTimer, Signal, QEvent

from gui.settings.common import get_addon_dir, get_cs2_path
from gui.settings.main import get_settings_value, get_settings_bool

from keyvalues3 import kv3_to_json
from gui.editors.smartprop_editor.ui_document import Ui_MainWindow
from gui.settings.main import settings
from gui.editors.smartprop_editor.objects import (
    variables_list,
    variable_prefix,
    elements_list,
    operators_list,
    selection_criteria_list,
    filters_list
)
from gui.editors.smartprop_editor.vsmart import (
    VsmartOpen, VsmartSave, serialization_hierarchy_items, deserialize_hierarchy_item
)
from gui.editors.smartprop_editor.completion_utils import CompletionUtils
from gui.editors.smartprop_editor.props.panel import SmartPropPropertyPanel
from gui.editors.smartprop_editor.choices import AddChoice, AddVariable, AddOption
from gui.widgets.popup_menu.main import PopupMenu
from gui.editors.smartprop_editor.commands import (
    GroupElementsCommand, BulkModelImportCommand, NewFromPresetCommand, PasteItemsCommand,
    PropertySnapshotCommand, VariablesSnapshotCommand, ChoicesSnapshotCommand,
)
from gui.forms.replace_dialog.main import FindAndReplaceDialog
from gui.widgets import ErrorInfo, on_three_hierarchyitem_clicked, HierarchyItemModel, error, exception_handler
from gui.widgets.element_id import ElementIDGenerator
from gui.editors.smartprop_editor._common import (
    get_clean_class_name_value,
    get_clean_class_name,
    get_label_id_from_value
)

from gui.common import (
    enable_dark_title_bar,
    Kv3ToJson,
    JsonToKv3,
    SmartPropEditor_Preset_Path,
    set_qdock_tab_style
)
from gui.widgets.tree import HierarchyTreeWidget
from gui.editors.smartprop_editor.variables_viewport import SmartPropEditorVariableViewport
from gui.editors.smartprop_editor.manual_editor import ManualEditor

cs2_path = get_cs2_path()

# Regex for parsing diff keys like 'm_Modifiers[2].m_flAmount' or 'm_SelectionCriteria[0]'
_DIFF_KEY_RE = re.compile(r'^(m_Modifiers|m_SelectionCriteria)\[(\d+)\](?:\.(.+))?$')

#TODO Future improvement: Implement a node view for elements.
# In the node view, users will click on a node to edit its properties, triggering a context menu similar to that found in the Hammer editor (using, for example, Alt+Enter) or just show and hide properties in the viewport.
# The node view should be arranged vertically. All node-related information will be stored within the elements themselves.
# Nodes that are not connected via the Child input (i.e. isolated nodes) will be automatically attached as children of the root.

class SmartPropDocument(QMainWindow):
    _edited = Signal()
    def __init__(self, parent=None, update_title=None):
        super().__init__()
        self.parent = parent
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.settings = settings
        self.element_id_generator = ElementIDGenerator()
        self.opened_file = None
        self.update_title = update_title
        enable_dark_title_bar(self)

        self.undo_stack = QUndoStack(self)
        self.undo_stack.cleanChanged.connect(self._on_undo_clean_changed)

        # Window-level undo/redo shortcuts are handled by main window menu actions
        # (action_undo, action_redo, action_isolate) in SmartPropEditorMainWindow.

        # Guard counter: while > 0, update_tree_item_value skips pushing to the undo stack.
        # Incremented before rebuilding the properties panel during undo/redo; decremented
        # after all deferred QTimer.singleShot(0) callbacks have had a chance to fire.
        self._property_undo_guard = 0

        # Slider-drag tracking: while _slider_dragging > 0 the view is updated in
        # real-time but no undo commands are pushed.  A single command is pushed in
        # _on_slider_committed once the last active slider is released.
        self._slider_dragging = 0
        self._slider_pre_drag_data = None
        self._gizmo_pre_drag_data = None
        # Set once per gizmo drag: guards the single panel rebuild that runs when
        # a transform modifier is *created* mid-drag (see update_property_frame_values),
        # so the async rebuild can't thrash on every subsequent mouse-move.
        self._gizmo_live_rebuilt = False

        # Guard flag: while True, add_variable skips marking the document as modified
        # and emitting _edited (used during undo/redo restore).
        self._restoring_state = False

        # Flag set by PropertySnapshotCommand before it calls tree.setCurrentItem()
        # to sync the tree selection.  on_tree_current_item_changed returns early
        # when this is True so the panel is not double-rebuilt.
        self._undo_redo_rebuilding = False

        # Choices rename undo state: captured on itemDoubleClicked, consumed by itemChanged.
        self._choices_rename_old_state = None

        # Hierarchy item rename undo state: captured on itemDoubleClicked, consumed by itemChanged.
        self._hierarchy_rename_old_label = None
        self._hierarchy_rename_item = None

        # Choices widget-edit debounce (ComboboxTreeChild, VariableWidget, etc.)
        self._choices_widget_old_state = None
        self._last_committed_choices_state = None
        self._choices_widget_debounce_desc = "Edit Choices"
        self._choices_widget_debounce = QTimer()
        self._choices_widget_debounce.setSingleShot(True)
        self._choices_widget_debounce.timeout.connect(self._push_choices_widget_edit)

        self.variable_viewport = SmartPropEditorVariableViewport(self)
        self.ui.VariableDockWidgetContent.layout().addWidget(self.variable_viewport)

        # Track changes
        self._modified = False
        
        
        # Hierarchy tree wdiget setup
        self.ui.tree_hierarchy_widget.deleteLater()
        self.ui.tree_hierarchy_widget = HierarchyTreeWidget(self.undo_stack)
        self.ui.frame_2.layout().addWidget(self.ui.tree_hierarchy_widget)
        
        self.ui.tree_hierarchy_widget.setColumnCount(4)
        self.ui.tree_hierarchy_widget.setHeaderLabels(["Label", "Data", "Class", "ID"])

        self.ui.tree_hierarchy_widget.installEventFilter(self)

        self.ui.tree_hierarchy_widget.hideColumn(1)
        self.ui.tree_hierarchy_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.tree_hierarchy_widget.customContextMenuRequested.connect(self.open_hierarchy_menu)
        self.ui.tree_hierarchy_widget.currentItemChanged.connect(self.on_tree_current_item_changed)
        self.ui.tree_hierarchy_widget.itemClicked.connect(on_three_hierarchyitem_clicked)
        self.ui.tree_hierarchy_widget.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.ui.tree_hierarchy_widget.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.ui.tree_hierarchy_widget.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        self.ui.tree_hierarchy_widget.setDragEnabled(True)
        self.ui.tree_hierarchy_widget.setAcceptDrops(True)
        self.ui.tree_hierarchy_widget.setDropIndicatorShown(True)
        self.ui.tree_hierarchy_widget.setDragDropMode(QTreeWidget.InternalMove)
        self.ui.tree_hierarchy_widget.external_drop_handler = self.drop_files_into_hierarchy
        self.ui.tree_hierarchy_widget.itemDoubleClicked.connect(self._on_hierarchy_item_about_to_edit)
        self.ui.tree_hierarchy_widget.itemChanged.connect(self._on_hierarchy_item_changed)

        self.content_version_spinbox = QSpinBox()
        self.content_version_label = QLabel("Content Version")
        self.content_version_layout = QHBoxLayout()
        self.content_version_layout.setContentsMargins(0,0,0,0)
        self.content_version_layout.addWidget(self.content_version_label)
        self.content_version_layout.addWidget(self.content_version_spinbox)
        content_version_widget = QWidget()
        content_version_widget.setContentsMargins(0,0,0,0)
        content_version_widget.setLayout(self.content_version_layout)
        self.ui.frame_2.layout().addWidget(content_version_widget)

        # Choices setup
        self.ui.choices_tree_widget.hideColumn(2)
        self.ui.choices_tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.choices_tree_widget.customContextMenuRequested.connect(self.open_MenuChoices)
        self.ui.choices_tree_widget.itemDoubleClicked.connect(self._on_choices_item_about_to_edit)
        self.ui.choices_tree_widget.itemChanged.connect(self._on_choices_item_changed)

        # Groups setup
        self.properties_groups_init()

        BUTTON_H = 24
        self.ui.tree_hierarchy_search_bar_widget.setFixedHeight(BUTTON_H)
        self.ui.tree_hierarchy_search_bar_widget.setPlaceholderText("Filter...")
        self.ui.tree_hierarchy_filter_bar_widget = self.ui.tree_hierarchy_search_bar_widget

        # ── Hierarchy Top Action Bar (+ Add & Favorites Star Button) ───────────
        self.hierarchy_top_bar_layout = QHBoxLayout()
        self.hierarchy_top_bar_layout.setContentsMargins(0, 0, 0, 4)
        self.hierarchy_top_bar_layout.setSpacing(4)

        self.hierarchy_add_button = QPushButton("  Add")
        self.hierarchy_add_button.setIcon(QIcon(":/valve_common/icons/tools/common/add_sm.png"))
        self.hierarchy_add_button.setToolTip("Add SmartProp Element")
        self.hierarchy_add_button.setFixedHeight(BUTTON_H)
        self.hierarchy_add_button.setStyleSheet("""
            QPushButton {
                background-color: #2e2e2e;
                color: #e5e5e5;
                border: 2px solid #5e5e5e;
                border-radius: 0px;
                padding: 2px 8px;
                font: 580 9pt "Segoe UI";
            }
            QPushButton:hover {
                background-color: #515965;
                border-color: #787878;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #272727;
                border-color: #5e5e5e;
            }
        """)
        self.hierarchy_add_button.clicked.connect(self.add_an_element)

        self.hierarchy_preset_button = QPushButton()
        self.hierarchy_preset_button.setIcon(QIcon(":/valve_common/icons/tools/common/favorite.png"))
        self.hierarchy_preset_button.setToolTip("Favorite Elements")
        self.hierarchy_preset_button.setFixedSize(BUTTON_H, BUTTON_H)
        self.hierarchy_preset_button.setStyleSheet("""
            QPushButton {
                background-color: #2e2e2e;
                border: 2px solid #5e5e5e;
                border-radius: 0px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #515965;
                border-color: #787878;
            }
            QPushButton:pressed {
                background-color: #272727;
                border-color: #5e5e5e;
            }
        """)
        self.hierarchy_preset_button.clicked.connect(self.open_favorite_elements)

        self.hierarchy_top_bar_layout.addWidget(self.hierarchy_add_button)
        self.hierarchy_top_bar_layout.addWidget(self.hierarchy_preset_button)

        hierarchy_top_bar_widget = QWidget()
        hierarchy_top_bar_widget.setLayout(self.hierarchy_top_bar_layout)
        self.ui.frame_2.layout().insertWidget(0, hierarchy_top_bar_widget)

        self.ui.tree_hierarchy_search_bar_widget.textChanged.connect(
            lambda text: self.search_hierarchy(text, self.ui.tree_hierarchy_widget.invisibleRootItem())
        )

        # ── Dockable panels ─────────────────────────────────────────────
        # Every major panel (Property Editor, Manual Editor, 3D Viewport,
        # Hierarchy, History, Variables, Choices) is a QDockWidget, so the user
        # can freely rearrange, float, tab, or hide any of them.  The central
        # widget is collapsed to zero size so the docks fill the whole window.
        _dock_features = (
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )

        # Property Editor dock (wraps the existing PropertiesFrame).
        self.ui.PropertiesFrame.setParent(None)
        self._property_dock = QDockWidget("Property Editor", self)
        self._property_dock.setObjectName("SPE_property_dock")
        self._property_dock.setFeatures(_dock_features)
        self._property_dock.setWidget(self.ui.PropertiesFrame)

        self._manual_editor = ManualEditor(document=self)
        self._manual_dock = QDockWidget("Manual Editor", self)
        self._manual_dock.setObjectName("SPE_manual_dock")
        self._manual_dock.setFeatures(_dock_features)
        self._manual_dock.setWidget(self._manual_editor)

        # 3D Viewport dock.  The OpenGL viewport (and its GL context / VRF
        # decompilation) is expensive and can misbehave if created eagerly, so the
        # dock starts with a cheap placeholder.  The real SmartProp3DViewport is
        # built lazily the first time the dock becomes visible (see
        # _on_viewport_dock_visibility_changed / _ensure_viewport_3d).
        self._viewport_3d = None
        self._viewport_3d_loaded = False
        self._viewport_3d_failed = False
        self._viewport_3d_placeholder = QWidget()
        self._viewport_dock = QDockWidget("3D Viewport", self)
        self._viewport_dock.setObjectName("SPE_viewport_dock")
        self._viewport_dock.setFeatures(_dock_features)
        self._viewport_dock.setWidget(self._viewport_3d_placeholder)

        # Collapse the central widget: all content lives in docks now.
        _central = QWidget(self)
        _central.setObjectName("SPE_central_collapsed")
        _central.setMaximumSize(0, 0)
        self.setCentralWidget(_central)

        # Create the History dock (placed by the default-layout block below).
        self._setup_history_dock()

        self._apply_default_layout()

        # ── Continuous layout persistence ───────────────────────────────
        # The dock/viewport arrangement is saved (debounced) whenever a dock is
        # moved, floated, or resized, so the layout survives crashes and abrupt
        # termination (e.g. stopping the debugger) rather than only a clean
        # close. A short timer coalesces bursts (drag-resize) into one save.
        self._layout_docks = (
            self.ui.HierarchyDock, self.ui.ChoicesDock, self.ui.VariablesDock,
            self._property_dock, self._manual_dock, self._viewport_dock,
            self._history_dock,
        )
        self._layout_save_timer = QTimer(self)
        self._layout_save_timer.setSingleShot(True)
        self._layout_save_timer.setInterval(500)
        self._layout_save_timer.timeout.connect(self._save_user_prefs)
        for _dock in self._layout_docks:
            _dock.dockLocationChanged.connect(self._schedule_layout_save)
            _dock.topLevelChanged.connect(self._schedule_layout_save)
            _dock.installEventFilter(self)

        # Refresh a panel when its dock becomes visible (replaces tab-change).
        self._manual_dock.visibilityChanged.connect(self._on_manual_dock_visibility_changed)
        self._viewport_dock.visibilityChanged.connect(self._on_viewport_dock_visibility_changed)

        # Keep the 3D viewport following the hierarchy in real-time: whenever
        # elements are added, removed, reordered, or their data edited, the scene
        # is rebuilt (models loaded/unloaded to match).  A short debounce coalesces
        # bursts (e.g. paste, bulk import, drag-drop) into a single rebuild, and the
        # sync no-ops unless the 3D viewport dock is actually visible.
        self._viewport_3d_sync_timer = QTimer(self)
        self._viewport_3d_sync_timer.setSingleShot(True)
        self._viewport_3d_sync_timer.setInterval(50)
        self._viewport_3d_sync_timer.timeout.connect(self._sync_viewport_3d)
        tree_model = self.ui.tree_hierarchy_widget.model()
        tree_model.rowsInserted.connect(self._schedule_viewport_3d_sync)
        tree_model.rowsRemoved.connect(self._schedule_viewport_3d_sync)
        tree_model.rowsMoved.connect(self._schedule_viewport_3d_sync)
        tree_model.dataChanged.connect(self._schedule_viewport_3d_sync)
        # Variable edits (default value, variable/expression bindings, add/remove)
        # live in the variables panel, not the hierarchy tree, so they don't emit
        # the tree-model signals above.  They do emit the document's _edited signal,
        # so hook it too: a bound field (e.g. a model path bound to a variable)
        # re-reads the variable's default on the next debounced rebuild.
        self._edited.connect(self._schedule_viewport_3d_sync)

        self._did_show_restore = False
        QTimer.singleShot(0, self._restore_user_prefs)

        # Apply dock tab styling to the whole window.
        set_qdock_tab_style(self.findChildren)

        # Pre-warm pooled property widgets after first paint.
        # This pays widget setup cost at startup rather than on first node selection.
        QTimer.singleShot(500, self._prewarm_property_pools)

    def is_modified(self):
        return self._modified

    def _on_undo_clean_changed(self, clean):
        if not self._restoring_state:
            self._modified = not clean
            self._edited.emit()

    def _on_manual_dock_visibility_changed(self, visible):
        """Refresh the manual editor whenever its dock becomes visible."""
        if visible and getattr(self, '_manual_editor', None) is not None:
            self._manual_editor.refresh()

    def _on_viewport_dock_visibility_changed(self, visible):
        """Lazily build and refresh the 3D viewport when its dock becomes visible."""
        if not visible:
            return
        if self._viewport_3d is None and not self._viewport_3d_failed:
            self._ensure_viewport_3d()
        if self._viewport_3d is not None:
            self._refresh_viewport_3d()

    def _ensure_viewport_3d(self):
        """Lazily construct the OpenGL 3D viewport on first dock activation.

        Building it here (rather than at document init) keeps the GL context and
        VRF decompilation from spinning up unless the user actually shows the dock.
        """
        if self._viewport_3d is not None or self._viewport_3d_failed:
            return
        try:
            from gui.editors.smartprop_editor.viewport_3d.viewport import SmartProp3DViewport
            self._viewport_3d = SmartProp3DViewport(document=self)
            self._viewport_3d.elementClicked.connect(self._on_viewport_element_clicked)
        except Exception as e:
            # The viewport depends on OpenGL/VRF; never let it break the editor.
            print(f"[SmartProp3D] 3D Viewport unavailable: {e}")
            self._viewport_3d_failed = True
            from PySide6.QtWidgets import QVBoxLayout
            label = QLabel("3d preview for this smartprop unavalible due to using of unsupported properties and elements.")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: #929292; font-size: 11pt;")
            layout = QVBoxLayout(self._viewport_3d_placeholder)
            layout.addWidget(label)
            return

        # Swap the placeholder for the real viewport inside the dock.
        self._viewport_dock.setWidget(self._viewport_3d)
        self._viewport_3d_placeholder.deleteLater()
        self._viewport_3d_placeholder = None
        set_qdock_tab_style(self.findChildren)

    def _refresh_viewport_3d(self):
        """Rebuild the 3D scene from the hierarchy and sync the current selection.

        This is what triggers model loading / decompilation, so it only runs while
        the 3D tab is active.
        """
        if self._viewport_3d is None:
            return
        self._viewport_3d.update_viewport()
        if not self._viewport_3d_loaded:
            self._viewport_3d_loaded = True
            self._viewport_3d.fit_view()
        current = self.ui.tree_hierarchy_widget.currentItem()
        data = current.data(0, Qt.UserRole) if current is not None else None
        eid = data.get("m_nElementID", 0) if isinstance(data, dict) else 0
        self._viewport_3d.highlight_element(eid)

    def _schedule_viewport_3d_sync(self, *args):
        """Queue a debounced 3D scene rebuild after a hierarchy change.

        Connected to the tree model's row/data signals.  Cheap and safe to call
        for every mutation: it bails immediately unless the 3D viewport has been
        built and is the active tab, so nothing happens while the user works in
        the Property or Manual editors (or before the viewport is ever opened).
        """
        if getattr(self, '_viewport_3d', None) is None:
            return
        if not self._viewport_dock.isVisible():
            return
        # While the transform gizmo is being dragged the render area already
        # mirrors the change locally every frame; a full rebuild mid-drag would
        # be wasteful (and is applied once the drag settles anyway).
        try:
            if self._viewport_3d.render_area.gizmo.is_dragging:
                return
        except AttributeError:
            pass
        self._viewport_3d_sync_timer.start()

    def _sync_viewport_3d(self):
        """Rebuild the 3D scene from the hierarchy and re-apply the selection.

        This is the debounced target of _schedule_viewport_3d_sync.  update_viewport
        re-reads the tree, so newly added model elements are loaded and removed ones
        are unloaded; the current selection's highlight/gizmo is then restored.
        """
        if getattr(self, '_viewport_3d', None) is None:
            return
        if not self._viewport_dock.isVisible():
            return
        self._viewport_3d.update_viewport()
        current = self.ui.tree_hierarchy_widget.currentItem()
        data = current.data(0, Qt.UserRole) if current is not None else None
        eid = data.get("m_nElementID", 0) if isinstance(data, dict) else 0
        self._viewport_3d.highlight_element(eid)

    def _on_viewport_element_clicked(self, element_id):
        """Clicking an element in the 3D viewport selects it in the hierarchy."""
        self.select_element_by_id(element_id)

    def select_element_by_id(self, element_id):
        if element_id == 0:
            self.ui.tree_hierarchy_widget.setCurrentItem(None)
            return
        root = self.ui.tree_hierarchy_widget.invisibleRootItem()
        item = self._find_item_by_element_id(root, element_id)
        if item:
            self.ui.tree_hierarchy_widget.setCurrentItem(item)
            self.ui.tree_hierarchy_widget.scrollToItem(item)

    def _find_item_by_element_id(self, parent_item, element_id):
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            data = child.data(0, Qt.UserRole)
            if data and data.get("m_nElementID") == element_id:
                return child
            res = self._find_item_by_element_id(child, element_id)
            if res:
                return res
        return None

    def _prewarm_property_pools(self):
        """
        Create and immediately release a small number of each common pooled
        property widget type so their constructors are paid during idle time.
        """
        try:
            dummy_sa = self.variable_viewport.ui.variables_scrollArea
            dummy_eid = self.element_id_generator

            PREWARM_COUNT = 4  # keep in sync with typical progressive chunking

            from gui.editors.smartprop_editor.property.float import PropertyFloat
            from gui.editors.smartprop_editor.property.bool import PropertyBool
            from gui.editors.smartprop_editor.property.string import PropertyString
            from gui.editors.smartprop_editor.property.vector3d import PropertyVector3D
            from gui.editors.smartprop_editor.property.combobox import PropertyCombobox
            from gui.editors.smartprop_editor.property.color import PropertyColor

            # Common float: non-int with a wide slider range.
            float_kwargs = dict(
                element_id_generator=dummy_eid,
                value_class='m_flWidth',
                value=0.0,
                variables_scrollArea=dummy_sa,
                int_bool=False,
                slider_range=[0, 4096],
            )

            bool_kwargs = dict(
                value_class='m_bEnabled',
                value=False,
                variables_scrollArea=dummy_sa,
                element_id_generator=dummy_eid,
            )

            string_kwargs = dict(
                element_id_generator=dummy_eid,
                value_class='m_sModelName',
                value='',
                variables_scrollArea=dummy_sa,
                expression_bool=False,
                only_string=False,
                only_variable=False,
                force_variable=False,
                placeholder='String',
                filter_types=None,  # use PropertyString default
            )

            color_kwargs = dict(
                value_class='m_HandleColor',
                value=[255, 255, 255],
                variables_scrollArea=dummy_sa,
                element_id_generator=dummy_eid,
            )

            vector_kwargs = dict(
                value_class='m_v',
                value=[0.0, 0.0, 0.0],
                variables_scrollArea=dummy_sa,
                element_id_generator=dummy_eid,
            )

            # One common combobox: PickMode.
            combobox_kwargs = dict(
                value_class='m_nPickMode',
                value='LARGEST_FIRST',
                variables_scrollArea=dummy_sa,
                items=['LARGEST_FIRST', 'RANDOM', 'ALL_IN_ORDER'],
                filter_types=['PickMode'],
                element_id_generator=dummy_eid,
            )

            for _ in range(PREWARM_COUNT):
                for wcls, kwargs in [
                    (PropertyBool, bool_kwargs),
                    (PropertyFloat, float_kwargs),
                    (PropertyString, string_kwargs),
                    (PropertyVector3D, vector_kwargs),
                    (PropertyCombobox, combobox_kwargs),
                    (PropertyColor, color_kwargs),
                ]:
                    w = wcls.acquire(**kwargs)
                    wcls.release(w)
        except Exception:
            # Prewarm must never prevent the editor from loading.
            pass

    # [Properties groups]
    def properties_groups_init(self):
        self.smartprop_property_panel = SmartPropPropertyPanel(
            document=self, parent=self
        )
        self.ui.properties_layout.addWidget(self.smartprop_property_panel)
        self.property_panel = self.smartprop_property_panel

        self.ui.properties_placeholder.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ui.properties_placeholder.setAlignment(Qt.AlignCenter)
        if hasattr(self.ui, "properties_spacer"):
            self.ui.properties_spacer.hide()

        self.properties_groups_hide()

    def properties_groups_hide(self):
        self.ui.properties_placeholder.show()
        if hasattr(self.ui, "properties_spacer"):
            self.ui.properties_spacer.hide()
        if hasattr(self, "smartprop_property_panel"):
            self.smartprop_property_panel.hide()

    def properties_groups_show(self):
        self.ui.properties_placeholder.hide()
        if hasattr(self.ui, "properties_spacer"):
            self.ui.properties_spacer.hide()
        if hasattr(self, "smartprop_property_panel"):
            self.smartprop_property_panel.show()

    # [Tree Hierarchy updating]
    def on_tree_current_item_changed(self, current_item, previous_item):
        if getattr(self, "_undo_redo_rebuilding", False):
            return

        # Refresh the manual editor if its dock is currently visible.
        if (getattr(self, '_manual_dock', None) is not None
                and getattr(self, '_manual_editor', None) is not None
                and self._manual_dock.isVisible()):
            self._manual_editor.refresh()

        # Mirror the tree selection into the 3D viewport highlight when it is visible.
        if (getattr(self, '_viewport_3d', None) is not None
                and getattr(self, '_viewport_dock', None) is not None
                and self._viewport_dock.isVisible()):
            data = current_item.data(0, Qt.UserRole) if current_item is not None else None
            eid = data.get("m_nElementID", 0) if isinstance(data, dict) else 0
            self._viewport_3d.highlight_element(eid)

        if current_item is not None:
            self.properties_groups_show()
        else:
            self.properties_groups_hide()

        if hasattr(self, "smartprop_property_panel"):
            self.smartprop_property_panel.set_element(current_item)

        # Legacy _get_property_frame() population removed (P7).
        # Property panel is now handled entirely by SmartPropPropertyPanel above.

    # [Event Filter]
    def _schedule_layout_save(self, *args):
        """Debounced trigger to persist the dock layout after it changes."""
        timer = getattr(self, '_layout_save_timer', None)
        if timer is not None:
            timer.start()

    def eventFilter(self, source, event):
        # A dock being resized (splitter drag or window resize) or moved is a
        # layout change worth persisting; schedule a debounced save.
        if event.type() in (QEvent.Resize, QEvent.Move):
            docks = getattr(self, '_layout_docks', None)
            if docks and source in docks:
                self._schedule_layout_save()
        if event.type() == QKeyEvent.KeyPress:
            if source == self.ui.tree_hierarchy_widget:
                if event.matches(QKeySequence.Copy):
                    self.copy_item(self.ui.tree_hierarchy_widget)
                    return True
                if event.matches(QKeySequence.Cut):
                    self.cut_item(self.ui.tree_hierarchy_widget)
                    return True
                if event.matches(QKeySequence.Paste):
                    self.paste_item(self.ui.tree_hierarchy_widget)
                    return True
                if event.matches(QKeySequence.Delete):
                    self.ui.tree_hierarchy_widget.DeleteSelectedItems()
                    return True
                if event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier) and event.key() == Qt.Key_V:
                    self.new_item_with_replacement(QApplication.clipboard().text())
                    return True
                if event.modifiers() == (Qt.ControlModifier) and event.key() == Qt.Key_G:
                    self.undo_stack.push(GroupElementsCommand(self.ui.tree_hierarchy_widget))
                    return True
                if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_D:
                    self.ui.tree_hierarchy_widget.DuplicateSelectedItems(self.element_id_generator)
                    return True
                if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_H:
                    self.toggle_isolation()
                    return True
                if event.matches(QKeySequence.Undo):
                    self.undo_stack.undo()
                    return True
                is_redo = event.matches(QKeySequence.Redo) or (
                    event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier) and event.key() == Qt.Key_Z
                )
                if is_redo:
                    self.undo_stack.redo()
                    return True
                if source.viewport().underMouse():
                    if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
                        self.add_an_element()
                        return True
        return super().eventFilter(source, event)

    # [Tree Widget Hierarchy New Element]
    def _safe_parent_item(self, candidate):
        """Model/SmartProp elements are leaf-only; redirect to beside them, not inside them."""
        if candidate is not None and not (candidate.flags() & Qt.ItemIsDropEnabled):
            return candidate.parent() or self.ui.tree_hierarchy_widget.invisibleRootItem()
        return candidate

    def add_preset(self):
        from gui.common import get_all_presets, SmartPropEditor_Internal_Preset_Path, SmartPropEditor_User_Preset_Path
        presets = get_all_presets(SmartPropEditor_Internal_Preset_Path, SmartPropEditor_User_Preset_Path)
        self.popup_menu = PopupMenu(presets, add_once=False, window_name="SPE_elements_presets")
        self.popup_menu.add_property_signal.connect(lambda name, value: self.load_preset(name, value))
        self.popup_menu.show()

    def file_deserialization(self, __data: dict, to_parent: bool = False):
        def populate_tree(data, parent=None):
            if parent is None:
                parent = self.ui.tree_hierarchy_widget.invisibleRootItem()
            if isinstance(data, dict):
                for key, value in data.items():
                    if key == "m_Children" and isinstance(value, list):
                        for item in value:
                            item_class = item.get("_class")
                            value_dict = item.copy()
                            value_dict.pop("m_Children", None)
                            self.element_id_generator.update_value(value_dict)
                            value_dict = self.element_id_generator.update_child_value(value_dict, force=True)
                            child_item = HierarchyItemModel(
                                _name=value_dict.get("m_sLabel", get_label_id_from_value(value_dict)),
                                _data=value_dict,
                                _class=get_clean_class_name(item_class),
                                _id=self.element_id_generator.get_key(value_dict)
                            )
                            if to_parent and parent.parent() is not None:
                                parent.parent().addChild(child_item)
                            elif to_parent:
                                self.ui.tree_hierarchy_widget.invisibleRootItem().addChild(child_item)
                            else:
                                parent.addChild(child_item)
                            populate_tree(item, child_item)

        # Extracted populate_choices and populate_variables to class methods

        if self.ui.tree_hierarchy_widget.currentItem() is None:
            parent_item = self.ui.tree_hierarchy_widget.invisibleRootItem()
        else:
            parent_item = self.ui.tree_hierarchy_widget.currentItem()

        populate_tree(__data, parent_item)
        self._populate_variables(__data.get("m_Variables"))
        self._populate_choices(__data.get("m_Choices", None))
        self._connect_choices_widget_signals()

    def load_preset(self, name: str = None, path: str = None):
        with open(path, "r") as file:
            __data = file.read()
        __data = Kv3ToJson(self.fix_format(__data))

        old_variables = self._snapshot_variables()
        old_choices = self._snapshot_choices()

        parent = (
            self.ui.tree_hierarchy_widget.currentItem()
            or self.ui.tree_hierarchy_widget.invisibleRootItem()
        )
        
        # 1. Create items
        items = [
            deserialize_hierarchy_item(child, self.element_id_generator)
            for child in __data.get("m_Children", [])
        ]
        
        # 2. Add items to tree (Manually, so we can capture full new state before pushing command)
        for item in items:
            parent.addChild(item)
            parent.setExpanded(True)
            
        # 3. Add variables and choices (variables first so choices can resolve types and defaults)
        self._populate_variables(__data.get("m_Variables"))
        self._populate_choices(__data.get("m_Choices", None))
        self._connect_choices_widget_signals()
        
        new_variables = self._snapshot_variables()
        new_choices = self._snapshot_choices()

        if items or new_variables != old_variables or new_choices != old_choices:
            from gui.editors.smartprop_editor.commands import NewFromPresetCommand
            self.undo_stack.push(NewFromPresetCommand(
                self, parent, items, 
                old_variables, new_variables, 
                old_choices, new_choices
            ))
            self._modified = True
            self._edited.emit()
            
            if items:
                self.ui.tree_hierarchy_widget.clearSelection()
                items[0].setSelected(True)
                self.ui.tree_hierarchy_widget.scrollToItem(items[0])

    def _populate_choices(self, data):
        if data is None:
            return
        for choice in data:
            name = (
                choice.get("m_Name") or
                choice.get("m_sChoiceName") or
                choice.get("m_sName") or
                "Choice"
            )
            default = choice.get("m_DefaultOption", None)
            options = choice.get("m_Options", []) or []
            new_choice = AddChoice(
                name=name,
                tree=self.ui.choices_tree_widget,
                default=default,
                variables_scrollArea=self.variable_viewport.ui.variables_scrollArea
            ).item
            if options:
                for option in options:
                    opt_name = (
                        option.get("m_Name") or
                        option.get("m_sName") or
                        option.get("m_sOptionName") or
                        "Option"
                    )
                    option_item = AddOption(parent=new_choice, name=opt_name).item
                    variables_list_ = option.get("m_VariableValues", []) or []
                    for variable in variables_list_:
                        target_name = (
                            variable.get("m_TargetName") or
                            variable.get("m_sVariableName") or
                            variable.get("m_VariableName") or
                            variable.get("m_Name") or
                            ""
                        )
                        target_type = (
                            variable.get("m_DataType") or
                            variable.get("m_sDataType") or
                            variable.get("m_Type") or
                            ""
                        )
                        target_val = variable.get("m_Value", variable.get("m_sValue", ""))
                        AddVariable(
                            element_id_generator=self.element_id_generator,
                            parent=option_item,
                            variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
                            name=target_name,
                            type=target_type,
                            value=target_val
                        )

    def _populate_variables(self, data):
        if isinstance(data, list):
            for item in data:
                var_class = (item.get("_class", "")).replace(variable_prefix, "")
                var_name = item.get("m_VariableName", None)
                
                cat_name = item.get("m_Hammer5ToolsCategoryName")
                import re
                is_category = False
                is_start = False
                if var_name:
                    if re.match(r"hammer5tools_category_([a-z0-9]+)_(start|end)", var_name) or re.match(r"hammer5tools_category_(.*)_category_(.*)_(start|end)", var_name):
                        is_category = True
                        is_start = var_name.endswith('_start')
                
                if is_category and cat_name is not None:
                    if is_start:
                        var_display_name = f"---------- {cat_name} ----------"
                    else:
                        var_display_name = "                                             "
                else:
                    var_display_name = item.get("m_DisplayName", None)
                    if var_display_name is None:
                        var_display_name = item.get("m_sCommentary", None)
                    if var_display_name is None:
                        var_display_name = item.get("m_ParameterName", None)
                        
                var_visible_in_editor = bool(item.get("m_bExposeAsParameter", None))
                var_value = {
                    "default": item.get("m_DefaultValue", None),
                    "model": item.get("m_sModelName", None),
                    "m_nElementID": item.get("m_nElementID", None),
                    'm_HideExpression': item.get("m_HideExpression", None),
                    'm_ReadOnlyExpression': item.get("m_ReadOnlyExpression", None)
                }
                if var_class == "Float":
                    var_value.update({
                        "min": item.get("m_flParamaterMinValue", None),
                        "max": item.get("m_flParamaterMaxValue", None)
                    })
                elif var_class == "Int":
                    var_value.update({
                        "min": item.get("m_nParamaterMinValue", None),
                        "max": item.get("m_nParamaterMaxValue", None)
                    })
                else:
                    var_value.update({"min": None, "max": None})

                existing_variables = self.get_variables(layout=self.variable_viewport.ui.variables_scrollArea, only_names=True)
                variable_exists = False
                for index, variable in existing_variables.items():
                    name_ = variable[0]
                    if name_ == var_name:
                        variable_exists = True
                        break

                if not variable_exists:
                    if is_category:
                        self.add_category(
                            name=var_name,
                            var_visible_in_editor=var_visible_in_editor,
                            var_display_name=var_display_name
                        )
                    else:
                        self.add_variable(
                            name=var_name,
                            var_value=var_value,
                            var_visible_in_editor=var_visible_in_editor,
                            var_class=var_class,
                            var_display_name=var_display_name
                        )

    def add_an_element(self):
        hide_experimental = get_settings_bool('SmartPropEditor', 'hide_experimental', True)
        visible_list = [
            item for item in elements_list
            if not (hide_experimental and any(v.get('_WARN_NOT_VERIFIED') for v in item.values() if isinstance(v, dict)))
        ]
        self.popup_menu = PopupMenu(visible_list, add_once=False, window_name="SPE_elements")
        self.popup_menu.add_property_signal.connect(lambda name, value: self.new_element(name, value))
        self.popup_menu.show()

    def open_favorite_elements(self):
        from gui.settings.main import get_settings_value
        saved = get_settings_value('Bookmarks', 'SPE_elements')
        bookmarked_items = set(saved.split(',')) if saved else set()

        fav_elements = [
            item for item in elements_list
            if any(k in bookmarked_items for k in item.keys())
        ]
        hide_experimental = get_settings_bool('SmartPropEditor', 'hide_experimental', True)
        if hide_experimental:
            fav_elements = [
                item for item in fav_elements
                if not any(v.get('_WARN_NOT_VERIFIED') for v in item.values() if isinstance(v, dict))
            ]

        if not fav_elements:
            fav_elements = [
                item for item in elements_list
                if not (hide_experimental and any(v.get('_WARN_NOT_VERIFIED') for v in item.values() if isinstance(v, dict)))
            ]

        self.popup_menu = PopupMenu(fav_elements, add_once=False, window_name="SPE_elements")
        self.popup_menu.add_property_signal.connect(lambda name, value: self.new_element(name, value))
        self.popup_menu.show()

    def new_element(self, element_class, element_value):
        element_value = ast.literal_eval(element_value)
        self.element_id_generator.update_value(element_value)
        new_element_item = HierarchyItemModel(
            _name=get_label_id_from_value(element_value),
            _data=element_value,
            _class=get_clean_class_name_value(element_value),
            _id=self.element_id_generator.get_key(element_value)
        )
        self.ui.tree_hierarchy_widget.AddItem(new_element_item)

    # [Properties operator]
    def _append_component(self, container_key, component_value, force_new_id=False):
        """Append a modifier/selection-criteria dict to the current item and commit.

        Mirrors ComponentList._add_component_dict (props/components.py) so both
        the toolbar Add/Paste actions and the Section-1 "+" button produce
        identically-shaped data + undo history.
        """
        item = self.ui.tree_hierarchy_widget.currentItem()
        if item is None:
            return
        if not isinstance(component_value, dict):
            component_value = ast.literal_eval(component_value)
        component_value = dict(component_value)
        component_value.setdefault('m_bEnabled', True)
        self.element_id_generator.update_value(component_value, force=force_new_id)

        old_data = fast_deepcopy(item.data(0, Qt.UserRole))
        new_data = fast_deepcopy(old_data)
        new_data.setdefault(container_key, []).append(component_value)
        item.setData(0, Qt.UserRole, new_data)

        self._modified = True
        self._edited.emit()
        self.undo_stack.push(PropertySnapshotCommand(self, item, old_data, new_data))
        self.smartprop_property_panel.set_element(item)

    def new_operator(self, element_class, element_value):
        self._append_component("m_Modifiers", element_value)

    def add_an_operator(self):
        """
        Combines operators and filters, determines which classes already exist,
        excludes duplicates unless an item is forced, and then displays a popup
        menu to add new operators.
        """
        operators_and_filters = operators_list + filters_list
        elements_in_popupmenu = []
        exists_classes = []
        force_items_names = ["SetVariable", "SaveState", 'Translate', 'Rotate']
        force_items = []
        for item in operators_and_filters:
            for key in item.keys():
                if key in force_items_names:
                    force_items.append(item)
        current_item = self.ui.tree_hierarchy_widget.currentItem()
        current_data = current_item.data(0, Qt.UserRole) if current_item is not None else None
        if isinstance(current_data, dict):
            for mod in current_data.get("m_Modifiers") or []:
                if isinstance(mod, dict):
                    exists_classes.append(mod.get("_class", "").split('_', 1)[-1])
        for class_name in force_items_names:
            if class_name in exists_classes:
                exists_classes.remove(class_name)
        for item in operators_and_filters:
            for key in item.keys():
                if key not in exists_classes:
                    if item not in elements_in_popupmenu:
                        elements_in_popupmenu.append(item)
        for item in force_items:
            if item not in elements_in_popupmenu:
                elements_in_popupmenu.append(item)
        hide_experimental = get_settings_bool('SmartPropEditor', 'hide_experimental', True)
        if hide_experimental:
            elements_in_popupmenu = [
                item for item in elements_in_popupmenu
                if not any(v.get('_WARN_NOT_VERIFIED') for v in item.values() if isinstance(v, dict))
            ]
        self.popup_menu = PopupMenu(
            elements_in_popupmenu,
            add_once=True,
            window_name="SPE_operators",
            ignore_list=force_items_names
        )
        self.popup_menu.add_property_signal.connect(lambda name, value: self.new_operator(name, value))
        self.popup_menu.show()

    def paste_operator(self):
        clipboard_text = QApplication.clipboard().text()
        clipboard_data = clipboard_text.split(";;")
        if clipboard_data[0] != "hammer5tools:smartprop_editor_property":
            print("Clipboard data format is not valid.")
            return
        data = ast.literal_eval(clipboard_data[2])
        self._append_component("m_Modifiers", data, force_new_id=True)

    # [Properties Selection Criteria]
    def add_a_selection_criteria(self):
        elements_in_popupmenu = []
        exists_classes = []
        force_items_names = []
        force_items = []

        for item in selection_criteria_list:
            for key in item.keys():
                if key in force_items_names:
                    force_items.append(item)

        current_item = self.ui.tree_hierarchy_widget.currentItem()
        current_data = current_item.data(0, Qt.UserRole) if current_item is not None else None
        if isinstance(current_data, dict):
            for crit in current_data.get("m_SelectionCriteria") or []:
                if isinstance(crit, dict):
                    exists_classes.append(crit.get("_class", "").split('_', 1)[-1])

        for class_name in force_items_names:
            if class_name in exists_classes:
                exists_classes.remove(class_name)

        for item in selection_criteria_list:
            for key, value in item.items():
                if key not in exists_classes:
                    if item not in elements_in_popupmenu:
                        elements_in_popupmenu.append(item)

        for item in force_items:
            if item not in elements_in_popupmenu:
                elements_in_popupmenu.append(item)

        hide_experimental = get_settings_bool('SmartPropEditor', 'hide_experimental', True)
        if hide_experimental:
            elements_in_popupmenu = [
                item for item in elements_in_popupmenu
                if not any(v.get('_WARN_NOT_VERIFIED') for v in item.values() if isinstance(v, dict))
            ]

        self.popup_menu = PopupMenu(
            elements_in_popupmenu,
            add_once=True,
            window_name="SPE_selection_criteria",
            ignore_list=force_items_names
        )
        self.popup_menu.add_property_signal.connect(lambda name, value: self.new_selection_criteria(name, value))
        self.popup_menu.show()

    def new_selection_criteria(self, element_class, element_value):
        self._append_component("m_SelectionCriteria", element_value)

    def paste_selection_criteria(self):
        clipboard_text = QApplication.clipboard().text()
        clipboard_data = clipboard_text.split(";;")
        if clipboard_data[0] != "hammer5tools:smartprop_editor_property":
            print("Clipboard data format is not valid.")
            return
        data = ast.literal_eval(clipboard_data[2])
        self._append_component("m_SelectionCriteria", data, force_new_id=True)

    # [Open File]
    @exception_handler
    def open_file(self, filename):
        # Suppress property snapshot commands while the file is being loaded.
        # The guard is released in the finally block so that @exception_handler
        # catching a mid-load exception can never leave the guard permanently
        # raised (which would permanently block all future property undo entries).
        self._property_undo_guard += 1
        self._restoring_state = True
        try:
            self.opened_file = filename
            vsmart_instance = VsmartOpen(
                element_id_generator= self.element_id_generator,
                filename=filename,
                tree=self.ui.tree_hierarchy_widget,
                choices_tree=self.ui.choices_tree_widget,
                variables_scrollArea=self.variable_viewport.ui.variables_scrollArea
            )
            variables = vsmart_instance.variables
            cv = vsmart_instance.content_version
            try:
                self.content_version_spinbox.setValue(int(cv) if cv not in (None, "") else 0)
            except (ValueError, TypeError):
                self.content_version_spinbox.setValue(0)

            # Clear existing variables
            index = 0
            while index < self.variable_viewport.ui.variables_scrollArea.count() - 1:
                item = self.variable_viewport.ui.variables_scrollArea.takeAt(index)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    index += 1

            # Rebuild variables
            if isinstance(variables, list):
                import re
                for item in variables:
                    var_class = (item["_class"]).replace(variable_prefix, "")
                    var_name = item.get("m_VariableName", None)
                    var_visible_in_editor = bool(item.get("m_bExposeAsParameter", None))

                    # Detect category markers
                    is_category = False
                    is_start = False
                    if var_name:
                        if re.match(r"hammer5tools_category_([a-z0-9]+)_(start|end)", var_name) or re.match(r"hammer5tools_category_(.*)_category_(.*)_(start|end)", var_name):
                            is_category = True
                            is_start = var_name.endswith('_start')

                    if is_category:
                        cat_name = item.get("m_Hammer5ToolsCategoryName")
                        if cat_name is not None:
                            if is_start:
                                var_display_name = f"---------- {cat_name} ----------"
                            else:
                                var_display_name = "                                             "
                        else:
                            var_display_name = item.get("m_DisplayName", None)
                            if var_display_name is None:
                                var_display_name = item.get("m_sCommentary", None)
                            if var_display_name is None:
                                var_display_name = item.get("m_ParameterName", None)

                        # Still register element ID
                        element_id = item.get("m_nElementID", None)
                        if element_id is not None:
                            self.element_id_generator.add_id(element_id)

                        self.add_category(
                            name=var_name,
                            var_visible_in_editor=var_visible_in_editor,
                            var_display_name=var_display_name
                        )
                    else:
                        var_display_name = item.get("m_DisplayName", None)
                        if var_display_name is None:
                            var_display_name = item.get("m_sCommentary", None)
                        if var_display_name is None:
                            var_display_name = item.get("m_ParameterName", None)

                        var_value = {
                            "default": item.get("m_DefaultValue", None),
                            "model": item.get("m_sModelName", None),
                            "m_nElementID": item.get("m_nElementID", None),
                            'm_HideExpression': item.get("m_HideExpression", None),
                            'm_ReadOnlyExpression': item.get("m_ReadOnlyExpression", None)
                        }
                        element_id = var_value['m_nElementID']
                        if element_id is not None:
                            self.element_id_generator.add_id(element_id)
                        else:
                            var_value = self.element_id_generator.update_value(var_value)
                        if var_class == "Float":
                            var_value.update({
                                "min": item.get("m_flParamaterMinValue", None),
                                "max": item.get("m_flParamaterMaxValue", None)
                            })
                        elif var_class == "Int":
                            var_value.update({
                                "min": item.get("m_nParamaterMinValue", None),
                                "max": item.get("m_nParamaterMaxValue", None)
                            })
                        else:
                            var_value.update({"min": None, "max": None})
                        self.add_variable(
                            name=var_name,
                            var_value=var_value,
                            var_visible_in_editor=var_visible_in_editor,
                            var_class=var_class,
                            var_display_name=var_display_name
                        )

            # Populate choices after variables layout has been built
            self.ui.choices_tree_widget.clear()
            self._populate_choices(getattr(vsmart_instance, "raw_choices", None))
            self._connect_choices_widget_signals()
            self._last_committed_choices_state = self._snapshot_choices()

            self._modified = False
        finally:
            # Always release the guard and clear the stack, even if an exception
            # occurred mid-load.  Both are deferred so all singleShot(0)
            # _finish_init callbacks that were queued during file load fire first.
            self._restoring_state = False
            QTimer.singleShot(0, self._dec_property_undo_guard)
            QTimer.singleShot(0, self.undo_stack.clear)
            QTimer.singleShot(0, self._edited.emit)

    # [Save File]
    def build_smartprop_document(self):
        """Return the current editor state as a JSON-compatible SmartProp document."""
        self._flush_choices_widget_if_pending()
        serializer = VsmartSave(
            filename="",
            tree=self.ui.tree_hierarchy_widget,
            choices_tree=self.ui.choices_tree_widget,
            variables_layout=self.variable_viewport.ui.variables_scrollArea,
            content_version=self.content_version_spinbox.value(),
            write_file=False,
        )
        return serializer.document_data

    def save_file(self, external=False):
        if external:
            if not self.opened_file:
                filename = None
            else:
                filename = self.opened_file
        else:
            if self.opened_file:
                filename = self.opened_file
                external = False
            else:
                filename = None
                external = True

        if external:
            start_dir = ""
            if hasattr(self, "parent") and self.parent and hasattr(self.parent, "mini_explorer"):
                try:
                    folder = self.parent.mini_explorer.get_current_folder(True)
                    if folder and os.path.exists(folder):
                        start_dir = folder
                except Exception:
                    pass
            if not start_dir:
                try:
                    from gui.settings.common import get_addon_name
                    from gui.common import get_cs2_path
                    cs2_path = get_cs2_path()
                    addon_name = get_addon_name()
                    if cs2_path and addon_name:
                        smartprops_dir = os.path.join(cs2_path, "content", "csgo_addons", addon_name, "smartprops")
                        addon_dir = os.path.join(cs2_path, "content", "csgo_addons", addon_name)
                        if os.path.exists(smartprops_dir):
                            start_dir = smartprops_dir
                        elif os.path.exists(addon_dir):
                            start_dir = addon_dir
                except Exception:
                    pass

            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save File",
                start_dir,
                "VSmart Files (*.vsmart);;All Files (*)"
            )
            if not filename:
                return False

        self._flush_choices_widget_if_pending()
        content_version = self.content_version_spinbox.value()
        if filename:
            try:
                VsmartSaveInstance = VsmartSave(
                    filename=filename,
                    tree=self.ui.tree_hierarchy_widget,
                    choices_tree=self.ui.choices_tree_widget,
                    variables_layout=self.variable_viewport.ui.variables_scrollArea,
                    content_version=content_version
                )
            except Exception as e:
                error_message = f"An error while saving Vsmart File: {e}"
                error_details = traceback.format_exc()
                error(error_message)

                # Ensure the dialog is executed in the main thread
                app = QApplication.instance()
                if app is not None:
                    ErrorInfo(text=error_message, details=error_details).exec_()
                else:
                    print("Error: QApplication instance is not available.")
                return False

            self.opened_file = VsmartSaveInstance.filename
            if self.update_title:
                self.update_title("saved", filename)
            # Mark document as unmodified after saving
            self._modified = False
            self.undo_stack.setClean()
            self._edited.emit()
            return True
        return False

    # [Choices Context Menu]
    def open_MenuChoices(self, position):
        menu = QMenu()
        item = self.ui.choices_tree_widget.itemAt(position)
        
        # Pin callbacks to 'self' to avoid PySide6 Garbage Collector silently dropping lambdas
        self._active_choices_menu_callbacks = []
        
        def add_menu_action(label, op_name, callback):
            action = menu.addAction(label)
            
            def wrapper(*args):
                self._choices_op_with_undo(op_name, callback)
                
            action.triggered.connect(wrapper)
            self._active_choices_menu_callbacks.append(wrapper)
            return action

        add_menu_action(
            "Add Choice", "Choice Add",
            lambda: AddChoice(
                tree=self.ui.choices_tree_widget,
                variables_scrollArea=self.variable_viewport.ui.variables_scrollArea
            )
        )

        if item:
            if item.text(2) == "choice":
                add_menu_action(
                    "Add Option", "Choice option add",
                    lambda: AddOption(parent=item, name="Option")
                )
            elif item.text(2) == "option":
                add_menu_action(
                    "Add Variable", "Choice Option Variable Add",
                    lambda: AddVariable(
                        parent=item,
                        variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
                        name="default",
                        value="",
                        type="",
                        element_id_generator=self.element_id_generator
                    )
                )

        menu.addSection("")
        add_menu_action("Move Up", "Move Up", lambda: self.move_choice_tree_item(-1))
        add_menu_action("Move Down", "Move Down", lambda: self.move_choice_tree_item(1))
        
        menu.addSection("")

        def get_remove_desc(item_desc):
            if not item_desc: return "Choice Remove"
            t = item_desc.text(2)
            if t == "choice": return "Choice Remove"
            elif t == "option": return "Choice Option remove"
            elif t == "variable": return "Choice Option Variable Remove"
            return "Choice Remove"

        add_menu_action(
            "Remove", get_remove_desc(item),
            lambda: self.remove_tree_item(self.ui.choices_tree_widget)
        )

        menu.exec(self.ui.choices_tree_widget.viewport().mapToGlobal(position))

    # [Variables Actions]
    def add_variable(
            self,
            name,
            var_class,
            var_value,
            var_visible_in_editor,
            var_display_name,
            index: int = None,
            expanded: bool = False
    ):
        self.variable_viewport.add_variable(name, var_class, var_value, var_visible_in_editor, var_display_name, index, expanded)
        if not self._restoring_state:
            self._modified = True
            self._edited.emit()

    def add_category(self, name, var_visible_in_editor, var_display_name, index: int = None, expanded: bool = True):
        self.variable_viewport.add_category(name, var_visible_in_editor, var_display_name, index, expanded)
        if not self._restoring_state:
            self._modified = True
            self._edited.emit()

    def duplicate_variable(self, __data, __index):
        self.variable_viewport.duplicate_variable(__data, __index)

    def add_new_variable(self):
        self.variable_viewport.add_new_variable()

    # [Variables Other]

    def get_variables(self, layout, only_names=False):
        if only_names:
            data_out = {}
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if widget:
                    item_ = {i: [widget.name, widget.var_class, widget.var_display_name]}
                    data_out.update(item_)
            return data_out
        else:
            data_out = {}
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if widget:
                    item_ = {
                        i: [
                            widget.name,
                            widget.var_class,
                            widget.var_value,
                            widget.var_visible_in_editor,
                            widget.var_display_name
                        ]
                    }
                    data_out.update(item_)
            return data_out

    # [Tree widget hierarchy filter]
    def search_hierarchy(self, filter_text, parent_item):
        self.filter_tree_item(parent_item, filter_text.lower(), True)

    def filter_tree_item(self, item, filter_text, is_root=False):
        if not isinstance(item, QTreeWidgetItem):
            return False

        item_text = item.text(0).lower()
        item_visible = filter_text in item_text

        if is_root:
            item.setHidden(False)
        else:
            item.setHidden(not item_visible)

        any_child_visible = False

        for i in range(item.childCount()):
            child_item = item.child(i)
            child_visible = self.filter_tree_item(child_item, filter_text, False)
            if child_visible:
                any_child_visible = True

        if any_child_visible:
            item.setHidden(False)
            item.setExpanded(True)

        return item_visible or any_child_visible

    def drop_files_into_hierarchy(self, paths, target_item):
        """Create elements for .vmdl / .vsmart files dropped onto the hierarchy from the explorer."""
        from gui.settings.main import debug
        addon_path = get_addon_dir()
        items = []
        for path in paths:
            ext = os.path.splitext(path)[1].lower()
            if ext not in ('.vmdl', '.vsmart'):
                continue
            try:
                rel_path = os.path.relpath(path, addon_path).replace(os.path.sep, '/')
            except ValueError:
                continue
            if rel_path.startswith('..'):
                debug(f'Dropped file is outside the addon, skipping: {path}')
                continue
            base_name = os.path.splitext(os.path.basename(path))[0]
            if ext == '.vsmart':
                element = {
                    '_class': 'CSmartPropElement_SmartProp',
                    'm_sSmartProp': rel_path,
                    'm_Modifiers': [],
                    'm_SelectionCriteria': []
                }
            else:
                element = {
                    '_class': 'CSmartPropElement_Model',
                    'm_sModelName': rel_path,
                    'm_Modifiers': [],
                    'm_SelectionCriteria': []
                }
            element['m_sLabel'] = base_name
            self.element_id_generator.update_value(element)
            items.append(HierarchyItemModel(
                _name=base_name,
                _data=element,
                _class=get_clean_class_name_value(element),
                _id=self.element_id_generator.get_key(element)
            ))
        if not items:
            return
        parent_item = self._safe_parent_item(target_item) or self.ui.tree_hierarchy_widget.invisibleRootItem()
        command = BulkModelImportCommand(self, parent_item, items)
        command.setText("Drop Files")
        self.undo_stack.push(command)
        self._modified = True
        self._edited.emit()

    def open_bulk_model_importer(self):
        from gui.editors.smartprop_editor.actions.bulk_model_importer import BulkModelImporterDialog
        from gui.editors.smartprop_editor._common import get_clean_class_name_value, get_label_id_from_value
        from gui.widgets import HierarchyItemModel
        current_folder = ""
        if hasattr(self, "parent") and self.parent and hasattr(self.parent, "mini_explorer"):
            try:
                current_folder = self.parent.mini_explorer.get_current_folder(True) or ""
            except Exception:
                pass
        dialog = BulkModelImporterDialog(self, current_folder=current_folder)
        def on_accept(files, create_ref, ref_index):
            addon_path = get_addon_dir()
            ref_id = None
            parent_item = self.ui.tree_hierarchy_widget.currentItem()
            if parent_item is None:
                parent_item = self.ui.tree_hierarchy_widget.invisibleRootItem()
            else:
                parent_item = self._safe_parent_item(parent_item)
            items = []
            for index, file_path in enumerate(files):
                rel_path = os.path.relpath(file_path, addon_path).replace(os.path.sep, '/')
                base_name, _ = os.path.splitext(os.path.basename(file_path))
                element_dict = {
                    "_class": "CSmartPropElement_Model",
                    "m_sModelName": rel_path,
                    "m_Modifiers": [],
                    "m_SelectionCriteria": []
                }
                is_reference = create_ref and (index == ref_index)
                if is_reference:
                    element_dict["m_sLabel"] = f"{base_name}_REF"
                else:
                    element_dict["m_sLabel"] = base_name
                    if create_ref and ref_id is not None:
                        element_dict["m_nReferenceID"] = ref_id
                        element_dict["m_sReferenceObjectID"] = str(uuid.uuid4())
                element_value = fast_deepcopy(element_dict)
                self.element_id_generator.update_value(element_value)
                label = element_value.get("m_sLabel", get_label_id_from_value(element_value))
                new_item = HierarchyItemModel(
                    _name=label,
                    _data=element_value,
                    _class=get_clean_class_name_value(element_value),
                    _id=self.element_id_generator.get_key(element_value)
                )
                items.append(new_item)
                if is_reference:
                    try:
                        ref_id = element_value.get("m_nElementID")
                    except Exception:
                        ref_id = None
            self.undo_stack.push(BulkModelImportCommand(self, parent_item, items))
            self._modified = True
            self._edited.emit()
        dialog.accepted_data.connect(on_accept)
        dialog.exec()

    # [Tree widget hierarchy context menu]
    def open_hierarchy_menu(self, position):
        menu = QMenu()
        add_new_action = menu.addAction("New element (Ctrl+F)")
        add_new_action.triggered.connect(self.add_an_element)

        add_preset_action = menu.addAction("New from preset")
        add_preset_action.triggered.connect(self.add_preset)

        menu.addSeparator()

        remove_action = menu.addAction("Remove (Delete)")
        remove_action.triggered.connect(lambda: self.ui.tree_hierarchy_widget.DeleteSelectedItems())

        duplicate_action = menu.addAction("Duplicate (Ctrl+D)")
        duplicate_action.triggered.connect(lambda: self.ui.tree_hierarchy_widget.DuplicateSelectedItems(self.element_id_generator))

        grouping_action = menu.addAction("Group selected (Ctrl+G)")
        grouping_action.triggered.connect(lambda: self.undo_stack.push(GroupElementsCommand(self.ui.tree_hierarchy_widget)))

        menu.addSeparator()

        copy_action = menu.addAction("Copy (Ctrl+C)")
        copy_action.triggered.connect(lambda: self.copy_item(self.ui.tree_hierarchy_widget))

        cut_action = menu.addAction("Cut (Ctrl+X)")
        cut_action.triggered.connect(lambda: self.cut_item(self.ui.tree_hierarchy_widget))

        paste_action = menu.addAction("Paste (Ctrl+V)")
        paste_action.triggered.connect(lambda: self.paste_item(self.ui.tree_hierarchy_widget))

        paste_replace_action = menu.addAction("Paste with replacement (Ctrl+Shift+V)")
        paste_replace_action.triggered.connect(lambda: self.new_item_with_replacement(QApplication.clipboard().text()))

        bulk_import_action = menu.addAction("Bulk Model Importer")
        bulk_import_action.triggered.connect(self.open_bulk_model_importer)

        menu.addSeparator()
        load_vmap_action = menu.addAction("Load Vmap...")
        load_vmap_action.triggered.connect(self.load_vmap_into_hierarchy)

        current_item = self.ui.tree_hierarchy_widget.currentItem()
        if current_item:
            data = current_item.data(0, Qt.UserRole)
            if isinstance(data, dict):
                eid = data.get("m_nElementID", 0)
                if eid > 0:
                    menu.addSeparator()
                    render_area = self._viewport_3d.render_area if self._viewport_3d else None
                    is_isolated = render_area and render_area.isolated_element_id == eid
                    isolate_action = menu.addAction("Isolate in 3d viewport (Ctrl+H)")
                    isolate_action.setCheckable(True)
                    isolate_action.setChecked(bool(is_isolated))
                    isolate_action.triggered.connect(self.toggle_isolation)

        menu.exec(self.ui.tree_hierarchy_widget.viewport().mapToGlobal(position))

    def toggle_isolation(self):
        """Toggle isolated view for the currently selected element in the 3D viewport."""
        if not self._viewport_3d:
            return

        # If dynamic isolation was active, uncheck it so manual isolation takes over
        if hasattr(self._viewport_3d, 'isolate_check') and self._viewport_3d.isolate_check.isChecked():
            self._viewport_3d.isolate_check.setChecked(False)

        render_area = self._viewport_3d.render_area
        current_item = self.ui.tree_hierarchy_widget.currentItem()

        if not current_item:
            if render_area.isolated_element_id is not None:
                render_area.isolated_element_id = None
                self._viewport_3d.update_viewport()
            return

        data = current_item.data(0, Qt.UserRole)
        if not isinstance(data, dict):
            return

        eid = data.get("m_nElementID", 0)
        if eid <= 0:
            return

        if render_area.isolated_element_id == eid:
            render_area.isolated_element_id = None
        else:
            render_area.isolated_element_id = eid

        self._viewport_3d.update_viewport()

    def load_vmap_into_hierarchy(self):
        from gui.common import get_cs2_path
        from gui.settings.common import get_addon_name
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        from hammer5tools_core.bridge import CoreBridge
        from gui.editors.smartprop_editor.vsmart import deserialize_hierarchy_item
        import os
        
        cs2_path = get_cs2_path()
        addon_name = get_addon_name() or "addon"
        start_dir = os.path.join(cs2_path, "content", "csgo_addons", addon_name, "maps") if cs2_path else ""
        if not os.path.exists(start_dir):
            start_dir = ""
            
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select VMAP File to Load", start_dir, "VMAP Files (*.vmap)"
        )
        if not file_path:
            return
            
        try:
            map_document = CoreBridge.instance().read_valve_map(file_path)

            class MapNodeAdapter:
                def __init__(self, node):
                    self._node = node
                    self.ClassName = node.class_name
                    self.Name = node.name

                def ContainsKey(self, name):
                    return (
                        name in self._node.properties
                        or name == "children" and bool(self._node.children)
                        or name == "entity_properties" and self._entity_properties() is not None
                    )

                def __getitem__(self, name):
                    if name == "children":
                        return [MapNodeAdapter(child) for child in self._node.children]
                    if name == "entity_properties":
                        entity_properties = self._entity_properties()
                        return None if entity_properties is None else MapNodeAdapter(entity_properties)
                    if name == "nodeID":
                        return self._node.properties.get(name, "0")
                    value = self._node.properties[name]
                    if name in ("origin", "scales"):
                        components = self._components(value, [0.0, 0.0, 0.0])
                        return type("Vector3", (), dict(zip(("X", "Y", "Z"), components)))()
                    if name == "angles":
                        components = self._components(value, [0.0, 0.0, 0.0])
                        return type("QAngle", (), dict(zip(("Pitch", "Yaw", "Roll"), components)))()
                    return value

                def _entity_properties(self):
                    return next(
                        (child for child in self._node.children if "classname" in child.properties),
                        None,
                    )

                @staticmethod
                def _components(value, default):
                    try:
                        normalized = str(value).replace(",", " ").replace("<", " ").replace(">", " ")
                        values = [float(component) for component in normalized.split()]
                        return (values + default)[:3]
                    except (TypeError, ValueError):
                        return default

            world = MapNodeAdapter(map_document.world)
            if world is None:
                QMessageBox.critical(self, "Error", "Invalid VMAP file structure: could not find world element.")
                return
            
            # 2. Traverse the hierarchy recursively starting from world to find groups, smartprops, props
            scanned_elements = []
            
            def traverse(el, parent=None):
                if el is None:
                    return
                cn = el.ClassName
                if cn in ["CMapGroup", "CMapSmartProp", "CMapEntity"]:
                    scanned_elements.append(el)
                    if cn in ["CMapGroup", "CMapSmartProp"]:
                        # Groups and smartprops return early to avoid scanning children separately
                        return
                
                if el.ContainsKey("children") and el["children"] is not None:
                    for child in el["children"]:
                        traverse(child, el)
                        
            traverse(world)
            
            # Filter scanned elements to only include actual valid ones
            valid_elements = []
            for el in scanned_elements:
                cn = el.ClassName
                if cn == "CMapGroup":
                    valid_elements.append(el)
                elif cn == "CMapSmartProp":
                    valid_elements.append(el)
                elif cn == "CMapEntity" and el.ContainsKey("entity_properties"):
                    ep = el["entity_properties"]
                    if ep is not None:
                        classname = ep["classname"] if ep.ContainsKey("classname") else ""
                        if classname.startswith("prop_") or "smart" in classname.lower():
                            valid_elements.append(el)
                            
            if not valid_elements:
                QMessageBox.warning(self, "No Props Found", "No valid props, groups, or smartprops were found in the selected map file.")
                return
                
            # 3. Calculate pivot point P (Center of selection)
            def format_imported_vector(vector):
                should_round = get_settings_bool('SmartPropEditor', 'round_vmap_values', False)
                if should_round:
                    try:
                        decimals = int(get_settings_value('SmartPropEditor', 'round_vmap_decimals', 4))
                    except:
                        decimals = 4
                    return [round(float(x), decimals) for x in vector]
                else:
                    # Emit raw float values so they load into the float fields
                    # (full precision preserved) instead of the expression field.
                    return [float(x) for x in vector]
            origins = []
            for el in valid_elements:
                if el.ContainsKey("origin") and el["origin"] is not None:
                    try:
                        origins.append([float(el["origin"].X), float(el["origin"].Y), float(el["origin"].Z)])
                    except:
                        pass
            if not origins:
                origins = [[0.0, 0.0, 0.0]]
                
            avg_x = sum(o[0] for o in origins) / len(origins)
            avg_y = sum(o[1] for o in origins) / len(origins)
            avg_z = sum(o[2] for o in origins) / len(origins)
            pivot = [avg_x, avg_y, avg_z]
            
            import math
            
            def inverse_rotate_point_pyr(x, y, z, pitch, yaw, roll):
                if yaw != 0:
                    y_rad = math.radians(-yaw)
                    c, s = math.cos(y_rad), math.sin(y_rad)
                    x, y = x * c - y * s, x * s + y * c
                if pitch != 0:
                    p = math.radians(-pitch)
                    c, s = math.cos(p), math.sin(p)
                    x, z = x * c - z * s, x * s + z * c
                if roll != 0:
                    r = math.radians(-roll)
                    c, s = math.cos(r), math.sin(r)
                    y, z = y * c - z * s, y * s + z * c
                return x, y, z

            def normalize_angles(angles):
                return [((a + 180) % 360) - 180 for a in angles]

            # Helper to convert VMAP elements recursively
            element_id_counter = [1]
            
            def convert_element(el, parent_origin, parent_angles=[0.0, 0.0, 0.0], parent_scale=[1.0, 1.0, 1.0]):
                el_cn = el.ClassName
                
                origin = [0.0, 0.0, 0.0]
                if el.ContainsKey("origin") and el["origin"] is not None:
                    try:
                        origin = [float(el["origin"].X), float(el["origin"].Y), float(el["origin"].Z)]
                    except:
                        pass
                angles = [0.0, 0.0, 0.0]
                if el.ContainsKey("angles") and el["angles"] is not None:
                    try:
                        angles = [float(el["angles"].Pitch), float(el["angles"].Yaw), float(el["angles"].Roll)]
                    except:
                        pass
                scales = [1.0, 1.0, 1.0]
                if el.ContainsKey("scales") and el["scales"] is not None:
                    try:
                        scales = [float(el["scales"].X), float(el["scales"].Y), float(el["scales"].Z)]
                    except:
                        pass
                        
                diff_pos = [origin[0] - parent_origin[0], origin[1] - parent_origin[1], origin[2] - parent_origin[2]]
                if parent_angles != [0.0, 0.0, 0.0]:
                    rel_pos = list(inverse_rotate_point_pyr(diff_pos[0], diff_pos[1], diff_pos[2], parent_angles[0], parent_angles[1], parent_angles[2]))
                else:
                    rel_pos = diff_pos
                    
                rel_rot = normalize_angles([angles[0] - parent_angles[0], angles[1] - parent_angles[1], angles[2] - parent_angles[2]])
                rel_scale = [scales[i] / parent_scale[i] for i in range(3)]
                
                modifiers = []
                if rel_pos != [0.0, 0.0, 0.0]:
                    modifiers.append({
                        "_class": "CSmartPropOperation_Translate",
                        "m_vPosition": {
                            "m_Components": format_imported_vector(rel_pos)
                        }
                    })
                if rel_rot != [0.0, 0.0, 0.0]:
                    modifiers.append({
                        "_class": "CSmartPropOperation_Rotate",
                        "m_vRotation": {
                            "m_Components": format_imported_vector(rel_rot)
                        }
                    })
                    
                element_id = element_id_counter[0]
                element_id_counter[0] += 1
                
                if el_cn == "CMapGroup":
                    group_element = {
                        "_class": "CSmartPropElement_Group",
                        "m_nElementID": element_id,
                        "m_sLabel": el.Name or f"Group_{el['nodeID']}",
                        "m_Modifiers": modifiers,
                        "m_SelectionCriteria": [],
                        "m_Children": []
                    }
                    if rel_scale != [1.0, 1.0, 1.0]:
                        should_round = get_settings_bool('SmartPropEditor', 'round_vmap_values', False)
                        if should_round:
                            try:
                                decimals = int(get_settings_value('SmartPropEditor', 'round_vmap_decimals', 4))
                            except:
                                decimals = 4
                            s_val = round(rel_scale[0], decimals)
                        else:
                            s_val = float(rel_scale[0])
                        modifiers.append({
                            "_class": "CSmartPropOperation_Scale",
                            "m_flScale": s_val
                        })
                        
                    if el.ContainsKey("children") and el["children"] is not None:
                        for child in el["children"]:
                            if child.ClassName in ["CMapEntity", "CMapSmartProp", "CMapGroup"]:
                                child_vsmart = convert_element(child, origin, angles, scales)
                                if child_vsmart:
                                    group_element["m_Children"].append(child_vsmart)
                    return group_element
                    
                elif el_cn == "CMapSmartProp":
                    smartprop_file = el["smartPropFilename"] if el.ContainsKey("smartPropFilename") else ""
                    smartprop_element = {
                        "_class": "CSmartPropElement_SmartProp",
                        "m_sSmartProp": smartprop_file,
                        "m_nElementID": element_id,
                        "m_sLabel": el.Name or f"SmartProp_{el['nodeID']}",
                        "m_Modifiers": modifiers,
                        "m_SelectionCriteria": []
                    }
                    if rel_scale != [1.0, 1.0, 1.0]:
                        if len(set(rel_scale)) == 1:
                            should_round = get_settings_bool('SmartPropEditor', 'round_vmap_values', False)
                            if should_round:
                                try:
                                    decimals = int(get_settings_value('SmartPropEditor', 'round_vmap_decimals', 4))
                                except:
                                    decimals = 4
                                s_val = round(rel_scale[0], decimals)
                            else:
                                s_val = float(rel_scale[0])
                            smartprop_element["m_flUniformScale"] = s_val
                        else:
                            modifiers.append({
                                "_class": "CSmartPropOperation_Scale",
                                "m_flScale": format_imported_vector(rel_scale)[0]
                            })
                    return smartprop_element
                    
                elif el_cn == "CMapEntity":
                    ep = el["entity_properties"]
                    if ep is not None:
                        classname = ep["classname"] if ep.ContainsKey("classname") else ""
                        model_path = ep["model"] if ep.ContainsKey("model") else ""
                        if not model_path and ep.ContainsKey("model_name"):
                            model_path = ep["model_name"]
                            
                        model_name = os.path.splitext(os.path.basename(model_path))[0] if model_path else f"Prop_{classname}_{el['nodeID']}"
                        model_element = {
                            "_class": "CSmartPropElement_Model",
                            "m_nElementID": element_id,
                            "m_sModelName": model_path,
                            "m_sLabel": model_name,
                            "m_Modifiers": modifiers,
                            "m_SelectionCriteria": []
                        }
                        if rel_scale != [1.0, 1.0, 1.0]:
                            model_element["m_vModelScale"] = {"m_Components": format_imported_vector(rel_scale)}
                        return model_element
                return None
                
            # 4. Generate the parent Group element in JSON format
            vmap_basename = os.path.splitext(os.path.basename(file_path))[0]
            parent_group_vsmart = {
                "_class": "CSmartPropElement_Group",
                "m_sLabel": f"Imported_{vmap_basename}",
                "m_Modifiers": [
                    {
                        "_class": "CSmartPropOperation_Translate",
                        "m_vPosition": {
                            "m_Components": format_imported_vector(pivot)
                        }
                    }
                ],
                "m_SelectionCriteria": [],
                "m_Children": []
            }
            
            # Convert all elements relative to the pivot and add as children of the parent group
            for el in valid_elements:
                converted = convert_element(el, pivot, [0.0, 0.0, 0.0], [1.0, 1.0, 1.0])
                if converted:
                    parent_group_vsmart["m_Children"].append(converted)
                    
            # 5. Deserialize to QTreeWidget items and add to hierarchy tree
            imported_group_item = deserialize_hierarchy_item(parent_group_vsmart, self.element_id_generator)
            self.ui.tree_hierarchy_widget.AddItem(imported_group_item)
            
            # Mark document as modified
            self._modified = True
            self._edited.emit()
            
            QMessageBox.information(
                self,
                "Import Success",
                f"Successfully imported {len(valid_elements)} elements from {os.path.basename(file_path)} under a new parent Group."
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", f"An error occurred while importing VMAP: {e}")
            import traceback
            traceback.print_exc()

    # [Tree widget functions]
    def new_item_with_replacement(self, data):
        instance = FindAndReplaceDialog(data=data)
        instance.accepted_output.connect(lambda text: self.paste_item(self.ui.tree_hierarchy_widget, data_input=text))
        instance.exec()

    def move_tree_item(self, tree, direction):
        selected_items = tree.selectedItems()
        if not selected_items:
            return

        parent_to_items = {}
        for itm in selected_items:
            parent = itm.parent() or tree.invisibleRootItem()
            if parent not in parent_to_items:
                parent_to_items[parent] = []
            parent_to_items[parent].append(itm)

        for parent, items in parent_to_items.items():
            items.sort(key=lambda it_: parent.indexOfChild(it_), reverse=(direction > 0))
            for it_ in items:
                current_index = parent.indexOfChild(it_)
                new_index = current_index + direction
                if 0 <= new_index < parent.childCount():
                    parent.takeChild(current_index)
                    parent.insertChild(new_index, it_)

        tree.clearSelection()
        for it_ in selected_items:
            it_.setSelected(True)
        tree.scrollToItem(selected_items[-1] if direction > 0 else selected_items[0])

    def copy_item(self, tree, copy_to_clipboard=True):
        selected_indexes = tree.selectedIndexes()
        selected_items = [tree.itemFromIndex(index) for index in selected_indexes]
        selected_items = list(set(selected_items))
        root_data = {"m_Children": []}

        for tree_item in selected_items:
            item_data = serialization_hierarchy_items(item=tree_item)
            if item_data and "m_Children" in item_data:
                root_data["m_Children"].extend(item_data["m_Children"])

        if root_data["m_Children"]:
            if copy_to_clipboard:
                clipboard = QApplication.clipboard()
                clipboard.setText(JsonToKv3(root_data))
                return None
            else:
                return JsonToKv3(root_data)
        else:
            return None

    def cut_item(self, tree: QTreeWidget):
        self.copy_item(tree)
        self.ui.tree_hierarchy_widget.DeleteSelectedItems()

    def paste_item(self, tree, data_input=None, paste_to_parent=False):
        from gui.common import Kv3ToJson
        from gui.editors.smartprop_editor.vsmart import deserialize_hierarchy_item
        if data_input is None:
            data_input = QApplication.clipboard().text()
        try:
            obj = Kv3ToJson(self.fix_format(data_input))
            items = []
            parent = tree.currentItem() or tree.invisibleRootItem()
            if paste_to_parent:
                parent = parent.parent() or tree.invisibleRootItem()
            if "m_Children" in obj:
                for child in obj["m_Children"]:
                    item = deserialize_hierarchy_item(child, self.element_id_generator)
                    items.append(item)
            else:
                items.append(deserialize_hierarchy_item(obj, self.element_id_generator))
            self.undo_stack.push(PasteItemsCommand(tree, parent, items))
            self._modified = True
            self._edited.emit()
        except Exception as error:
            error_message = str(error)
            error_dialog = ErrorInfo(
                text="Wrong format of the pasting content",
                details=error_message
            )
            error_dialog.exec()

    def remove_tree_item(self, tree):
        selected_indexes = tree.selectedIndexes()
        selected_items = [tree.itemFromIndex(index) for index in selected_indexes]
        for itm in selected_items:
            if itm:
                if itm == tree.invisibleRootItem():
                    pass
                else:
                    parent = itm.parent() or tree.invisibleRootItem()
                    idx = parent.indexOfChild(itm)
                    if idx != -1:
                        parent.takeChild(idx)
        self._modified = True
        self._edited.emit()

    # [Window State]
    def _apply_default_layout(self):
        """Arrange the docks into the built-in factory layout.

        Left:   Hierarchy
        Center: Property Editor (tabbed with Manual Editor)
        Right:  3D Viewport | vertical column of Variables over Choices (tabbed with History)
        """
        self.addDockWidget(Qt.LeftDockWidgetArea, self.ui.HierarchyDock)
        self.addDockWidget(Qt.LeftDockWidgetArea, self._property_dock)
        self.splitDockWidget(self.ui.HierarchyDock, self._property_dock, Qt.Horizontal)
        self.tabifyDockWidget(self._property_dock, self._manual_dock)

        self.addDockWidget(Qt.RightDockWidgetArea, self._viewport_dock)
        # Right of the viewport: a single vertical column with Variables on top and
        # Choices (tabbed with History) below it.
        self.splitDockWidget(self._viewport_dock, self.ui.VariablesDock, Qt.Horizontal)
        self.splitDockWidget(self.ui.VariablesDock, self.ui.ChoicesDock, Qt.Vertical)
        self.tabifyDockWidget(self.ui.ChoicesDock, self._history_dock)

        # All docks visible (a prior custom layout may have closed some).
        for dock in (
            self.ui.HierarchyDock, self._property_dock, self._manual_dock,
            self._viewport_dock, self.ui.VariablesDock, self.ui.ChoicesDock,
            self._history_dock,
        ):
            dock.show()

        self.ui.ChoicesDock.raise_()
        # Property Editor is the front tab of the center group.
        self._property_dock.raise_()

        # Give the columns and the right-hand column starting sizes matching the
        # reference layout: a narrow Hierarchy, roughly equal Property Editor and
        # 3D Viewport, a narrow Variables/Choices column, and an even split between
        # Variables and Choices.
        self.resizeDocks(
            [self.ui.HierarchyDock, self._property_dock, self._viewport_dock],
            [310, 670, 690],
            Qt.Horizontal,
        )
        # Start the Variables/Choices column at its minimum width so the viewport
        # gets the rest of the space by default.
        self.resizeDocks(
            [self._viewport_dock, self.ui.VariablesDock],
            [10000, 1],
            Qt.Horizontal,
        )
        self.resizeDocks(
            [self.ui.VariablesDock, self.ui.ChoicesDock],
            [300, 300],
            Qt.Vertical,
        )

    def reset_layout(self):
        """Discard any saved layout and restore the built-in factory layout."""
        self.settings.remove("SmartPropEditorMainWindow/default_windowState_v3")
        self.settings.remove("SmartPropEditorMainWindow/windowState_v3")
        self._apply_default_layout()

    def _restore_user_prefs(self):
        # First try to load the explicit default layout.  The key is versioned
        # (v3) because the panel set changed when Property/Manual/Viewport became
        # docks; older saved states describe a layout that no longer exists.
        state = self.settings.value("SmartPropEditorMainWindow/default_windowState_v3")
        if not state:
            # Fallback to the last closed document's layout.
            state = self.settings.value("SmartPropEditorMainWindow/windowState_v3")

        if state:
            self.restoreState(state)
            # restoreState() rebuilds the dock tab bars, discarding the tab
            # styling applied in __init__. Re-apply so every dock's tabs
            # (Choices/History included) match the Property/Manual docks.
            set_qdock_tab_style(self.findChildren)

        saved_index = self.settings.value("SmartPropEditorMainWindow/currentComboBoxIndex")
        if saved_index is not None:
            self.variable_viewport.ui.add_new_variable_combobox.setCurrentIndex(int(saved_index))

    def _save_user_prefs(self):
        current_index = self.variable_viewport.ui.add_new_variable_combobox.currentIndex()
        self.settings.setValue("SmartPropEditorMainWindow/currentComboBoxIndex", current_index)
        # Persist the dock layout to the 'last closed' key.
        self.settings.setValue("SmartPropEditorMainWindow/windowState_v3", self.saveState())
        # Flush immediately so the layout is not lost if the process is killed
        # (crash / debugger-stop) before QSettings' normal buffered write.
        self.settings.sync()

    def save_layout_as_default(self):
        """Saves the current dock widget layout as the default for new documents."""
        # We explicitly save to a 'default' key that takes precedence in _restore_user_prefs
        self.settings.setValue("SmartPropEditorMainWindow/default_windowState_v3", self.saveState())
        # Also save to the regular key so it's consistent
        self.settings.setValue("SmartPropEditorMainWindow/windowState_v3", self.saveState())

    # [Properties Panel Undo]
    def _rebuild_properties_panel(self, item):
        """Rebuild the properties panel from the current tree-item data."""
        if hasattr(self, "smartprop_property_panel"):
            self.smartprop_property_panel.set_element(item)

    def _dec_property_undo_guard(self):
        self._property_undo_guard = max(0, self._property_undo_guard - 1)

    def apply_property_data(self, item, new_data, changed_keys=()):
        """Apply externally-produced element data to the item and refresh the property panel."""
        if item is not None:
            item.setData(0, Qt.UserRole, fast_deepcopy(new_data))
        panel = getattr(self, "property_panel", None)
        if panel is not None and hasattr(panel, "apply_external_data"):
            panel.apply_external_data(item, new_data, changed_keys)

    def _incremental_property_update(self, item, new_data, changed_keys=()):
        """Update property values on item and forward to panel."""
        self.apply_property_data(item, new_data, changed_keys)

    def _on_slider_started(self):
        """Called when a slider begins a drag."""
        if self._slider_dragging == 0:
            item = self.ui.tree_hierarchy_widget.currentItem()
            if item is not None:
                self._slider_pre_drag_data = fast_deepcopy(item.data(0, Qt.UserRole))
        self._slider_dragging += 1

    def _on_slider_committed(self):
        """Called when a slider is released."""
        self._slider_dragging = max(0, self._slider_dragging - 1)
        if self._slider_dragging == 0 and self._slider_pre_drag_data is not None:
            item = self.ui.tree_hierarchy_widget.currentItem()
            if item is not None and not self._property_undo_guard:
                new_data = fast_deepcopy(item.data(0, Qt.UserRole))
                if new_data != self._slider_pre_drag_data:
                    cmd = PropertySnapshotCommand(self, item, self._slider_pre_drag_data, new_data)
                    self.undo_stack.push(cmd)
            self._slider_pre_drag_data = None

    def _gizmo_commit_drag(self):
        """Called when transform gizmo drag is finished/released."""
        if self._gizmo_pre_drag_data is not None:
            item = self.ui.tree_hierarchy_widget.currentItem()
            if item is not None and not self._property_undo_guard:
                new_data = fast_deepcopy(item.data(0, Qt.UserRole))
                if new_data != self._gizmo_pre_drag_data:
                    cmd = PropertySnapshotCommand(self, item, self._gizmo_pre_drag_data, new_data)
                    self.undo_stack.push(cmd)
            self._gizmo_pre_drag_data = None

    def update_property_frame_values(self, data, changed_keys=None):
        """Live-update the Property panel to track a transform-gizmo drag."""
        if not changed_keys:
            return
        item = self.ui.tree_hierarchy_widget.currentItem()
        if item is not None:
            panel = getattr(self, "property_panel", None)
            if panel is not None and hasattr(panel, "selected_refs"):
                refs = panel.selected_refs()
                if not any(getattr(r, "kind", None) == "modifier" for r in refs):
                    item.setData(0, Qt.UserRole, fast_deepcopy(data))
                    return
            self.apply_property_data(item, data, changed_keys)


    # [Variables Panel Undo]
    def _snapshot_variables(self):
        """Serialise all variable widgets to a list of dicts."""
        layout = self.variable_viewport.ui.variables_scrollArea
        state = []
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget and hasattr(widget, 'name') and hasattr(widget, 'var_class'):
                state.append({
                    'name': widget.name,
                    'var_class': widget.var_class,
                    'var_value': fast_deepcopy(widget.var_value),
                    'var_visible_in_editor': widget.var_visible_in_editor,
                    'var_display_name': widget.var_display_name,
                    'expanded': widget.ui.show_child.isChecked(),
                })
        return state

    def _restore_variables(self, state):
        """Clear all variable widgets and recreate from a serialised state list."""
        layout = self.variable_viewport.ui.variables_scrollArea
        # Remove all VariableFrame widgets, preserving the trailing spacer
        while layout.count() > 1:
            item = layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self._restoring_state = True
        try:
            for var_data in state:
                name = var_data['name']
                import re
                is_category = False
                if name:
                    if re.match(r"hammer5tools_category_([a-z0-9]+)_(start|end)", name) or re.match(r"hammer5tools_category_(.*)_category_(.*)_(start|end)", name):
                        is_category = True
                        
                if is_category:
                    self.add_category(
                        name=name,
                        var_visible_in_editor=var_data['var_visible_in_editor'],
                        var_display_name=var_data['var_display_name'],
                        expanded=var_data.get('expanded', True)
                    )
                else:
                    self.add_variable(
                        name=name,
                        var_class=var_data['var_class'],
                        var_value=var_data['var_value'],
                        var_visible_in_editor=var_data['var_visible_in_editor'],
                        var_display_name=var_data['var_display_name'],
                        expanded=var_data.get('expanded', False),
                    )
        finally:
            self._restoring_state = False
        self._modified = True
        self._edited.emit()
        # Sync the variables viewport's committed-state reference so the next
        # user edit correctly uses the restored state as its "before" snapshot.
        self.variable_viewport._sync_committed_state()
        CompletionUtils.invalidate_cache(self.variable_viewport.ui.variables_scrollArea)

    # [Choices Panel Undo]
    def _snapshot_choices(self):
        """Serialise the choices tree to a list of dicts."""
        tree = self.ui.choices_tree_widget
        state = []
        root = tree.invisibleRootItem()
        for ci in range(root.childCount()):
            choice = root.child(ci)
            combo = tree.itemWidget(choice, 1)
            default_txt = combo.currentText() if combo and hasattr(combo, 'currentText') else ''
            if default_txt == "None":
                default_txt = ""
            choice_data = {
                'name': choice.text(0),
                'default': default_txt,
                'expanded': choice.isExpanded(),
                'options': [],
            }
            for oi in range(choice.childCount()):
                option = choice.child(oi)
                option_data = {'name': option.text(0), 'expanded': option.isExpanded(), 'variables': []}
                for vi in range(option.childCount()):
                    var_item = option.child(vi)
                    val_widget = tree.itemWidget(var_item, 1)
                    name_widget = tree.itemWidget(var_item, 0)
                    var_name = (
                        name_widget.combobox.currentText()
                        if name_widget and hasattr(name_widget, 'combobox')
                        else var_item.text(0)
                    )
                    if var_name == "None" or not var_name:
                        var_name = var_item.text(0)

                    if val_widget and hasattr(val_widget, 'data'):
                        var_type = val_widget.data.get('m_DataType', '')
                        var_value = val_widget.data.get('m_Value', '')
                    else:
                        var_type = ''
                        var_value = var_item.text(1)
                    option_data['variables'].append({
                        'name': var_name,
                        'type': var_type,
                        'value': var_value,
                    })
                choice_data['options'].append(option_data)
            state.append(choice_data)
        return state

    def _restore_choices(self, state):
        """Clear the choices tree and rebuild it from a serialised state list."""
        self.ui.choices_tree_widget.blockSignals(True)
        try:
            self.ui.choices_tree_widget.clear()
            for choice_data in state:
                choice_item = AddChoice(
                    tree=self.ui.choices_tree_widget,
                    name=choice_data.get('name', 'Choice'),
                    default=choice_data.get('default', ''),
                    variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
                ).item
                for option_data in choice_data.get('options', []):
                    option_item = AddOption(
                        parent=choice_item, name=option_data.get('name', 'Option')
                    ).item
                    for var_data in option_data.get('variables', []):
                        AddVariable(
                            element_id_generator=self.element_id_generator,
                            parent=option_item,
                            variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
                            name=var_data.get('name', ''),
                            value=var_data.get('value', ''),
                            type=var_data.get('type', ''),
                        )
                    option_item.setExpanded(option_data.get('expanded', False))
                choice_item.setExpanded(choice_data.get('expanded', False))
        finally:
            self.ui.choices_tree_widget.blockSignals(False)
        self._connect_choices_widget_signals()
        self._last_committed_choices_state = state
        self._modified = True
        self._edited.emit()

    def move_choice_tree_item(self, direction):
        """Move a choice, option, or choice variable up or down without destroying widgets."""
        selected_items = self.ui.choices_tree_widget.selectedItems()
        if not selected_items:
            return
        item = selected_items[0]
        item_type = item.text(2)
        state = self._snapshot_choices()
        root = self.ui.choices_tree_widget.invisibleRootItem()

        target_path = None
        if item_type == "choice":
            ci = root.indexOfChild(item)
            new_ci = ci + direction
            if 0 <= new_ci < len(state):
                state[ci], state[new_ci] = state[new_ci], state[ci]
                target_path = ("choice", new_ci)
        elif item_type == "option":
            choice_item = item.parent()
            if choice_item:
                ci = root.indexOfChild(choice_item)
                oi = choice_item.indexOfChild(item)
                new_oi = oi + direction
                if 0 <= ci < len(state) and 0 <= new_oi < len(state[ci]['options']):
                    opts = state[ci]['options']
                    opts[oi], opts[new_oi] = opts[new_oi], opts[oi]
                    target_path = ("option", ci, new_oi)
        elif item_type == "variable":
            option_item = item.parent()
            choice_item = option_item.parent() if option_item else None
            if option_item and choice_item:
                ci = root.indexOfChild(choice_item)
                oi = choice_item.indexOfChild(option_item)
                vi = option_item.indexOfChild(item)
                new_vi = vi + direction
                if (0 <= ci < len(state) and 0 <= oi < len(state[ci]['options'])
                        and 0 <= new_vi < len(state[ci]['options'][oi]['variables'])):
                    vars_ = state[ci]['options'][oi]['variables']
                    vars_[vi], vars_[new_vi] = vars_[new_vi], vars_[vi]
                    target_path = ("variable", ci, oi, new_vi)

        if target_path:
            self._restore_choices(state)
            try:
                tree = self.ui.choices_tree_widget
                root_item = tree.invisibleRootItem()
                target_item = None
                if target_path[0] == "choice":
                    target_item = root_item.child(target_path[1])
                elif target_path[0] == "option":
                    target_item = root_item.child(target_path[1]).child(target_path[2])
                elif target_path[0] == "variable":
                    target_item = root_item.child(target_path[1]).child(target_path[2]).child(target_path[3])
                if target_item:
                    tree.clearSelection()
                    target_item.setSelected(True)
                    tree.scrollToItem(target_item)
            except Exception:
                pass

    def _connect_choices_widget_signals(self):
        """Connect change signals on all inline widgets inside the choices tree.

        Called after every structural op and after _restore_choices so that
        ComboboxTreeChild and VariableWidget/Float/Bool edits are tracked.
        """
        from functools import partial
        from PySide6.QtWidgets import QLineEdit, QCheckBox, QSlider
        tree = self.ui.choices_tree_widget
        root = tree.invisibleRootItem()
        for ci in range(root.childCount()):
            choice = root.child(ci)
            combo = tree.itemWidget(choice, 1)
            if combo:
                if hasattr(combo, '_undo_handler'):
                    try:
                        combo.currentTextChanged.disconnect(combo._undo_handler)
                    except (RuntimeError, TypeError):
                        pass
                handler = partial(self._on_choices_widget_changed, "Edit Choice Default")
                combo._undo_handler = handler
                combo.currentTextChanged.connect(handler)

            for oi in range(choice.childCount()):
                option = choice.child(oi)
                for vi in range(option.childCount()):
                    var_item = option.child(vi)
                    var_widget = tree.itemWidget(var_item, 0)
                    if hasattr(var_widget, 'combobox'):
                        if hasattr(var_widget, '_undo_handler_type'):
                            try:
                                var_widget.combobox.changed.disconnect(var_widget._undo_handler_type)
                            except (RuntimeError, TypeError):
                                pass
                        handler = partial(self._on_choices_widget_type_changed, "Choice Option Variable type changed")
                        var_widget._undo_handler_type = handler
                        var_widget.combobox.changed.connect(handler)

                    val_widget = tree.itemWidget(var_item, 1)
                    if val_widget:
                        handler = partial(self._on_choices_widget_changed, "Choice Option Variable Value Changed")
                        val_widget._undo_handler_val = handler
                        for child in val_widget.findChildren(QLineEdit):
                            old_h = getattr(child, '_undo_handler_val', None)
                            if old_h:
                                try:
                                    child.textChanged.disconnect(old_h)
                                except (RuntimeError, TypeError):
                                    pass
                            child._undo_handler_val = handler
                            child.textChanged.connect(handler)
                        for child in val_widget.findChildren(QCheckBox):
                            old_h = getattr(child, '_undo_handler_val', None)
                            if old_h:
                                try:
                                    child.checkStateChanged.disconnect(old_h)
                                except (RuntimeError, TypeError):
                                    pass
                            child._undo_handler_val = handler
                            child.checkStateChanged.connect(handler)
                        for child in val_widget.findChildren(QSlider):
                            old_h = getattr(child, '_undo_handler_val', None)
                            if old_h:
                                try:
                                    child.valueChanged.disconnect(old_h)
                                except (RuntimeError, TypeError):
                                    pass
                            child._undo_handler_val = handler
                            child.valueChanged.connect(handler)

    def _on_choices_widget_type_changed(self, description, *args):
        """When user changes var type, choices.py swaps widget instantly. We must reconnect."""
        self._on_choices_widget_changed(description)
        QTimer.singleShot(50, self._connect_choices_widget_signals)

    def _choices_op_with_undo(self, description, op_fn):
        """Helper: flush any pending choices widget edit, run op_fn, push ChoicesSnapshotCommand."""
        self._flush_choices_widget_if_pending()
        old = self._snapshot_choices()
        op_fn()
        new = self._snapshot_choices()
        self._connect_choices_widget_signals()
        self._last_committed_choices_state = new

        print(f"DEBUG _choices_op_with_undo: desc='{description}' | old_len={len(old)} new_len={len(new)}")
        if new != old:
            print(f"DEBUG _choices_op_with_undo: PUSHING -> {description}")
            cmd = ChoicesSnapshotCommand(self, old, new, description)
            self.undo_stack.push(cmd)
        else:
            print("DEBUG _choices_op_with_undo: ABORTED (new == old)!")

    def _on_choices_item_about_to_edit(self, item, column):
        """Capture the 'before' snapshot when the user starts an inline rename."""
        if column == 0 and (item.flags() & Qt.ItemIsEditable):
            self._choices_rename_old_state = self._snapshot_choices()

    def _on_choices_item_changed(self, item, column):
        """Push rename undo command once the inline edit is committed."""
        if (
            column == 0
            and self._choices_rename_old_state is not None
        ):
            new_state = self._snapshot_choices()
            if new_state != self._choices_rename_old_state:
                self.undo_stack.push(
                    ChoicesSnapshotCommand(self, self._choices_rename_old_state, new_state, "Rename")
                )
            self._last_committed_choices_state = new_state
            self._choices_rename_old_state = None

    def _on_choices_widget_changed(self, description="Edit Choices", *args):
        """Debounce handler for ComboboxTreeChild / VariableWidget changes."""
        if self._choices_widget_old_state is None:
            self._choices_widget_old_state = self._last_committed_choices_state or self._snapshot_choices()
        self._choices_widget_debounce_desc = description
        self._choices_widget_debounce.start(500)

    def _push_choices_widget_edit(self):
        """Called when the choices widget debounce timer fires."""
        if self._choices_widget_old_state is not None:
            new_state = self._snapshot_choices()
            if new_state != self._choices_widget_old_state:
                self.undo_stack.push(
                    ChoicesSnapshotCommand(
                        self,
                        self._choices_widget_old_state,
                        new_state,
                        self._choices_widget_debounce_desc,
                    )
                )
                self._modified = True
                self._edited.emit()
            self._last_committed_choices_state = new_state
            self._choices_widget_old_state = None

    def _flush_choices_widget_if_pending(self):
        """Flush any in-progress widget edit before a structural choices op."""
        if self._choices_widget_debounce.isActive():
            self._choices_widget_debounce.stop()
            self._push_choices_widget_edit()

    def _on_hierarchy_item_about_to_edit(self, item, column):
        """Capture the 'before' label when the user starts an inline rename in the hierarchy tree."""
        if column == 0:
            self._hierarchy_rename_old_label = item.text(0)
            self._hierarchy_rename_item = item

    def _on_hierarchy_item_changed(self, item, column):
        """Push rename undo command once the inline edit is committed in the hierarchy tree."""
        if (
            column == 0
            and self._hierarchy_rename_item is item
            and self._hierarchy_rename_old_label is not None
        ):
            new_label = item.text(0)
            if new_label != self._hierarchy_rename_old_label:
                from gui.editors.smartprop_editor.commands import HierarchyItemRenameCommand
                self.undo_stack.push(
                    HierarchyItemRenameCommand(item, self._hierarchy_rename_old_label, new_label)
                )
            self._hierarchy_rename_old_label = None
            self._hierarchy_rename_item = None

    def _setup_history_dock(self):
        self._history_dock = QDockWidget("History", self)
        self._history_dock.setObjectName("SPE_history_dock")
        self._history_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea  |
            Qt.DockWidgetArea.RightDockWidgetArea |
            Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self._history_dock.setMinimumWidth(160)
        history_view = QUndoView(self.undo_stack, self._history_dock)
        self._history_dock.setWidget(history_view)
        self._history_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        # Placement is handled by the default-layout block in __init__.

    def showEvent(self, event):
        super().showEvent(event)
        # Re-apply the saved layout once the window has its real on-screen size.
        # restoreState() during __init__ (via singleShot) can run before the dock
        # area is sized, which distorts the restored dock proportions so the
        # loaded layout doesn't match what was saved. Doing it once more after the
        # first real show (deferred a tick so the resize settles) fixes that; it's
        # idempotent when the earlier restore was already correct.
        if not getattr(self, "_did_show_restore", False):
            self._did_show_restore = True
            QTimer.singleShot(0, self._restore_user_prefs)

    def closeEvent(self, event):
        self._save_user_prefs()

    # [Other]
    def fix_format(self, file_content):
        pattern = re.compile(r"= resource_name:")
        modified_content = re.sub(pattern, "= ", file_content)
        modified_content = modified_content.replace("null,", "")
        return modified_content

    # [Global Rename]
    def rename_variable_references(self, old_name, new_name):
        """Find and replace all references to old_name with new_name throughout the document."""
        import re
        pattern = re.compile(rf'\b{re.escape(old_name)}\b')

        def replace_in_val(val):
            if isinstance(val, str):
                return pattern.sub(new_name, val)
            if isinstance(val, list):
                return [replace_in_val(v) for v in val]
            if isinstance(val, dict):
                return {k: replace_in_val(v) for k, v in val.items()}
            return val

        self._rename_in_hierarchy_recursive(self.ui.tree_hierarchy_widget.invisibleRootItem(), replace_in_val)

        old_choices = self._snapshot_choices()
        new_choices_state = replace_in_val(old_choices)
        if new_choices_state != old_choices:
            # We don't push a separate command here because we expect to be inside a macro
            # or we want it to be part of the rename operation.
            self.undo_stack.push(ChoicesSnapshotCommand(self, old_choices, new_choices_state, "Rename variable in choices"))
            self._restore_choices(new_choices_state)

        # 3. Other Variables (hide expressions)
        old_vars = self._snapshot_variables()
        # Filter out the variable that was just renamed from the snapshot comparison 
        # to avoid conflicts with the command that triggered this.
        # Actually, new_vars will have the new name for the renamed var too, which is fine.
        new_vars_state = replace_in_val(old_vars)
        if new_vars_state != old_vars:
            self.undo_stack.push(VariablesSnapshotCommand(self, old_vars, new_vars_state, "Rename variable in expressions"))
            self._restore_variables(new_vars_state)

    def _rename_in_hierarchy_recursive(self, item, replace_fn):
        """Recursively update hierarchy item data with renamed variable references."""
        old_data = item.data(0, Qt.UserRole)
        if isinstance(old_data, dict):
            new_data = replace_fn(old_data)
            if new_data != old_data:
                self.undo_stack.push(PropertySnapshotCommand(self, item, old_data, new_data))
                # Apply the change
                item.setData(0, Qt.UserRole, new_data)
                # If this item is currently selected, refresh the properties panel
                if self.ui.tree_hierarchy_widget.currentItem() is item:
                    self._rebuild_properties_panel(item)

        for i in range(item.childCount()):
            self._rename_in_hierarchy_recursive(item.child(i), replace_fn)

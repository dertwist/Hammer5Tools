import os.path
import re
import ast
from src.common import fast_deepcopy
from collections import deque

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
    QScrollArea,
)
from PySide6.QtGui import (
    QAction,
    QKeyEvent,
    QUndoStack,
    QKeySequence,
    QShortcut,
)
import uuid
import traceback, ctypes
from PySide6.QtCore import Qt, QTimer, Signal, QEvent

from src.settings.common import get_addon_dir
from src.settings.main import get_settings_value, get_settings_bool

from keyvalues3 import kv3_to_json
from src.editors.smartprop_editor.ui_document import Ui_MainWindow
from src.settings.main import settings
from src.editors.smartprop_editor.objects import (
    variables_list,
    variable_prefix,
    elements_list,
    operators_list,
    selection_criteria_list,
    filters_list
)
from src.editors.smartprop_editor.vsmart import (
    VsmartOpen, VsmartSave, serialization_hierarchy_items, deserialize_hierarchy_item
)
from src.editors.smartprop_editor.completion_utils import CompletionUtils
from src.editors.smartprop_editor.property_frame import PropertyFrame
from src.editors.smartprop_editor.property_data_worker import BatchPropertyDataWorker
from src.editors.smartprop_editor.properties_group_frame import PropertiesGroupFrame
from src.editors.smartprop_editor.choices import AddChoice, AddVariable, AddOption
from src.widgets.popup_menu.main import PopupMenu
from src.editors.smartprop_editor.commands import (
    GroupElementsCommand, BulkModelImportCommand, NewFromPresetCommand, PasteItemsCommand,
    PropertySnapshotCommand, VariablesSnapshotCommand, ChoicesSnapshotCommand,
)
from src.forms.replace_dialog.main import FindAndReplaceDialog
from src.widgets import ErrorInfo, on_three_hierarchyitem_clicked, HierarchyItemModel, error, exception_handler
from src.widgets.element_id import ElementIDGenerator
from src.editors.smartprop_editor._common import (
    get_clean_class_name_value,
    get_clean_class_name,
    get_label_id_from_value,
    unique_counter_name
)
from src.common import (
    enable_dark_title_bar,
    Kv3ToJson,
    JsonToKv3,
    get_cs2_path,
    SmartPropEditor_Preset_Path,
    set_qdock_tab_style
)
from src.widgets.tree import HierarchyTreeWidget
from src.editors.smartprop_editor.variables_viewport import SmartPropEditorVariableViewport

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

        # Window-level undo/redo shortcuts so they work regardless of which
        # child widget has focus (properties panel, variable fields, etc.).
        # QShortcut with WindowShortcut context fires before the key event is
        # dispatched to the focused widget, so there is no double-triggering
        # with the identical bindings in the tree's event filter.
        _undo_sc = QShortcut(QKeySequence.Undo, self)
        _undo_sc.activated.connect(self.undo_stack.undo)
        _redo_sc = QShortcut(QKeySequence.Redo, self)
        _redo_sc.activated.connect(self.undo_stack.redo)

        # Guard counter: while > 0, update_tree_item_value skips pushing to the undo stack.
        # Incremented before rebuilding the properties panel during undo/redo; decremented
        # after all deferred QTimer.singleShot(0) callbacks have had a chance to fire.
        self._property_undo_guard = 0

        # Slider-drag tracking: while _slider_dragging > 0 the view is updated in
        # real-time but no undo commands are pushed.  A single command is pushed in
        # _on_slider_committed once the last active slider is released.
        self._slider_dragging = 0
        self._slider_pre_drag_data = None

        # Guard flag: while True, add_variable skips marking the document as modified
        # and emitting _edited (used during undo/redo restore).
        self._restoring_state = False

        # Flag set by PropertySnapshotCommand before it calls tree.setCurrentItem()
        # to sync the tree selection.  on_tree_current_item_changed returns early
        # when this is True so the panel is not double-rebuilt.
        self._undo_redo_rebuilding = False

        # Progressive m_Modifiers loader (large Group nodes): session bumps invalidate QTimer chunks.
        self._modifier_load_session = 0
        self._modifier_batch_worker = None
        self._modifier_batch_signal_ref = None
        self._modifier_load_precomputed = None
        self._prewarm_cache = {}
        self._prewarm_order = deque()
        self._prewarm_cache_max = 32
        self._prewarm_signal_refs = {}

        # Choices rename undo state: captured on itemDoubleClicked, consumed by itemChanged.
        self._choices_rename_old_state = None

        # Choices widget-edit debounce (ComboboxTreeChild, VariableWidget, etc.)
        self._choices_widget_old_state = None
        self._choices_widget_debounce_desc = "Edit Choices"
        self._choices_widget_debounce = QTimer()
        self._choices_widget_debounce.setSingleShot(True)
        self._choices_widget_debounce.timeout.connect(self._push_choices_widget_edit)

        #Viewports
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
        self.ui.tree_hierarchy_widget.itemExpanded.connect(self._prewarm_node_modifiers)
        self.ui.tree_hierarchy_widget.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.ui.tree_hierarchy_widget.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.ui.tree_hierarchy_widget.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        self.ui.tree_hierarchy_widget.setDragEnabled(True)
        self.ui.tree_hierarchy_widget.setAcceptDrops(True)
        self.ui.tree_hierarchy_widget.setDropIndicatorShown(True)
        self.ui.tree_hierarchy_widget.setDragDropMode(QTreeWidget.InternalMove)

        # Content version
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

        # Modifiers panel scroll: cache once for batched repaint suppression (viewport).
        self._modifiers_scroll_area = None
        w = self.modifiers_group_instance.parentWidget()
        for _ in range(8):
            if w is None:
                break
            if isinstance(w, QScrollArea):
                self._modifiers_scroll_area = w
                break
            w = w.parentWidget()

        self.ui.tree_hierarchy_search_bar_widget.textChanged.connect(
            lambda text: self.search_hierarchy(text, self.ui.tree_hierarchy_widget.invisibleRootItem())
        )

        self._restore_user_prefs()

        # Hierarchy lives on the left; History / Variables / Choices stack on the right.
        self.addDockWidget(Qt.LeftDockWidgetArea, self.ui.HierarchyDock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.ui.VariablesDock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.ui.ChoicesDock)

        self._setup_history_dock()

        set_qdock_tab_style(self.findChildren)

        # Pre-warm pooled property widgets after first paint.
        # This pays widget setup cost at startup rather than on first node selection.
        QTimer.singleShot(500, self._prewarm_property_pools)

    def is_modified(self):
        return self._modified

    def _prewarm_property_pools(self):
        """
        Create and immediately release a small number of each common pooled
        property widget type so their constructors are paid during idle time.
        """
        try:
            dummy_sa = self.variable_viewport.ui.variables_scrollArea
            dummy_eid = self.element_id_generator

            PREWARM_COUNT = 4  # keep in sync with typical progressive chunking

            from src.editors.smartprop_editor.property.float import PropertyFloat
            from src.editors.smartprop_editor.property.bool import PropertyBool
            from src.editors.smartprop_editor.property.string import PropertyString
            from src.editors.smartprop_editor.property.vector3d import PropertyVector3D
            from src.editors.smartprop_editor.property.combobox import PropertyCombobox
            from src.editors.smartprop_editor.property.color import PropertyColor

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

    # ======================================[Properties groups]========================================
    def properties_groups_init(self):
        self.modifiers_group_instance = PropertiesGroupFrame(
            widget_list=self.ui.properties_layout,
            name=str("Modifiers"),
            group_type="modifier"
        )
        self.ui.properties_layout.insertWidget(0, self.modifiers_group_instance)
        self.modifiers_group_instance.add_signal.connect(self.add_an_operator)
        self.modifiers_group_instance.paste_signal.connect(self.paste_operator)

        self.selection_criteria_group_instance = PropertiesGroupFrame(
            widget_list=self.ui.properties_layout,
            name=str("Section criteria"),
            group_type="selection_criteria"
        )
        self.selection_criteria_group_instance.add_signal.connect(self.add_a_selection_criteria)
        self.ui.properties_layout.insertWidget(1, self.selection_criteria_group_instance)
        self.selection_criteria_group_instance.paste_signal.connect(self.paste_selection_criteria)

        self._selected_property_frame = None

        self.properties_groups_hide()

    def properties_groups_hide(self):
        self.ui.properties_spacer.hide()
        self.ui.properties_placeholder.show()
        self.modifiers_group_instance.hide()
        self.selection_criteria_group_instance.hide()

    def properties_groups_show(self):
        self.ui.properties_placeholder.hide()
        self.ui.properties_spacer.show()
        self.modifiers_group_instance.show()
        self.selection_criteria_group_instance.show()

    def _on_property_frame_selected(self, frame):
        for layout in (self.modifiers_group_instance.layout, self.selection_criteria_group_instance.layout):
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if isinstance(widget, PropertyFrame) and widget is not frame:
                    widget.set_selected(False)
        frame.set_selected(True)
        self._selected_property_frame = frame

    def _setup_property_frame_group(self, frame, group_type):
        frame.set_group_type(group_type)
        frame.selected_signal.connect(lambda f=frame: self._on_property_frame_selected(f))

    # ======================================[Progressive modifier frames (large m_Modifiers)]========================================
    def _modifier_batch_scroll_target(self):
        """Scroll area wrapping the modifiers group, or fallback to the group widget."""
        return self._modifiers_scroll_area or self.modifiers_group_instance

    def _modifier_batch_paint_suppress_widget(self):
        """Widget whose repaints to suppress during chunked modifier load (scroll viewport)."""
        t = self._modifier_batch_scroll_target()
        if isinstance(t, QScrollArea):
            return t.viewport()
        return t

    def _cancel_modifier_load(self):
        """
        Invalidate in-flight chunked modifier population (new tree selection / rebuild).
        Bumps session so scheduled QTimer callbacks no-op.
        """
        self._modifier_load_session += 1
        self._modifier_load_chunks = []
        self._modifier_load_index = 0
        self._modifier_load_precomputed = None
        bw = getattr(self, "_modifier_batch_worker", None)
        if bw is not None:
            try:
                bw.cancel()
            except Exception:
                pass
        self._modifier_batch_worker = None
        br = getattr(self, "_modifier_batch_signal_ref", None)
        if br is not None:
            QTimer.singleShot(0, br.deleteLater)
        self._modifier_batch_signal_ref = None
        sp = getattr(self, "_modifier_load_scroll_parent", None)
        if sp is not None:
            try:
                sp.setUpdatesEnabled(True)
                sp.update()
            except Exception:
                pass
        self._modifier_load_scroll_parent = None

    def _modifier_load_finish_suppress(self):
        sp = getattr(self, "_modifier_load_scroll_parent", None)
        if sp is not None:
            try:
                sp.setUpdatesEnabled(True)
                sp.update()
            except Exception:
                pass
        self._modifier_load_scroll_parent = None

    def _prewarm_evict_if_full(self):
        while len(self._prewarm_order) >= self._prewarm_cache_max:
            old = self._prewarm_order.popleft()
            self._prewarm_cache.pop(old, None)

    def _prewarm_node_modifiers(self, item):
        """On tree expand: batch-parse m_Modifiers in the background for faster later selection."""
        if item is None:
            return
        node_key = id(item)
        if node_key in self._prewarm_cache:
            return
        data = item.data(0, Qt.UserRole)
        if not isinstance(data, dict):
            return
        modifiers = data.get("m_Modifiers", []) or []
        if not modifiers:
            return
        self._prewarm_evict_if_full()
        self._prewarm_order.append(node_key)
        self._prewarm_cache[node_key] = None
        ordered_mods = list(reversed(modifiers))
        worker = BatchPropertyDataWorker(
            raw_values=ordered_mods,
            element_id_generator=self.element_id_generator,
            prop_classes_map_cache=PropertyFrame._prop_classes_map_cache,
            ordered_pairs_cache=PropertyFrame._ORDERED_PAIRS_CACHE,
        )
        self._prewarm_signal_refs[node_key] = worker.signals
        worker.signals.finished.connect(
            lambda results, k=node_key: self._on_modifier_prewarm_finished(k, results)
        )
        worker.signals.error.connect(
            lambda _err, k=node_key: self._on_modifier_prewarm_failed(k)
        )
        PropertyFrame._get_worker_pool().start(worker)

    def _on_modifier_prewarm_finished(self, node_key, results):
        sigs = self._prewarm_signal_refs.pop(node_key, None)
        if sigs is not None:
            QTimer.singleShot(0, sigs.deleteLater)
        if node_key not in self._prewarm_cache:
            return
        self._prewarm_cache[node_key] = results

    def _on_modifier_prewarm_failed(self, node_key):
        sigs = self._prewarm_signal_refs.pop(node_key, None)
        if sigs is not None:
            QTimer.singleShot(0, sigs.deleteLater)
        self._prewarm_cache.pop(node_key, None)
        try:
            self._prewarm_order.remove(node_key)
        except ValueError:
            pass

    def _take_prewarm_modifier_results(self, tree_item, ordered_len):
        """If expand pre-computed the same modifier stack, consume the cache entry."""
        if tree_item is None:
            return None
        node_key = id(tree_item)
        entry = self._prewarm_cache.get(node_key)
        if not isinstance(entry, list) or len(entry) != ordered_len:
            return None
        del self._prewarm_cache[node_key]
        try:
            self._prewarm_order.remove(node_key)
        except ValueError:
            pass
        return entry

    def _submit_modifier_batch_worker(self, session, ordered_modifiers):
        worker = BatchPropertyDataWorker(
            raw_values=ordered_modifiers,
            element_id_generator=self.element_id_generator,
            prop_classes_map_cache=PropertyFrame._prop_classes_map_cache,
            ordered_pairs_cache=PropertyFrame._ORDERED_PAIRS_CACHE,
        )
        self._modifier_batch_worker = worker
        self._modifier_batch_signal_ref = worker.signals

        def _on_ready(results, sess=session):
            self._on_modifier_batch_ready(sess, results)

        def _on_err(msg, sess=session):
            self._on_modifier_batch_error(sess, msg)

        worker.signals.finished.connect(_on_ready)
        worker.signals.error.connect(_on_err)
        PropertyFrame._get_worker_pool().start(worker)

    def _on_modifier_batch_ready(self, session, results):
        self._modifier_batch_worker = None
        br = getattr(self, "_modifier_batch_signal_ref", None)
        if br is not None:
            QTimer.singleShot(0, br.deleteLater)
        self._modifier_batch_signal_ref = None
        if session != self._modifier_load_session:
            return
        self._modifier_load_precomputed = results
        self._load_next_modifier_chunk(session)

    def _on_modifier_batch_error(self, session, _msg):
        self._modifier_batch_worker = None
        br = getattr(self, "_modifier_batch_signal_ref", None)
        if br is not None:
            QTimer.singleShot(0, br.deleteLater)
        self._modifier_batch_signal_ref = None
        if session != self._modifier_load_session:
            return
        self._modifier_load_precomputed = None
        self._load_next_modifier_chunk(session)

    def _wire_modifier_property_frame(self, frame, pending_init, inited_frame_ids):
        frame.edited.connect(self.update_tree_item_value)
        self._setup_property_frame_group(frame, "modifier")
        pending_init["remaining"] += 1
        frame_id = id(frame)

        def _on_prop_frame_inited(fid=frame_id):
            if fid in inited_frame_ids:
                return
            inited_frame_ids.add(fid)
            pending_init["remaining"] -= 1
            if pending_init["remaining"] <= 0:
                self._dec_property_undo_guard()

        frame.edited.connect(_on_prop_frame_inited)
        frame.slider_pressed.connect(self._on_slider_started)
        frame.committed.connect(self._on_slider_committed)

    def _acquire_modifier_property_frame(self, modifier_value, precomputed=None):
        """Pool acquire with fallback to direct PropertyFrame (same layout wiring as before)."""
        val = fast_deepcopy(modifier_value)
        if not PropertyFrame._is_complete_precomputed_payload(precomputed):
            precomputed = None
        if precomputed is not None:
            prop_class = precomputed.get("prop_class") or ""
        else:
            wc = val.get("_class", "") if isinstance(val, dict) else ""
            prop_class = wc.split("_", 1)[-1] if wc else ""
        kwargs = dict(
            variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
            element_id_generator=self.element_id_generator,
            tree_hierarchy=self.ui.tree_hierarchy_widget,
        )
        mod_layout = self.modifiers_group_instance.layout
        try:
            from src.editors.smartprop_editor.property_widget_pool import PropertyWidgetPool

            return PropertyWidgetPool.instance().acquire(
                prop_class=prop_class,
                value=val,
                widget_list=mod_layout,
                precomputed=precomputed,
                **kwargs,
            )
        except Exception:
            if PropertyFrame._is_complete_precomputed_payload(precomputed):
                return PropertyFrame(
                    value=precomputed["value"],
                    widget_list=mod_layout,
                    precomputed=precomputed,
                    parent=self,
                    **kwargs,
                )
            return PropertyFrame(
                value=val,
                widget_list=mod_layout,
                parent=self,
                **kwargs,
            )

    def _load_next_modifier_chunk(self, session):
        if session != self._modifier_load_session:
            return
        chunks = getattr(self, "_modifier_load_chunks", None) or []
        idx = getattr(self, "_modifier_load_index", 0)
        mod_layout = getattr(self, "_modifier_load_mod_layout", None)
        pending_init = getattr(self, "_modifier_load_pending_init", None)
        inited_frame_ids = getattr(self, "_modifier_load_inited_ids", None)
        delay_ms = getattr(self, "_modifier_load_delay_ms", 16)

        if not chunks or mod_layout is None or pending_init is None or inited_frame_ids is None:
            self._modifier_load_finish_suppress()
            return

        if idx >= len(chunks):
            self._modifier_load_finish_suppress()
            return

        chunk = chunks[idx]
        self._modifier_load_index = idx + 1

        offset = self._modifier_load_offsets[idx]
        precomputed_list = getattr(self, "_modifier_load_precomputed", None)

        for j, modifier_value in enumerate(chunk):
            if session != self._modifier_load_session:
                return
            pc = None
            if precomputed_list is not None:
                try:
                    pc = precomputed_list[offset + j]
                except IndexError:
                    pc = None
            frame = self._acquire_modifier_property_frame(modifier_value, precomputed=pc)
            self._wire_modifier_property_frame(frame, pending_init, inited_frame_ids)
            mod_layout.insertWidget(0, frame)

        if session != self._modifier_load_session:
            return

        if self._modifier_load_index < len(chunks):
            QTimer.singleShot(delay_ms, lambda s=session: self._load_next_modifier_chunk(s))
        else:
            self._modifier_load_finish_suppress()

    def _populate_modifiers_progressive(
        self,
        data_modif,
        pending_init,
        inited_frame_ids,
        tree_item=None,
        chunk_size=4,
        delay_ms=16,
    ):
        """
        Insert modifier PropertyFrames in chunks so 35 modifiers do not all start
        workers/timers in one event-loop slice. Order matches reversed(insertWidget(0,...)).
        One BatchPropertyDataWorker prepares all modifiers; optional prewarm skips the batch.
        """
        if not data_modif:
            return

        # Caller must _cancel_modifier_load() before this (selection / rebuild).
        session = self._modifier_load_session

        ordered = list(reversed(data_modif))
        self._modifier_load_chunks = [
            ordered[i : i + chunk_size] for i in range(0, len(ordered), chunk_size)
        ]
        offsets = [0]
        for chunk in self._modifier_load_chunks:
            offsets.append(offsets[-1] + len(chunk))
        self._modifier_load_offsets = offsets
        self._modifier_load_index = 0
        self._modifier_load_mod_layout = self.modifiers_group_instance.layout
        self._modifier_load_pending_init = pending_init
        self._modifier_load_inited_ids = inited_frame_ids
        self._modifier_load_delay_ms = delay_ms

        precomputed_list = self._take_prewarm_modifier_results(tree_item, len(ordered))
        self._modifier_load_precomputed = precomputed_list

        paint_w = self._modifier_batch_paint_suppress_widget()
        self._modifier_load_scroll_parent = paint_w
        if paint_w is not None:
            paint_w.setUpdatesEnabled(False)

        if precomputed_list is not None:
            self._load_next_modifier_chunk(session)
        else:
            self._submit_modifier_batch_worker(session, ordered)

    # ======================================[Tree Hierarchy updating]========================================
    def on_tree_current_item_changed(self, current_item, previous_item):
        # When a PropertySnapshotCommand undo/redo calls setCurrentItem to sync
        # the tree selection, we must not rebuild the panel here — the command
        # handles that itself via _rebuild_properties_panel.
        if self._undo_redo_rebuilding:
            return

        # Raise the guard BEFORE creating any PropertyFrame so the guard decrement
        # is queued AFTER all _finish_init singleShot(0) callbacks.  The decrement
        # is scheduled at the very end of this function, after all frames are
        # instantiated, ensuring the queue order is:
        #   [_finish_init callbacks …, _dec_property_undo_guard]
        self._property_undo_guard += 1

        # With PropertyFrame init moving off the main thread (QThreadPool),
        # the old "decrement after QTimer(0)" timing can release the guard too
        # early.  We keep it raised until all PropertyFrame instances created
        # for this selection have emitted their initial `edited` (phase 2).
        pending_init = {"remaining": 0}
        inited_frame_ids = set()

        self._cancel_modifier_load()

        # Cancel any in-progress slider drag when the selection changes.
        self._slider_dragging = 0
        self._slider_pre_drag_data = None

        item = current_item
        if current_item is not None:
            self.properties_groups_show()
        else:
            self.properties_groups_hide()

        try:
            # Remove any existing PropertyFrame widgets from their layouts immediately
            # so that update_tree_item_value never sees both the old (pending deletion)
            # and new frames at the same time.  removeWidget() detaches the widget from
            # layout management right away; deleteLater() handles deferred memory cleanup.
            for layout in (
                self.ui.properties_layout,
                self.modifiers_group_instance.layout,
                self.selection_criteria_group_instance.layout,
            ):
                for i in reversed(range(layout.count())):
                    widget = layout.itemAt(i).widget()
                    if isinstance(widget, PropertyFrame):
                        widget.cancel_worker()
                        layout.removeWidget(widget)
                        widget.hide()
                        if layout is self.modifiers_group_instance.layout:
                            from src.editors.smartprop_editor.property_widget_pool import (
                                PropertyWidgetPool,
                            )

                            PropertyWidgetPool.instance().release(
                                getattr(widget, "prop_class", None), widget
                            )
                        else:
                            try:
                                # Return pooled child widgets to their pools first.
                                widget._clear_widgets()
                            except Exception:
                                pass
                            widget.deleteLater()
        except Exception as error:
            print(error)

        try:
            # No tree selection: panel was cleared above; do not touch item.data.
            if item is not None:
                # deepcopy so we never mutate the data stored in the tree item
                data = fast_deepcopy(item.data(0, Qt.UserRole))
                data_modif = data.pop("m_Modifiers", None) or []
                data_sel_criteria = data.pop("m_SelectionCriteria", None) or []
                property_instance = PropertyFrame(
                    widget_list=self.ui.properties_layout,
                    value=data,
                    variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
                    element=True,
                    tree_hierarchy=self.ui.tree_hierarchy_widget,
                    element_id_generator=self.element_id_generator,
                    parent=self,
                )
                property_instance.edited.connect(self.update_tree_item_value)

                pending_init["remaining"] += 1
                frame_id = id(property_instance)

                def _on_prop_frame_inited(fid=frame_id):
                    if fid in inited_frame_ids:
                        return
                    inited_frame_ids.add(fid)
                    pending_init["remaining"] -= 1
                    if pending_init["remaining"] <= 0:
                        self._dec_property_undo_guard()

                property_instance.edited.connect(_on_prop_frame_inited)

                property_instance.slider_pressed.connect(self._on_slider_started)
                property_instance.committed.connect(self._on_slider_committed)
                self.ui.properties_layout.insertWidget(0, property_instance)

                if data_modif:
                    self._populate_modifiers_progressive(
                        data_modif,
                        pending_init,
                        inited_frame_ids,
                        tree_item=item,
                    )

                if data_sel_criteria:
                    for entry in reversed(data_sel_criteria):
                        prop_instance = PropertyFrame(
                            widget_list=self.selection_criteria_group_instance.layout,
                            value=fast_deepcopy(entry),
                            variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
                            tree_hierarchy=self.ui.tree_hierarchy_widget,
                            element_id_generator=self.element_id_generator,
                            parent=self,
                        )
                        prop_instance.edited.connect(self.update_tree_item_value)
                        self._setup_property_frame_group(prop_instance, "selection_criteria")

                        pending_init["remaining"] += 1
                        frame_id = id(prop_instance)

                        def _on_prop_frame_inited(fid=frame_id):
                            if fid in inited_frame_ids:
                                return
                            inited_frame_ids.add(fid)
                            pending_init["remaining"] -= 1
                            if pending_init["remaining"] <= 0:
                                self._dec_property_undo_guard()

                        prop_instance.edited.connect(_on_prop_frame_inited)

                        prop_instance.slider_pressed.connect(self._on_slider_started)
                        prop_instance.committed.connect(self._on_slider_committed)
                        self.selection_criteria_group_instance.layout.insertWidget(0, prop_instance)
        except Exception as error:
            print(error)

        # If no PropertyFrames were created, release the guard on the next tick.
        # Otherwise, it will be released after the last frame emits its initial edited.
        if pending_init["remaining"] <= 0:
            QTimer.singleShot(0, self._dec_property_undo_guard)

    def update_tree_item_value(self, item=None):
        if item is None:
            item = self.ui.tree_hierarchy_widget.currentItem()
        if item:
            # Capture old state BEFORE assembling the new value
            old_data = fast_deepcopy(item.data(0, Qt.UserRole))

            output_value = {}
            modifiers = []
            selection_criteria = []

            # Collect modifiers
            for i in range(self.modifiers_group_instance.layout.count()):
                widget = self.modifiers_group_instance.layout.itemAt(i).widget()
                if isinstance(widget, PropertyFrame):
                    value = widget.value
                    if value is not None:
                        modifiers.append(value)

            # Collect selection criteria
            for i in range(self.selection_criteria_group_instance.layout.count()):
                widget = self.selection_criteria_group_instance.layout.itemAt(i).widget()
                if isinstance(widget, PropertyFrame):
                    value = widget.value
                    if value is not None:
                        selection_criteria.append(value)

            # Collect main properties
            for i in range(self.ui.properties_layout.count()):
                widget = self.ui.properties_layout.itemAt(i).widget()
                if isinstance(widget, PropertyFrame):
                    value = widget.value
                    if value is not None:
                        output_value.update(value)

            try:
                if modifiers[0] is None:
                    modifiers = []
            except IndexError:
                pass
            try:
                if selection_criteria[0] is None:
                    selection_criteria = []
            except IndexError:
                pass

            output_value.update({"m_Modifiers": modifiers})
            output_value.update({"m_SelectionCriteria": selection_criteria})

            # Safety: if the main PropertyFrame hasn't emitted on_edited yet its value
            # won't contain '_class', meaning the panel is still initializing.  Writing
            # an incomplete dict would corrupt the stored data and cause a KeyError the
            # next time _rebuild_properties_panel tries to recreate the PropertyFrame.
            if '_class' not in output_value:
                return

            item.setData(0, Qt.UserRole, output_value)

            # Mark document as modified
            self._modified = True
            self._edited.emit()

            # Push undo command only when something actually changed, we are not
            # inside a panel rebuild triggered by undo/redo, and no slider is
            # currently being dragged.  During a slider drag the view is updated
            # in real-time but only one command is pushed on release via
            # _on_slider_committed, which preserves the true pre-drag state.
            if not self._property_undo_guard and not self._slider_dragging and output_value != old_data:
                new_data = fast_deepcopy(output_value)
                cmd = PropertySnapshotCommand(self, item, old_data, new_data)
                self.undo_stack.push(cmd)

    # ======================================[Event Filter]========================================
    def eventFilter(self, source, event):
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
                if event.matches(QKeySequence.Undo):
                    self.undo_stack.undo()
                    return True
                if event.matches(QKeySequence.Redo):
                    self.undo_stack.redo()
                    return True
                if source.viewport().underMouse():
                    if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
                        self.add_an_element()
                        return True
        return super().eventFilter(source, event)

    # ======================================[Tree Widget Hierarchy New Element]========================================
    def add_preset(self):
        presets = []
        for root, dirs, files in os.walk(SmartPropEditor_Preset_Path):
            for file in files:
                presets.append({file: os.path.join(root, file)})
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

        def populate_choices(data):
            if data is None:
                print("No choices")
                return
            for choice in data:
                name = choice["m_Name"]
                default = choice.get("m_DefaultOption", None)
                options = choice.get("m_Options", None)
                new_choice = AddChoice(
                    name=name,
                    tree=self.ui.choices_tree_widget,
                    default=default,
                    variables_scrollArea=self.variable_viewport.ui.variables_scrollArea
                ).item
                if options:
                    for option in options:
                        option_item = AddOption(parent=new_choice, name=option["m_Name"]).item
                        variables_list_ = option["m_VariableValues"]
                        for variable in variables_list_:
                            AddVariable(
                                parent=option_item,
                                variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
                                name=variable["m_TargetName"],
                                type=variable.get("m_DataType", ""),
                                value=variable["m_Value"]
                            )

        def populate_variables(data):
            if isinstance(data, list):
                for item in data:
                    var_class = (item["_class"]).replace(variable_prefix, "")
                    var_name = item.get("m_VariableName", None)
                    var_display_name = item.get("m_DisplayName", None)
                    if var_display_name is None:
                        var_display_name = item.get("m_ParameterName", None)
                    var_visible_in_editor = bool(item.get("m_bExposeAsParameter", None))
                    var_value = {
                        "default": item.get("m_DefaultValue", None),
                        "model": item.get("m_sModelName", None),
                        "m_nElementID": item.get("m_nElementID", None),
                        'm_HideExpression': item.get("m_HideExpression", None)
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
                        self.add_variable(
                            name=var_name,
                            var_value=var_value,
                            var_visible_in_editor=var_visible_in_editor,
                            var_class=var_class,
                            var_display_name=var_display_name
                        )

        if self.ui.tree_hierarchy_widget.currentItem() is None:
            parent_item = self.ui.tree_hierarchy_widget.invisibleRootItem()
        else:
            parent_item = self.ui.tree_hierarchy_widget.currentItem()

        populate_tree(__data, parent_item)
        populate_choices(__data.get("m_Choices", None))
        populate_variables(__data.get("m_Variables"))

    def load_preset(self, name: str = None, path: str = None):
        with open(path, "r") as file:
            __data = file.read()
        __data = Kv3ToJson(self.fix_format(__data))

        parent = (
            self.ui.tree_hierarchy_widget.currentItem()
            or self.ui.tree_hierarchy_widget.invisibleRootItem()
        )
        items = [
            deserialize_hierarchy_item(child, self.element_id_generator)
            for child in __data.get("m_Children", [])
        ]
        if items:
            self.undo_stack.push(NewFromPresetCommand(self.ui.tree_hierarchy_widget, parent, items))
            self._modified = True
            self._edited.emit()

    def add_an_element(self):
        self.popup_menu = PopupMenu(elements_list, add_once=False, window_name="SPE_elements")
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

    # ======================================[Properties operator]========================================
    def new_operator(self, element_class, element_value):
        operator_instance = PropertyFrame(
            widget_list=self.modifiers_group_instance.layout,
            value=element_value,
            variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
            tree_hierarchy=self.ui.tree_hierarchy_widget,
            element_id_generator=self.element_id_generator,
            parent=self,
        )
        operator_instance.edited.connect(self.update_tree_item_value)
        self._setup_property_frame_group(operator_instance, "modifier")
        self.modifiers_group_instance.layout.insertWidget(1, operator_instance)
        self.update_tree_item_value()

    def add_an_operator(self):
        """
        Combines operators and filters, determines which classes already exist,
        excludes duplicates unless an item is forced, and then displays a popup
        menu to add new operators.
        """
        operators_and_filters = operators_list + filters_list
        elements_in_popupmenu = []
        exists_classes = []
        force_items_names = ["SetVariable", "SaveState", 'Comment']
        force_items = []
        for item in operators_and_filters:
            for key in item.keys():
                if key in force_items_names:
                    force_items.append(item)
        for i in range(self.modifiers_group_instance.layout.count()):
            widget = self.modifiers_group_instance.layout.itemAt(i).widget()
            if isinstance(widget, PropertyFrame):
                exists_classes.append(widget.name)
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
        self.popup_menu = PopupMenu(
            elements_in_popupmenu,
            add_once=True,
            window_name="SPE_operators",
            ignore_list=force_items_names
        )
        self.popup_menu.add_property_signal.connect(lambda name, value: self.new_operator(name, value))
        self.popup_menu.show()

    def paste_operator(self):
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text()
        clipboard_data = clipboard_text.split(";;")

        if clipboard_data[0] == "hammer5tools:smartprop_editor_property":
            data = ast.literal_eval(clipboard_data[2])
            data = self.element_id_generator.update_value(data, force=True)
            operator_instance = PropertyFrame(
                widget_list=self.modifiers_group_instance.layout,
                value=data,
                variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
                tree_hierarchy=self.ui.tree_hierarchy_widget,
                element_id_generator=self.element_id_generator,
                parent=self,
            )
            operator_instance.edited.connect(self.update_tree_item_value)
            self._setup_property_frame_group(operator_instance, "modifier")
            self.modifiers_group_instance.layout.insertWidget(1, operator_instance)
        else:
            print("Clipboard data format is not valid.")
        self.update_tree_item_value()

    # ======================================[Properties Selection Criteria]========================================
    def add_a_selection_criteria(self):
        elements_in_popupmenu = []
        exists_classes = []
        for i in range(self.selection_criteria_group_instance.layout.count()):
            widget = self.selection_criteria_group_instance.layout.itemAt(i).widget()
            if isinstance(widget, PropertyFrame):
                exists_classes.append(widget.name)
        for item in selection_criteria_list:
            for key, value in item.items():
                if key not in exists_classes:
                    elements_in_popupmenu.append(item)
        self.popup_menu = PopupMenu(elements_in_popupmenu, add_once=True, window_name="SPE_selection_criteria")
        self.popup_menu.add_property_signal.connect(lambda name, value: self.new_selection_criteria(name, value))
        self.popup_menu.show()

    def new_selection_criteria(self, element_class, element_value):
        operator_instance = PropertyFrame(
            widget_list=self.selection_criteria_group_instance.layout,
            value=element_value,
            variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
            tree_hierarchy=self.ui.tree_hierarchy_widget,
            element_id_generator=self.element_id_generator,
            parent=self,
        )
        operator_instance.edited.connect(self.update_tree_item_value)
        self._setup_property_frame_group(operator_instance, "selection_criteria")
        self.selection_criteria_group_instance.layout.insertWidget(1, operator_instance)
        self.update_tree_item_value()

    def paste_selection_criteria(self):
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text()
        clipboard_data = clipboard_text.split(";;")

        if clipboard_data[0] == "hammer5tools:smartprop_editor_property":
            data = ast.literal_eval(clipboard_data[2])
            data = self.element_id_generator.update_value(data, force=True)
            operator_instance = PropertyFrame(
                widget_list=self.selection_criteria_group_instance.layout,
                value=data,
                variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
                tree_hierarchy=self.ui.tree_hierarchy_widget,
                element_id_generator=self.element_id_generator,
                parent=self,
            )
            operator_instance.edited.connect(self.update_tree_item_value)
            self._setup_property_frame_group(operator_instance, "selection_criteria")
            self.selection_criteria_group_instance.layout.insertWidget(1, operator_instance)
        else:
            print("Clipboard data format is not valid.")
        self.update_tree_item_value()

    # ======================================[Open File]========================================
    @exception_handler
    def open_file(self, filename):
        # Suppress property snapshot commands while the file is being loaded.
        # The guard is released in the finally block so that @exception_handler
        # catching a mid-load exception can never leave the guard permanently
        # raised (which would permanently block all future property undo entries).
        self._property_undo_guard += 1
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
                for item in variables:
                    var_class = (item["_class"]).replace(variable_prefix, "")
                    var_name = item.get("m_VariableName", None)
                    var_display_name = item.get("m_DisplayName", None)
                    if var_display_name is None:
                        var_display_name = item.get("m_ParameterName", None)
                    var_visible_in_editor = bool(item.get("m_bExposeAsParameter", None))

                    var_value = {
                        "default": item.get("m_DefaultValue", None),
                        "model": item.get("m_sModelName", None),
                        "m_nElementID": item.get("m_nElementID", None),
                        'm_HideExpression': item.get("m_HideExpression", None)
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

            self._modified = False
        finally:
            # Always release the guard and clear the stack, even if an exception
            # occurred mid-load.  Both are deferred so all singleShot(0)
            # _finish_init callbacks that were queued during file load fire first.
            QTimer.singleShot(0, self._dec_property_undo_guard)
            QTimer.singleShot(0, self.undo_stack.clear)

    # ======================================[Save File]========================================
    def save_file(self, external=False, realtime_save=False):
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
            current_folder = self.parent.mini_explorer.get_current_folder(True)
            filename, _ = QFileDialog.getSaveFileName(
                None,
                "Save File",
                current_folder,
                "VSmart Files (*.vsmart);;All Files (*)"
            )
        self.get_variables(self.variable_viewport.ui.variables_scrollArea)
        content_version = self.content_version_spinbox.value()
        if filename:
            if not realtime_save:
                try:
                    VsmartSaveInstance = VsmartSave(filename=filename, tree=self.ui.tree_hierarchy_widget,choices_tree=self.ui.choices_tree_widget,variables_layout=self.variable_viewport.ui.variables_scrollArea, content_version=content_version)
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
            else:
                VsmartSaveInstance = VsmartSave(filename=filename,tree=self.ui.tree_hierarchy_widget,choices_tree=self.ui.choices_tree_widget, variables_layout=self.variable_viewport.ui.variables_scrollArea, content_version=content_version)

            self.opened_file = VsmartSaveInstance.filename
            if self.update_title:
                self.update_title("saved", filename)
            # Mark document as unmodified after saving
            self._modified = False

    # ======================================[Choices Context Menu]========================================
    def open_MenuChoices(self, position):
        menu = QMenu()
        item = self.ui.choices_tree_widget.itemAt(position)

        add_choice = menu.addAction("Add Choice")
        add_choice.triggered.connect(lambda: self._choices_op_with_undo(
            "Add Choice",
            lambda: AddChoice(
                tree=self.ui.choices_tree_widget,
                variables_scrollArea=self.variable_viewport.ui.variables_scrollArea
            )
        ))

        if item:
            if item.text(2) == "choice":
                add_option = menu.addAction("Add Option")
                add_option.triggered.connect(lambda: self._choices_op_with_undo(
                    "Add Option",
                    lambda: AddOption(parent=item, name="Option")
                ))
            elif item.text(2) == "option":
                add_variable = menu.addAction("Add Variable")
                add_variable.triggered.connect(lambda: self._choices_op_with_undo(
                    "Add Variable to Choice",
                    lambda: AddVariable(
                        parent=item,
                        variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
                        name="default",
                        value="",
                        type="",
                        element_id_generator=self.element_id_generator
                    )
                ))

        menu.addSection("")
        move_up_action = menu.addAction("Move Up")
        move_down_action = menu.addAction("Move Down")
        move_up_action.triggered.connect(lambda: self._choices_op_with_undo(
            "Move Up", lambda: self.move_tree_item(self.ui.choices_tree_widget, -1)
        ))
        move_down_action.triggered.connect(lambda: self._choices_op_with_undo(
            "Move Down", lambda: self.move_tree_item(self.ui.choices_tree_widget, 1)
        ))
        menu.addSection("")

        remove_action = menu.addAction("Remove")
        remove_action.triggered.connect(lambda: self._choices_op_with_undo(
            "Remove Choice", lambda: self.remove_tree_item(self.ui.choices_tree_widget)
        ))

        menu.exec(self.ui.choices_tree_widget.viewport().mapToGlobal(position))

    # ======================================[Variables Actions]========================================
    def add_variable(
            self,
            name,
            var_class,
            var_value,
            var_visible_in_editor,
            var_display_name,
            index: int = None
    ):
        self.variable_viewport.add_variable(name, var_class, var_value, var_visible_in_editor, var_display_name, index)
        if not self._restoring_state:
            self._modified = True
            self._edited.emit()

    def duplicate_variable(self, __data, __index):
        self.variable_viewport.duplicate_variable(__data, __index)

    def add_new_variable(self):
        self.variable_viewport.add_new_variable()

    # ======================================[Variables Other]========================================

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

    # ======================================[Tree widget hierarchy filter]========================================
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

    def open_bulk_model_importer(self):
        from src.editors.smartprop_editor.actions.bulk_model_importer import BulkModelImporterDialog
        from src.editors.smartprop_editor._common import get_clean_class_name_value, get_label_id_from_value
        from src.widgets import HierarchyItemModel
        import os
        dialog = BulkModelImporterDialog(self, current_folder=self.parent.mini_explorer.get_current_folder(True))
        def on_accept(files, create_ref, ref_index):
            addon_path = get_addon_dir()
            ref_id = None
            parent_item = self.ui.tree_hierarchy_widget.currentItem()
            if parent_item is None:
                parent_item = self.ui.tree_hierarchy_widget.invisibleRootItem()
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

    # ======================================[Tree widget hierarchy context menu]========================================
    def open_hierarchy_menu(self, position):
        menu = QMenu()
        add_new_action = menu.addAction("New element")
        add_new_action.triggered.connect(self.add_an_element)
        add_new_action.setShortcut(QKeySequence("Ctrl+F"))

        add_preset_action = menu.addAction("New from preset")
        add_preset_action.triggered.connect(self.add_preset)

        menu.addSeparator()

        remove_action = menu.addAction("Remove")
        remove_action.triggered.connect(lambda: self.ui.tree_hierarchy_widget.DeleteSelectedItems())
        remove_action.setShortcut(QKeySequence("Delete"))

        duplicate_action = menu.addAction("Duplicate")
        duplicate_action.triggered.connect(lambda: self.ui.tree_hierarchy_widget.DuplicateSelectedItems(self.element_id_generator))
        duplicate_action.setShortcut(QKeySequence("Ctrl+D"))

        grouping_action = menu.addAction("Group selected")
        grouping_action.triggered.connect(lambda: self.undo_stack.push(GroupElementsCommand(self.ui.tree_hierarchy_widget)))
        grouping_action.setShortcut(QKeySequence("Ctrl+G"))

        menu.addSeparator()

        copy_action = menu.addAction("Copy")
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(lambda: self.copy_item(self.ui.tree_hierarchy_widget))

        copy_action = menu.addAction("Cut")
        copy_action.setShortcut(QKeySequence.Cut)
        copy_action.triggered.connect(lambda: self.cut_item(self.ui.tree_hierarchy_widget))

        paste_action = menu.addAction("Paste")
        paste_action.setShortcut(QKeySequence.Paste)
        paste_action.triggered.connect(lambda: self.paste_item(self.ui.tree_hierarchy_widget))

        paste_replace_action = menu.addAction("Paste with replacement")
        paste_replace_action.setShortcut(QKeySequence("Ctrl+Shift+V"))
        paste_replace_action.triggered.connect(lambda: self.new_item_with_replacement(QApplication.clipboard().text()))

        bulk_import_action = menu.addAction("Bulk Model Importer")
        bulk_import_action.triggered.connect(self.open_bulk_model_importer)

        menu.exec(self.ui.tree_hierarchy_widget.viewport().mapToGlobal(position))

    # ======================================[Tree widget functions]========================================
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
        from src.common import Kv3ToJson
        from src.editors.smartprop_editor.vsmart import deserialize_hierarchy_item
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
                if itm == itm.treeWidget().invisibleRootItem():
                    pass
                else:
                    parent = itm.parent() or itm.treeWidget().invisibleRootItem()
                    idx = parent.indexOfChild(itm)
                    parent.takeChild(idx)
        self._modified = True
        self._edited.emit()

    # ======================================[Window State]========================================
    def _restore_user_prefs(self):
        geo = self.settings.value("SmartPropEditorMainWindow/geometry")
        if geo:
            self.restoreGeometry(geo)

        state = self.settings.value("SmartPropEditorMainWindow/windowState_v2")
        if state:
            self.restoreState(state)

        saved_index = self.settings.value("SmartPropEditorMainWindow/currentComboBoxIndex")
        if saved_index is not None:
            self.variable_viewport.ui.add_new_variable_combobox.setCurrentIndex(int(saved_index))

    def _save_user_prefs(self):
        current_index = self.ui.add_new_variable_combobox.currentIndex()
        self.settings.setValue("SmartPropEditorMainWindow/currentComboBoxIndex", current_index)
        self.settings.setValue("SmartPropEditorMainWindow/geometry", self.saveGeometry())
        self.settings.setValue("SmartPropEditorMainWindow/windowState_v2", self.saveState())

    # ======================================[Properties Panel Undo]========================================
    def _rebuild_properties_panel(self, item):
        """Rebuild the properties panel from the current tree-item data.

        Called by PropertySnapshotCommand during undo/redo.  The
        _property_undo_guard counter is incremented here and decremented after
        all QTimer.singleShot(0) deferred-init callbacks have fired, so that
        the resulting update_tree_item_value() calls do NOT push new commands.
        """
        self._property_undo_guard += 1
        pending_init = {"remaining": 0}
        inited_frame_ids = set()
        self._cancel_modifier_load()
        # Cancel any in-progress slider drag so stale state is not committed.
        self._slider_dragging = 0
        self._slider_pre_drag_data = None
        try:
            # Clear existing PropertyFrame widgets.  hide() fires synchronously
            # so the panel is cleared visually before the new content is built.
            for layout in (
                self.ui.properties_layout,
                self.modifiers_group_instance.layout,
                self.selection_criteria_group_instance.layout,
            ):
                for i in reversed(range(layout.count())):
                    widget = layout.itemAt(i).widget()
                    if isinstance(widget, PropertyFrame):
                        widget.cancel_worker()
                        layout.removeWidget(widget)
                        widget.hide()
                        if layout is self.modifiers_group_instance.layout:
                            from src.editors.smartprop_editor.property_widget_pool import (
                                PropertyWidgetPool,
                            )

                            PropertyWidgetPool.instance().release(
                                getattr(widget, "prop_class", None), widget
                            )
                        else:
                            try:
                                # Return pooled child widgets to their pools first.
                                widget._clear_widgets()
                            except Exception:
                                pass
                            widget.deleteLater()

            # Show/hide panel groups
            if item is not None:
                self.properties_groups_show()
            else:
                self.properties_groups_hide()
                return

            # Create new PropertyFrame widgets from the item's stored data
            data = fast_deepcopy(item.data(0, Qt.UserRole))
            if data is None:
                return
            data_modif = data.pop("m_Modifiers", None) or []
            data_sel_criteria = data.pop("m_SelectionCriteria", None) or []

            prop = PropertyFrame(
                widget_list=self.ui.properties_layout,
                value=data,
                variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
                element=True,
                tree_hierarchy=self.ui.tree_hierarchy_widget,
                element_id_generator=self.element_id_generator,
                parent=self,
            )
            prop.edited.connect(self.update_tree_item_value)

            pending_init["remaining"] += 1
            frame_id = id(prop)

            def _on_prop_frame_inited(fid=frame_id):
                if fid in inited_frame_ids:
                    return
                inited_frame_ids.add(fid)
                pending_init["remaining"] -= 1
                if pending_init["remaining"] <= 0:
                    self._dec_property_undo_guard()

            prop.edited.connect(_on_prop_frame_inited)

            prop.slider_pressed.connect(self._on_slider_started)
            prop.committed.connect(self._on_slider_committed)
            self.ui.properties_layout.insertWidget(0, prop)

            if data_modif:
                self._populate_modifiers_progressive(
                    data_modif,
                    pending_init,
                    inited_frame_ids,
                    tree_item=item,
                )

            for entry in reversed(data_sel_criteria):
                p = PropertyFrame(
                    widget_list=self.selection_criteria_group_instance.layout,
                    value=fast_deepcopy(entry),
                    variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
                    tree_hierarchy=self.ui.tree_hierarchy_widget,
                    element_id_generator=self.element_id_generator,
                    parent=self,
                )
                p.edited.connect(self.update_tree_item_value)
                self._setup_property_frame_group(p, "selection_criteria")

                pending_init["remaining"] += 1
                frame_id = id(p)

                def _on_prop_frame_inited(fid=frame_id):
                    if fid in inited_frame_ids:
                        return
                    inited_frame_ids.add(fid)
                    pending_init["remaining"] -= 1
                    if pending_init["remaining"] <= 0:
                        self._dec_property_undo_guard()

                p.edited.connect(_on_prop_frame_inited)

                p.slider_pressed.connect(self._on_slider_started)
                p.committed.connect(self._on_slider_committed)
                self.selection_criteria_group_instance.layout.insertWidget(0, p)

        except Exception as e:
            print(f"[SPE] _rebuild_properties_panel: ERROR — {e}")
        finally:
            # If no PropertyFrames were created, release the guard on the next tick.
            # Otherwise it will be released after the last frame emits its initial edited.
            if pending_init["remaining"] <= 0:
                QTimer.singleShot(0, self._dec_property_undo_guard)

    def _dec_property_undo_guard(self):
        self._property_undo_guard = max(0, self._property_undo_guard - 1)

    def _get_nth_property_frame(self, layout, n):
        """Return the Nth PropertyFrame in *layout*, skipping non-PropertyFrame widgets."""
        count = 0
        for i in range(layout.count()):
            w = layout.itemAt(i).widget()
            if isinstance(w, PropertyFrame):
                if count == n:
                    return w
                count += 1
        return None

    def _rebuild_group_section(self, key, new_data, item):
        """Rebuild only the modifiers or selection criteria section (not the whole panel)."""
        if key == 'm_Modifiers':
            layout = self.modifiers_group_instance.layout
            new_list = new_data.get('m_Modifiers', [])
        else:
            layout = self.selection_criteria_group_instance.layout
            new_list = new_data.get('m_SelectionCriteria', [])

        # Clear existing PropertyFrames in this section only
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if isinstance(widget, PropertyFrame):
                widget.cancel_worker()
                layout.removeWidget(widget)
                widget.hide()
                if key == 'm_Modifiers':
                    from src.editors.smartprop_editor.property_widget_pool import (
                        PropertyWidgetPool,
                    )
                    PropertyWidgetPool.instance().release(
                        getattr(widget, "prop_class", None), widget
                    )
                else:
                    try:
                        widget._clear_widgets()
                    except Exception:
                        pass
                    widget.deleteLater()

        # Recreate for the new list
        if key == 'm_Modifiers' and new_list:
            self._cancel_modifier_load()
            pending_init = {"remaining": 0}
            inited_frame_ids = set()
            self._populate_modifiers_progressive(
                new_list, pending_init, inited_frame_ids, tree_item=item,
            )
        elif key == 'm_SelectionCriteria':
            for entry in reversed(new_list):
                p = PropertyFrame(
                    widget_list=layout,
                    value=fast_deepcopy(entry),
                    variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
                    tree_hierarchy=self.ui.tree_hierarchy_widget,
                    element_id_generator=self.element_id_generator,
                    parent=self,
                )
                p.edited.connect(self.update_tree_item_value)
                self._setup_property_frame_group(p, "selection_criteria")
                p.slider_pressed.connect(self._on_slider_started)
                p.committed.connect(self._on_slider_committed)
                layout.insertWidget(0, p)

    def _incremental_property_update(self, item, new_data, changed_keys):
        """Update only the changed property widgets instead of full rebuild.

        Handles all diff key types: top-level properties, modifier/criteria
        sub-properties, whole-element changes, and structural list changes.
        """
        item.setData(0, Qt.UserRole, fast_deepcopy(new_data))

        self._property_undo_guard += 1
        try:
            main_frame = None
            for i in range(self.ui.properties_layout.count()):
                w = self.ui.properties_layout.itemAt(i).widget()
                if isinstance(w, PropertyFrame):
                    main_frame = w
                    break

            updated_frames = set()

            for key in changed_keys:
                if key in ('_class', 'm_nElementID'):
                    continue

                m = _DIFF_KEY_RE.match(key)
                if m:
                    # Modifier or criteria sub-property / whole-element change
                    container = m.group(1)
                    index = int(m.group(2))
                    sub_key = m.group(3)  # None when whole element changed
                    layout = (self.modifiers_group_instance.layout
                             if container == 'm_Modifiers'
                             else self.selection_criteria_group_instance.layout)
                    frame = self._get_nth_property_frame(layout, index)
                    if frame is not None:
                        arr = new_data.get(container, [])
                        if index < len(arr):
                            if sub_key is not None:
                                base_sub = sub_key.split('.')[0]
                                frame.update_property_value(base_sub, arr[index].get(base_sub))
                            else:
                                frame._reconfigure(
                                    value=fast_deepcopy(arr[index]),
                                    variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
                                    element_id_generator=self.element_id_generator,
                                    widget_list=layout,
                                    tree_hierarchy=self.ui.tree_hierarchy_widget,
                                )
                            updated_frames.add(id(frame))

                elif key in ('m_Modifiers', 'm_SelectionCriteria'):
                    # Structural change — rebuild just this section
                    self._rebuild_group_section(key, new_data, item)

                else:
                    # Top-level property
                    if main_frame is not None:
                        base_key = key.split('.')[0]
                        main_frame.update_property_value(base_key, new_data.get(base_key))
                        updated_frames.add(id(main_frame))

            # Silently update value dicts on affected frames (no signal emission)
            if main_frame is not None and id(main_frame) in updated_frames:
                main_frame.blockSignals(True)
                main_frame.on_edited()
                main_frame.blockSignals(False)

            for layout in (self.modifiers_group_instance.layout,
                           self.selection_criteria_group_instance.layout):
                for i in range(layout.count()):
                    w = layout.itemAt(i).widget()
                    if isinstance(w, PropertyFrame) and id(w) in updated_frames:
                        w.blockSignals(True)
                        w.on_edited()
                        w.blockSignals(False)

        finally:
            QTimer.singleShot(0, self._dec_property_undo_guard)

    def _on_slider_started(self):
        """Called when any FloatWidget slider begins a drag.

        Captures the element's full data snapshot ONCE (before the first value
        change) and increments the drag counter so update_tree_item_value skips
        undo pushes for the duration of the drag.
        """
        if self._slider_dragging == 0:
            item = self.ui.tree_hierarchy_widget.currentItem()
            if item is not None:
                self._slider_pre_drag_data = fast_deepcopy(item.data(0, Qt.UserRole))
        self._slider_dragging += 1

    def _on_slider_committed(self):
        """Called when a FloatWidget slider is released.

        Decrements the drag counter and, when the last active slider is released,
        pushes a single PropertySnapshotCommand covering the full drag range.
        """
        self._slider_dragging = max(0, self._slider_dragging - 1)
        if self._slider_dragging == 0 and self._slider_pre_drag_data is not None:
            item = self.ui.tree_hierarchy_widget.currentItem()
            if item is not None and not self._property_undo_guard:
                new_data = fast_deepcopy(item.data(0, Qt.UserRole))
                if new_data != self._slider_pre_drag_data:
                    cmd = PropertySnapshotCommand(self, item, self._slider_pre_drag_data, new_data)
                    self.undo_stack.push(cmd)
            self._slider_pre_drag_data = None

    # ======================================[Variables Panel Undo]========================================
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
                self.add_variable(
                    name=var_data['name'],
                    var_class=var_data['var_class'],
                    var_value=var_data['var_value'],
                    var_visible_in_editor=var_data['var_visible_in_editor'],
                    var_display_name=var_data['var_display_name'],
                )
        finally:
            self._restoring_state = False
        self._modified = True
        self._edited.emit()
        # Sync the variables viewport's committed-state reference so the next
        # user edit correctly uses the restored state as its "before" snapshot.
        self.variable_viewport._sync_committed_state()
        CompletionUtils.invalidate_cache(self.variable_viewport.ui.variables_scrollArea)

    # ======================================[Choices Panel Undo]========================================
    def _snapshot_choices(self):
        """Serialise the choices tree to a list of dicts."""
        tree = self.ui.choices_tree_widget
        state = []
        root = tree.invisibleRootItem()
        for ci in range(root.childCount()):
            choice = root.child(ci)
            combo = tree.itemWidget(choice, 1)
            choice_data = {
                'name': choice.text(0),
                'default': combo.currentText() if combo else '',
                'options': [],
            }
            for oi in range(choice.childCount()):
                option = choice.child(oi)
                option_data = {'name': option.text(0), 'variables': []}
                for vi in range(option.childCount()):
                    var_item = option.child(vi)
                    val_widget = tree.itemWidget(var_item, 1)
                    name_widget = tree.itemWidget(var_item, 0)
                    var_name = (
                        name_widget.combobox.currentText()
                        if name_widget and hasattr(name_widget, 'combobox')
                        else var_item.text(0)
                    )
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
                    name=choice_data['name'],
                    default=choice_data['default'],
                    variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
                ).item
                for option_data in choice_data['options']:
                    option_item = AddOption(
                        parent=choice_item, name=option_data['name']
                    ).item
                    for var_data in option_data['variables']:
                        AddVariable(
                            element_id_generator=self.element_id_generator,
                            parent=option_item,
                            variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
                            name=var_data['name'],
                            value=var_data['value'],
                            type=var_data['type'],
                        )
        finally:
            self.ui.choices_tree_widget.blockSignals(False)
        self._connect_choices_widget_signals()
        self._modified = True
        self._edited.emit()

    def _connect_choices_widget_signals(self):
        """Connect change signals on all inline widgets inside the choices tree.

        Called after every structural op and after _restore_choices so that
        ComboboxTreeChild and VariableWidget/Float/Bool edits are tracked.
        """
        tree = self.ui.choices_tree_widget
        root = tree.invisibleRootItem()
        for ci in range(root.childCount()):
            choice = root.child(ci)
            combo = tree.itemWidget(choice, 1)
            if combo:
                try:
                    combo.currentTextChanged.disconnect()
                except RuntimeError:
                    pass
                combo.currentTextChanged.connect(
                    lambda _, d="Edit Choice Default": self._on_choices_widget_changed(d)
                )
            for oi in range(choice.childCount()):
                option = choice.child(oi)
                for vi in range(option.childCount()):
                    var_item = option.child(vi)
                    val_widget = tree.itemWidget(var_item, 1)
                    if val_widget:
                        if hasattr(val_widget, 'editline'):
                            try:
                                val_widget.editline.textChanged.disconnect()
                            except RuntimeError:
                                pass
                            val_widget.editline.textChanged.connect(
                                lambda _, d="Edit Choice Variable Value": self._on_choices_widget_changed(d)
                            )
                        elif hasattr(val_widget, 'checkbox'):
                            try:
                                val_widget.checkbox.checkStateChanged.disconnect()
                            except RuntimeError:
                                pass
                            val_widget.checkbox.checkStateChanged.connect(
                                lambda _, d="Edit Choice Variable Value": self._on_choices_widget_changed(d)
                            )

    def _choices_op_with_undo(self, description, op_fn):
        """Helper: flush any pending choices widget edit, run op_fn, push ChoicesSnapshotCommand."""
        self._flush_choices_widget_if_pending()
        old = self._snapshot_choices()
        op_fn()
        new = self._snapshot_choices()
        self._connect_choices_widget_signals()
        if new != old:
            self.undo_stack.push(ChoicesSnapshotCommand(self, old, new, description))

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
            self.undo_stack.push(
                ChoicesSnapshotCommand(self, self._choices_rename_old_state, new_state, "Rename")
            )
            self._choices_rename_old_state = None

    def _on_choices_widget_changed(self, description="Edit Choices"):
        """Debounce handler for ComboboxTreeChild / VariableWidget changes."""
        if self._choices_widget_old_state is None:
            self._choices_widget_old_state = self._snapshot_choices()
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
            self._choices_widget_old_state = None

    def _flush_choices_widget_if_pending(self):
        """Flush any in-progress widget edit before a structural choices op."""
        if self._choices_widget_debounce.isActive():
            self._choices_widget_debounce.stop()
            self._push_choices_widget_edit()

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

        # Anchor History at the top of the right column, then split Variables and
        # Choices below it so the right panel reads: History → Variables → Choices.
        self.addDockWidget(Qt.RightDockWidgetArea, self._history_dock)
        self.splitDockWidget(self._history_dock, self.ui.VariablesDock, Qt.Vertical)
        self.splitDockWidget(self.ui.VariablesDock, self.ui.ChoicesDock, Qt.Vertical)
        self.resizeDocks(
            [self._history_dock, self.ui.VariablesDock, self.ui.ChoicesDock],
            [120, 300, 260],
            Qt.Vertical,
        )

    def closeEvent(self, event):
        self._save_user_prefs()

    # ======================================[Other]========================================
    def fix_format(self, file_content):
        pattern = re.compile(r"= resource_name:")
        modified_content = re.sub(pattern, "= ", file_content)
        modified_content = modified_content.replace("null,", "")
        return modified_content

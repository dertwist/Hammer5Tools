from src.common import fast_deepcopy

from PySide6.QtWidgets import (
    QMainWindow,
    QTreeWidgetItem,
    QFileDialog,
    QMenu,
    QWidget,
    QApplication,
    QHeaderView,
    QTreeWidget
)
from PySide6.QtGui import (
    QAction,
    QKeyEvent,
    QUndoStack,
    QKeySequence
)


from keyvalues3 import kv3_to_json
from src.editors.smartprop_editor.variable_frame import VariableFrame
from src.editors.smartprop_editor.completion_utils import CompletionUtils
from src.editors.smartprop_editor.objects import (
    variables_list,
)
from src.editors.smartprop_editor.ui_variables_viewport import Ui_Form
from src.widgets import ErrorInfo, on_three_hierarchyitem_clicked, HierarchyItemModel

class SmartPropEditorVariableViewport(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self._document = parent
        self.element_id_generator = parent.element_id_generator

        self.ui.add_new_variable_button.clicked.connect(self.add_new_variable)
        self.ui.variables_scroll_area_searchbar.textChanged.connect(self.search_variables)
        self.ui.paste_variable_button.clicked.connect(self.paste_variable)

        # Add variable classes to combobox
        for item in variables_list:
            self.ui.add_new_variable_combobox.addItem(item)

        # Committed-state reference for variable field edits.
        # Represents the last state that was pushed to the undo stack (or the
        # state when the panel was last loaded/restored).  pre_change signals from
        # VariableFrame set this BEFORE the widget updates so we always have a
        # correct "before" snapshot.  On content_changed we push immediately and
        # update _var_committed_state; VariablesSnapshotCommand.mergeWith() collapses
        # rapid same-field edits (e.g. holding down a spinbox arrow) into one entry.
        self._var_committed_state = None


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
        variable = VariableFrame(
            name=name,
            widget_list=self.ui.variables_scrollArea,
            var_value=var_value,
            var_class=var_class,
            var_visible_in_editor=var_visible_in_editor,
            var_display_name=var_display_name,
            element_id_generator=self.element_id_generator
        )
        variable.duplicate.connect(self.duplicate_variable)
        variable.delete_requested.connect(lambda vf=variable: self._on_delete_requested(vf))
        variable.pre_change.connect(self._on_pre_change)
        variable.content_changed.connect(self._on_content_changed)
        if index is None:
            index = (self.ui.variables_scrollArea.count()) - 1
        else:
            index = index + 1
        self.ui.variables_scrollArea.insertWidget(index, variable)
        CompletionUtils.invalidate_cache(self.ui.variables_scrollArea)

    def duplicate_variable(self, __data, __index):
        self._flush_var_edit_if_pending()
        old_state = self._snapshot()
        __data[2] = self.element_id_generator.update_value(__data[2], force=True)
        self.add_variable(__data[0], __data[1], __data[2], __data[3], __data[4], __index)
        new_state = self._snapshot()
        from src.editors.smartprop_editor.commands import VariablesSnapshotCommand
        self._document.undo_stack.push(
            VariablesSnapshotCommand(self._document, old_state, new_state, "Duplicate Variable")
        )
        self._sync_committed_state()

    def add_new_variable(self):
        self._flush_var_edit_if_pending()
        old_state = self._snapshot()

        name = "new_var"
        existing_variables = []
        variables_ = self.get_variables(self.ui.variables_scrollArea)
        for key, value in variables_.items():
            existing_variables.append(value[0])

        if name in existing_variables:
            suffix = 1
            while f"{name}_{suffix}" in existing_variables:
                suffix += 1
            name = f"{name}_{suffix}"

        var_class = self.ui.add_new_variable_combobox.currentText()
        var_name = name
        var_display_name = None
        var_visible_in_editor = False
        var_value = {"default": None, "min": None, "max": None, "model": None}
        var_value = self.element_id_generator.update_value(var_value, force=True)
        self.add_variable(
            name=var_name,
            var_value=var_value,
            var_visible_in_editor=var_visible_in_editor,
            var_class=var_class,
            var_display_name=var_display_name
        )

        new_state = self._snapshot()
        from src.editors.smartprop_editor.commands import VariablesSnapshotCommand
        self._document.undo_stack.push(
            VariablesSnapshotCommand(self._document, old_state, new_state, "Add Variable")
        )
        self._sync_committed_state()

    # ======================================[Variables Other]========================================
    def search_variables(self, search_term=None):
        for i in range(self.ui.variables_scrollArea.layout().count()):
            widget = self.ui.variables_scrollArea.layout().itemAt(i).widget()
            if widget:
                if search_term.lower() in widget.name.lower():
                    widget.show()
                else:
                    widget.hide()

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

    # ======================================[Variables Context menu]========================================
    def contextMenuEvent(self, event):
        context_menu = QMenu(self)
        if self.ui.variables_QscrollArea is QApplication.focusWidget():
            paste_action = QAction("Paste Variable", self)
            paste_action.triggered.connect(self.paste_variable)
            context_menu.addAction(paste_action)

        context_menu.exec_(event.globalPos())

    def paste_variable(self):
        self._flush_var_edit_if_pending()
        old_state = self._snapshot()
        clipboard = QApplication.clipboard()
        pasted_any = False
        try:
            m_data = kv3_to_json(clipboard.text())
            if not isinstance(m_data, dict):
                ErrorInfo(text="Clipboard data format is not valid.", details=m_data).exec()
                return

            if 'm_Variables' not in m_data:
                ErrorInfo(text="No variables found in clipboard data.").exec()
                return

            for variable in m_data['m_Variables']:
                _class = variable.get('_class', '')
                if not _class.startswith('CSmartPropVariable_'):
                    continue

                var_class = _class.replace('CSmartPropVariable_', '')
                var_name = variable.get('m_VariableName', '')
                var_visible = variable.get('m_bExposeAsParameter', False)

                var_value = {
                    'default': variable.get('m_DefaultValue'),
                    'min': variable.get('m_flParamaterMinValue'),
                    'max': variable.get('m_flParamaterMaxValue'),
                    'model': variable.get('m_sModelName'),
                    'm_HideExpression': variable.get('m_HideExpression')
                }

                self.element_id_generator.update_value(var_value, force=True)

                self.add_variable(
                    name=var_name,
                    var_class=var_class,
                    var_value=var_value,
                    var_visible_in_editor=var_visible,
                    var_display_name=variable.get('m_ParameterName')
                )
                pasted_any = True

        except Exception as e:
            ErrorInfo(text="Failed to paste variable data.", details=str(e)).exec()
            return

        if pasted_any:
            new_state = self._snapshot()
            from src.editors.smartprop_editor.commands import VariablesSnapshotCommand
            self._document.undo_stack.push(
                VariablesSnapshotCommand(self._document, old_state, new_state, "Paste Variable")
            )
            self._sync_committed_state()

    # ======================================[Variables Undo Helpers]========================================
    def _snapshot(self):
        """Serialise the current variable list to a list of dicts."""
        state = []
        layout = self.ui.variables_scrollArea
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

    def _sync_committed_state(self):
        """Update the committed-state reference to the current snapshot.

        Call after any undo/redo restore or structural operation (add/delete/paste)
        so the next user edit has a correct "before" reference.
        """
        self._var_committed_state = self._snapshot()

    def _on_pre_change(self):
        """Called BEFORE a VariableFrame modifies its stored values.

        Captures the snapshot while all widgets still reflect the OLD state,
        giving us a correct "before" reference for the next undo command.
        Only the FIRST pre_change per edit session sets the snapshot; subsequent
        pre_change calls (rapid same-field edits) are ignored so the original
        pre-edit state is preserved.
        """
        if self._var_committed_state is None:
            self._var_committed_state = self._snapshot()

    def _on_content_changed(self):
        """Push an undo command immediately after any variable field changes.

        Uses _var_committed_state (captured by _on_pre_change before the change)
        as the "before" snapshot.  VariablesSnapshotCommand.mergeWith() collapses
        rapid edits to the *same* field into a single history entry, while changes
        to different fields each get their own entry.
        """
        if self._var_committed_state is None:
            # Fallback: _on_pre_change wasn't called (e.g. a code path that emits
            # content_changed directly).  We cannot determine the "before" state, so
            # initialise committed state from the current snapshot and wait for the
            # next change to produce a proper before/after pair.
            self._var_committed_state = self._snapshot()
            return

        new_state = self._snapshot()
        if new_state != self._var_committed_state:
            from src.editors.smartprop_editor.commands import VariablesSnapshotCommand
            self._document.undo_stack.push(
                VariablesSnapshotCommand(
                    self._document, self._var_committed_state, new_state, "Edit Variable"
                )
            )
            self._var_committed_state = new_state
            CompletionUtils.invalidate_cache(self.ui.variables_scrollArea)

    def _on_delete_requested(self, variable_frame):
        """Handle delete_requested signal: snapshot → remove → snapshot → push undo."""
        self._sync_committed_state()
        old_state = self._snapshot()
        layout = self.ui.variables_scrollArea
        idx = -1
        for i in range(layout.count()):
            if layout.itemAt(i).widget() == variable_frame:
                idx = i
                break
        if idx != -1:
            item = layout.takeAt(idx)
            if item and item.widget():
                item.widget().deleteLater()
        new_state = self._snapshot()
        from src.editors.smartprop_editor.commands import VariablesSnapshotCommand
        self._document.undo_stack.push(
            VariablesSnapshotCommand(self._document, old_state, new_state, "Delete Variable")
        )
        self._sync_committed_state()
        CompletionUtils.invalidate_cache(self.ui.variables_scrollArea)

    def _flush_var_edit_if_pending(self):
        """Sync committed state before a structural operation."""
        self._sync_committed_state()
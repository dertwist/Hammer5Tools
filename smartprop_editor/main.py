import os.path
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QTreeWidgetItem, QVBoxLayout, QSpacerItem, QSizePolicy
from PySide6.QtCore import QTimer, QSettings
from PySide6.QtGui import QCloseEvent
from smartprop_editor.ui_main import Ui_MainWindow
from preferences import get_config_value
from distutils.util import strtobool
from PySide6.QtWidgets import QMenu, QApplication
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QCursor, QDrag,QAction

from soudevent_editor.properties.legacy_property import LegacyProperty
from smartprop_editor.variable_frame import VariableFrame
from smartprop_editor.objects import variables_list, variable_prefix

class SmartPropEditorMainWindow(QMainWindow):
    def __init__(self, version="v0.0.2", parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.version_label.setText(version)




        self.ui.show_child_ClassProperties.clicked.connect(lambda: self.group_child_check(self.ui.show_child_ClassProperties, self.ui.ClassProperties_layout_frame))
        self.ui.group_modifiers.clicked.connect(lambda: self.groupBox_check(self.ui.group_modifiers))
        # self.ui.group_class_properties.clicked.connect(lambda: self.groupBox_check(self.ui.group_class_properties))
        self.ui.group_selection_criteria.clicked.connect(lambda: self.groupBox_check(self.ui.group_selection_criteria))

        self.soundevent_properties_widget = QWidget()
        self.soundevent_properties_layout = QVBoxLayout(self.ui.modifiers_widget)
        self.soundevent_properties_widget.setLayout(self.soundevent_properties_layout)
        self.ui.scrollArea_modifiers.setWidget(self.soundevent_properties_widget)

        # adding var classes to combobox
        for item in variables_list:
            self.ui.add_new_variable_combobox.addItem(item)

        # connections
        self.ui.add_new_variable_button.clicked.connect(self.add_new_variable)

        # restore_prefs
        settings_path = get_config_value('PATHS', 'settings')
        self.settings = QSettings(os.path.join(settings_path, "smartprop_editor.cfg"), QSettings.IniFormat)
        self._restore_user_prefs()



    def group_child_check(self, checkbox, frame):
        if checkbox.isChecked():
            frame.setMaximumSize(15000, 15000)
        else:
            frame.setMaximumSize(15000, 16)
    def groupBox_check(self, groupBox):
        if groupBox.isChecked():
            groupBox.setMaximumSize(15000, 15000)
        else:
            groupBox.setMaximumSize(15000, 16)


    # variables

    def add_new_variable(self):
        name = 'new_var'
        existing_variables = []
        variables = self.get_variables(self.ui.variables_scrollArea)
        for key, value in variables.items():
            existing_variables.append(value[0])

        # Check if the name already exists
        if name in existing_variables:
            suffix = 1
            while f"{name}_{suffix}" in existing_variables:
                suffix += 1
            name = f"{name}_{suffix}"
        self.add_variable(name=name, var_value='', var_visible_in_editor=False,var_class=self.ui.add_new_variable_combobox.currentText())

    def add_variable(self, name, var_class, var_value, var_visible_in_editor):
        variable = VariableFrame(name=name, widget_list=self.ui.variables_scrollArea, var_value=var_value, var_class=var_class,var_visible_in_editor=var_visible_in_editor)
        index = (self.ui.variables_scrollArea.count()) - 1
        self.ui.variables_scrollArea.insertWidget(index, variable)

    def get_variables(self, layout):
        data_out = {}
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget:
                item = {i: [widget.name, widget.var_class, widget.var_value, widget.var_visible_in_editor]}
                data_out.update(item)
        return data_out


    # ContextMenu
    def contextMenuEvent(self, event):
        context_menu = QMenu(self)
        if self.ui.variables_QscrollArea is QApplication.focusWidget():
            paste_action = QAction("Paste Variable", self)
            paste_action.triggered.connect(self.paste_action)
            context_menu.addAction(paste_action)
        else:
            pass

        context_menu.exec_(event.globalPos())

    def paste_action(self):
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text()
        clipboard_data = clipboard_text.split(';;')

        if clipboard_data[0] == "hammer5tools:smartprop_editor_var":
            visible_in_editor = bool(strtobool(clipboard_data[4]))
            self.add_variable(clipboard_data[1], clipboard_data[2], clipboard_data[3],visible_in_editor)
        else:
            print("Clipboard data format is not valid.")

    # Prefs
    def _restore_user_prefs(self):
        geo = self.settings.value("SmartPropEditorMainWindow/geometry")
        if geo:
            self.restoreGeometry(geo)

        state = self.settings.value("SmartPropEditorMainWindow/windowState")
        if state:
            self.restoreState(state)

        saved_index = self.settings.value("SmartPropEditorMainWindow/currentComboBoxIndex")
        if saved_index is not None:
            self.ui.add_new_variable_combobox.setCurrentIndex(int(saved_index))

    def _save_user_prefs(self):
        current_index = self.ui.add_new_variable_combobox.currentIndex()
        self.settings.setValue("SmartPropEditorMainWindow/currentComboBoxIndex", current_index)
        self.settings.setValue("SmartPropEditorMainWindow/geometry", self.saveGeometry())
        self.settings.setValue("SmartPropEditorMainWindow/windowState", self.saveState())

    def closeEvent(self, event: QCloseEvent):
        self._save_user_prefs()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    from qt_styles.qt_global_stylesheet import QT_Stylesheet_global
    app.setStyleSheet(QT_Stylesheet_global)
    window = SmartPropEditorMainWindow()
    window.show()
    sys.exit(app.exec())
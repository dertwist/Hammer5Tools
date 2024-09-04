import os.path
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QTreeWidgetItem, QVBoxLayout, QSpacerItem, QSizePolicy
from PySide6.QtCore import QTimer, QSettings
from PySide6.QtGui import QCloseEvent
from smartprop_editor.ui_main import Ui_MainWindow
from preferences import get_config_value

from soudevent_editor.properties.legacy_property import LegacyProperty

class SmartPropEditorMainWindow(QMainWindow):
    def __init__(self, version="v0.0.2", parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.version_label.setText(version)

        settings_path = get_config_value('PATHS', 'settings')
        self.settings = QSettings(os.path.join(settings_path, "smartprop_editor.cfg"), QSettings.IniFormat)

        self._restore_user_prefs()
        # self.ui.groupBox.setMaximumSize(15000,16)
        self.ui.group_modifiers.clicked.connect(lambda: self.groupBox_check(self.ui.group_modifiers))
        self.ui.group_class_properties.clicked.connect(lambda: self.groupBox_check(self.ui.group_class_properties))
        self.ui.group_selection_criteria.clicked.connect(lambda: self.groupBox_check(self.ui.group_selection_criteria))


        self.soundevent_properties_widget = QWidget()
        self.soundevent_properties_layout = QVBoxLayout(self.ui.modifiers_widget)
        self.soundevent_properties_widget.setLayout(self.soundevent_properties_layout)
        self.ui.scrollArea_modifiers.setWidget(self.soundevent_properties_widget)
        items = ['1','1','1','1','1','1','1']
        for item in items:
            property_class = LegacyProperty(name=item, value='1', widget_list=self.soundevent_properties_layout)
            self.soundevent_properties_layout.insertWidget(0, property_class)
            self.soundevent_properties_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        # self.ui.groupBox_list.insertWidget(0, property_class)

    def groupBox_check(self, groupBox):
        if groupBox.isChecked():
            groupBox.setMaximumSize(15000, 15000)
        else:
            groupBox.setMaximumSize(15000, 16)
    def _restore_user_prefs(self):
        geo = self.settings.value("SmartPropEditorMainWindow/geometry")
        if geo:
            self.restoreGeometry(geo)

        state = self.settings.value("SmartPropEditorMainWindow/windowState")
        if state:
            self.restoreState(state)

    def closeEvent(self, event: QCloseEvent):
        self._save_user_prefs()

    def _save_user_prefs(self):
        self.settings.setValue("SmartPropEditorMainWindow/geometry", self.saveGeometry())
        self.settings.setValue("SmartPropEditorMainWindow/windowState", self.saveState())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    from qt_styles.qt_global_stylesheet import QT_Stylesheet_global
    app.setStyleSheet(QT_Stylesheet_global)
    window = SmartPropEditorMainWindow()
    window.show()


    sys.exit(app.exec())
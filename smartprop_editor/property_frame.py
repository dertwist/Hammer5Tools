from time import process_time_ns

from smartprop_editor.ui_property_frame import Ui_Form


from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal
from soudevent_editor.properties.property_actions import PropertyActions

from PySide6.QtWidgets import QMenu, QApplication
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QCursor, QDrag,QAction


import ast

class PropertyFrame(QWidget):
    edited = Signal()
    def __init__(self, value, widget_list, variables_scrollArea, element=False):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.ui.property_class.setAcceptDrops(False)
        self.variables_scrollArea = variables_scrollArea
        self.element = element
        if isinstance(value, dict):
            pass
        else:
            value = ast.literal_eval(value)

        self.name = value['_class']
        self.name = (value['_class'].split('_'))[1]
        self.name_prefix = (value['_class'].split('_'))[0]
        del value['_class']
        self.value = value
        # print(self.value)
        self.layout = self.ui.layout
        self.enable = value.get('m_bEnabled', True)
        prop_class = self.name


        self.ui.property_class.setText(self.name)

        self.ui.enable.setChecked(self.enable)
        self.ui.enable.clicked.connect(self.on_edited)


        # self.ui.variable_name.textChanged.connect(self.update_self)
        self.widget_list = widget_list

        if self.element:
            self.ui.copy_button.deleteLater()
            self.ui.delete_button.deleteLater()
        else:
            self.ui.copy_button.clicked.connect(self.copy_action)
            self.ui.delete_button.clicked.connect(self.delete_action)

        # For parsed stuff
        from smartprop_editor.properties_classes.legacy import PropertyLegacy
        from smartprop_editor.properties_classes.vector3d import PropertyVector3D
        from smartprop_editor.properties_classes.float import PropertyFloat


        def adding_instances(value_class, value):
            def add_instance():
                property_instance.edited.connect(self.on_edited)
                self.ui.layout.insertWidget(0, property_instance)
            if 'm_v' in value_class:
                property_instance = PropertyVector3D(value=value, value_class=value_class,variables_scrollArea=self.variables_scrollArea)
                add_instance()
            elif 'm_fl' in value_class:
                property_instance = PropertyFloat(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea)
                add_instance()
            elif 'm_n' in value_class:
                property_instance = PropertyFloat(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea, int_bool=True)
                add_instance()
            elif value_class == 'm_bEnabled':
                pass
            else:
                property_instance = PropertyLegacy(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea)
                add_instance()

        if prop_class == 'PathPosition':
            classes = ['m_PlaceAtPositions','m_nPlaceEveryNthPosition','m_nNthPositionIndexOffset','m_bAllowAtStart','m_bAllowAtEnd']
            for item in classes:
                if item in self.value:
                    adding_instances(item, self.value[item])
                else:
                    adding_instances(item, None)
            # for value_class, value in reversed(list(self.value.items())):
            #     adding_instances(value_class, value)
            # for value_class, value in reversed(list(self.value.items())):
            #     property_instance = PropertyVector3D(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea)
            #     property_instance.edited.connect(self.on_edited)
            #     self.ui.layout.insertWidget(0, property_instance)
        elif prop_class == 'Float':
            pass
        else:
            # Generic shit
            for value_class, value in reversed(list(self.value.items())):
                adding_instances(value_class, value)
        self.on_edited()
        self.show_child()
        self.ui.show_child.clicked.connect(self.show_child)

        self.init_ui()

    def show_child(self):
        if not self.ui.show_child.isChecked():
            self.ui.frame_layout.setMaximumSize(16666,0)
        else:
            self.ui.frame_layout.setMaximumSize(16666, 16666)

    def on_edited(self):
        self.value = {
            '_class': f'{self.name_prefix}_{self.name}',
            'm_bEnabled': self.ui.enable.isChecked()
        }
        try:
            for index in range(self.ui.layout.count()):
                widget = self.ui.layout.itemAt(index).widget()
                new_value = widget.value
                self.value.update(new_value)
        except:
            pass
        self.edited.emit()

    def update_self(self):
        pass
    def init_ui(self):
        if self.element:
            pass
        else:
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            self.customContextMenuRequested.connect(self.show_context_menu)

    mousePressEvent = PropertyActions.mousePressEvent
    mouseMoveEvent = PropertyActions.mouseMoveEvent
    dragEnterEvent = PropertyActions.dragEnterEvent
    dropEvent = PropertyActions.dropEvent
    def show_context_menu(self):
        context_menu = QMenu()
        delete_action = QAction("Delete", context_menu)
        copy_action = QAction("Copy", context_menu)  # Change 'Duplicate' to 'Copy'
        context_menu.addActions([delete_action, copy_action])  # Replace 'duplicate_action' with 'copy_action'

        action = context_menu.exec(QCursor.pos())

        if action == delete_action:
            self.delete_action()

        elif action == copy_action:
            self.copy_action()
    def copy_action(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(f"hammer5tools:smartprop_editor_property;;{self.name};;{self.value}")
    def delete_action(self):
        self.value = None
        self.edited.emit()
        self.deleteLater()
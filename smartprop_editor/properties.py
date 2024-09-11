from PySide6.QtWidgets import QTreeWidgetItem, QTreeWidget, QLineEdit, QCheckBox, QGroupBox, QHBoxLayout, QVBoxLayout, QFrame, QWidget
from PySide6.QtCore import QSize
import ast
from PySide6.QtCore import Qt, Signal
from qt_styles.qt_smartprops_tree_stylesheet import QT_Stylesheet_smartprop_tree
class Properties:
    edited = Signal()
    def __init__(self, tree=QTreeWidget, data=None):
        self.tree = tree
        self.data = ast.literal_eval(data)
        print(type(data), data)
        self.populate_modifers()
        self.populate_class_properties()
        self.populate_selection_critiria()

    def clear_children(self, item):
        while item.childCount() > 0:
            child = item.child(0)
            item.removeChild(child)
    def new_item(self, item, name, value, edit=False):
        new_child_item = QTreeWidgetItem(item)
        new_child_item.setText(0, str(name))
        new_child_item.setText(1, str(value))
        if edit:
            new_child_item.setFlags(new_child_item.flags() | Qt.ItemIsEditable)
        item.addChild(new_child_item)
        return new_child_item

    def populate_class_properties(self):
        item = self.tree.topLevelItem(0)
        self.clear_children(item)
        item.setText(0, self.data['_class'].replace('CSmartPropElement_',''))
        for key, value in self.data.items():
            print('key', key)
            if key == 'm_Modifiers':
                pass
            elif key == 'm_SelectionCriteria':
                pass
            elif key == '_class':
                pass
            elif key == 'm_nElementID':
                pass
            else:
                self.new_item(item, key, value, edit=True)
    def populate_modifers(self):
        item = self.tree.topLevelItem(1)
        self.clear_children(item)
        if 'm_Modifiers' in self.data:
            for modifier in self.data['m_Modifiers']:
                modifier_item = self.new_item(item, modifier['_class'].replace('CSmartPropOperation_', ''), '')
                modifier_item.setExpanded(True)
                for key, value in modifier.items():
                    if key == 'm_nElementID':
                        pass
                    if key == '_class':
                        pass
                    else:
                        self.new_item(modifier_item, key, value, edit=True)
    def populate_selection_critiria(self):
        item = self.tree.topLevelItem(2)
        self.clear_children(item)
        if 'm_SelectionCriteria' in self.data:
            for modifier in self.data['m_SelectionCriteria']:
                modifier_item = self.new_item(item, modifier['_class'].replace('CSmartPropSelectionCriteria_', ''),'')
                modifier_item.setExpanded(True)
                for key, value in modifier.items():
                    if key == 'm_nElementID':
                        pass
                    if key == '_class':
                        pass
                    else:
                        self.new_item(modifier_item, key, value, edit=True)


class AddProperty:
    changed = Signal()
    def __init__(self, parent=QTreeWidget, key=None,value=None):
        name = key
        self.parent = parent.currentItem()
        element_value = ast.literal_eval(value)
        new_element = QTreeWidgetItem()
        # new_element.setFlags(new_element.flags() | Qt.ItemIsEditable)
        new_element.setText(0, name)
        new_element.setText(1, '')
        self.parent.addChild(new_element)
        new_element.setExpanded(True)


        for key, value in element_value.items():
            if key == 'm_nElementID':
                pass
            if key == '_class':
                pass
            else:
                # self.new_item(new_element, key, value, edit=True)
                new_child_item = QTreeWidgetItem(new_element)
                new_child_item.setText(0, str(name))
                new_child_item.setText(1, str(value))
                new_element.addChild(new_child_item)

                group_box = QLineEdit()
                group_box.textChanged.connect(self.on_changed)
                self.parent.treeWidget().setItemWidget(new_child_item, 1, group_box)

    def new_item(self, item, name, value, edit=False):
        new_child_item = QTreeWidgetItem(item)
        new_child_item.setText(0, str(name))
        new_child_item.setText(1, str(value))
        item.addChild(new_child_item)


        # group_box = CustomEditLines()
        # group_box.changed_event.connect(self.on_changed)
        #
        #
        # self.parent.treeWidget().setItemWidget(new_child_item, 1, group_box)

        # group_box = CustomEditLines()
        # group_box.changed_event.connect(self.on_changed)
        group_box = QLineEdit()
        group_box.textChanged.connect(self.on_changed)
        self.parent.treeWidget().setItemWidget(new_child_item, 1, group_box)

        return new_child_item

    def on_changed(self, text):
        print('Changed', text)
        # json_format = {}
        # for index in range(self.parent.childCount()):
        #     child_item = self.parent.child(index)
        #     json_format[child_item.text(0)] = child_item.text(1)
        #     for i in range(child_item.childCount()):
        #         sub_child_item = child_item.child(i)
        #         json_format[child_item.text(0)][sub_child_item.text(0)] = sub_child_item.text(1)
        # print(json_format)


class CustomEditLines(QGroupBox):
    changed_event = Signal()
    def __init__(self):
        super().__init__()
        self.value = {}
        self.group_layout = QVBoxLayout()
        self.setLayout(self.group_layout)
        self.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet(QT_Stylesheet_smartprop_tree)

        # Create and connect QLineEdit widgets
        self.edit_line = QLineEdit()
        self.edit_line.textChanged.connect(lambda text: self.on_change(text, self.edit_line))
        self.group_layout.addWidget(self.edit_line)

        self.edit_line_2 = QLineEdit()
        self.edit_line_2.textChanged.connect(lambda text: self.on_change(text, self.edit_line_2))
        self.group_layout.addWidget(self.edit_line_2)

    def on_change(self, text, edit_line):
        self.value = {'1': self.edit_line.text(), '2': self.edit_line_2.text()}
        self.changed_event.emit()
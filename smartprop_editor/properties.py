from PySide6.QtWidgets import QTreeWidgetItem, QTreeWidget
import ast
from PySide6.QtCore import Qt
class Properties:
    def __init__(self, tree=QTreeWidget, data=None):
        self.tree = tree
        self.data = ast.literal_eval(data)
        print(type(data), data)
        for index in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(index)
            if item.text(0) == 'Modifiers':
                self.clear_children(item)
                if 'm_Modifiers' in self.data:
                    for modifier in self.data['m_Modifiers']:
                        modifier_item = self.new_item(item, modifier['_class'], '')
                        for key, value in modifier.items():
                            self.new_item(modifier_item, key, value, edit=True)

            if item.text(0) == 'ClassProperties':
                self.clear_children(item)
                for key, value in self.data.items():
                    print('key', key)
                    if key == 'm_Modifiers':
                        pass
                    elif key == 'm_SelectionCriteria':
                        pass
                    else:
                        self.new_item(item, key, value, edit=True)

            if item.text(0) == 'SelectionCriteria':
                self.clear_children(item)
                if 'm_SelectionCriteria' in self.data:
                    for modifier in self.data['m_SelectionCriteria']:
                        modifier_item = self.new_item(item, modifier['_class'].replace('CSmartPropSelectionCriteria_', ''), '')
                        for key, value in modifier.items():
                            self.new_item(modifier_item, key, value, edit=True)

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

from smartprop_editor.widgets import ComboboxTreeChild, ComboboxDynamicItems
from preferences import  debug

class AddChoice():
    def __init__(self, tree=None):
        super().__init__()
        self.tree = tree
    def add_choice(self):
        item = self.tree.itemAt(1, 1)
        combobox = ComboboxTreeChild(layout=self.tree, root=item)
        item.childCount()
        # combobox = ComboboxVariables(layout=self.ui.variables_scrollArea)

        debug(item.text(0))
        self.tree.setItemWidget(item, 1, combobox)
        self.tree.setStyleSheet("")
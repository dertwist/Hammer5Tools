from src.editors.smartprop_editor._common import get_clean_class_name
from src.widgets import HierarchyItemModel
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QColor, QBrush

VIRTUAL_ROLE = Qt.UserRole + 10  # flag key

class VirtualChildItem(HierarchyItemModel):
    """
    A non-element tree row representing one modifier or selection-criteria entry.
    Parent item owns the real data; this row stores only its index + type.
    """
    MODIFIER = "modifier"
    SELECTION_CRITERIA = "selection_criteria"

    def __init__(self, label, entry_data, entry_index, virtual_type):
        real_class = entry_data.get("_class", virtual_type)
        super().__init__(_name=label, _data=entry_data, _class=real_class, _id="")
        self.setData(0, VIRTUAL_ROLE, {
            "virtual": True,
            "type": virtual_type,
            "index": entry_index,
        })
        
        # Stylize
        if virtual_type == self.MODIFIER:
            self.setIcon(0, QIcon(":/valve_common/icons/tools/common/setting.png"))
            self.setForeground(0, QBrush(QColor("#9CDCFE"))) # Light blue
        else:
            self.setIcon(0, QIcon(":/valve_common/icons/tools/common/options_activated.png"))
            self.setForeground(0, QBrush(QColor("#CE9178"))) # Orange/Peach
            
        # Disable rename
        self.setFlags(self.flags() & ~Qt.ItemIsEditable)

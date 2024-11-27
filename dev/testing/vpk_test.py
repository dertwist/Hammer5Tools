import os
import vpk
from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, QMessageBox
from PySide6.QtCore import Qt
from src.preferences import get_cs2_path

def create_tree_widget():
    app = QApplication([])

    window = QWidget()
    window.setWindowTitle("Sound Files Tree")
    layout = QVBoxLayout(window)

    tree_widget = QTreeWidget()
    tree_widget.setHeaderLabels(["Category", "File"])
    layout.addWidget(tree_widget)

    try:
        path = os.path.join(get_cs2_path(), 'game', 'csgo', 'pak01_dir.vpk')
        with vpk.open(path) as pak1:
            folders = []
            for filepath in pak1:
                if 'vsnd_c' in filepath:
                    path_clear = filepath
                    element = path_clear.split('/')
                    folders.append(element)

            for path_elements in folders:
                parent_item = None
                for element in path_elements:
                    if parent_item is None:
                        found_items = tree_widget.findItems(element, Qt.MatchExactly, 0)
                    else:
                        found_items = [child for child in (parent_item.child(i) for i in range(parent_item.childCount())) if child.text(0) == element]

                    if found_items:
                        parent_item = found_items[0]
                    else:
                        new_item = QTreeWidgetItem([element])
                        if parent_item is None:
                            tree_widget.addTopLevelItem(new_item)
                        else:
                            parent_item.addChild(new_item)
                        parent_item = new_item

    except FileNotFoundError:
        QMessageBox.critical(window, "Error", "VPK file not found.")
    except Exception as e:
        QMessageBox.critical(window, "Error", f"Failed to load VPK file: {e}")

    window.show()
    app.exec()

if __name__ == "__main__":
    create_tree_widget()
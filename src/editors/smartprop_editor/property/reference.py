from src.editors.smartprop_editor.property.ui_reference import Ui_Widget
import ast
import re
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal
from src.widgets.popup_menu.main import PopupMenu
from src.styles.common import qt_stylesheet_button
from src.widgets import HierarchyItemModel
import uuid

class PropertyReference(QWidget):
    edited = Signal()
    
    def __init__(self, value_class, value, variables_scrollArea, element_id_generator, tree_hierarchy=None):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value
        self.variables_scrollArea = variables_scrollArea
        self.element_id_generator = element_id_generator
        self.tree_hierarchy = tree_hierarchy

        self.ui.reference_show_button.setStyleSheet(qt_stylesheet_button)

        # Set up the property class label
        output = re.sub(r'm_fl|m_n|m_b|m_s|m_', '', self.value_class)
        output = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', output)
        self.ui.property_class.setText(output)

        # Connect signals
        self.ui.reference_search.clicked.connect(self.reference_id_search)
        self.ui.reference_clear.clicked.connect(self.reference_id_clear)
        self.ui.reference_show_button.clicked.connect(self.show_reference_in_hierarchy)
        self.ui.reference_id.textChanged.connect(self.on_changed)

        # Initialize with existing value
        if isinstance(value, dict):
            if 'm_nReferenceID' in value:
                self.ui.reference_id.setText(str(value['m_nReferenceID']))
        elif isinstance(value, int):
            self.ui.reference_id.setText(str(value))
        elif value is not None:
            self.ui.reference_id.setText(str(value))

        self.on_changed()

    def reference_id_search(self):
        """
        Create and display a popup menu with all hierarchy items from the tree_hierarchy.
        Items with m_bReferenceObject set to True are excluded.
        Each menu item displays in the format: [Label] | [Class] | [ElementID].
        """
        if not self.tree_hierarchy:
            return

        # Helper function to recursively collect all items from the tree
        def collect_tree_items(parent_item):
            items = []
            try:
                for i in range(parent_item.childCount()):
                    item = parent_item.child(i)
                    if item:
                        # Add the current item
                        items.append(item)
                        # Recursively add all children
                        if item.childCount() > 0:
                            items.extend(collect_tree_items(item))
            except Exception as e:
                print(f"Error collecting tree items: {e}")
            return items

        # Collect all items from the tree hierarchy
        try:
            root_item = self.tree_hierarchy.invisibleRootItem()
            all_items = collect_tree_items(root_item)
        except Exception as e:
            print(f"Error getting root item: {e}")
            return

        # Create a list of property dictionaries for the PopupMenu
        properties = []
        for item in all_items:
            try:
                if not item:
                    continue
                    
                # Check if this is a reference object (skip if it is)
                # Safely check if column 5 exists and contains 'True'
                is_reference_object = False
                try:
                    if item.columnCount() > 5:
                        ref_text = item.text(5)
                        if ref_text == 'True':
                            is_reference_object = True
                except:
                    pass
                
                if is_reference_object:
                    continue
                
                # Safely get the text values
                label = "Unknown"
                class_name = "Unknown"
                element_id = "0"
                
                try:
                    label = item.text(0) if item.text(0) else "Unknown"
                except:
                    pass
                    
                try:
                    if item.columnCount() > 2:
                        class_name = item.text(2) if item.text(2) else "Unknown"
                except:
                    pass
                    
                try:
                    if item.columnCount() > 3:
                        element_id = item.text(3) if item.text(3) else "0"
                except:
                    pass

                display_text = f"{label} | {class_name} | {element_id}"
                properties.append({display_text: element_id})
                
            except Exception as e:
                print(f"Error processing item: {e}")
                continue

        if not properties:
            print("No valid items found for reference selection")
            return

        # Create and show the popup menu
        try:
            self.hierarchy_menu = PopupMenu(properties=properties, window_name='hierarchy_item_menu')
            self.hierarchy_menu.add_property_signal.connect(self.on_hierarchy_item_selected)
            self.hierarchy_menu.show()
        except Exception as e:
            print(f"Error creating popup menu: {e}")

    def on_hierarchy_item_selected(self, name, element_id):
        """Handle the selection of a hierarchy item from the popup menu."""
        self.ui.reference_id.setText(str(element_id))

    def reference_id_clear(self):
        """Clear the reference ID field."""
        self.ui.reference_id.clear()

    def show_reference_in_hierarchy(self):
        """Show the referenced element in the hierarchy tree."""
        if not self.tree_hierarchy:
            print("No hierarchy tree available")
            return
            
        ref_id = self.reference_id_get()
        if ref_id is None:
            print("No reference ID to show")
            return
            
        # Helper function to recursively search for the item with matching element ID
        def find_item_by_element_id(parent_item, target_id):
            try:
                for i in range(parent_item.childCount()):
                    item = parent_item.child(i)
                    if item:
                        # Check if this item has the target element ID
                        try:
                            if item.columnCount() > 3:
                                element_id_text = item.text(3)
                                if element_id_text and str(element_id_text) == str(target_id):
                                    return item
                        except:
                            pass
                        
                        # Recursively search children
                        if item.childCount() > 0:
                            found_item = find_item_by_element_id(item, target_id)
                            if found_item:
                                return found_item
            except Exception as e:
                print(f"Error searching for item: {e}")
            return None
        
        try:
            # Search for the item with the reference ID
            root_item = self.tree_hierarchy.invisibleRootItem()
            target_item = find_item_by_element_id(root_item, ref_id)
            
            if target_item:
                # Select and scroll to the item
                self.tree_hierarchy.setCurrentItem(target_item)
                self.tree_hierarchy.scrollToItem(target_item)
                
                # Expand parent items to make sure the item is visible
                parent = target_item.parent()
                while parent:
                    parent.setExpanded(True)
                    parent = parent.parent()
                    
                print(f"Found and selected element with ID {ref_id} in hierarchy")
            else:
                print(f"Element with ID {ref_id} not found in hierarchy")
                
        except Exception as e:
            print(f"Error showing reference in hierarchy: {e}")

    def reference_object_id_get(self):
        """Generate a new reference object ID."""
        return str(uuid.uuid4())

    def reference_id_get(self):
        """Get the reference ID value."""
        value = self.ui.reference_id.text().strip()
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def on_changed(self):
        """Handle changes to the reference ID."""
        self.change_value()
        self.edited.emit()
        
    def change_value(self):
        """Update the value based on current input."""
        ref_id = self.reference_id_get()
        
        if ref_id is not None:
            # Create the reference values
            reference_values = {
                'm_nReferenceID': ref_id,
                'm_sReferenceObjectID': self.reference_object_id_get()
            }
            self.value = reference_values
        else:
            self.value = None
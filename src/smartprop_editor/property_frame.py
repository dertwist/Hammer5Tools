from src.settings.main import debug
from src.smartprop_editor.ui_property_frame import Ui_Form

from PySide6.QtWidgets import QWidget, QMenu, QApplication
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QCursor, QAction

from src.property.methods import PropertyMethods
from src.popup_menu.main import PopupMenu
from src.smartprop_editor.element_id import update_value_ElementID, get_ElementID_key

from src.smartprop_editor.property.legacy import PropertyLegacy
from src.smartprop_editor.property.vector3d import PropertyVector3D
from src.smartprop_editor.property.float import PropertyFloat
from src.smartprop_editor.property.bool import PropertyBool
from src.smartprop_editor.property.combobox import PropertyCombobox
from src.smartprop_editor.property.string import PropertyString
from src.smartprop_editor.property.color import PropertyColor
from src.smartprop_editor.property.comparison import PropertyComparison
from src.smartprop_editor.property.filtersurface import PropertySurface
from src.smartprop_editor.property.colormatch import PropertyColorMatch
from src.smartprop_editor.property.variable import PropertyVariableOutput
from src.smartprop_editor.property.set_variable import PropertyVariableValue
from src.smartprop_editor.property.comment import PropertyComment
from PySide6.QtGui import QCursor
from src.widgets import HierarchyItemModel
from src.smartprop_editor.element_id import get_ElementID_key, set_ElementID
import uuid

import ast

class PropertyFrame(QWidget):
    edited = Signal()

    # A lookup dictionary to avoid multiple if/elif checks; cached at class level
    _prop_classes_map_cache = {
        # Elements
        'FitOnLine': [
            'm_vStart','m_vEnd', 'm_vUpDirection', 'm_PointSpace', 'm_nScaleMode', 'm_nPickMode', 'm_bOrientAlongLine'
        ],
        'PickOne': [
            'm_SelectionMode','m_PointSpace','m_HandleShape','m_HandleColor', 'm_HandleSize','m_vHandleOffset','m_bConfigurable'
        ],
        'PlaceInSphere': [
            'm_nCountMin','m_nCountMax','m_flPositionRadiusInner','m_flPositionRadiusOuter', 'm_flRandomness', 'm_bAlignOrientation', 'm_PlacementMode'
        ],
        'PlaceOnPath': [
            'm_PathName','m_vPathOffset','m_flOffsetAlongPath','m_PathSpace', 'm_flSpacing', 'm_DefaultPath'
        ],
        'Model': [
            'm_sModelName','m_vModelScale','m_MaterialGroupName'
        ],
        'SmartProp': [
            'm_sSmartProp','m_vModelScale'
        ],
        'PlaceMultiple': [
            'm_nCount', 'm_Expression'
        ],
        'BendDeformer': [
            'm_bDeformationEnabled', 'm_vSize', 'm_vOrigin', 'm_vAngles', 'm_flBendAngle', 'm_flBendPoint', 'm_flBendRadius'
        ],
        # Operators
        'CreateSizer': [
            'm_flInitialMinX', 'm_flInitialMaxX', 'm_flConstraintMinX', 'm_flConstraintMaxX',
            'm_OutputVariableMinX', 'm_OutputVariableMaxX', 'm_flInitialMinY', 'm_flInitialMaxY',
            'm_flConstraintMinY', 'm_flConstraintMaxY', 'm_OutputVariableMinY', 'm_OutputVariableMaxY',
            'm_flInitialMinZ', 'm_flInitialMaxZ', 'm_flConstraintMinZ', 'm_flConstraintMaxZ',
            'm_OutputVariableMinZ', 'm_OutputVariableMaxZ'
        ],
        'CreateRotator': [
            'm_vRotationAxis', 'm_CoordinateSpace', 'm_flDisplayRadius', 'm_bApplyToCurrentTransform',
            'm_OutputVariable', 'm_flSnappingIncrement', 'm_bEnforceLimits', 'm_flMinAngle', 'm_flMaxAngle'
        ],
        'CreateLocator': [
            'm_flDisplayScale', 'm_bAllowScale'
        ],
        'RandomRotation': [
            'm_vRandomRotationMin', 'm_vRandomRotationMax'
        ],
        'RandomOffset': [
            'm_vRandomPositionMin', 'm_vRandomPositionMax'
        ],
        'RandomScale': [
            'm_flRandomScaleMin', 'm_flRandomScaleMax'
        ],
        'Scale': [
            'm_flScale'
        ],
        'SetTintColor': [
            'm_Mode', 'm_ColorChoices', 'm_SelectionMode', 'm_ColorSelection'
        ],
        'SetVariable': [
            'm_VariableValue'
        ],
        # Filters
        'SurfaceProperties': [
            'm_DisallowedSurfaceProperties', 'm_AllowedSurfaceProperties'
        ],
        'VariableValue': [
            'm_VariableComparison'
        ],
        'SurfaceAngle': [
            'm_flSurfaceSlopeMin', 'm_flSurfaceSlopeMax'
        ],
        # Selection Criteria
        'PathPosition': [
            'm_PlaceAtPositions', 'm_nPlaceEveryNthPosition', 'm_nNthPositionIndexOffset', 'm_bAllowAtStart','m_bAllowAtEnd'
        ],
        'EndCap': [
            'm_bStart', 'm_bEnd'
        ],
        'LinearLength': [
            'm_flLength', 'm_bAllowScale', 'm_flMinLength', 'm_flMaxLength'
        ],
        'ChoiceWeight': [
            'm_flWeight'
        ],
        'TraceInDirection': [
            'm_DirectionSpace', 'm_nNoHitResult', 'm_flSurfaceUpInfluence', 'm_flOriginOffset', 'm_flTraceLength'
        ],
        'SaveState': [
            'm_StateName'
        ]
    }

    def __init__(self, value, widget_list, variables_scrollArea, element=False, reference_bar=False, tree_hierarchy=None):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.ui.property_class.setAcceptDrops(False)
        self.variables_scrollArea = variables_scrollArea
        self.element = element
        if tree_hierarchy is None:
            raise ValueError("tree_hierarchy cannot be None - a valid hierarchy structure is required")
        else:
            self.tree_hierarchy = tree_hierarchy

        # Use ast.literal_eval only if not already a dict
        if not isinstance(value, dict):
            value = ast.literal_eval(value)

        self.name_prefix, self.name = value['_class'].split('_', 1)
        del value['_class']
        self.value = value

        if reference_bar:
            self.ui.ReferenceID.setText(str(self.value.get('m_nReferenceID', '')))
            self.ui.ReferenceID_Search.clicked.connect(self.ReferenceIDSearch)
            self.ui.ReferenceID_Clear.clicked.connect(self.ReferenceIDClear)
            self.ui.ReferenceID.textChanged.connect(self.on_edited)

        else:
            self.ui.ReferenceID.deleteLater()
            self.ui.ReferenceID_Label.deleteLater()
            self.ui.ReferenceID_Clear.deleteLater()
            self.ui.ReferenceID_Search.deleteLater()

        self.layout = self.ui.layout

        #===========================================================<  Element ID  >========================================================
        update_value_ElementID(self.value)
        self.element_id = get_ElementID_key(self.value)
        debug(f'Property frame get_ElementID: {self.element_id}')
        self.ui.element_id_display.setText(str(self.element_id))

        self.enable = value.get('m_bEnabled', True)
        self.prop_class = self.name

        self.ui.property_class.setText(self.name)
        try:
            self.ui.enable.setChecked(self.enable)
        except:
            # For cases where self.enable might be a dict or unrecognized
            if isinstance(self.enable, dict):
                if 'm_SourceName' in self.enable:
                    self.ui.variable_display.setText(self.enable['m_SourceName'])
                if 'm_Expression' in self.enable:
                    self.ui.variable_display.setText(self.enable['m_Expression'])
            else:
                print(f'Error with setting m_bEnabled: {self.enable}; Name: {self.name};Value: {self.value}')
            self.ui.enable.setChecked(True)

        self.ui.enable.clicked.connect(self.on_edited)
        self.ui.variables_search.clicked.connect(self.search_enable_variable)
        self.ui.variable_clear.clicked.connect(lambda: self.ui.variable_display.clear())
        self.ui.variable_display.textChanged.connect(self.on_edited)

        self.widget_list = widget_list

        if self.element:
            self.ui.copy_button.deleteLater()
            self.ui.delete_button.deleteLater()
        else:
            self.ui.copy_button.clicked.connect(self.copy_action)
            self.ui.delete_button.clicked.connect(self.delete_action)

        # only_variable_properties
        self.only_variable_properties = [
            'm_OutputVariableMaxZ',
            'm_OutputVariableMinZ',
            'm_OutputVariableMaxY',
            'm_OutputVariableMinY',
            'm_OutputVariableMaxX',
            'm_OutputVariableMinX',
            'm_OutputVariable'
        ]

        # Defer heavier property initialization to the event loop,
        # improving UI responsiveness and perceived performance.
        QTimer.singleShot(0, self._finish_init)

    def _finish_init(self):
        # Populate property widgets after the constructor returns
        self._add_properties_by_class()
        self.show_child()
        self.ui.show_child.clicked.connect(self.show_child)

        self.init_ui()
        self.on_edited()

    def _add_properties_by_class(self):
        # This function adds property widgets when needed
        def adding_instances(value_class, val):
            def add_instance():
                property_instance.edited.connect(self.on_edited)
                property_instance.setAcceptDrops(False)
                self.ui.layout.insertWidget(0, property_instance)
            if 'm_nPickMode' in value_class:
                property_instance = PropertyCombobox(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['LARGEST_FIRST','RANDOM','ALL_IN_ORDER'], filter_types=['PickMode']); add_instance()
            elif value_class == 'm_bEnabled':
                pass
            elif value_class == 'm_sLabel':
                pass
            elif value_class == 'm_nElementID':
                pass
            elif 'm_nScaleMode' in value_class: property_instance = PropertyCombobox(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['NONE','SCALE_END_TO_FIT','SCALE_EQUALLY','SCALE_MAXIMAIZE'], filter_types=['ScaleMode']); add_instance()
            elif 'm_CoordinateSpace' in value_class: property_instance = PropertyCombobox(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['ELEMENT','OBJECT','WORLD'], filter_types=['CoordinateSpace']); add_instance()
            elif 'm_DirectionSpace' in value_class: property_instance = PropertyCombobox(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['ELEMENT','OBJECT','WORLD'], filter_types=['DirectionSpace']); add_instance()
            elif 'm_GridPlacementMode' in value_class: property_instance = PropertyCombobox(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['SEGMENT','FILL'], filter_types=['GridPlacementMode']); add_instance()
            elif 'm_GridOriginMode' in value_class: property_instance = PropertyCombobox(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['CENTER','CORNER'], filter_types=['GridOriginMode']); add_instance()
            elif 'm_nNoHitResult' in value_class: property_instance = PropertyCombobox(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['NOTHING','DISCARD','MOVE_TO_START','MOVE_TO_END'], filter_types=['TraceNoHit']); add_instance()
            elif 'm_SelectionMode' in value_class: property_instance = PropertyCombobox(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['RANDOM','FIRST','SPECIFIC'], filter_types=['ChoiceSelectionMode']); add_instance()
            elif 'm_PlacementMode' in value_class: property_instance = PropertyCombobox(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['SPHERE','CIRCLE'], filter_types=['RadiusPlacementMode']); add_instance()
            elif 'm_DistributionMode' in value_class: property_instance = PropertyCombobox(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['RANDOM','REGULAR'], filter_types=['DistributionMode']); add_instance()
            elif 'm_HandleShape' in value_class: property_instance = PropertyCombobox(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['SQUARE','DIAMOND','CIRCLE'], filter_types=['HandleShape']); add_instance()
            elif 'm_PointSpace' in value_class: property_instance = PropertyCombobox(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['ELEMENT','OBJECT','WORLD'], filter_types=['CoordinateSpace']); add_instance()
            elif 'm_PathSpace' in value_class: property_instance = PropertyCombobox(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['ELEMENT','OBJECT','WORLD'], filter_types=['CoordinateSpace']); add_instance()
            elif 'm_PlaceAtPositions' in value_class: property_instance = PropertyCombobox(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['ALL','NTH','START_AND_END','CONTROL_POINTS'], filter_types=['PathPositions']); add_instance()
            elif 'm_Mode' in value_class: property_instance = PropertyCombobox(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['MULTIPLY_OBJECT','MULTIPLY_CURRENT','REPLACE'], filter_types=['ApplyColorMode']); add_instance()
            elif 'm_ApplyColorMode' in value_class: property_instance = PropertyCombobox(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['MULTIPLY_OBJECT','MULTIPLY_CURRENT','REPLACE'], filter_types=['ApplyColorMode']); add_instance()
            elif 'm_v' in value_class: property_instance = PropertyVector3D(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea); add_instance()
            elif 'm_flBendPoint' in value_class: property_instance = PropertyFloat(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, slider_range=[0,1]); add_instance()
            elif 'm_fl' in value_class: property_instance = PropertyFloat(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea); add_instance()
            elif 'm_HandleSize' in value_class: property_instance = PropertyFloat(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea); add_instance()
            elif 'm_n' in value_class: property_instance = PropertyFloat(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, int_bool=True); add_instance()
            elif 'm_ColorSelection' in value_class: property_instance = PropertyFloat(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, int_bool=True); add_instance()
            elif 'm_HandleColor' in value_class: property_instance = PropertyColor(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea); add_instance()
            elif 'm_ColorChoices' in value_class: property_instance = PropertyColorMatch(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea); add_instance()
            elif 'm_b' in value_class: property_instance = PropertyBool(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea); add_instance()
            elif 'm_s' in value_class: property_instance = PropertyString(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, expression_bool=False, placeholder='String'); add_instance()
            elif 'm_MaterialGroupName' in value_class: property_instance = PropertyString(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, expression_bool=False, placeholder='Material group name'); add_instance()
            elif 'm_Expression' in value_class: property_instance = PropertyString(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, expression_bool=True, placeholder='Expression example: var_bool ? var_sizer * var_multiply'); add_instance()
            elif 'm_StateName' in value_class: property_instance = PropertyString(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, expression_bool=False, only_string=True, placeholder='State name'); add_instance()
            elif value_class in self.only_variable_properties: property_instance = PropertyVariableOutput(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea); add_instance()
            elif 'm_VariableName' in value_class: property_instance = PropertyString(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, expression_bool=False, only_string=False, only_variable=True, force_variable=True, placeholder='Variable name', filter_types=['String','Int','Float','Bool']); add_instance()
            elif 'm_Comment' in value_class: property_instance = PropertyComment(value=val, value_class=value_class); add_instance()
            elif 'm_VariableValue' in value_class:
                if val is None:
                    property_instance = PropertyVariableValue(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea); add_instance()
                else:
                    if 'm_TargetName' not in val:
                        property_instance = PropertyString(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, expression_bool=True); add_instance()
                    else:
                        property_instance = PropertyVariableValue(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea); add_instance()
            elif 'm_VariableComparison' in value_class: property_instance = PropertyComparison(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea); self.ui.property_class.setText('Variable Comparison'); add_instance()
            elif 'm_AllowedSurfaceProperties' in value_class: property_instance = PropertySurface(value=val,value_class=value_class,variables_scrollArea=self.variables_scrollArea); add_instance()
            elif 'm_DisallowedSurfaceProperties' in value_class: property_instance = PropertySurface(value=val,value_class=value_class,variables_scrollArea=self.variables_scrollArea); add_instance()
            else: property_instance = PropertyLegacy(value=val,value_class=value_class,variables_scrollArea=self.variables_scrollArea); add_instance()

        def operator_adding_instances(classes):
            for item in classes:
                if item in self.value:
                    adding_instances(item, self.value[item])
                else:
                    adding_instances(item, None)

        if self.prop_class in self._prop_classes_map_cache:
            operator_adding_instances(self._prop_classes_map_cache[self.prop_class])
        else:
            for value_class, val_data in reversed(list(self.value.items())):
                adding_instances(value_class, val_data)

    def show_child(self):
        if not self.ui.show_child.isChecked():
            self.ui.frame_layout.setMaximumSize(16666, 0)
        else:
            self.ui.frame_layout.setMaximumSize(16666, 16666)

    def search_enable_variable(self):
        variables = self.get_variables()
        self.popup_menu = PopupMenu(variables, add_once=False)
        self.popup_menu.add_property_signal.connect(lambda name, value: self.add_variable(name, value))
        self.popup_menu.show()

    def add_variable(self, name, value):
        self.ui.variable_display.setText(name)

    def get_variables(self, search_term=None):
        data_out = []
        for i in range(self.variables_scrollArea.count()):
            widget = self.variables_scrollArea.itemAt(i).widget()
            if widget:
                if 'Bool' in getattr(widget, 'var_class', ''):
                    data_out.append({widget.name: {widget.var_class}})
        return data_out

    def update_reference_values(self):
        try:
            if self.ReferenceIDGet() is not None:
                reference_values = {
                    'm_nReferenceID': self.ReferenceIDGet(),
                    'm_sReferenceObjectID': self.ReferenceObjectIDGet()
                }
                print(reference_values)
                return reference_values
            return {}
        except:
            return {}

    def on_edited(self):
        debug('Property frame was edited')
        if self.ui.variable_display.text() != '':
            enabled = {'m_Expression': str(self.ui.variable_display.text())}
        else:
            enabled = self.ui.enable.isChecked()

        self.value = {
            '_class': f'{self.name_prefix}_{self.name}',
            'm_bEnabled': enabled,
            'm_nElementID': self.element_id,
        }

        reference_values = self.update_reference_values()
        self.value.update(reference_values)


        try:
            for index in range(self.ui.layout.count()):
                widget = self.ui.layout.itemAt(index).widget()
                new_value = getattr(widget, 'value', None)
                if new_value:
                    self.value.update(new_value)
        except Exception as error:
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

    mousePressEvent = PropertyMethods.mousePressEvent
    mouseMoveEvent = PropertyMethods.mouseMoveEvent
    dragEnterEvent = PropertyMethods.dragEnterEvent

    def dropEvent(self, event):
        if event.source() == self:
            return

        mime_data = event.mimeData()
        if mime_data.hasText():
            if event.source() != self:
                source_index = self.widget_list.layout().indexOf(event.source())
                target_index = self.widget_list.layout().indexOf(self)
                if source_index != -1 and target_index != -1:
                    if source_index < self.widget_list.layout().count():
                        source_widget = self.widget_list.layout().takeAt(source_index).widget()
                        if source_widget:
                            self.widget_list.layout().insertWidget(target_index, source_widget)
        self.edited.emit()
        event.accept()

    def show_context_menu(self):
        context_menu = QMenu()
        delete_action = QAction("Delete", context_menu)
        copy_action = QAction("Copy", context_menu)
        context_menu.addActions([delete_action, copy_action])
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
    # ===========================================================<  Referencing  >=========================================================
    # The concept of referencing in this system involves two distinct entities: the "reference" and the "reference object."
    # A "reference" is any element within the hierarchy, while the "referenced object" is the element that provides the data.
    # When an element functions as a reference object, it inherits all data from the reference and then
    # selectively overrides those values with its own, except for specific keys that must remain unique.
    #
    # For example:
    # Referenced Object:
    # {
    #    _class: "CSmartPropElement_Model",
    #    m_bEnabled: true,
    #    m_nElementID: 5,
    #    m_MaterialGroupName: "Default",
    #    m_Scale: [1, 1, 1],
    #    m_sModelName: "Test_01",
    #    m_sLabel: "Model Test"
    # }
    #
    # Reference Object:
    # {
    #    _class: "CSmartPropElement_Model",
    #    m_bEnabled: true,
    #    m_nElementID: 6,
    #    m_sModelName: "model_final",
    #    m_sLabel: "Model Final"
    # }
    #
    # Result for the Reference Object (after saving/processing):
    # {
    #    _class: "CSmartPropElement_Model",
    #    m_bEnabled: true,
    #    m_Scale: [1, 1, 1],
    #    m_MaterialGroupName: "Default",
    #    m_nElementID: 6,
    #    m_sModelName: "model_final",
    #    m_sLabel: "Model Final"
    # }
    #
    # The boolean flag m_bReferenceObject (True/False) indicates whether this element serves as a reference
    # object that overrides data inherited from a referenced object. When set to True, the element cannot
    # be used as a reference by other elements.
    #
    # The m_nReferenceID stores the ID of the referenced element (note that duplicate IDs may result in conflicting issues).
    #
    # Non-processed reference objects will be saved in the m_ReferenceObjects list.
    # The m_sReferenceObjectID stores the ID of the non-processed reference object.
    # The ID is formatted as "Class_ElementID_###", where "#" represents a random ASCII symbol.
    #
    # The saving algorithm operates as follows:
    # The program copies all reference objects to the m_ReferenceObjects list, along with m_Variables, m_Choices, and m_Children.
    # m_ReferenceObjects Structure:
    # m_ReferenceObjects: {
    #     "Class_ElementID_###": {Reference Object data}
    # }
    # Initially, the reference object includes the m_sReferenceObjectID key with the non-processed reference ID.
    # Subsequently, the program locates the reference element by m_nReferenceID,
    # retrieves data from the reference, and compares it to the reference object's data.
    # Keys in the reference object take precedence over those in the reference.
    # After comparing and merging the data, the program writes the updated data to the reference object,
    # while also storing these keys:
    # m_bReferenceObject
    # m_sReferenceObjectID
    # m_nReferenceID
    #
    # While opening a file:
    # The program locates each reference object (by m_sReferenceObjectID) and replaces its data with the non-processed version.
    #
    # Visual Indicators:
    # - References are displayed in green.
    # - Reference objects are displayed in blue.
    def ReferenceIDSearch(self):
        """
        Create and display a popup menu with all hierarchy items from the tree_hierarchy.
        Items with m_bReferenceObject set to True are excluded.
        Each menu item displays in the format: [Class]-[Label]-[ElementID].
        """

        # Helper function to recursively collect all items from the tree
        def collect_tree_items(parent_item):
            items = []
            for i in range(parent_item.childCount()):
                item = parent_item.child(i)
                # Add the current item
                items.append(item)
                # Recursively add all children
                if item.childCount() > 0:
                    items.extend(collect_tree_items(item))
            return items

        # Collect all items from the tree hierarchy
        root_item = self.tree_hierarchy.invisibleRootItem()
        all_items = collect_tree_items(root_item)

        # Create a list of property dictionaries for the PopupMenu
        properties = []
        for item in all_items:
            item: HierarchyItemModel = item
            if item.text(5) == 'True':
                pass
            else:
                label = item.text(0)
                class_name = item.text(2)
                element_id = item.text(3)
                display_text = f"{label} | {class_name} | {element_id}"

                properties.append({display_text: element_id})

        # Create and show the popup menu
        self.hierarchy_menu = PopupMenu(properties=properties, window_name='hierarchy_item_menu')
        self.hierarchy_menu.add_property_signal.connect(self.on_hierarchy_item_selected)
        self.hierarchy_menu.show()

    def on_hierarchy_item_selected(self, name, element_id):
        """Handle the selection of a hierarchy item from the popup menu."""
        self.ui.ReferenceID.setText(str(element_id))
    def ReferenceIDClear(self):
        self.ui.ReferenceID.clear()
    def ReferenceObjectIDGet(self):
        _id = str(uuid.uuid5(uuid.NAMESPACE_DNS, self.value.get('m_sLabel', self.name)))
        return _id
    def ReferenceIDGet(self):
        value = self.ui.ReferenceID.text().strip()
        if not value:
            raise ValueError("ReferenceID cannot be empty")
        return int(value)

from src.settings.preferences import debug
from src.smartprop_editor.ui_property_frame import Ui_Form

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal
from src.property.methods import PropertyMethods

from PySide6.QtWidgets import QMenu, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QAction

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
        self.layout = self.ui.layout

        #===========================================================<  Element ID  >========================================================
        update_value_ElementID(self.value)
        self.element_id = get_ElementID_key(self.value)
        debug(f'Property frame get_ElementID: {self.element_id}')
        self.ui.element_id_display.setText(str(self.element_id))


        self.enable = value.get('m_bEnabled', True)

        prop_class = self.name


        self.ui.property_class.setText(self.name)
        try:
            self.ui.enable.setChecked(self.enable)
        except:
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


        # self.ui.variable_name.textChanged.connect(self.update_self)
        self.widget_list = widget_list

        if self.element:
            self.ui.copy_button.deleteLater()
            self.ui.delete_button.deleteLater()
        else:
            self.ui.copy_button.clicked.connect(self.copy_action)
            self.ui.delete_button.clicked.connect(self.delete_action)

        # For parsed stuff



        # only_variable_properties
        only_variable_properties = [
            'm_OutputVariableMaxZ',
            'm_OutputVariableMinZ',
            'm_OutputVariableMaxY',
            'm_OutputVariableMinY',
            'm_OutputVariableMaxX',
            'm_OutputVariableMinX',
            'm_OutputVariable'
        ]

        def operator_adding_instances(classes):
            for item in classes:
                if item in self.value:
                    adding_instances(item, self.value[item])
                else:
                    adding_instances(item, None)
        def adding_instances(value_class, value):
            def add_instance():
                property_instance.edited.connect(self.on_edited)
                property_instance.setAcceptDrops(False)
                self.ui.layout.insertWidget(0, property_instance)
            if 'm_nPickMode' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['LARGEST_FIRST', 'RANDOM', 'ALL_IN_ORDER'], filter_types=['PickMode'])
                add_instance()

            # pass
            elif value_class == 'm_bEnabled':
                pass
            elif value_class == 'm_sLabel':
                pass
            elif value_class == 'm_nElementID':
                pass

            elif 'm_nScaleMode' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['NONE', 'SCALE_END_TO_FIT', 'SCALE_EQUALLY', 'SCALE_MAXIMAIZE'], filter_types=['ScaleMode'])
                add_instance()
            elif 'm_CoordinateSpace' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['ELEMENT', 'OBJECT', 'WORLD'], filter_types=['CoordinateSpace'])
                add_instance()
            elif 'm_DirectionSpace' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['ELEMENT', 'OBJECT', 'WORLD'], filter_types=['DirectionSpace'])
                add_instance()
            elif 'm_GridPlacementMode' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['SEGMENT', 'FILL'], filter_types=['GridPlacementMode'])
                add_instance()
            elif 'm_GridOriginMode' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['CENTER', 'CORNER'], filter_types=['GridOriginMode'])
                add_instance()
            elif 'm_nNoHitResult' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['NOTHING', 'DISCARD', 'MOVE_TO_START', 'MOVE_TO_END'], filter_types=['TraceNoHit'])
                add_instance()
            elif 'm_SelectionMode' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['RANDOM', 'FIRST', 'SPECIFIC'], filter_types=['ChoiceSelectionMode'])
                add_instance()
            elif 'm_PlacementMode' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['SPHERE', 'CIRCLE'], filter_types=['RadiusPlacementMode'])
                add_instance()
            elif 'm_DistributionMode' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['RANDOM', 'REGULAR'], filter_types=['DistributionMode'])
                add_instance()
            elif 'm_HandleShape' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['SQUARE', 'DIAMOND', 'CIRCLE'], filter_types=['HandleShape'])
                add_instance()
            elif 'm_PointSpace' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['ELEMENT', 'OBJECT', 'WORLD'], filter_types=['CoordinateSpace'])
                add_instance()
            elif 'm_PathSpace' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['ELEMENT', 'OBJECT', 'WORLD'], filter_types=['CoordinateSpace'])
                add_instance()
            elif 'm_PlaceAtPositions' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['ALL', 'NTH', 'START_AND_END', 'CONTROL_POINTS'], filter_types=['PathPositions'])
                add_instance()
            elif 'm_Mode' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['MULTIPLY_OBJECT', 'MULTIPLY_CURRENT', 'REPLACE'], filter_types=['ApplyColorMode'])
                add_instance()
            elif 'm_ApplyColorMode' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['MULTIPLY_OBJECT', 'MULTIPLY_CURRENT', 'REPLACE'], filter_types=['ApplyColorMode'])
                add_instance()

            # Vector3D
            elif 'm_v' in value_class:
                property_instance = PropertyVector3D(value=value, value_class=value_class,variables_scrollArea=self.variables_scrollArea)
                add_instance()
            # Float
            elif 'm_flBendPoint' in value_class:
                property_instance = PropertyFloat(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea, slider_range=[0,1])
                add_instance()
            elif 'm_fl' in value_class:
                property_instance = PropertyFloat(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea)
                add_instance()
            elif 'm_HandleSize' in value_class:
                property_instance = PropertyFloat(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea)
                add_instance()
            #     Int
            elif 'm_n' in value_class:
                property_instance = PropertyFloat(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea, int_bool=True)
                add_instance()
            elif 'm_ColorSelection' in value_class:
                property_instance = PropertyFloat(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea, int_bool=True)
                add_instance()

            # Color
            elif 'm_HandleColor' in value_class:
                property_instance = PropertyColor(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea)
                add_instance()
            # Color match
            elif 'm_ColorChoices' in value_class:
                property_instance = PropertyColorMatch(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea)
                add_instance()

            # Bool
            elif 'm_b' in value_class:
                property_instance = PropertyBool(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea)
                add_instance()
            # String
            elif 'm_s' in value_class:
                property_instance = PropertyString(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea, expression_bool=False, placeholder='String')
                add_instance()
            elif 'm_MaterialGroupName' in value_class:
                property_instance = PropertyString(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea, expression_bool=False, placeholder='Material group name')
                add_instance()
            elif 'm_Expression' in value_class:
                property_instance = PropertyString(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea, expression_bool=True, placeholder='Expression example: var_bool ? var_sizer * var_multiply')
                add_instance()
            elif 'm_StateName' in value_class:
                property_instance = PropertyString(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea, expression_bool=False, only_string=True, placeholder='State name')
                add_instance()
            # Variable Output
            elif value_class in only_variable_properties:
                property_instance = PropertyVariableOutput(value=value, value_class=value_class,variables_scrollArea=self.variables_scrollArea)
                add_instance()

            elif 'm_VariableName' in value_class:
                property_instance = PropertyString(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea, expression_bool=False, only_string=False, only_variable=True, force_variable=True, placeholder='Variable name', filter_types=['String', 'Int', 'Float', 'Bool'])
                add_instance()
            elif 'm_VariableValue' in value_class:
                if value is None:
                    property_instance = PropertyVariableValue(value=value, value_class=value_class,variables_scrollArea=self.variables_scrollArea)
                    add_instance()
                else:
                    if not 'm_TargetName' in value:
                        property_instance = PropertyString(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea, expression_bool=True)
                        add_instance()
                    else:
                        property_instance = PropertyVariableValue(value=value, value_class=value_class,variables_scrollArea=self.variables_scrollArea)
                        add_instance()
            # Comparison
            elif 'm_VariableComparison' in value_class:
                property_instance = PropertyComparison(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea)
                # self.name = 'Variable Comparison'
                self.ui.property_class.setText('Variable Comparison')
                add_instance()
            # Surfaces

            elif 'm_AllowedSurfaceProperties' in value_class:
                property_instance = PropertySurface(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea)
                add_instance()
            elif 'm_DisallowedSurfaceProperties' in value_class:
                property_instance = PropertySurface(value=value, value_class=value_class,
                                                       variables_scrollArea=self.variables_scrollArea)
                add_instance()
            else:
                property_instance = PropertyLegacy(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea)
                add_instance()

        # Elements
        if prop_class == 'FitOnLine':
            classes = ['m_vStart','m_vEnd', 'm_vUpDirection', 'm_PointSpace', 'm_nScaleMode', 'm_nPickMode', 'm_bOrientAlongLine']
            operator_adding_instances(classes)
        elif prop_class == 'PickOne':
            classes = ['m_SelectionMode','m_PointSpace','m_HandleShape','m_HandleColor', 'm_HandleSize','m_vHandleOffset', 'm_bConfigurable']
            operator_adding_instances(classes)
        elif prop_class == 'PlaceInSphere':
            classes = ['m_nCountMin','m_nCountMax','m_flPositionRadiusInner','m_flPositionRadiusOuter', 'm_flRandomness', 'm_bAlignOrientation', 'm_PlacementMode']
            operator_adding_instances(classes)
        elif prop_class == 'PlaceOnPath':
            classes = ['m_PathName','m_vPathOffset','m_flOffsetAlongPath','m_PathSpace', 'm_flSpacing', 'm_DefaultPath']
            operator_adding_instances(classes)
        elif prop_class == 'Model':
            classes = ['m_sModelName','m_vModelScale','m_MaterialGroupName']
            operator_adding_instances(classes)
        elif prop_class == 'SmartProp':
            classes = ['m_sSmartProp','m_vModelScale']
            operator_adding_instances(classes)
        elif prop_class == 'PlaceMultiple':
            classes = ['m_nCount', 'm_Expression']
            operator_adding_instances(classes)
        elif prop_class == 'BendDeformer':
            classes = ['m_bDeformationEnabled', 'm_vSize', 'm_vOrigin', 'm_vAngles', 'm_flBendAngle', 'm_flBendPoint', 'm_flBendRadius']
            operator_adding_instances(classes)
        # Operators
        elif prop_class == 'CreateSizer':
            classes = ['m_flInitialMinX', 'm_flInitialMaxX', 'm_flConstraintMinX', 'm_flConstraintMaxX','m_OutputVariableMinX', 'm_OutputVariableMaxX', 'm_flInitialMinY', 'm_flInitialMaxY', 'm_flConstraintMinY', 'm_flConstraintMaxY', 'm_OutputVariableMinY', 'm_OutputVariableMaxY', 'm_flInitialMinZ', 'm_flInitialMaxZ', 'm_flConstraintMinZ', 'm_flConstraintMaxZ', 'm_OutputVariableMinZ', 'm_OutputVariableMaxZ']
            operator_adding_instances(classes)
        elif prop_class == 'CreateRotator':
            classes = ['m_vRotationAxis', 'm_CoordinateSpace', 'm_flDisplayRadius', 'm_bApplyToCurrentTransform','m_OutputVariable', 'm_flSnappingIncrement', 'm_bEnforceLimits', 'm_flMinAngle', 'm_flMaxAngle']
            operator_adding_instances(classes)
        elif prop_class == 'CreateLocator':
            classes = ['m_flDisplayScale', 'm_bAllowScale']
            operator_adding_instances(classes)
        elif prop_class == 'RandomRotation':
            classes = ['m_vRandomRotationMin', 'm_vRandomRotationMax']
            operator_adding_instances(classes)
        elif prop_class == 'RandomOffset':
            classes = ['m_vRandomPositionMin', 'm_vRandomPositionMax']
            operator_adding_instances(classes)
        elif prop_class == 'RandomScale':
            classes = ['m_flRandomScaleMin', 'm_flRandomScaleMax']
            operator_adding_instances(classes)
        elif prop_class == 'Scale':
            classes = ['m_flScale']
            operator_adding_instances(classes)
        elif prop_class == 'SetTintColor':
            classes = ['m_Mode', 'm_ColorChoices', 'm_SelectionMode', 'm_ColorSelection']
            operator_adding_instances(classes)

        elif prop_class == 'SetVariable':
            classes = ['m_VariableValue']
            operator_adding_instances(classes)

        # Filters
        elif prop_class == 'SurfaceProperties':
            classes = ['m_DisallowedSurfaceProperties', 'm_AllowedSurfaceProperties']
            operator_adding_instances(classes)
        elif prop_class == 'VariableValue':
            classes = ['m_VariableComparison']
            operator_adding_instances(classes)
        elif prop_class == 'SurfaceAngle':
            classes = ['m_flSurfaceSlopeMin', 'm_flSurfaceSlopeMax']
            operator_adding_instances(classes)
        # Selection Criteria
        elif prop_class == 'PathPosition':
            classes = ['m_PlaceAtPositions', 'm_nPlaceEveryNthPosition', 'm_nNthPositionIndexOffset', 'm_bAllowAtStart','m_bAllowAtEnd']
            operator_adding_instances(classes)
        elif prop_class == 'EndCap':
            classes = ['m_bStart', 'm_bEnd']
            operator_adding_instances(classes)
        elif prop_class == 'LinearLength':
            classes = ['m_flLength', 'm_bAllowScale', 'm_flMinLength', 'm_flMaxLength']
            operator_adding_instances(classes)
        elif prop_class == 'ChoiceWeight':
            classes = ['m_flWeight']
            operator_adding_instances(classes)
        elif prop_class == 'TraceInDirection':
            classes = ['m_DirectionSpace', 'm_nNoHitResult', 'm_flSurfaceUpInfluence', 'm_flOriginOffset', 'm_flTraceLength']
            operator_adding_instances(classes)
        elif prop_class == 'SaveState':
            classes = ['m_StateName']
            operator_adding_instances(classes)



        else:
            # Generic shit
            for value_class, value in reversed(list(self.value.items())):
                adding_instances(value_class, value)
        self.show_child()
        self.ui.show_child.clicked.connect(self.show_child)


        self.init_ui()
        self.on_edited()

    def show_child(self):
        if not self.ui.show_child.isChecked():
            self.ui.frame_layout.setMaximumSize(16666,0)
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
                if 'Bool' in widget.var_class:
                    data_out.append({widget.name: {widget.var_class}})
        return data_out

    def on_edited(self):
        debug('Property frame was edited')
        if self.ui.variable_display.text() != '':
            enabled = {'m_Expression': str(self.ui.variable_display.text())}
        else:
            enabled = self.ui.enable.isChecked()
        self.value = {
            '_class': f'{self.name_prefix}_{self.name}',
            'm_bEnabled': enabled,
            'm_nElementID': self.element_id
        }
        try:
            for index in range(self.ui.layout.count()):
                widget = self.ui.layout.itemAt(index).widget()
                new_value = widget.value
                if new_value:
                    self.value.update(new_value)
        except Exception as error:
            print(error)
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
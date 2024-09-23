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
        from smartprop_editor.properties_classes.bool import PropertyBool
        from smartprop_editor.properties_classes.combobox import PropertyCombobox
        from smartprop_editor.properties_classes.string import PropertyString
        from smartprop_editor.properties_classes.color import PropertyColor
        from smartprop_editor.properties_classes.comparison import PropertyComparison
        from smartprop_editor.properties_classes.filtersurface import PropertySurface



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
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['LARGEST_FIRST', 'RANDOM', 'ALL_IN_ORDER'])
                add_instance()

            # pass
            elif value_class == 'm_bEnabled':
                pass
            elif value_class == 'm_sLabel':
                pass

            elif 'm_nScaleMode' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['NONE', 'SCALE_END_TO_FIT', 'SCALE_EQUALLY', 'SCALE_MAXIMAIZE'])
                add_instance()
            elif 'm_CoordinateSpace' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['ELEMENT', 'OBJECT', 'WORLD'])
                add_instance()
            elif 'm_DirectionSpace' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['ELEMENT', 'OBJECT', 'WORLD'])
                add_instance()
            elif 'm_GridPlacementMode' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['SEGMENT', 'FILL'])
                add_instance()
            elif 'm_GridOriginMode' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['CENTER', 'CORNER'])
                add_instance()
            elif 'm_nNoHitResult' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['NOTHING', 'DISCARD', 'MOVE_TO_START', 'MOVE_TO_END'])
                add_instance()
            elif 'm_ApplyColorMode' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['MULTIPLY_OBJECT', 'MULTIPLY_CURRENT', 'REPLACE'])
                add_instance()
            elif 'm_SelectionMode' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['RANDOM', 'FIRST'])
                add_instance()
            elif 'm_PlacementMode' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['SPHERE', 'CIRCLE'])
                add_instance()
            elif 'm_DistributionMode' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['RANDOM', 'REGULAR'])
                add_instance()
            elif 'm_HandleShape' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['SQUARE', 'DIAMOND', 'CIRCLE'])
                add_instance()
            elif 'm_PointSpace' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['ELEMENT', 'OBJECT', 'WORLD'])
                add_instance()
            elif 'm_Mode' in value_class:
                property_instance = PropertyCombobox(value=value, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['MULTIPLY_OBJECT', 'MULTIPLY_CURRENT', 'REPLACE'])
                add_instance()
            elif 'm_v' in value_class:
                property_instance = PropertyVector3D(value=value, value_class=value_class,variables_scrollArea=self.variables_scrollArea)
                add_instance()
            # Float
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
            # Color
            elif 'm_HandleColor' in value_class:
                property_instance = PropertyColor(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea)
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
            elif 'm_OutputVariableMaxZ' in value_class:
                property_instance = PropertyString(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea, expression_bool=False, only_string=True, placeholder='Variable name')
                add_instance()
            elif 'm_OutputVariableMinZ' in value_class:
                property_instance = PropertyString(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea, expression_bool=False, only_string=True, placeholder='Variable name')
                add_instance()
            elif 'm_OutputVariableMaxY' in value_class:
                property_instance = PropertyString(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea, expression_bool=False, only_string=True, placeholder='Variable name')
                add_instance()
            elif 'm_OutputVariableMinY' in value_class:
                property_instance = PropertyString(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea, expression_bool=False, only_string=True, placeholder='Variable name')
                add_instance()
            elif 'm_OutputVariableMaxX' in value_class:
                property_instance = PropertyString(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea, expression_bool=False, only_string=True, placeholder='Variable name')
                add_instance()
            elif 'm_OutputVariableMinX' in value_class:
                property_instance = PropertyString(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea, expression_bool=False, only_string=True, placeholder='Variable name')
                add_instance()
            elif 'm_OutputVariable' in value_class:
                property_instance = PropertyString(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea)
                add_instance()
            # Comparison
            elif 'm_VariableComparison' in value_class:
                property_instance = PropertyComparison(value=value, value_class=value_class ,variables_scrollArea=self.variables_scrollArea)
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
            classes = ['m_SelectionMode','m_PointSpace','m_HandleShape','m_HandleColor', 'm_HandleSize','m_vHandleOffset']
            operator_adding_instances(classes)
        elif prop_class == 'PlaceInSphere':
            classes = ['m_nCountMin','m_nCountMax','m_flPositionRadiusInner','m_flPositionRadiusOuter', 'm_flRandomness', 'm_bAlignOrientation', 'm_PlacementMode']
            operator_adding_instances(classes)
        elif prop_class == 'PlaceOnPath':
            classes = ['m_PathName','m_vPathOffset','m_flOffsetAlongPath','m_PathSpace']
            operator_adding_instances(classes)
        elif prop_class == 'Model':
            classes = ['m_sModelName','m_vModelScale','m_MaterialGroupName']
            operator_adding_instances(classes)
        elif prop_class == 'SmartProp':
            classes = ['m_sSmartProp','m_vModelScale']
            operator_adding_instances(classes)
        elif prop_class == 'PlaceMultiple':
            classes = ['m_nCount']
            operator_adding_instances(classes)
        # Operators
        elif prop_class == 'CreateSizer':
            classes = ['m_flInitialMinX', 'm_flInitialMaxX', 'm_flConstraintMinX', 'm_flConstraintMaxX','m_OutputVariableMinX', 'm_OutputVariableMaxX', 'm_flInitialMinY', 'm_flInitialMaxY', 'm_flConstraintMinY', 'm_flConstraintMaxY', 'm_OutputVariableMinY', 'm_OutputVariableMaxY', 'm_flInitialMinZ', 'm_flInitialMaxZ', 'm_flConstraintMinZ', 'm_flConstraintMaxZ', 'm_OutputVariableMinZ', 'm_OutputVariableMaxZ']
            operator_adding_instances(classes)
        elif prop_class == 'CreateRotator':
            classes = ['m_vRotationAxis', 'm_CoordinateSpace', 'm_flDisplayRadius', 'm_bApplyToCurrentTrasnform','m_OutputVariable']
            operator_adding_instances(classes)
        elif prop_class == 'CreateLocator':
            classes = ['m_flDisplayScale', 'm_bAllowScale']
            operator_adding_instances(classes)
        elif prop_class == 'RandomRotation':
            classes = ['m_vRandomRotationMin', 'm_vRandomRotationMax']
            operator_adding_instances(classes)
        elif prop_class == 'Scale':
            classes = ['m_flScale']
            operator_adding_instances(classes)
        elif prop_class == 'SetTintColor':
            classes = ['m_Mode', 'm_ColorChoices']
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
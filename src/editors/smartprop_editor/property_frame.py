from src.settings.main import debug
from src.editors.smartprop_editor.ui_property_frame import Ui_Form

from PySide6.QtWidgets import QWidget, QMenu, QApplication
from PySide6.QtCore import Signal, Qt, QTimer, QThreadPool
from PySide6.QtGui import QAction

from src.property.methods import PropertyMethods
from src.widgets.popup_menu.main import PopupMenu
from src.widgets.element_id import ElementIDGenerator

from src.editors.smartprop_editor.property.legacy import PropertyLegacy
from src.editors.smartprop_editor.property.vector3d import PropertyVector3D
from src.editors.smartprop_editor.property.float import PropertyFloat
from src.editors.smartprop_editor.property.bool import PropertyBool
from src.editors.smartprop_editor.property.combobox import PropertyCombobox
from src.editors.smartprop_editor.property.string import PropertyString
from src.editors.smartprop_editor.property.color import PropertyColor
from src.editors.smartprop_editor.property.comparison import PropertyComparison
from src.editors.smartprop_editor.property.filtersurface import PropertySurface
from src.editors.smartprop_editor.property.colormatch import PropertyColorMatch
from src.editors.smartprop_editor.property.material_replacements import PropertyMaterialReplacements
from src.editors.smartprop_editor.property.material_group_choices import PropertyMaterialGroupChoices
from src.editors.smartprop_editor.property.variable import PropertyVariableOutput
from src.editors.smartprop_editor.objects import surfaces_list
from src.editors.smartprop_editor.property.set_variable import PropertyVariableValue
from src.editors.smartprop_editor.property.comment import PropertyComment
from src.editors.smartprop_editor.property.reference import PropertyReference
from src.editors.smartprop_editor.property.warning import PropertyWarning
from src.editors.smartprop_editor.property_tooltips import property_tooltips
from PySide6.QtGui import QCursor
from src.widgets import HierarchyItemModel
import uuid

import ast

from src.widgets import exception_handler
from src.editors.smartprop_editor.property_data_worker import (
    PropertyDataWorker,
)

class PropertyFrame(QWidget):
    edited = Signal()
    slider_pressed = Signal()
    committed = Signal()
    selected_signal = Signal()
    clicked = Signal(str)

    # A lookup dictionary to avoid multiple if/elif checks; cached at class level
    _prop_classes_map_cache = {
        'ModifyState': ['m_nReferenceID', 'm_bEnabled'],
        'Group': ['m_nReferenceID', 'm_bEnabled'],
        'SmartProp': ['m_nReferenceID', 'm_bEnabled', 'm_sSmartProp'],
        'PlaceInSphere': ['m_nReferenceID', 'm_bEnabled', 'm_flRandomness', 'm_nCountMin', 'm_nCountMax', 'm_flPositionRadiusInner', 'm_flPositionRadiusOuter', 'm_bAlignOrientation', 'm_PlacementMode', 'm_DistributionMode', 'm_vAlignDirection', 'm_vPlaneUpDirection'],
        'PlaceMultiple': ['m_nReferenceID', 'm_bEnabled', 'm_nCount'],
        'PlaceOnPath': ['m_nReferenceID', 'm_bEnabled', 'm_PathName', 'm_vPathOffset', 'm_flOffsetAlongPath', 'm_PathSpace', 'm_flSpacing', 'm_SpacingSpace', 'm_bContinuousSpline', 'm_bUseFixedUpDirection', 'm_bUseProjectedDistance', 'm_vUpDirection', 'm_UpDirectionSpace', 'm_DefaultPath'],
        'FitOnLine': ['m_nReferenceID', 'm_bEnabled', 'm_vStart', 'm_vEnd', 'm_PointSpace', 'm_bOrientAlongLine', 'm_vUpDirection', 'm_UpDirectionSpace', 'm_bPrioritizeUp', 'm_nScaleMode', 'm_nPickMode'],
        'PickOne': ['m_nReferenceID', 'm_bEnabled', 'm_SelectionMode', 'm_SpecificChildIndex', 'm_OutputChoiceVariableName', 'm_bConfigurable', 'm_vHandleOffset', 'm_HandleColor', 'm_HandleSize', 'm_HandleShape'],
        'Model': ['m_nReferenceID', 'm_bEnabled', 'm_sModelName', 'm_bForceStatic', 'm_vModelScale', 'm_MaterialGroupName', 'm_bDetailObject', 'm_bRigidDeformation', 'm_nLodLevel', 'm_DetailObjectFadeLevel', 'm_nDeformableAttachmentMode', 'm_nDeformableOrientationMode', 'm_bCastShadows', 'm_flUniformModelScale', 'm_SurfacePropertyOverride'],
        'ModelEntity': ['m_nReferenceID', 'm_bEnabled', 'm_sModelName', 'm_vModelScale', 'm_MaterialGroupName', 'm_bDetailObject', 'm_bRigidDeformation', 'm_nLodLevel', 'm_bCastShadows', 'm_bForceStatic', 'm_nDeformableAttachmentMode', 'm_nDeformableOrientationMode'],
        'BendDeformer': ['m_nReferenceID', 'm_bEnabled', 'm_bDeformationEnabled', 'm_vOrigin', 'm_vAngles', 'm_vSize', 'm_flBendAngle', 'm_flBendPoint', 'm_flBendRadius'],
        'PropPhysics': ['m_nReferenceID', 'm_bEnabled', 'm_sModelName', 'm_vModelScale', 'm_MaterialGroupName', 'm_flMass', 'm_bStartAsleep', 'm_nHealth', 'm_bEnableMotion', 'm_sPhysicsType'],
        'PropDynamic': ['m_nReferenceID', 'm_bEnabled', 'm_sModelName', 'm_sAnimationSequence', 'm_sDefaultAnimation', 'm_vModelScale', 'm_MaterialGroupName'],
        'MidpointDeformer': ['m_nReferenceID', 'm_bEnabled', 'm_bDeformationEnabled', 'm_vStart', 'm_vEnd', 'm_fRadius', 'm_bContinuousSpline', 'm_vOffset', 'm_vAngles', 'm_vScale', 'm_fFalloff', 'm_OutputVariable'],
        'Layout2DGrid': ['m_nReferenceID', 'm_bEnabled', 'm_flWidth', 'm_flLength', 'm_bVerticalLength', 'm_GridArrangement', 'm_GridOriginMode', 'm_nCountW', 'm_nCountL', 'm_flSpacingWidth', 'm_flSpacingLength', 'm_bAlternateShift', 'm_flAlternateShiftWidth', 'm_flAlternateShiftLength'],
        'Grid': ['m_nReferenceID', 'm_bEnabled', 'm_flWidth', 'm_flLength', 'm_bVerticalLength', 'm_GridArrangement', 'm_GridOriginMode', 'm_nCountW', 'm_nCountL', 'm_flSpacingWidth', 'm_flSpacingLength', 'm_bAlternateShift', 'm_flAlternateShiftWidth', 'm_flAlternateShiftLength'],
        'Rotate': ['m_bEnabled', 'm_vRotation'],
        'Scale': ['m_bEnabled', 'm_flScale'],
        'Translate': ['m_bEnabled', 'm_vPosition'],
        'SetTintColor': ['m_bEnabled', 'm_Mode', 'm_ColorChoices'],
        'MaterialOverride': ['m_bEnabled', 'm_bClearCurrentOverrides', 'm_MaterialReplacements'],
        'MaterialTint': ['m_bEnabled', 'm_Material', 'm_SelectionMode', 'm_Color', 'm_ColorPosition'],
        'RandomOffset': ['m_bEnabled', 'm_vRandomPositionMin', 'm_vRandomPositionMax', 'm_vSnapIncrement'],
        'RandomScale': ['m_bEnabled', 'm_flRandomScaleMin', 'm_flRandomScaleMax', 'm_flSnapIncrement'],
        'RandomColorTintColor': ['m_bEnabled', 'm_SelectionMode', 'm_Color', 'm_ColorPosition', 'm_Mode'],
        'CreateSizer': ['m_bEnabled', 'm_Name', 'm_bDisplayModel',
                        'm_flInitialMinX', 'm_flInitialMaxX', 'm_flConstraintMinX', 'm_flConstraintMaxX', 'm_OutputVariableMinX', 'm_OutputVariableMaxX',
                        'm_flInitialMinY', 'm_flInitialMaxY', 'm_flConstraintMinY', 'm_flConstraintMaxY', 'm_OutputVariableMinY', 'm_OutputVariableMaxY',
                        'm_flInitialMinZ', 'm_flInitialMaxZ', 'm_flConstraintMinZ', 'm_flConstraintMaxZ', 'm_OutputVariableMinZ', 'm_OutputVariableMaxZ'],
        'CreateRotator': ['m_bEnabled', 'm_Name', 'm_vOffset', 'm_vRotationAxis', 'm_CoordinateSpace', 'm_flDisplayRadius', 'm_DisplayColor', 'm_bApplyToCurrentTransform', 'm_flSnappingIncrement', 'm_flInitialAngle', 'm_bEnforceLimits', 'm_flMinAngle', 'm_flMaxAngle', 'm_OutputVariable'],
        'CreateLocator': ['m_bEnabled', 'm_LocatorName', 'm_vOffset', 'm_flDisplayScale', 'm_bConfigurable', 'm_bAllowTranslation', 'm_bAllowRotation', 'm_bAllowScale'],
        'RestoreState': ['m_bEnabled', 'm_bDiscardIfUknown'],
        'TraceInDirection': ['m_bEnabled', 'm_DirectionSpace', 'm_flSurfaceUpInfluence', 'm_nNoHitResult', 'm_flOriginOffset', 'm_flTraceLength'],
        'SaveState': ['m_bEnabled', 'm_StateName'],
        'SetVariable': ['m_bEnabled', 'm_VariableValue'],
        'RandomRotationSnapped': ['m_bEnabled', 'm_vMinAngles', 'm_vMaxAngles', 'm_flSnapIncrement', 'm_RotationAxes'],
        'ResetRotation': ['m_bEnabled', 'm_bIgnoreObjectRotation', 'm_bResetPitch', 'm_bResetYaw', 'm_bResetRoll'],
        'ResetScale': ['m_bEnabled', 'm_bIgnoreObjectScale'],
        'RotateTowards': ['m_bEnabled', 'm_vOriginPos', 'm_vTargetPos', 'm_vUpPos', 'm_flWeight', 'm_OriginSpace', 'm_TargetSpace', 'm_UpSpace'],
        'SaveColor': ['m_bEnabled', 'm_VariableName'],
        'SaveDirection': ['m_bEnabled', 'm_DirectionVector', 'm_CoordinateSpace', 'm_VariableName'],
        'SavePosition': ['m_bEnabled', 'm_CoordinateSpace', 'm_VariableName'],
        'SaveScale': ['m_bEnabled', 'm_VariableName'],
        'SaveSurfaceNormal': ['m_bEnabled', 'm_CoordinateSpace', 'm_VariableName'],
        'SetMaterialGroupChoice': ['m_bEnabled', 'm_VariableName', 'm_SelectionMode', 'm_ChoiceSelection', 'm_MaterialGroupChoices'],
        'SetOrientation': ['m_bEnabled', 'm_vForwardVector', 'm_ForwardDirectionSpace', 'm_vUpVector', 'm_UpDirectionSpace', 'm_bPrioritizeUp'],
        'SetPosition': ['m_bEnabled', 'm_vPosition', 'm_CoordinateSpace'],
        'Trace': ['m_bEnabled', 'm_Origin', 'm_OriginSpace', 'm_flOriginOffset', 'm_flSurfaceUpInfluence', 'm_nNoHitResult', 'm_bIgnoreToolMaterials', 'm_bIgnoreSky', 'm_bIgnoreNoDraw', 'm_bIgnoreTranslucent', 'm_bIgnoreModels', 'm_bIgnoreEntities', 'm_bIgnoreCables'],
        'Comment': ['m_bEnabled', 'm_Comment'],
        'Expression': ['m_bEnabled', 'm_Expression'],
        'Probability': ['m_bEnabled', 'm_flProbability'],
        'SurfaceAngle': ['m_bEnabled', 'm_flSurfaceSlopeMin', 'm_flSurfaceSlopeMax'],
        'SurfaceProperties': ['m_bEnabled', 'm_AllowedSurfaceProperties', 'm_DisallowedSurfaceProperties'],
        'VariableValue': ['m_bEnabled', 'm_VariableComparison'],
        'EndCap': ['m_bEnabled', 'm_bStart', 'm_bEnd'],
        'ChoiceWeight': ['m_bEnabled', 'm_flWeight'],
        'IsValid': ['m_bEnabled'],
        'LinearLength': ['m_bEnabled', 'm_flLength', 'm_bAllowScale', 'm_flMinLength', 'm_flMaxLength'],
        'PathPosition': ['m_bEnabled', 'm_PlaceAtPositions', 'm_nPlaceEveryNthPosition', 'm_nNthPositionIndexOffset', 'm_bAllowAtStart', 'm_bAllowAtEnd'],
        'ComputeDistance3D': ['m_bEnabled', 'm_OutputVariableName', 'm_OutputCoordinateSpace', 'm_InputPositionA', 'm_CoordinateSpaceA', 'm_InputPositionB', 'm_CoordinateSpaceB'],
        'ComputeDotProduct3D': ['m_bEnabled', 'm_OutputVariableName', 'm_InputVectorA', 'm_InputVectorB'],
        'ComputeCrossProduct3D': ['m_bEnabled', 'm_OutputVariableName', 'm_InputVectorA', 'm_InputVectorB'],
        'ComputeNormalizedVector3D': ['m_bEnabled', 'm_OutputVariableName', 'm_InputVector'],
        'ComputeProjectVector3D': ['m_bEnabled', 'm_OutputVariableName', 'm_OutputCoordinateSpace', 'm_InputVectorA', 'm_CoordinateSpaceA', 'm_InputVectorB', 'm_CoordinateSpaceB', 'm_bPlane'],
        'ComputeVectorBetweenPoints3D': ['m_bEnabled', 'm_OutputVariableName', 'm_OutputCoordinateSpace', 'm_bNormalized', 'm_InputPositionA', 'm_CoordinateSpaceA', 'm_InputPositionB', 'm_CoordinateSpaceB'],
    }

    # Pre-built ordered_pairs skeletons: (key, None) per known class; worker fills values.
    _ORDERED_PAIRS_CACHE: dict = {}

    # Dedicated pool for property data prep (avoid flooding QThreadPool.globalInstance()).
    _PROPERTY_WORKER_POOL = None

    @classmethod
    def _build_ordered_pairs_cache(cls):
        """Build once at import — same order as reversed(_prop_classes_map_cache[key])."""
        cls._ORDERED_PAIRS_CACHE.clear()
        for prop_class, keys in cls._prop_classes_map_cache.items():
            cls._ORDERED_PAIRS_CACHE[prop_class] = [
                (k, None) for k in reversed(keys)
            ]

    @classmethod
    def _get_worker_pool(cls) -> QThreadPool:
        if cls._PROPERTY_WORKER_POOL is None:
            pool = QThreadPool()
            pool.setMaxThreadCount(4)
            pool.setExpiryTimeout(10_000)
            cls._PROPERTY_WORKER_POOL = pool
        return cls._PROPERTY_WORKER_POOL

    _SKIP_PROPS = frozenset({'_class', 'm_sLabel', 'm_nElementID', 'm_sReferenceObjectID', '_WARN_NOT_VERIFIED'})

    # Class-level copy for batch/prewarm workers (same keys as instance only_variable_properties).
    _ONLY_VARIABLE_PROPERTIES = ()

    # Combobox fields: (substring in value_class, items, filter_types) — order matters.
    _COMBOBOX_SUBSTRING_RULES = (
        ('m_SurfacePropertyOverride', [list(d.keys())[0] for d in surfaces_list], ['SurfaceProperty']),
        ('m_nPickMode', ['LARGEST_FIRST', 'RANDOM', 'ALL_IN_ORDER'], ['PickMode']),
        ('m_nScaleMode', ['NONE', 'SCALE_END_TO_FIT', 'SCALE_EQUALLY', 'SCALE_MAXIMAIZE'], ['ScaleMode']),
        ('m_CoordinateSpace', ['ELEMENT', 'OBJECT', 'WORLD'], ['CoordinateSpace']),
        ('m_DirectionSpace', ['ELEMENT', 'OBJECT', 'WORLD'], ['DirectionSpace']),
        ('m_GridPlacementMode', ['SEGMENT', 'FILL'], ['GridPlacementMode']),
        ('m_GridArrangement', ['SEGMENT', 'FILL'], ['GridPlacementMode']),
        ('m_GridOriginMode', ['CENTER', 'CORNER'], ['GridOriginMode']),
        ('m_nNoHitResult', ['NOTHING', 'DISCARD', 'MOVE_TO_START', 'MOVE_TO_END'], ['TraceNoHit']),
        ('m_SelectionMode', ['RANDOM', 'FIRST', 'SPECIFIC', 'SPECIFIC_COLOR', 'GRADIENT_RANDOM', 'GRADIENT_RANDOM_STOP', 'GRADIENT_LOCATION'], ['ChoiceSelectionMode']),
        ('m_PlacementMode', ['SPHERE', 'CIRCLE', 'RING'], ['RadiusPlacementMode']),
        ('m_DistributionMode', ['RANDOM', 'UNIFORM'], ['DistributionMode']),
        ('m_SpacingSpace', ['ELEMENT', 'OBJECT', 'WORLD'], ['CoordinateSpace']),
        ('m_sPhysicsType', ['normal', 'multiplayer'], ['String']),
        ('m_DetailObjectFadeLevel', ['NONE', 'MOST_AGGRESSIVE', 'MORE_AGGRESSIVE', 'NORMAL', 'LESS_AGGRESSIVE', 'LEAST_AGGRESSIVE'], ['String']),
        ('m_RotationAxes', ['X', 'Y', 'Z', 'XY', 'XZ', 'YZ', 'XYZ'], ['Axes']),
        ('m_HandleShape', ['SQUARE', 'DIAMOND', 'CIRCLE'], ['HandleShape']),
        ('m_nDeformableAttachmentMode', ['RELATIVE', 'SNAP', 'STIFFEN'], ['SmartPropDeformableAttachMode_t']),
        ('m_nDeformableOrientationMode', ['NONE', 'FORWARD_NORMAL', 'UP_NORMAL', 'BACKWARD_NORMAL', 'MAINTAIN_OFFSET'], ['SmartPropDeformableOrientMode_t']),
        ('m_PointSpace', ['ELEMENT', 'OBJECT', 'WORLD'], ['CoordinateSpace']),
        ('m_PathSpace', ['ELEMENT', 'OBJECT', 'WORLD'], ['CoordinateSpace']),
        ('m_UpDirectionSpace', ['ELEMENT', 'OBJECT', 'WORLD'], ['CoordinateSpace']),
        ('m_PlaceAtPositions', ['ALL', 'NTH', 'START_AND_END', 'CONTROL_POINTS'], ['PathPositions']),
        ('m_Mode', ['MULTIPLY_OBJECT', 'MULTIPLY_CURRENT', 'REPLACE'], ['ApplyColorMode']),
        ('m_ApplyColorMode', ['MULTIPLY_OBJECT', 'MULTIPLY_CURRENT', 'REPLACE'], ['ApplyColorMode']),
        ('m_OriginSpace', ['ELEMENT', 'OBJECT', 'WORLD'], ['CoordinateSpace']),
        ('m_TargetSpace', ['ELEMENT', 'OBJECT', 'WORLD'], ['CoordinateSpace']),
        ('m_UpSpace', ['ELEMENT', 'OBJECT', 'WORLD'], ['CoordinateSpace']),
        ('m_TargetPointSpace', ['ELEMENT', 'OBJECT', 'WORLD'], ['CoordinateSpace']),
        ('m_EndPointSpaceA', ['ELEMENT', 'OBJECT', 'WORLD'], ['CoordinateSpace']),
        ('m_EndPointSpaceB', ['ELEMENT', 'OBJECT', 'WORLD'], ['CoordinateSpace']),
    )

    # Populated lazily in _resolve_dispatch() — ordered prefix fallthrough.
    _PREFIX_DISPATCH: list = []

    # Exact-match dispatch: maps value_class -> (WidgetClass, extra_kwargs_dict)
    # PropertyComment is NOT in this dict — handled separately (different signature)
    _EXACT_PROP_DISPATCH = None  # populated lazily by _resolve_dispatch()
    _DISPATCH_RESOLVED = False

    @classmethod
    def _resolve_dispatch(cls):
        if cls._DISPATCH_RESOLVED:
            return

        cls._EXACT_PROP_DISPATCH = {
            'm_bEnabled':              (PropertyBool,                 {}),
            'm_nReferenceID':          (PropertyReference,            {}),
            'm_HandleColor':           (PropertyColor,                {}),
            'm_HandleSize':            (PropertyFloat,                {}),
            'm_ColorChoices':          (PropertyColorMatch,           {}),
            'm_MaterialReplacements':  (PropertyMaterialReplacements, {}),
            'm_MaterialGroupChoices':  (PropertyMaterialGroupChoices, {}),
            'm_ChoiceSelection':       (PropertyFloat,   {'int_bool': True}),
            'm_Color':                 (PropertyColor,                {}),
            'm_ColorPosition':         (PropertyFloat,   {'slider_range': [0, 1]}),
            'm_Material':              (PropertyString,  {'expression_bool': False, 'placeholder': 'Material name (.vmat)', 'filter_types': ['String']}),
            'm_flBendPoint':           (PropertyFloat,   {'slider_range': [0, 1]}),
            'm_flWidth':               (PropertyFloat,   {'slider_range': [0, 4096]}),
            'm_flLength':              (PropertyFloat,   {'slider_range': [0, 4096]}),
            'm_flSpacingWidth':        (PropertyFloat,   {'slider_range': [0, 4096]}),
            'm_flSpacingLength':       (PropertyFloat,   {'slider_range': [0, 4096]}),
            'm_flAlternateShiftWidth': (PropertyFloat,   {'slider_range': [0, 4096]}),
            'm_flAlternateShiftLength':(PropertyFloat,   {'slider_range': [0, 4096]}),
            'm_nCountW':               (PropertyFloat,   {'int_bool': True, 'slider_range': [0, 256]}),
            'm_nCountL':               (PropertyFloat,   {'int_bool': True, 'slider_range': [0, 256]}),
            'm_SpecificChildIndex':    (PropertyFloat,   {'int_bool': True}),
            'm_ColorSelection':        (PropertyFloat,   {'int_bool': True}),
            'm_MaterialGroupName':     (PropertyString,  {'expression_bool': False, 'placeholder': 'Material group name'}),
            'm_Expression':            (PropertyString,  {'expression_bool': True,  'placeholder': 'Expression example: var_bool ? var_sizer * var_multiply'}),
            'm_StateName':             (PropertyString,  {'expression_bool': False, 'only_string': True, 'placeholder': 'State name'}),
            'm_LocatorName':           (PropertyString,  {'expression_bool': False, 'placeholder': 'Locator name'}),
            'm_VariableName':          (PropertyVariableOutput,  {'filter_types': ['String', 'Int', 'Float', 'Bool', 'Vector3D', 'Color']}),
            'm_OutputVariableName':    (PropertyVariableOutput,  {'filter_types': ['String', 'Int', 'Float', 'Bool', 'Vector3D']}),
            'm_OutputVariableMaxZ':    (PropertyVariableOutput,  {}),
            'm_OutputVariableMinZ':    (PropertyVariableOutput,  {}),
            'm_OutputVariableMaxY':    (PropertyVariableOutput,  {}),
            'm_OutputVariableMinY':    (PropertyVariableOutput,  {}),
            'm_OutputVariableMaxX':    (PropertyVariableOutput,  {}),
            'm_OutputVariableMinX':    (PropertyVariableOutput,  {}),
            'm_OutputVariable':        (PropertyVariableOutput,  {}),
            'm_OutputChoiceVariableName': (PropertyVariableOutput, {}),
            '_WARN_NOT_VERIFIED':      (PropertyWarning,              {}),
        }

        # Most frequent first; first matching substring wins after exact + combobox miss.
        cls._PREFIX_DISPATCH = [
            ('m_fl', PropertyFloat, {}),
            ('m_f', PropertyFloat, {}),
            ('m_n', PropertyFloat, {'int_bool': True}),
            ('m_InputVector', PropertyVector3D, {}),
            ('m_Origin', PropertyVector3D, {}),
            ('m_TargetPoint', PropertyVector3D, {}),
            ('m_EndPoint', PropertyVector3D, {}),
            ('m_v', PropertyVector3D, {}),
            ('m_b', PropertyBool, {}),
            ('m_s', PropertyString, {'expression_bool': False, 'placeholder': 'String'}),
            ('m_', PropertyString, {'expression_bool': False, 'placeholder': 'String'}),
        ]

        cls._DISPATCH_RESOLVED = True

    @staticmethod
    def _is_complete_precomputed_payload(prepared) -> bool:
        """Batch/worker dict must have every key _apply_precomputed_payload needs."""
        if prepared is None or not isinstance(prepared, dict):
            return False
        need = (
            "value",
            "ordered_pairs",
            "name_prefix",
            "name",
            "element_id",
            "prop_class",
        )
        if not all(k in prepared for k in need):
            return False
        if not isinstance(prepared.get("value"), dict):
            return False
        op = prepared.get("ordered_pairs")
        if not isinstance(op, list):
            return False
        return True

    def __init__(
        self,
        value,
        widget_list,
        variables_scrollArea,
        element_id_generator,
        element=False,
        tree_hierarchy=None,
        precomputed=None,
        parent=None,
    ):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        # Mirrors insertWidget(0, ...) order — avoids O(n) layout scan in on_edited.
        self._property_widgets: list = []
        self._is_selected = False
        self._group_type = None
        self.setAcceptDrops(True)
        self.ui.property_class.setAcceptDrops(False)
        self.variables_scrollArea = variables_scrollArea
        self.element = element
        if tree_hierarchy is None:
            raise ValueError("tree_hierarchy cannot be None - a valid hierarchy structure is required")
        else:
            self.tree_hierarchy = tree_hierarchy

        self.element_id_generator = element_id_generator

        self.layout = self.ui.layout

        self.widget_list = widget_list

        if self.element:
            self.ui.copy_button.deleteLater()
            self.ui.delete_button.deleteLater()
        else:
            self.ui.copy_button.clicked.connect(self.copy_action)
            self.ui.delete_button.clicked.connect(self.delete_action)

        self.only_variable_properties = list(self._ONLY_VARIABLE_PROPERTIES)

        # Worker result storage
        self._ordered_pairs = None
        self._worker_signals = None
        self._worker_generation = 0
        # PySide6 often cannot disconnect(bound_method) reliably; connect once per frame.
        self._show_child_signal_connected = False
        self._context_menu_signal_connected = False

        if self._is_complete_precomputed_payload(precomputed):
            self._apply_precomputed_payload(precomputed)
            QTimer.singleShot(0, self._finish_init)
        else:
            # Use ast.literal_eval only if not already a dict
            if not isinstance(value, dict):
                value = ast.literal_eval(value)

            # Keep a raw payload containing '_class' for the worker thread.
            self._worker_raw_value_with_class = dict(value)

            if "_class" not in value:
                raise ValueError(
                    "PropertyFrame value dict missing '_class' and no valid precomputed payload"
                )

            self.name_prefix, self.name = value['_class'].split('_', 1)
            self.value = {'m_bEnabled': True}
            self.value.update(value)

            #===========================================================<  Element ID  >========================================================
            self.element_id_generator.update_value(self.value)
            self.element_id = self.element_id_generator.get_key(self.value)
            debug(f'Property frame get_ElementID: {self.element_id}')
            self.ui.element_id_display.setText(str(self.element_id))
            if isinstance(self._worker_raw_value_with_class, dict):
                self._worker_raw_value_with_class['m_nElementID'] = self.element_id

            self.prop_class = self.name
            self.ui.property_class.setText(self.name)

            self._start_data_worker()

    def _apply_precomputed_payload(self, prepared_data: dict):
        """Apply worker/batch-prepared fields; no background worker."""
        self.value = dict(prepared_data["value"])
        self.name_prefix = prepared_data["name_prefix"]
        self.name = prepared_data["name"]
        self.element_id = prepared_data["element_id"]
        self.prop_class = prepared_data["prop_class"]
        self._ordered_pairs = prepared_data["ordered_pairs"]
        self.value["m_nElementID"] = self.element_id
        debug(f'Property frame get_ElementID (precomputed): {self.element_id}')
        self.ui.element_id_display.setText(str(self.element_id))
        self.ui.property_class.setText(self.name)
        self._worker_raw_value_with_class = dict(self.value)
        self._worker_raw_value_with_class["_class"] = f"{self.name_prefix}_{self.name}"

    def _finish_init(self):
        """
        Phase 1: populate the first 4 property widgets immediately for fast
        perceived response. The remaining properties are deferred one tick.
        on_edited() is NOT called here — the value dict is incomplete until
        Phase 2 finishes.
        """
        self._add_properties_by_class(limit=4)
        self.show_child()

        # Connect once per PropertyFrame lifetime (pool reuse / repeated _finish_init).
        if not self._show_child_signal_connected:
            self.ui.show_child.clicked.connect(self.show_child)
            self._show_child_signal_connected = True

        self.init_ui()

        # Defer Phase 2 one event-loop tick (no artificial ms delay)
        QTimer.singleShot(0, self._finish_init_phase2)

    def _finish_init_phase2(self):
        """
        Phase 2: populate remaining properties and finalize the value dict.
        _setup_layout2dgrid_suppression requires ALL widgets to be present.
        on_edited() is called here for the first time — value dict is now complete.
        """
        self._add_properties_by_class(offset=4)
        
        # Add unverified warning at the VERY END of both phases so that 
        # insertWidget(0,...) puts it at the absolute top of the layout.
        if "_WARN_NOT_VERIFIED" in self.value:
            self._add_widget_for_property('_WARN_NOT_VERIFIED', self.value.get("_WARN_NOT_VERIFIED"), force=True)

        self._setup_layout2dgrid_suppression()
        self.on_edited()

    @exception_handler
    def _add_widget_for_property(self, value_class, val, force=False):
        """Internal helper to create and initialize a property widget instance."""
        def add_instance():
            # PropertyWarning is a static label — do NOT connect its edited
            # signal to on_edited, otherwise it triggers spurious undo actions.
            if not isinstance(property_instance, PropertyWarning):
                property_instance.edited.connect(self.on_edited)
            property_instance.setAcceptDrops(False)
            self.ui.layout.insertWidget(0, property_instance)
            self._property_widgets.insert(0, property_instance)
            # Pooled widgets return from acquire() hidden (never shown in
            # acquire to avoid top-level flash); show after reparenting.
            property_instance.show()

            # Apply tooltips if available for this property.
            if hasattr(property_instance, 'ui') and hasattr(property_instance.ui, 'property_class'):
                tip = property_tooltips.get(value_class, "")
                if tip:
                    property_instance.ui.property_class.setToolTip(tip)

            if hasattr(property_instance, 'slider_pressed'):
                property_instance.slider_pressed.connect(self.slider_pressed)
            if hasattr(property_instance, 'committed'):
                property_instance.committed.connect(self.committed)

        # ---- FAST PATH: skip list ----
        if not force and value_class in PropertyFrame._SKIP_PROPS:
            return

        # ---- FAST PATH: exact dispatch ----
        PropertyFrame._resolve_dispatch()
        dispatch = PropertyFrame._EXACT_PROP_DISPATCH
        if dispatch is not None and value_class in dispatch:
            widget_cls, extra_kwargs = dispatch[value_class]

            if widget_cls is PropertyReference:
                property_instance = widget_cls(
                    value=val,
                    value_class=value_class,
                    variables_scrollArea=self.variables_scrollArea,
                    element_id_generator=self.element_id_generator,
                    tree_hierarchy=self.tree_hierarchy,
                    **extra_kwargs
                )
            else:
                if hasattr(widget_cls, "acquire") and callable(getattr(widget_cls, "acquire")):
                    property_instance = widget_cls.acquire(
                        value=val,
                        value_class=value_class,
                        variables_scrollArea=self.variables_scrollArea,
                        element_id_generator=self.element_id_generator,
                        **extra_kwargs,
                    )
                else:
                    property_instance = widget_cls(
                        value=val,
                        value_class=value_class,
                        variables_scrollArea=self.variables_scrollArea,
                        element_id_generator=self.element_id_generator,
                        **extra_kwargs
                    )

            add_instance()
            return

        if 'm_VariableValue' in value_class:
            if val is None:
                property_instance = PropertyVariableValue(
                    value=val,
                    value_class=value_class,
                    variables_scrollArea=self.variables_scrollArea,
                    element_id_generator=self.element_id_generator,
                )
            elif 'm_TargetName' not in val:
                property_instance = PropertyString.acquire(
                    value=val,
                    value_class=value_class,
                    variables_scrollArea=self.variables_scrollArea,
                    expression_bool=True,
                    element_id_generator=self.element_id_generator,
                )
            else:
                property_instance = PropertyVariableValue(
                    value=val,
                    value_class=value_class,
                    variables_scrollArea=self.variables_scrollArea,
                    element_id_generator=self.element_id_generator,
                )
            add_instance()
            return

        if 'm_VariableComparison' in value_class:
            property_instance = PropertyComparison(
                value=val,
                value_class=value_class,
                variables_scrollArea=self.variables_scrollArea,
                element_id_generator=self.element_id_generator,
            )
            self.ui.property_class.setText('Variable Comparison')
            add_instance()
            return

        if 'm_AllowedSurfaceProperties' in value_class:
            property_instance = PropertySurface(
                value=val,
                value_class=value_class,
                variables_scrollArea=self.variables_scrollArea,
            )
            add_instance()
            return

        if 'm_DisallowedSurfaceProperties' in value_class:
            property_instance = PropertySurface(
                value=val,
                value_class=value_class,
                variables_scrollArea=self.variables_scrollArea,
            )
            add_instance()
            return

        if 'm_Comment' in value_class:
            property_instance = PropertyComment(value=val, value_class=value_class)
            add_instance()
            return

        for sub, items, fts in PropertyFrame._COMBOBOX_SUBSTRING_RULES:
            if sub in value_class:
                property_instance = PropertyCombobox.acquire(
                    value=val,
                    value_class=value_class,
                    variables_scrollArea=self.variables_scrollArea,
                    items=list(items),
                    filter_types=list(fts),
                    element_id_generator=self.element_id_generator,
                )
                add_instance()
                return

        for prefix, widget_cls, extra_kw in PropertyFrame._PREFIX_DISPATCH:
            if prefix in value_class:
                if hasattr(widget_cls, 'acquire') and callable(getattr(widget_cls, 'acquire')):
                    property_instance = widget_cls.acquire(
                        value=val,
                        value_class=value_class,
                        variables_scrollArea=self.variables_scrollArea,
                        element_id_generator=self.element_id_generator,
                        **extra_kw,
                    )
                else:
                    property_instance = widget_cls(
                        value=val,
                        value_class=value_class,
                        variables_scrollArea=self.variables_scrollArea,
                        element_id_generator=self.element_id_generator,
                        **extra_kw
                    )
                add_instance()
                return

        property_instance = PropertyLegacy(
            value=val,
            value_class=value_class,
            variables_scrollArea=self.variables_scrollArea,
        )
        add_instance()

    @exception_handler
    def _add_properties_by_class(self, limit=None, offset=0):
        # This function adds property widgets when needed
        try:
            parent_widget = self.ui.layout.parentWidget()
            if parent_widget is not None:
                parent_widget.setUpdatesEnabled(False)
        except RuntimeError:
            # Widget or layout was destroyed before this scheduled update ran
            return

        try:
            # Prefer worker-prepared ordered pairs (Plan 5).
            if getattr(self, '_ordered_pairs', None) is not None:
                ordered_pairs = self._ordered_pairs
            elif self.prop_class in self._prop_classes_map_cache:
                classes = self._prop_classes_map_cache[self.prop_class]
                ordered_pairs = [
                    (item, self.value.get(item, None))
                    for item in reversed(classes)
                ]
            else:
                ordered_pairs = list(reversed(list(self.value.items())))

            end = (offset + limit) if limit is not None else None
            sliced = ordered_pairs[offset:end]
            for value_class, val_data in sliced:
                self._add_widget_for_property(value_class, val_data)
        finally:
            if parent_widget is not None:
                parent_widget.setUpdatesEnabled(True)
                parent_widget.update()

    def show_child(self):
        if not self.ui.show_child.isChecked():
            self.ui.frame_layout.setMaximumSize(16666, 0)
        else:
            self.ui.frame_layout.setMaximumSize(16666, 16666)

    def on_edited(self):
        old_value = getattr(self, 'value', {}).copy()
        
        self.value = {
            '_class': f'{self.name_prefix}_{self.name}',
            'm_nElementID': self.element_id,
        }
        
        widget_output = {}
        widget_managed_keys = set()
        
        for w in self._property_widgets:
            v = getattr(w, 'value', None)
            if v:
                widget_output.update(v)
                widget_managed_keys.update(v.keys())
            vc = getattr(w, 'value_class', None)
            if vc:
                widget_managed_keys.add(vc)
                
        # Bring over unmanaged properties (custom manual edits)
        for k, v in old_value.items():
            if k not in widget_managed_keys and k not in ('_class', 'm_nElementID'):
                self.value[k] = v
                
        self.value.update(widget_output)
        
        self.edited.emit()

    def update_self(self):
        pass

    def update_property_value(self, key, new_value):
        """Update a single child property widget by key. Returns True if successful."""
        for w in self._property_widgets:
            if getattr(w, 'value_class', None) == key:
                if hasattr(w, 'reconfigure'):
                    # Collect widget-specific config stored from prior construction
                    extra_kw = {}
                    if hasattr(w, '_pool_items'):
                        extra_kw['items'] = w._pool_items
                    if hasattr(w, '_pool_filter_types'):
                        extra_kw['filter_types'] = w._pool_filter_types
                    w.reconfigure(
                        element_id_generator=self.element_id_generator,
                        value_class=key,
                        value=new_value,
                        variables_scrollArea=self.variables_scrollArea,
                        **extra_kw,
                    )
                    return True
                return False
        return False

    def _clear_widgets(self):
        """
        Remove and schedule destruction of all property child widgets.
        Calls setParent(None) before deleteLater() to immediately detach from
        the layout — prevents a double-widget race if the frame is reused
        before the event loop processes deleteLater().
        """
        while self.ui.layout.count():
            item = self.ui.layout.takeAt(0)
            w = item.widget()
            if w is not None:
                try:
                    # Pooled widgets should be returned to their pool.
                    if hasattr(type(w), "release") and callable(getattr(type(w), "release")):
                        type(w).release(w)
                    else:
                        w.setParent(None)
                        w.deleteLater()
                except Exception:
                    # If pooling fails for any reason, fall back to safe deletion.
                    w.setParent(None)
                    w.deleteLater()
        self._property_widgets.clear()

    def _reconfigure(
        self,
        value,
        variables_scrollArea,
        element_id_generator,
        widget_list,
        tree_hierarchy,
        precomputed=None,
    ):
        """
        Reconfigure this pooled PropertyFrame with new data.
        Called by PropertyWidgetPool.acquire().
        """
        import ast as _ast

        self.cancel_worker()
        # Invalidate any in-flight worker results (race safety).
        self._worker_generation = getattr(self, "_worker_generation", 0) + 1
        self._ordered_pairs = None

        self._clear_widgets()
        self._property_widgets = []

        self.variables_scrollArea = variables_scrollArea
        self.widget_list = widget_list
        self.tree_hierarchy = tree_hierarchy
        self.element_id_generator = element_id_generator

        if self._is_complete_precomputed_payload(precomputed):
            self._apply_precomputed_payload(precomputed)
            self.show()
            QTimer.singleShot(0, self._finish_init)
            return

        if not isinstance(value, dict):
            value = _ast.literal_eval(value)

        if "_class" not in value:
            raise ValueError("PropertyFrame._reconfigure: value dict missing '_class'")

        self.name_prefix, self.name = value["_class"].split("_", 1)
        value = dict(value)

        # Definition of the value variable before getting property data.
        self.value = {"m_bEnabled": True}
        self.value.update(value)

        self.element_id_generator.update_value(self.value)
        self.element_id = self.element_id_generator.get_key(self.value)

        self.ui.element_id_display.setText(str(self.element_id))
        self.prop_class = self.name
        self.ui.property_class.setText(self.name)

        self.show()
        QTimer.singleShot(0, self._finish_init)

    def cancel_worker(self):
        """Cancel in-flight PropertyDataWorker (thread-safe); clears active reference."""
        w = getattr(self, "_active_worker", None)
        if w is not None:
            try:
                w.cancel()
            except Exception:
                pass
            self._active_worker = None

    def _start_data_worker(self):
        """Dispatch data preparation to QThreadPool worker."""
        if not hasattr(self, "_worker_raw_value_with_class"):
            # No raw payload available — fall back to synchronous init.
            self._ordered_pairs = None
            self._finish_init()
            return

        self.cancel_worker()
        self._worker_generation += 1
        expected_gen = self._worker_generation

        worker = PropertyDataWorker(
            raw_value=self._worker_raw_value_with_class,
            element_id_generator=self.element_id_generator,
            prop_classes_map_cache=self._prop_classes_map_cache,
            only_variable_properties=self.only_variable_properties,
            ordered_pairs_cache=self._ORDERED_PAIRS_CACHE,
        )

        # Store signals reference to prevent premature GC.
        self._worker_signals = worker.signals
        self._active_worker = worker

        def _on_ready(prepared_data, gen=expected_gen):
            self._on_data_ready(prepared_data, gen)

        def _on_error(error_msg, gen=expected_gen):
            self._on_data_error(error_msg, gen)

        worker.signals.finished.connect(_on_ready)
        worker.signals.error.connect(_on_error)
        self._get_worker_pool().start(worker)

    def _on_data_ready(self, prepared_data: dict, expected_gen: int):
        """
        Called on main thread when worker finishes.
        Guards against:
          1) the frame being destroyed
          2) staleness (frame reused after a new worker started)
        """
        if expected_gen != getattr(self, "_worker_generation", None):
            return

        try:
            _ = self.ui.layout
        except RuntimeError:
            return

        self._active_worker = None

        self.value = prepared_data["value"]
        self.name_prefix = prepared_data["name_prefix"]
        self.name = prepared_data["name"]
        self.element_id = prepared_data["element_id"]
        self.prop_class = prepared_data["prop_class"]
        self._ordered_pairs = prepared_data["ordered_pairs"]

        self.ui.element_id_display.setText(str(self.element_id))
        self.ui.property_class.setText(self.name)

        self._finish_init()

    def _on_data_error(self, error_msg: str, expected_gen: int):
        """Fallback when worker fails: build ordered pairs synchronously."""
        if expected_gen != getattr(self, "_worker_generation", None):
            return

        self._active_worker = None

        debug(f"PropertyDataWorker error — falling back to sync init: {error_msg}")
        self._ordered_pairs = None
        self._finish_init()

    def _setup_layout2dgrid_suppression(self):
        # Apply visibility rules for Layout2DGrid element
        if getattr(self, 'prop_class', None) != 'Layout2DGrid':
            return

        # Cached list from _add_properties_by_class — avoids O(n) layout scan.
        def find_widget(value_class_name):
            for w in self._property_widgets:
                if hasattr(w, 'value_class') and w.value_class == value_class_name:
                    return w
            return None

        # Cache relevant widgets
        self._w_arrangement = find_widget('m_GridArrangement') or find_widget('m_GridPlacementMode')
        self._w_count_w = find_widget('m_nCountW')
        self._w_count_l = find_widget('m_nCountL')
        self._w_spacing_w = find_widget('m_flSpacingWidth') or find_widget('m_flSpacingW')
        self._w_spacing_l = find_widget('m_flSpacingLength') or find_widget('m_flSpacingL')
        self._w_alt = find_widget('m_bAlternateShift')
        self._w_shift_w = find_widget('m_flAlternateShiftWidth')
        self._w_shift_l = find_widget('m_flAlternateShiftLength')

        # Connect signals
        if self._w_arrangement and hasattr(self._w_arrangement, 'edited'):
            self._w_arrangement.edited.connect(self._update_layout2dgrid_visibility)
        if self._w_alt and hasattr(self._w_alt, 'edited'):
            self._w_alt.edited.connect(self._update_layout2dgrid_visibility)

        # Initial apply
        self._update_layout2dgrid_visibility()

    def _update_layout2dgrid_visibility(self):
        if getattr(self, 'prop_class', None) != 'Layout2DGrid':
            return

        # Read arrangement mode as string when possible
        mode = None
        if getattr(self, '_w_arrangement', None) is not None:
            val = getattr(self._w_arrangement, 'value', None)
            if isinstance(val, dict):
                v = val.get('m_GridArrangement') or val.get('m_GridPlacementMode')
                if isinstance(v, str):
                    mode = v

        # Read alternate shift as bool when possible
        alt = False
        if getattr(self, '_w_alt', None) is not None:
            val = getattr(self._w_alt, 'value', None)
            if isinstance(val, dict):
                v = val.get('m_bAlternateShift')
                if isinstance(v, bool):
                    alt = v

        # Default: if mode unknown, show everything to avoid hiding usable fields
        show_all = mode not in ('SEGMENT', 'FILL')

        widgets = [
            ('segment', [self._w_count_w, self._w_count_l, self._w_alt]),
            ('shift', [self._w_shift_w, self._w_shift_l]),
            ('fill', [self._w_spacing_w, self._w_spacing_l])
        ]

        # Helper for visibility
        def set_list_visible(lst, visible):
            for w in lst:
                if w is not None:
                    w.setVisible(visible)

        if show_all:
            # Show everything if we cannot evaluate mode
            for _, lst in widgets:
                set_list_visible(lst, True)
            return

        if mode == 'SEGMENT':
            set_list_visible([self._w_count_w, self._w_count_l, self._w_alt], True)
            set_list_visible([self._w_spacing_w, self._w_spacing_l], False)
            # Shift fields depend on alt
            set_list_visible([self._w_shift_w, self._w_shift_l], bool(alt))
        elif mode == 'FILL':
            set_list_visible([self._w_spacing_w, self._w_spacing_l], True)
            set_list_visible([self._w_count_w, self._w_count_l, self._w_alt, self._w_shift_w, self._w_shift_l], False)

    def init_ui(self):
        if self.element:
            pass
        else:
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            if not self._context_menu_signal_connected:
                self.customContextMenuRequested.connect(self.show_context_menu)
                self._context_menu_signal_connected = True

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_position = event.pos()
            self.selected_signal.emit()
            prefix = getattr(self, 'name_prefix', None)
            name = getattr(self, 'prop_class', None)
            if prefix and name:
                self.clicked.emit(f"{prefix}_{name}")

    mouseMoveEvent = PropertyMethods.mouseMoveEvent
    dragEnterEvent = PropertyMethods.dragEnterEvent
    dragMoveEvent = PropertyMethods.dragMoveEvent
    dragLeaveEvent = PropertyMethods.dragLeaveEvent

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
        group_type = getattr(self, '_group_type', '') or ''
        clipboard.setText(f"hammer5tools:smartprop_editor_property;;{self.name};;{self.value};;{group_type}")

    def set_group_type(self, group_type):
        self._group_type = group_type
        color_map = {
            'modifier': '#8B5E3C',
            'selection_criteria': '#2E6B9E',
        }
        color = color_map.get(group_type)
        if color and hasattr(self.ui, 'label'):
            self.ui.label.setStyleSheet(
                f"image: url(:/icons/more_vert.png);\n"
                f"padding-left: 3px;\n"
                f"padding-right: 3px;\n"
                f"border: 2px solid #CCCCCC;\n"
                f"border-top: 0px;\n"
                f"border-right: 0px;\n"
                f"border-bottom: 0px;\n"
                f"border-left: 3px solid {color};\n"
                f"border-radius: 0px;\n"
                f"background-color: #242424;"
            )

    def set_selected(self, selected):
        self._is_selected = selected
        self.ui.frame.setProperty('selected', 'true' if selected else 'false')
        self.ui.frame.style().unpolish(self.ui.frame)
        self.ui.frame.style().polish(self.ui.frame)
        if selected:
            self.ui.frame.setStyleSheet(
                'QFrame#frame { background-color: #2A2E38; }'
            )
        else:
            self.ui.frame.setStyleSheet('')

    def keyPressEvent(self, event):
        from PySide6.QtGui import QKeySequence
        if event.matches(QKeySequence.Copy) and self._is_selected:
            self.copy_action()
            return
        super().keyPressEvent(event)

    def delete_action(self):
        self.value = None
        self.edited.emit()
        self.cancel_worker()
        # Invalidate any in-flight worker results (race safety).
        self._worker_generation = getattr(self, "_worker_generation", 0) + 1
        self._ordered_pairs = None

        # Deferred import to avoid circular import at module load time.
        try:
            from src.editors.smartprop_editor.property_widget_pool import PropertyWidgetPool
            PropertyWidgetPool.instance().release(self.prop_class, self)
        except Exception:
            self.deleteLater()


PropertyFrame._build_ordered_pairs_cache()
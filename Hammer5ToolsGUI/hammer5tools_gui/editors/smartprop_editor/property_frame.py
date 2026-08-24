from hammer5tools_gui.settings.main import debug
from hammer5tools_gui.editors.smartprop_editor.ui_property_frame import Ui_Form

from PySide6.QtWidgets import QWidget, QMenu, QApplication
from PySide6.QtCore import Signal, Qt, QEvent, QTimer, QThreadPool, QSize
from PySide6.QtGui import QAction
from hammer5tools_gui.editors.smartprop_editor.property import compact

from hammer5tools_gui.widgets.popup_menu.main import PopupMenu
from hammer5tools_gui.widgets.element_id import ElementIDGenerator

from hammer5tools_gui.editors.smartprop_editor.property.legacy import PropertyLegacy
from hammer5tools_gui.editors.smartprop_editor.property.vector3d import PropertyVector3D
from hammer5tools_gui.editors.smartprop_editor.property.float import PropertyFloat
from hammer5tools_gui.editors.smartprop_editor.property.bool import PropertyBool
from hammer5tools_gui.editors.smartprop_editor.property.combobox import PropertyCombobox
from hammer5tools_gui.editors.smartprop_editor.property.string import PropertyString
from hammer5tools_gui.editors.smartprop_editor.property.color import PropertyColor
from hammer5tools_gui.editors.smartprop_editor.property.comparison import PropertyComparison
from hammer5tools_gui.editors.smartprop_editor.property.filtersurface import PropertySurface
from hammer5tools_gui.editors.smartprop_editor.property.colormatch import PropertyColorMatch
from hammer5tools_gui.editors.smartprop_editor.property.material_replacements import PropertyMaterialReplacements
from hammer5tools_gui.editors.smartprop_editor.property.material_group_choices import PropertyMaterialGroupChoices
from hammer5tools_gui.editors.smartprop_editor.property.variable import PropertyVariableOutput
from hammer5tools_gui.editors.smartprop_editor.objects import surfaces_list
from hammer5tools_gui.editors.smartprop_editor.property.set_variable import PropertyVariableValue
from hammer5tools_gui.editors.smartprop_editor.property.reference import PropertyReference
from hammer5tools_gui.editors.smartprop_editor.property.warning import PropertyWarning
from hammer5tools_gui.editors.smartprop_editor.property.path_editor import PropertyPathEditor
from PySide6.QtGui import QCursor
from hammer5tools_gui.widgets import HierarchyItemModel
import uuid

import ast

from hammer5tools_gui.widgets import exception_handler
from hammer5tools_gui.styles.common import mark_paint_through
from hammer5tools_gui.editors.smartprop_editor.property_data_worker import (
    PropertyDataWorker,
)

class PropertyFrame(QWidget):
    edited = Signal()
    slider_pressed = Signal()
    committed = Signal()
    selected_signal = Signal()
    clicked = Signal(str)
    # A single property row was selected: (value_class, label). Empty strings
    # mean the selection was cleared.
    property_selected = Signal(str, str)

    # A lookup dictionary to avoid multiple if/elif checks; cached at class level
    _prop_classes_map_cache = {
        'ModifyState': ['m_nReferenceID', 'm_bEnabled'],
        'Group': ['m_nReferenceID', 'm_bEnabled'],
        'SmartProp': ['m_nReferenceID', 'm_bEnabled', 'm_sSmartProp', 'm_bLocalEvaluationState'],
        'PlaceInSphere': ['m_nReferenceID', 'm_bEnabled', 'm_flRandomness', 'm_nCountMin', 'm_nCountMax', 'm_flPositionRadiusInner', 'm_flPositionRadiusOuter', 'm_bAlignOrientation', 'm_PlacementMode', 'm_DistributionMode', 'm_vAlignDirection', 'm_vPlaneUpDirection'],
        'PlaceMultiple': ['m_nReferenceID', 'm_bEnabled', 'm_nCount', 'm_Expression'],
        'PlaceOnPath': ['m_nReferenceID', 'm_bEnabled', 'm_PathName', 'm_vPathOffset', 'm_flOffsetAlongPath', 'm_PathSpace', 'm_flSpacing', 'm_bUseFixedUpDirection', 'm_bUseProjectedDistance', 'm_vUpDirection', 'm_UpDirectionSpace', 'm_DefaultPathInWorldSpace', 'm_DefaultPath'],
        'FitOnLine': ['m_nReferenceID', 'm_bEnabled', 'm_vStart', 'm_vEnd', 'm_PointSpace', 'm_bOrientAlongLine', 'm_vUpDirection', 'm_UpDirectionSpace', 'm_bPrioritizeUp', 'm_nScaleMode', 'm_nPickMode'],
        'PickOne': ['m_nReferenceID', 'm_bEnabled', 'm_SelectionMode', 'm_SpecificChildIndex', 'm_OutputChoiceVariableName', 'm_bConfigurable', 'm_vHandleOffset', 'm_HandleColor', 'm_HandleSize', 'm_HandleShape'],
        'Model': ['m_nReferenceID', 'm_bEnabled', 'm_sModelName', 'm_vModelScale', 'm_MaterialGroupName', 'm_bDetailObject', 'm_bRigidDeformation', 'm_bDisableDynamicDeformable', 'm_nLodLevel', 'm_nDetailObjectFadeLevel', 'm_bCastShadows', 'm_flUniformModelScale', 'm_SurfacePropertyOverride'],
        'ModelEntity': ['m_nReferenceID', 'm_bEnabled', 'm_sModelName', 'm_MaterialGroupName', 'm_bCastShadows', 'm_bForceStatic', 'm_nDeformableAttachmentMode', 'm_nDeformableOrientationMode'],
        'BendDeformer': ['m_nReferenceID', 'm_bEnabled', 'm_bDeformationEnabled', 'm_vOrigin', 'm_vAngles', 'm_vSize', 'm_flBendAngle', 'm_flBendPoint', 'm_flBendRadius'],
        'PropPhysics': ['m_nReferenceID', 'm_bEnabled', 'm_sModelName', 'm_MaterialGroupName', 'm_bCastShadows', 'm_bForceStatic', 'm_nDeformableAttachmentMode', 'm_nDeformableOrientationMode', 'm_bStartAsleep'],
        'PropDynamic': ['m_nReferenceID', 'm_bEnabled', 'm_sModelName', 'm_MaterialGroupName', 'm_bCastShadows', 'm_bForceStatic', 'm_nDeformableAttachmentMode', 'm_nDeformableOrientationMode'],
        'MidpointDeformer': ['m_nReferenceID', 'm_bEnabled', 'm_bDeformationEnabled', 'm_vStart', 'm_vEnd', 'm_fRadius', 'm_bContinuousSpline', 'm_vOffset', 'm_vAngles', 'm_vScale', 'm_fFalloff', 'm_OutputVariable'],
        'PlaceOnMesh': ['m_nReferenceID', 'm_bEnabled', 'm_nPickMode', 'm_MeshName'],
        'Layout2DGrid': ['m_nReferenceID', 'm_bEnabled', 'm_flWidth', 'm_flLength', 'm_bVerticalLength', 'm_GridArrangement', 'm_GridOriginMode', 'm_nCountW', 'm_nCountL', 'm_flSpacingWidth', 'm_flSpacingLength', 'm_bAlternateShift', 'm_flAlternateShiftWidth', 'm_flAlternateShiftLength'],
        'Grid': ['m_nReferenceID', 'm_bEnabled', 'm_flWidth', 'm_flLength', 'm_bVerticalLength', 'm_GridArrangement', 'm_GridOriginMode', 'm_nCountW', 'm_nCountL', 'm_flSpacingWidth', 'm_flSpacingLength', 'm_bAlternateShift', 'm_flAlternateShiftWidth', 'm_flAlternateShiftLength'],
        'Rotate': ['m_bEnabled', 'm_vRotation'],
        'Scale': ['m_bEnabled', 'm_flScale'],
        'Translate': ['m_bEnabled', 'm_vPosition', 'm_CoordinateSpace'],
        'SetTintColor': ['m_bEnabled', 'm_SelectionMode', 'm_ColorSelection', 'm_Mode', 'm_ColorChoices'],
        'MaterialOverride': ['m_bEnabled', 'm_bClearCurrentOverrides', 'm_MaterialReplacements'],
        'MaterialTint': ['m_bEnabled', 'm_Material', 'm_SelectionMode', 'm_Color', 'm_ColorPosition'],
        'RandomOffset': ['m_bEnabled', 'm_vRandomPositionMin', 'm_vRandomPositionMax', 'm_vSnapIncrement'],
        'RandomScale': ['m_bEnabled', 'm_flRandomScaleMin', 'm_flRandomScaleMax', 'm_flSnapIncrement'],
        'RigidDeformation': ['m_bEnabled'],
        'CreateSizer': ['m_bEnabled', 'm_Name', 'm_bDisplayModel',
                        'm_flInitialMinX', 'm_flInitialMaxX', 'm_flConstraintMinX', 'm_flConstraintMaxX', 'm_OutputVariableMinX', 'm_OutputVariableMaxX',
                        'm_flInitialMinY', 'm_flInitialMaxY', 'm_flConstraintMinY', 'm_flConstraintMaxY', 'm_OutputVariableMinY', 'm_OutputVariableMaxY',
                        'm_flInitialMinZ', 'm_flInitialMaxZ', 'm_flConstraintMinZ', 'm_flConstraintMaxZ', 'm_OutputVariableMinZ', 'm_OutputVariableMaxZ'],
        'CreateRotator': ['m_bEnabled', 'm_Name', 'm_vOffset', 'm_vRotationAxis', 'm_CoordinateSpace', 'm_flDisplayRadius', 'm_DisplayColor', 'm_bApplyToCurrentTransform', 'm_flSnappingIncrement', 'm_flInitialAngle', 'm_bEnforceLimits', 'm_flMinAngle', 'm_flMaxAngle', 'm_OutputVariable'],
        'CreateLocator': ['m_bEnabled', 'm_LocatorName', 'm_vOffset', 'm_flDisplayScale', 'm_bConfigurable', 'm_bAllowTranslation', 'm_bAllowRotation', 'm_bAllowScale'],
        'RestoreState': ['m_bEnabled', 'm_StateName', 'm_bDiscardIfUknown'],
        'TraceInDirection': ['m_bEnabled', 'm_Origin', 'm_OriginSpace', 'm_vTraceDirection', 'm_DirectionSpace', 'm_flSurfaceUpInfluence', 'm_nNoHitResult', 'm_flOriginOffset', 'm_flTraceLength', 'm_bIgnoreToolMaterials', 'm_bIgnoreSky', 'm_bIgnoreNoDraw', 'm_bIgnoreTranslucent', 'm_bIgnoreModels', 'm_bIgnoreEntities', 'm_bIgnoreCables'],
        'SaveState': ['m_bEnabled', 'm_StateName'],
        'SetVariable': ['m_bEnabled', 'm_VariableValue'],
        'SetVariableBool': ['m_bEnabled', 'm_VariableName', 'm_VariableValue'],
        'SetVariableFloat': ['m_bEnabled', 'm_VariableName', 'm_VariableValue'],
        'SetVariableInt': ['m_bEnabled', 'm_VariableName', 'm_VariableValue'],
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
        'Expression': ['m_bEnabled', 'm_Expression'],
        'Probability': ['m_bEnabled', 'm_flProbability'],
        'SurfaceAngle': ['m_bEnabled', 'm_flSurfaceSlopeMin', 'm_flSurfaceSlopeMax'],
        'SurfaceProperties': ['m_bEnabled', 'm_AllowedSurfaceProperties', 'm_DisallowedSurfaceProperties'],
        'VariableValue': ['m_bEnabled', 'm_VariableComparison'],
        'EndCap': ['m_bEnabled', 'm_bStart', 'm_bEnd'],
        'ChoiceWeight': ['m_bEnabled', 'm_flWeight'],
        'IsValid': ['m_bEnabled', 'm_Expression'],
        'LinearLength': ['m_bEnabled', 'm_flLength', 'm_bAllowScale', 'm_flMinLength', 'm_flMaxLength'],
        'PathPosition': ['m_bEnabled', 'm_PlaceAtPositions', 'm_nPlaceEveryNthPosition', 'm_nNthPositionIndexOffset', 'm_bAllowAtStart', 'm_bAllowAtEnd'],
        'EdgeAngleCriteria': ['m_bEnabled', 'm_flMinAngle', 'm_flMaxAngle', 'm_bInvert'],
        'TopoEdgeCountCriteria': ['m_bEnabled', 'm_nTargetOpenEdgeCount', 'm_bInvert', 'm_bSharedVert'],
        'VertexCountCriteria': ['m_bEnabled', 'm_nTargetVertexCount'],
        'MaterialCriteria': ['m_bEnabled', 'm_material', 'm_bInvert'],
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
        """Build once at import — forward schema order (m_bEnabled first).

        Forward order lets _add_properties_by_class append widgets in O(1) each
        instead of the old insertWidget(0, ...) which was O(n) per widget
        (O(n²) to build a whole frame). The cache mirrors the visual top-to-bottom
        order directly; the reversed-list + insert-at-0 dance it replaced existed
        only to produce this same order.
        """
        cls._ORDERED_PAIRS_CACHE.clear()
        for prop_class, keys in cls._prop_classes_map_cache.items():
            cls._ORDERED_PAIRS_CACHE[prop_class] = [
                (k, None) for k in keys
            ]

    @classmethod
    def _get_worker_pool(cls) -> QThreadPool:
        if cls._PROPERTY_WORKER_POOL is None:
            pool = QThreadPool()
            pool.setMaxThreadCount(4)
            pool.setExpiryTimeout(10_000)
            cls._PROPERTY_WORKER_POOL = pool
        return cls._PROPERTY_WORKER_POOL

    _SKIP_PROPS = frozenset({'_class', 'm_sLabel', 'm_nElementID', 'm_sReferenceObjectID', '_WARN_NOT_VERIFIED', 'm_sNote', 'm_Comment', 'm_sComment', 'note', '_comment'})

    # Rows built per event-loop tick. Small enough that a tick stays well under
    # a frame, large enough that a typical element finishes in a handful of them.
    _BUILD_CHUNK = 4

    # Clipboard tag for a single copied property value.
    _FIELD_CLIP_TAG = "hammer5tools:smartprop_editor_field"

    # Class-level copy for batch/prewarm workers (same keys as instance only_variable_properties).
    _ONLY_VARIABLE_PROPERTIES = ()

    # Combobox fields: (substring in value_class, items, filter_types) ΓÇö order matters.
    _COMBOBOX_SUBSTRING_RULES = (
        ('m_SurfacePropertyOverride', [list(d.keys())[0] for d in surfaces_list], ['SurfaceProperty']),
        ('m_nPickMode', ['LARGEST_FIRST', 'RANDOM', 'ALL_IN_ORDER'], ['PickMode']),
        ('m_nScaleMode', ['NONE', 'SCALE_END_TO_FIT', 'SCALE_EQUALLY', 'SCALE_MAXIMIZE'], ['ScaleMode']),
        ('m_CoordinateSpace', ['ELEMENT', 'OBJECT', 'WORLD'], ['CoordinateSpace']),
        ('m_DirectionSpace', ['ELEMENT', 'OBJECT', 'WORLD'], ['DirectionSpace']),
        ('m_GridPlacementMode', ['SEGMENT', 'FILL'], ['GridPlacementMode']),
        ('m_GridArrangement', ['SEGMENT', 'FILL'], ['GridPlacementMode']),
        ('m_GridOriginMode', ['CENTER', 'CORNER'], ['GridOriginMode']),
        ('m_nNoHitResult', ['NOTHING', 'DISCARD', 'MOVE_TO_START', 'MOVE_TO_END'], ['TraceNoHit']),
        ('m_SelectionMode', ['RANDOM', 'FIRST', 'SPECIFIC'], ['ChoiceSelectionMode']),
        ('m_PlacementMode', ['SPHERE', 'CIRCLE'], ['RadiusPlacementMode']),
        ('m_DistributionMode', ['RANDOM', 'REGULAR'], ['DistributionMode']),
        ('m_DirectionVector', ['FORWARD', 'LEFT', 'UP'], ['Direction']),
        ('m_SpacingSpace', ['ELEMENT', 'OBJECT', 'WORLD'], ['CoordinateSpace']),
        ('m_sPhysicsType', ['normal', 'multiplayer'], ['String']),
        ('m_nDetailObjectFadeLevel', ['NONE', 'MOST_AGGRESSIVE', 'MORE_AGGRESSIVE', 'NORMAL', 'LESS_AGGRESSIVE', 'LEAST_AGGRESSIVE'], ['String']),
        ('m_RotationAxes', ['X', 'Y', 'Z', 'XY', 'XZ', 'YZ', 'XYZ'], ['Axes']),
        ('m_HandleShape', ['NONE', 'SQUARE', 'CIRCLE', 'DIAMOND'], ['HandleShape']),
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

    # Per-(prop_class, field) combobox overrides — checked before the memoized
    # field-name-only _COMBOBOX_SUBSTRING_RULES lookup below, since that memo can't
    # distinguish two classes reusing the same field name for different enums.
    # PlaceOnMesh's m_nPickMode (FIRST_OPEN_EDGE/FIRST_CLOSED_EDGE/UVMAP1/UVMAP2) vs
    # FitOnLine's m_nPickMode (LARGEST_FIRST/RANDOM/ALL_IN_ORDER) is the current case.
    _CLASS_FIELD_COMBOBOX_OVERRIDES = {
        ('PlaceOnMesh', 'm_nPickMode'): (['FIRST_OPEN_EDGE', 'FIRST_CLOSED_EDGE', 'UVMAP1', 'UVMAP2'], ['OrientationMode']),
    }

    # Populated lazily in _resolve_dispatch() ΓÇö ordered prefix fallthrough.
    _PREFIX_DISPATCH: list = []

    # Exact-match dispatch: maps value_class -> (WidgetClass, extra_kwargs_dict)
    _EXACT_PROP_DISPATCH = None  # populated lazily by _resolve_dispatch()
    _DISPATCH_RESOLVED = False

    # Memoized combobox substring lookup: value_class -> (items, filter_types) or None.
    # _COMBOBOX_SUBSTRING_RULES (~30 entries) is otherwise scanned with
    # ``sub in value_class`` for every non-exact field on every frame build; the
    # set of distinct field names is tiny and stable, so caching turns each hit
    # after the first into an O(1) dict lookup.
    _COMBOBOX_MEMO: dict = {}

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
            'm_sModelName':            (PropertyString,  {'expression_bool': False, 'placeholder': 'models/example.vmdl', 'model_browser': True, 'filter_types': ['String', 'Model']}),
            'm_sSmartProp':            (PropertyString,  {'expression_bool': False, 'placeholder': 'smartprops/example.vsmart', 'smartprop_browser': True, 'filter_types': ['String']}),
            'm_MaterialGroupName':     (PropertyString,  {'expression_bool': False, 'placeholder': 'Material group name'}),
            'm_Expression':            (PropertyString,  {'expression_bool': True,  'placeholder': 'Expression example: var_bool ? var_sizer * var_multiply'}),
            'm_StateName':             (PropertyString,  {'expression_bool': False, 'only_string': True, 'placeholder': 'State name'}),
            'm_LocatorName':           (PropertyString,  {'expression_bool': False, 'placeholder': 'Locator name'}),
            'm_MeshName':              (PropertyString,  {'expression_bool': False, 'placeholder': 'Mesh name'}),
            'm_VariableName':          (PropertyVariableOutput,  {'filter_types': ['String', 'Int', 'Float', 'Bool', 'Vector3D', 'Color']}),
            'm_OutputVariableName':    (PropertyVariableOutput,  {'filter_types': ['String', 'Int', 'Float', 'Bool', 'Vector3D']}),
            'm_OutputVariableMaxZ':    (PropertyVariableOutput,  {}),
            'm_OutputVariableMinZ':    (PropertyVariableOutput,  {}),
            'm_OutputVariableMaxY':    (PropertyVariableOutput,  {}),
            'm_OutputVariableMinY':    (PropertyVariableOutput,  {}),
            'm_OutputVariableMaxX':    (PropertyVariableOutput,  {}),
            'm_OutputVariableMinX':    (PropertyVariableOutput,  {}),
            'm_OutputVariable':        (PropertyVariableOutput,  {}),
            'm_PathName':              (PropertyString,  {'expression_bool': False, 'placeholder': 'Path name'}),
            'm_flSpacing':             (PropertyFloat,   {'slider_range': [0, 4096]}),
            'm_flOffsetAlongPath':     (PropertyFloat,   {'slider_range': [0, 4096]}),
            'm_vPathOffset':           (PropertyVector3D, {}),
            'm_vUpDirection':          (PropertyVector3D, {}),
            'm_DefaultPath':           (PropertyPathEditor,           {}),
            'm_DefaultPathInWorldSpace': (PropertyBool,               {}),
            'm_bUseFixedUpDirection':  (PropertyBool,                 {}),
            'm_bUseProjectedDistance': (PropertyBool,                 {}),
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
        # Two stylesheets would otherwise paint over everything paintEvent draws:
        # the .ui's flat "background-color: #2e2e2e" on the form, and the
        # application-wide "QWidget { background-color: #272727; }". Replace the
        # first with an explicit transparent rule, which also beats the second
        # (a widget's own sheet wins over the application sheet). paintEvent
        # then supplies the base colour, the zebra stripes and the highlight.
        self.setStyleSheet("")
        # frame_layout sits between this frame and the rows, and an opaque child
        # covers whatever paintEvent draws. Marking it beats editing its
        # stylesheet: the .ui keeps owning its border-top and margins, and a
        # dynamic property costs nothing next to restyling a whole subtree.
        mark_paint_through(self.ui.frame_layout)
        # Mirrors insertWidget(0, ...) order ΓÇö avoids O(n) layout scan in on_edited.
        self._property_widgets: list = []
        self._is_selected = False
        self._group_type = None
        # Drag-and-drop reordering of property rows is disabled in the property
        # list: field order is schema-driven (forward order in _add_properties_by_class),
        # and per-row drag handlers intercepted mouse events / did layout work on
        # every move for no benefit here. Reordering is owned by Section 1
        # (ComponentTree), not by these value rows.
        self.setAcceptDrops(False)
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
            # CS2 tool icons for the per-element action strip.
            self.ui.copy_button.setIcon(compact.cs2_icon('copy'))
            self.ui.copy_button.setIconSize(QSize(16, 16))
            self.ui.delete_button.setIcon(compact.cs2_icon('delete'))
            self.ui.delete_button.setIconSize(QSize(16, 16))

        self.only_variable_properties = list(self._ONLY_VARIABLE_PROPERTIES)

        # Chunked build state (see _finish_init).
        self._build_offset = 0
        self._build_generation = 0
        # Currently selected property row, for help / copy / paste.
        self._selected_row = None
        # One deferred restripe in flight at a time (see paintEvent).
        self._zebra_pending = False

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
        """Build the first chunk of rows, then hand the rest to the event loop.

        Rows cost 18-67 ms each to construct, so a 15-field element takes most
        of a second to build in one go and the panel stays blank for all of it.
        Building _BUILD_CHUNK rows per event-loop tick lets the first rows paint
        almost immediately and the rest stream in; total work is unchanged, but
        the panel stops looking frozen.

        on_edited() is NOT called here — the value dict stays incomplete until
        _finalize_build() runs after the last chunk.
        """
        try:
            self.parent()
        except RuntimeError:
            return  # underlying C/C++ object has been deleted

        self._build_offset = 0
        self._build_generation += 1
        # `or 0` — exception_handler swallows errors and returns None.
        self._build_offset += self._add_properties_by_class(limit=self._BUILD_CHUNK) or 0
        self.show_child()

        # Connect once per PropertyFrame lifetime (pool reuse / repeated _finish_init).
        if not self._show_child_signal_connected:
            self.ui.show_child.clicked.connect(self.show_child)
            self._show_child_signal_connected = True

        self.init_ui()

        self._schedule_next_chunk()

    def _schedule_next_chunk(self):
        generation = self._build_generation
        QTimer.singleShot(0, lambda g=generation: self._build_next_chunk(g))

    def _build_next_chunk(self, generation: int):
        """Build one more chunk of rows; finalize once none are left."""
        if generation != self._build_generation:
            return  # frame was reconfigured out from under this build
        try:
            self.parent()
        except RuntimeError:
            return  # underlying C/C++ object has been deleted

        added = self._add_properties_by_class(
            offset=self._build_offset, limit=self._BUILD_CHUNK
        ) or 0
        self._build_offset += added
        if added == self._BUILD_CHUNK:
            self._schedule_next_chunk()
        else:
            self._finalize_build()

    def _finalize_build(self):
        """Run once every row exists: warning row, field suppression, first commit.

        _setup_layout2dgrid_suppression requires ALL widgets to be present, and
        on_edited() is called here for the first time — the value dict is only
        complete now.
        """
        # Add unverified warning at the VERY END of the build; prepend=True
        # forces it to the absolute top of the layout regardless of build order.
        if "_WARN_NOT_VERIFIED" in self.value:
            self._add_widget_for_property('_WARN_NOT_VERIFIED', self.value.get("_WARN_NOT_VERIFIED"), force=True, prepend=True)

        self._setup_layout2dgrid_suppression()
        self.on_edited()

    def paintEvent(self, event):
        """Keep the row stripes in step with whatever is currently visible.

        Rows appear and disappear from a lot of places — chunked building, the
        2D-grid field suppression, and every logic_switch that swaps a row
        between value/variable/expression mode — so rather than hunting down
        each of those call sites, the parity is checked against what is on
        screen right here and corrected when it has drifted. zebra_plan() is a
        walk over ~20 frames returning nothing in the steady state, so the check
        is not worth avoiding; the repolish is deferred out of the paint because
        restyling a widget mid-paint is not allowed.
        """
        super().paintEvent(event)
        if not self._zebra_pending and compact.zebra_plan(
            self.ui.layout, self._selected_row
        ):
            self._zebra_pending = True
            QTimer.singleShot(0, self._apply_zebra)

    def _apply_zebra(self):
        self._zebra_pending = False
        compact.assign_zebra(self.ui.layout, selected=self._selected_row)

    # ── Per-property selection ──────────────────────────────────────────────

    def eventFilter(self, obj, event):
        """Select the property row the user pressed on.

        Only clicks landing on the row's own inert area reach here; clicks that
        land on a child control are handled by the focus route in
        LegacyPropertyList, which covers keyboard navigation too.
        """
        if event.type() == QEvent.MouseButtonPress and obj in self._property_widgets:
            self.select_row(obj)
        return super().eventFilter(obj, event)

    def select_row(self, widget) -> None:
        """Mark ``widget`` as the selected property row and announce it."""
        if widget is not None and widget not in self._property_widgets:
            return
        if widget is self._selected_row:
            return
        self._selected_row = widget
        self._apply_zebra()
        value_class = getattr(widget, 'value_class', '') or ''
        self.property_selected.emit(value_class, self._row_label(widget))

    def row_for_widget(self, widget):
        """Walk up from ``widget`` to the property row containing it, if any."""
        while widget is not None:
            if widget in self._property_widgets:
                return widget
            if widget is self:
                return None
            widget = widget.parentWidget()
        return None

    @staticmethod
    def _row_label(widget) -> str:
        """The row's on-screen label, for the help panel title."""
        ui = getattr(widget, 'ui', None)
        field = getattr(ui, 'property_class', None) if ui is not None else None
        if field is not None:
            try:
                return field.text()
            except RuntimeError:
                pass
        return getattr(widget, 'value_class', '') or ''

    # ── Per-property copy / paste ───────────────────────────────────────────

    def copy_property(self) -> bool:
        """Put the selected row's value on the clipboard. False if nothing to copy."""
        row = self._selected_row
        if row is None:
            return False
        value_class = getattr(row, 'value_class', None)
        if not value_class:
            return False
        # Row values are {value_class: payload}; None means "Default" mode.
        payload = getattr(row, 'value', None)
        if isinstance(payload, dict):
            payload = payload.get(value_class)
        QApplication.clipboard().setText(
            f"{self._FIELD_CLIP_TAG};;{value_class};;{payload!r}"
        )
        return True

    @classmethod
    def _clipboard_has_property(cls) -> bool:
        return QApplication.clipboard().text().startswith(cls._FIELD_CLIP_TAG + ";;")

    def paste_property(self) -> bool:
        """Apply a copied value to the selected row. False if it can't be applied.

        The value is applied to whichever row is selected, not to the field it
        was copied from — copying a spacing onto a length is the useful case.
        Commits through on_edited(), so the change lands on the undo stack like
        any other edit.
        """
        row = self._selected_row
        if row is None:
            return False
        value_class = getattr(row, 'value_class', None)
        if not value_class:
            return False

        parts = QApplication.clipboard().text().split(";;")
        if len(parts) < 3 or parts[0] != self._FIELD_CLIP_TAG:
            return False
        try:
            payload = ast.literal_eval(parts[2])
        except (ValueError, SyntaxError):
            return False

        if not self.update_property_value(value_class, payload):
            return False
        self.on_edited()
        return True

    @exception_handler
    def _add_widget_for_property(self, value_class, val, force=False, prepend=False):
        """Internal helper to create and initialize a property widget instance.

        By default the widget is appended to the layout and to
        ``_property_widgets`` (O(1)) so a whole frame builds in O(n). Pass
        ``prepend=True`` to force the widget to the top instead — used only by
        the unverified-warning row, which must sit above everything else.
        """
        def add_instance():
            # PropertyWarning is a static label ΓÇö do NOT connect its edited
            # signal to on_edited, otherwise it triggers spurious undo actions.
            if not isinstance(property_instance, PropertyWarning):
                property_instance.edited.connect(self.on_edited)
            property_instance.setAcceptDrops(False)
            if prepend:
                self.ui.layout.insertWidget(0, property_instance)
                self._property_widgets.insert(0, property_instance)
            else:
                self.ui.layout.addWidget(property_instance)
                self._property_widgets.append(property_instance)
            # Pooled widgets return from acquire() hidden (never shown in
            # acquire to avoid top-level flash); show after reparenting.
            property_instance.show()

            # Descriptions are shown in the help panel (Section 3) on selection
            # rather than as a hover tooltip — see _select_row.
            property_instance.installEventFilter(self)

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
            # Handle the universal SetVariable operation (outputs a complex object)
            if (isinstance(val, dict) and ('m_TargetName' in val or 'm_DataType' in val)) or (val is None and self.prop_class == 'SetVariable'):
                property_instance = PropertyVariableValue(
                    value=val,
                    value_class=value_class,
                    variables_scrollArea=self.variables_scrollArea,
                    element_id_generator=self.element_id_generator,
                )
            else:
                # Type-specific SetVariableBool/Float/Int operation (outputs a simple value or expression)
                if isinstance(val, bool) or self.prop_class.endswith('Bool'):
                    property_instance = PropertyBool(
                        value=val,
                        value_class=value_class,
                        variables_scrollArea=self.variables_scrollArea,
                        element_id_generator=self.element_id_generator,
                    )
                elif isinstance(val, (int, float)) or self.prop_class.endswith('Float') or self.prop_class.endswith('Int'):
                    property_instance = PropertyFloat(
                        value=val,
                        value_class=value_class,
                        variables_scrollArea=self.variables_scrollArea,
                        element_id_generator=self.element_id_generator,
                        int_bool=self.prop_class.endswith('Int')
                    )
                else:
                    # Fallback to string/expression
                    property_instance = PropertyString.acquire(
                        value=val,
                        value_class=value_class,
                        variables_scrollArea=self.variables_scrollArea,
                        expression_bool=True,
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

        # Per-class combobox override (same field name, different enum per class) —
        # checked ahead of the field-name-only memo below, which can't tell classes apart.
        override = PropertyFrame._CLASS_FIELD_COMBOBOX_OVERRIDES.get((self.prop_class, value_class))
        if override is not None:
            items, fts = override
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

        # Combobox substring dispatch — memoized per distinct field name so the
        # ~30-entry rule list is scanned at most once per field name, ever.
        combo = PropertyFrame._COMBOBOX_MEMO.get(value_class, False)
        if combo is False:
            combo = None
            for sub, items, fts in PropertyFrame._COMBOBOX_SUBSTRING_RULES:
                if sub in value_class:
                    combo = (items, fts)
                    break
            PropertyFrame._COMBOBOX_MEMO[value_class] = combo
        if combo is not None:
            items, fts = combo
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
        """Add up to ``limit`` rows starting at ``offset``. Returns how many
        entries were consumed, so the chunked builder knows when it is done."""
        try:
            parent_widget = self.ui.layout.parentWidget()
            if parent_widget is not None:
                parent_widget.setUpdatesEnabled(False)
        except RuntimeError:
            # Widget or layout was destroyed before this scheduled update ran
            return 0

        try:
            # Prefer worker-prepared ordered pairs (Plan 5).
            if getattr(self, '_ordered_pairs', None) is not None:
                ordered_pairs = self._ordered_pairs
            elif self.prop_class in self._prop_classes_map_cache:
                classes = self._prop_classes_map_cache[self.prop_class]
                ordered_pairs = [
                    (item, self.value.get(item, None))
                    for item in classes
                ]
            else:
                ordered_pairs = list(self.value.items())

            end = (offset + limit) if limit is not None else None
            sliced = ordered_pairs[offset:end]
            for value_class, val_data in sliced:
                self._add_widget_for_property(value_class, val_data)
            return len(sliced)
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
                if hasattr(w, 'set_value'):
                    w.set_value(new_value)
                    return True
                elif hasattr(w, 'reconfigure'):
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
        the layout ΓÇö prevents a double-widget race if the frame is reused
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
        self._selected_row = None

    def dispose(self):
        """Tear this frame down, returning its rows to the per-class pools.

        The only supported way for an owner to drop a PropertyFrame. Going
        straight to deleteLater() destroys the child rows along with the frame,
        so PooledPropertyMixin's pools never refill and every subsequent build
        pays cold construction (18-67 ms per row, against 0.4 ms for a pooled
        reconfigure).
        """
        self.cancel_worker()
        # Invalidate any in-flight worker results (race safety).
        self._worker_generation = getattr(self, "_worker_generation", 0) + 1
        self._ordered_pairs = None
        self._clear_widgets()
        self.hide()
        self.setParent(None)
        self.deleteLater()

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
            # No raw payload available ΓÇö fall back to synchronous init.
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

        debug(f"PropertyDataWorker error ΓÇö falling back to sync init: {error_msg}")
        self._ordered_pairs = None
        self._finish_init()

    def _setup_layout2dgrid_suppression(self):
        # Apply visibility rules for Layout2DGrid element
        if getattr(self, 'prop_class', None) != 'Layout2DGrid':
            return

        # Cached list from _add_properties_by_class ΓÇö avoids O(n) layout scan.
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
        # The context menu carries the per-property Copy/Paste entries, so it is
        # wired up in element mode too (where the component-level entries, owned
        # by Section 1, are left out).
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        if not self._context_menu_signal_connected:
            self.customContextMenuRequested.connect(self.show_context_menu)
            self._context_menu_signal_connected = True

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Drag-start bookkeeping removed: property rows are no longer draggable.
            self.selected_signal.emit()
            prefix = getattr(self, 'name_prefix', None)
            name = getattr(self, 'prop_class', None)
            if prefix and name:
                self.clicked.emit(f"{prefix}_{name}")

    # ── Drag-and-drop disabled for property-list rows ───────────────────────
    # Property rows are not reorderable here (order is schema-driven, and the
    # old dropEvent reordered the layout + emitted spurious edits). The shared
    # PropertyMethods drag handlers are NOT assigned, and setAcceptDrops(False)
    # is set in __init__, so these no-op overrides reject any inbound drag and
    # never start one. PropertyMethods itself is left intact for the other
    # editors that depend on it (assetgroup_maker, variable_frame, etc.).
    # NOTE: mousePressEvent above is kept (it drives selection/click signaling);
    # only its drag-start bookkeeping line was removed.
    def mouseMoveEvent(self, event):
        # Dragging of this frame is disabled — just defer to the default handler.
        super().mouseMoveEvent(event)

    def dragEnterEvent(self, event):
        event.ignore()

    def dragMoveEvent(self, event):
        event.ignore()

    def dragLeaveEvent(self, event):
        event.ignore()

    def dropEvent(self, event):
        event.ignore()

    def show_context_menu(self):
        context_menu = QMenu()

        # ── Selected property row ───────────────────────────────────────────
        copy_property_action = paste_property_action = None
        row = self._selected_row
        if row is not None:
            label = self._row_label(row)
            copy_property_action = QAction(f"Copy '{label}'", context_menu)
            paste_property_action = QAction(f"Paste into '{label}'", context_menu)
            paste_property_action.setEnabled(self._clipboard_has_property())
            context_menu.addActions([copy_property_action, paste_property_action])

        # ── Whole component ─────────────────────────────────────────────────
        # In element mode Section 1 owns delete/copy of the component itself.
        delete_action = copy_action = None
        if not self.element:
            if not context_menu.isEmpty():
                context_menu.addSeparator()
            delete_action = QAction("Delete", context_menu)
            copy_action = QAction("Copy", context_menu)
            context_menu.addActions([delete_action, copy_action])

        if context_menu.isEmpty():
            return
        action = context_menu.exec(QCursor.pos())
        if action is None:
            return
        if action == copy_property_action:
            self.copy_property()
        elif action == paste_property_action:
            self.paste_property()
        elif delete_action is not None and action == delete_action:
            self.delete_action()
        elif copy_action is not None and action == copy_action:
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
                f"border: 2px solid #d0d0d0;\n"
                f"border-top: 0px;\n"
                f"border-right: 0px;\n"
                f"border-bottom: 0px;\n"
                f"border-left: 3px solid {color};\n"
                f"border-radius: 0px;\n"
                f"background-color: #363636;"
            )

    def set_selected(self, selected):
        self._is_selected = selected
        self.ui.frame.setProperty('selected', 'true' if selected else 'false')
        self.ui.frame.style().unpolish(self.ui.frame)
        self.ui.frame.style().polish(self.ui.frame)
        if selected:
            self.ui.frame.setStyleSheet(
                'QFrame#frame { background-color: #3b3f48; }'
            )
        else:
            self.ui.frame.setStyleSheet('')

    def keyPressEvent(self, event):
        from PySide6.QtGui import QKeySequence
        # A selected property row takes precedence: Ctrl+C/Ctrl+V then act on
        # that one field rather than on the whole component.
        if self._selected_row is not None:
            if event.matches(QKeySequence.Copy) and self.copy_property():
                return
            if event.matches(QKeySequence.Paste) and self.paste_property():
                return
        if event.matches(QKeySequence.Copy) and self._is_selected:
            self.copy_action()
            return
        super().keyPressEvent(event)

    def delete_action(self):
        self.value = None
        self.edited.emit()
        self.dispose()


PropertyFrame._build_ordered_pairs_cache()

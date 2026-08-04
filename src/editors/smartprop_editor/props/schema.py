"""
Schema — declarative property dispatch tables and resolution logic.

Extracted from PropertyFrame._add_widget_for_property() to enable:
  - data-driven field resolution (widget-free)
  - testing (equivalence check vs. old chain)
  - future schema-driven visibility, grouping, and styling

P1: data tables + FieldDef + resolve() only. Widget instantiation stays in property_frame.py.
Groups and visibility predicates come in P5.

NOTE: m_VariableValue handling is value-dependent (control choice depends on m_TargetName
presence and prop_class suffix). resolve() returns 'set_variable' unconditionally; the
caller uses resolve_variable_value(prop_class, value) to pick the fallback when value
is not a SetVariable dict.
"""

import re
from dataclasses import dataclass
from src.editors.smartprop_editor.objects import surfaces_list


@dataclass(frozen=True)
class FieldDef:
    """
    Immutable schema for a single property field.

    - field: e.g. 'm_flWidth'
    - control: control-kind string (see CONTROL_KIND_MAP keys)
    - kwargs: widget-constructor kwargs (items, filter_types, slider_range, int_bool, etc.)
    - label: prettified display name (derived from field)
    - icon: IconCache key (derived from control + kwargs)
    - group: collapsible group name (None in P1; populated in P5)
    """
    field: str
    control: str
    kwargs: dict
    label: str
    icon: str
    group: str | None = None


# Field lists per property class (69 classes, 393 fields; order matches the source).
_PROP_CLASSES_MAP = {
    'ModifyState': ['m_nReferenceID', 'm_bEnabled'],
    'Group': ['m_nReferenceID', 'm_bEnabled'],
    'SmartProp': ['m_nReferenceID', 'm_bEnabled', 'm_sSmartProp', 'm_bLocalEvaluationState'],
    'PlaceInSphere': ['m_nReferenceID', 'm_bEnabled', 'm_flRandomness', 'm_nCountMin', 'm_nCountMax', 'm_flPositionRadiusInner', 'm_flPositionRadiusOuter', 'm_bAlignOrientation', 'm_PlacementMode', 'm_DistributionMode', 'm_vAlignDirection', 'm_vPlaneUpDirection'],
    'PlaceMultiple': ['m_nReferenceID', 'm_bEnabled', 'm_nCount', 'm_Expression'],
    'PlaceOnPath': ['m_nReferenceID', 'm_bEnabled', 'm_PathName', 'm_vPathOffset', 'm_flOffsetAlongPath', 'm_PathSpace', 'm_flSpacing', 'm_bUseFixedUpDirection', 'm_bUseProjectedDistance', 'm_vUpDirection', 'm_UpDirectionSpace', 'm_DefaultPathInWorldSpace', 'm_DefaultPath'],
    'FitOnLine': ['m_nReferenceID', 'm_bEnabled', 'm_vStart', 'm_vEnd', 'm_PointSpace', 'm_bOrientAlongLine', 'm_vUpDirection', 'm_UpDirectionSpace', 'm_bPrioritizeUp', 'm_nScaleMode', 'm_nPickMode'],
    'PickOne': ['m_nReferenceID', 'm_bEnabled', 'm_SelectionMode', 'm_SpecificChildIndex', 'm_OutputChoiceVariableName', 'm_bConfigurable', 'm_vHandleOffset', 'm_HandleColor', 'm_HandleSize', 'm_HandleShape'],
    'Model': ['m_nReferenceID', 'm_bEnabled', 'm_sModelName', 'm_vModelScale', 'm_MaterialGroupName', 'm_bDetailObject', 'm_bRigidDeformation', 'm_bDisableDynamicDeformable', 'm_nLodLevel', 'm_nDetailObjectFadeLevel', 'm_bCastShadows', 'm_flUniformModelScale', 'm_SurfacePropertyOverride'],
    'ModelEntity': ['m_nReferenceID', 'm_bEnabled', 'm_sModelName', 'm_vModelScale', 'm_MaterialGroupName', 'm_bDetailObject', 'm_bRigidDeformation', 'm_nLodLevel', 'm_bCastShadows', 'm_bForceStatic', 'm_nDeformableAttachmentMode', 'm_nDeformableOrientationMode'],
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
    'Comment': ['m_bEnabled', 'm_Comment'],
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

SKIP = frozenset({'_class', 'm_sLabel', 'm_nElementID', 'm_sReferenceObjectID', '_WARN_NOT_VERIFIED'})

# Exact-match dispatch: field name -> (control, kwargs_dict)
_EXACT_PROP_DISPATCH = {
    'm_bEnabled':              ('bool', {}),
    'm_nReferenceID':          ('reference', {}),
    'm_HandleColor':           ('color', {}),
    'm_HandleSize':            ('float', {}),
    'm_ColorChoices':          ('colormatch', {}),
    'm_MaterialReplacements':  ('material_replacements', {}),
    'm_MaterialGroupChoices':  ('material_group_choices', {}),
    'm_ChoiceSelection':       ('float', {'int_bool': True}),
    'm_Color':                 ('color', {}),
    'm_ColorPosition':         ('float', {'slider_range': [0, 1]}),
    'm_Material':              ('string', {'expression_bool': False, 'placeholder': 'Material name (.vmat)', 'filter_types': ['String']}),
    'm_flBendPoint':           ('float', {'slider_range': [0, 1]}),
    'm_flWidth':               ('float', {'slider_range': [0, 4096]}),
    'm_flLength':              ('float', {'slider_range': [0, 4096]}),
    'm_flSpacingWidth':        ('float', {'slider_range': [0, 4096]}),
    'm_flSpacingLength':       ('float', {'slider_range': [0, 4096]}),
    'm_flAlternateShiftWidth': ('float', {'slider_range': [0, 4096]}),
    'm_flAlternateShiftLength':('float', {'slider_range': [0, 4096]}),
    'm_nCountW':               ('float', {'int_bool': True, 'slider_range': [0, 256]}),
    'm_nCountL':               ('float', {'int_bool': True, 'slider_range': [0, 256]}),
    'm_SpecificChildIndex':    ('float', {'int_bool': True}),
    'm_ColorSelection':        ('float', {'int_bool': True}),
    'm_sModelName':            ('string', {'expression_bool': False, 'placeholder': 'models/example.vmdl', 'model_browser': True, 'filter_types': ['String', 'Model']}),
    'm_MaterialGroupName':     ('string', {'expression_bool': False, 'placeholder': 'Material group name'}),
    'm_Expression':            ('string', {'expression_bool': True,  'placeholder': 'Expression example: var_bool ? var_sizer * var_multiply'}),
    'm_StateName':             ('string', {'expression_bool': False, 'only_string': True, 'placeholder': 'State name'}),
    'm_LocatorName':           ('string', {'expression_bool': False, 'placeholder': 'Locator name'}),
    'm_MeshName':              ('string', {'expression_bool': False, 'placeholder': 'Mesh name'}),
    'm_VariableName':          ('variable', {'filter_types': ['String', 'Int', 'Float', 'Bool', 'Vector3D', 'Color']}),
    'm_OutputVariableName':    ('variable', {'filter_types': ['String', 'Int', 'Float', 'Bool', 'Vector3D']}),
    'm_OutputVariableMaxZ':    ('variable', {}),
    'm_OutputVariableMinZ':    ('variable', {}),
    'm_OutputVariableMaxY':    ('variable', {}),
    'm_OutputVariableMinY':    ('variable', {}),
    'm_OutputVariableMaxX':    ('variable', {}),
    'm_OutputVariableMinX':    ('variable', {}),
    'm_OutputVariable':        ('variable', {}),
    'm_OutputChoiceVariableName': ('variable', {}),
    'm_DefaultPath':           ('path_editor', {}),
    'm_DefaultPathInWorldSpace': ('bool', {}),
    '_WARN_NOT_VERIFIED':      ('warning', {}),
}

# Combobox substring rules: (substring, items, filter_types) — order matters.
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
    ('m_SelectionMode', ['RANDOM', 'FIRST', 'SPECIFIC'], ['ChoiceSelectionMode']),
    ('m_PlacementMode', ['SPHERE', 'CIRCLE', 'RING'], ['RadiusPlacementMode']),
    ('m_DistributionMode', ['RANDOM', 'UNIFORM'], ['DistributionMode']),
    ('m_SpacingSpace', ['ELEMENT', 'OBJECT', 'WORLD'], ['CoordinateSpace']),
    ('m_sPhysicsType', ['normal', 'multiplayer'], ['String']),
    ('m_nDetailObjectFadeLevel', ['NONE', 'MOST_AGGRESSIVE', 'MORE_AGGRESSIVE', 'NORMAL', 'LESS_AGGRESSIVE', 'LEAST_AGGRESSIVE'], ['String']),
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

# Per-(prop_class, field) combobox overrides — checked before _COMBOBOX_SUBSTRING_RULES.
# Needed when the same field name means a different enum on different classes: e.g.
# PlaceOnMesh's m_nPickMode (FIRST_OPEN_EDGE/FIRST_CLOSED_EDGE/UVMAP1/UVMAP2, real enum
# SmartPropPlaceMeshOrientationMode_t) vs FitOnLine's m_nPickMode (LARGEST_FIRST/RANDOM/
# ALL_IN_ORDER) — the generic substring rule can only encode one of them.
_CLASS_FIELD_COMBOBOX_OVERRIDES = {
    ('PlaceOnMesh', 'm_nPickMode'): (['FIRST_OPEN_EDGE', 'FIRST_CLOSED_EDGE', 'UVMAP1', 'UVMAP2'], ['OrientationMode']),
}

# Prefix dispatch: (prefix, control, kwargs) — order matters (most frequent first).
_PREFIX_DISPATCH = [
    ('m_fl', 'float', {}),
    ('m_f', 'float', {}),
    ('m_n', 'float', {'int_bool': True}),
    ('m_InputVector', 'vector3d', {}),
    ('m_Origin', 'vector3d', {}),
    ('m_TargetPoint', 'vector3d', {}),
    ('m_EndPoint', 'vector3d', {}),
    ('m_v', 'vector3d', {}),
    ('m_b', 'bool', {}),
    ('m_s', 'string', {'expression_bool': False, 'placeholder': 'String'}),
    ('m_', 'string', {'expression_bool': False, 'placeholder': 'String'}),
]


def _prettify_label(field: str) -> str:
    """
    Strip m_* prefix patterns and split camelCase into readable label.
    Matches the logic in PropertyFloat.__init__ (lines 69-71).
    """
    output = re.sub(r'm_fl|m_n|m_b|m_s|m_v|m_f|m_', '', field)
    output = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', output)
    return output


def _icon_for_control(control: str, kwargs: dict) -> str:
    """
    Map control type + kwargs to IconCache key.

    Every control kind gets a distinct icon (added in Phase D); unknown kinds
    still fall back to 'string'.
    """
    if control == 'float':
        return 'number' if kwargs.get('int_bool') else 'float'
    if control == 'number':
        return 'number'
    if control == 'string':
        return 'string'
    if control == 'bool':
        return 'bool'
    if control == 'vector3d':
        return 'vector'
    if control == 'variable':
        return 'variablename'
    if control == 'color':
        return 'color'
    if control == 'combobox':
        return 'combobox'
    if control == 'reference':
        return 'reference'
    if control == 'comment':
        return 'comment'
    if control == 'warning':
        return 'warning'
    if control == 'legacy':
        return 'legacy'
    if control == 'comparison':
        return 'comparison'
    if control == 'surface':
        return 'surface'
    if control == 'colormatch':
        return 'colormatch'
    if control == 'material_replacements':
        return 'material'
    if control == 'material_group_choices':
        return 'materialgroup'
    if control == 'set_variable':
        return 'setvariable'
    return 'string'


def fields_for(prop_class: str) -> list[str]:
    """
    Return the ordered list of field names for a property class.
    Returns empty list if the class is not in the schema.
    """
    return list(_PROP_CLASSES_MAP.get(prop_class, []))


def resolve(prop_class: str, field: str) -> FieldDef | None:
    """
    Resolve the FieldDef for a single property field.

    Returns None if field is in SKIP or does not match any dispatch rule.

    Resolution order (must match _add_widget_for_property exactly):
      1. field in SKIP -> None
      2. exact match in _EXACT_PROP_DISPATCH
      3. 'm_VariableValue' in field -> 'set_variable' (+ note about fallback to caller)
      4. 'm_VariableComparison' in field -> 'comparison'
      5. 'm_AllowedSurfaceProperties' or 'm_DisallowedSurfaceProperties' in field -> 'surface'
      6. 'm_Comment' in field -> 'comment'
      6.5. (prop_class, field) in _CLASS_FIELD_COMBOBOX_OVERRIDES -> 'combobox'
      7. first matching substring in _COMBOBOX_SUBSTRING_RULES -> 'combobox'
      8. first matching substring in _PREFIX_DISPATCH -> that control
      9. fallback -> 'legacy'
    """
    # 1. Skip list
    if field in SKIP:
        return None

    # 2. Exact match
    if field in _EXACT_PROP_DISPATCH:
        control, kwargs = _EXACT_PROP_DISPATCH[field]
        label = _prettify_label(field)
        icon = _icon_for_control(control, kwargs)
        return FieldDef(field=field, control=control, kwargs=kwargs, label=label, icon=icon)

    # 3. m_VariableValue (value-dependent; see resolve_variable_value for fallback)
    if 'm_VariableValue' in field:
        kwargs = {}
        label = _prettify_label(field)
        icon = _icon_for_control('variable', kwargs)
        return FieldDef(field=field, control='set_variable', kwargs=kwargs, label=label, icon=icon)

    # 4. m_VariableComparison
    if 'm_VariableComparison' in field:
        kwargs = {}
        label = _prettify_label(field)
        icon = _icon_for_control('comparison', kwargs)
        return FieldDef(field=field, control='comparison', kwargs=kwargs, label=label, icon=icon)

    # 5. Surface properties
    if 'm_AllowedSurfaceProperties' in field or 'm_DisallowedSurfaceProperties' in field:
        kwargs = {}
        label = _prettify_label(field)
        icon = _icon_for_control('surface', kwargs)
        return FieldDef(field=field, control='surface', kwargs=kwargs, label=label, icon=icon)

    # 6. Comment
    if 'm_Comment' in field:
        kwargs = {}
        label = _prettify_label(field)
        icon = _icon_for_control('comment', kwargs)
        return FieldDef(field=field, control='comment', kwargs=kwargs, label=label, icon=icon)

    # 6.5. Per-class combobox override (same field name, different enum per class)
    if (prop_class, field) in _CLASS_FIELD_COMBOBOX_OVERRIDES:
        items, filter_types = _CLASS_FIELD_COMBOBOX_OVERRIDES[(prop_class, field)]
        kwargs = {'items': list(items), 'filter_types': list(filter_types)}
        label = _prettify_label(field)
        icon = _icon_for_control('combobox', kwargs)
        return FieldDef(field=field, control='combobox', kwargs=kwargs, label=label, icon=icon)

    # 7. Combobox substring rules (order matters)
    for substring, items, filter_types in _COMBOBOX_SUBSTRING_RULES:
        if substring in field:
            kwargs = {'items': list(items), 'filter_types': list(filter_types)}
            label = _prettify_label(field)
            icon = _icon_for_control('combobox', kwargs)
            return FieldDef(field=field, control='combobox', kwargs=kwargs, label=label, icon=icon)

    # 8. Prefix dispatch (order matters)
    for prefix, control, extra_kwargs in _PREFIX_DISPATCH:
        if prefix in field:
            kwargs = dict(extra_kwargs)
            label = _prettify_label(field)
            icon = _icon_for_control(control, kwargs)
            return FieldDef(field=field, control=control, kwargs=kwargs, label=label, icon=icon)

    # 9. Fallback
    kwargs = {}
    label = _prettify_label(field)
    icon = _icon_for_control('legacy', kwargs)
    return FieldDef(field=field, control='legacy', kwargs=kwargs, label=label, icon=icon)


def resolve_variable_value(prop_class: str, value) -> str:
    """
    For fields with m_VariableValue in the name, determine the fallback control
    when the value is NOT a SetVariable dict.

    NOTE: resolve(prop_class, field) returns 'set_variable' unconditionally.
    This helper is called by the widget layer to pick the actual control when
    the value doesn't match SetVariable structure.

    Returns:
      - 'bool' if value is bool or prop_class ends 'Bool'
      - 'float' if value is numeric or prop_class ends 'Float'/'Int'
      - 'string' with expression_bool=True otherwise
    """
    if isinstance(value, bool) or prop_class.endswith('Bool'):
        return 'bool'
    elif isinstance(value, (int, float)) or prop_class.endswith('Float') or prop_class.endswith('Int'):
        return 'float'
    else:
        return 'string'


if __name__ == '__main__':
    # Verify resolve() for known classes
    count = 0
    for cls, fields in _PROP_CLASSES_MAP.items():
        for f in fields:
            res = resolve(cls, f)
            if res is not None:
                assert res.control is not None
                count += 1
    print(f"[PASS] schema.resolve() verified {count} fields across {len(_PROP_CLASSES_MAP)} classes.")

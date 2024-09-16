variable_prefix = 'CSmartPropVariable_'
variables_list = [
    'CoordinateSpace',
    'Direction',
    'DistributionMode',
    'RadiusPlacementMode',
    'ChoiceSelectionMode',
    'String',
    'Bool',
    'Int',
    'Float',
    'Vector2D',
    'Vector3D',
    'Vector4D',
    'Color',
    'Angles',
    'MaterialGroup',
    'Model',
    'ApplyColorMode',
    'TraceNoHit',
    'ScaleMode',
    'PickMode',
    'GridPlacementMode',
    'GridOriginMode',
    'PathPositions'
]

element_prefix = 'CSmartPropElement_'
elements_list = [
    {'ModifyState': {'_class': 'CSmartPropElement_ModifyState', 'm_Modifiers': [], 'm_SelectionCriteria': []}},
    {'Group': {'_class': 'CSmartPropElement_Group', 'm_Modifiers': [], 'm_SelectionCriteria': []}},
    {'SmartProp': {'_class': 'CSmartPropElement_SmartProp', 'm_sSmartProp': '', 'm_Modifiers': [], 'm_SelectionCriteria': []}},
    {'PlaceInSphere': {'_class': 'CSmartPropElement_PlaceInSphere', 'm_flRandomness': 0, 'm_nCountMin': 0, 'm_nCountMax': 0, 'm_flPositionRadiusInner': 0, 'm_flPositionRadiusOuter': 0, 'm_bAlignOrientation': False, 'm_Modifiers': [], 'm_SelectionCriteria': []}},
    {'PlaceMultiple': {'_class': 'CSmartPropElement_PlaceMultiple', 'm_nCount': 0, 'm_Modifiers': [], 'm_SelectionCriteria': []}},
    {'PlaceOnPath': {'_class': 'CSmartPropElement_PlaceOnPath', 'm_PathName': 'path', 'm_vPathOffset': {'m_Components': [0, 0, 0]}, 'm_flOffsetAlongPath': 0, 'm_PathSpace': 'ELEMENT', 'm_Modifiers': [], 'm_SelectionCriteria': []}},
    {'FitOnLine': {'_class': 'CSmartPropElement_FitOnLine', 'm_bOrientAlongLine': False, 'm_Modifiers': [], 'm_SelectionCriteria': []}},
    {'PickOne': {'_class': 'CSmartPropElement_PickOne', 'm_SelectionMode': 'RANDOM', 'm_vHandleOfffset': {'m_Components': [0, 0, 0]}, 'm_HandleShape': 'SQUARE', 'm_Modifiers': [], 'm_SelectionCriteria': []}},
    {'Model': {'_class': 'CSmartPropElement_Model', 'm_sModelName': '', 'm_vModelScale': {'m_Components': [0, 0, 0]}, 'm_MaterialGroupName': '', 'm_Modifiers': [], 'm_SelectionCriteria': []}}
]
filter_prefix = 'CSmartPropFilter_'
filters_list = [
    {'Expression': {'_class': 'CSmartPropFilter_Expression', 'm_Expression': ''}},
    {'Probability': {'_class': 'CSmartPropFilter_Probability', 'm_flProbability': 0}},
    {'SurfaceAngle': {'_class': 'CSmartPropFilter_SurfaceAngle', 'm_flSurfaceSlopeMin': 0, 'm_flSurfaceSlopeMax': 0}},
    {'SurfaceProperties': {'_class': 'CSmartPropFilter_SurfaceProperties', 'm_AllowedSurfaceProperties': [], "m_DisallowedSurfaceProperties": []}},
    {'VariableValue': {'_class': 'CSmartPropFilter_VariableValue', 'm_VariableComparison': {'m_Name': '', 'm_Value': 0, 'm_Comparison': 'EQUAL'}}}
]

operator_prefix = 'CSmartPropOperation_'
operators_list = [
    {'Rotate': {'_class': "CSmartPropOperation_Rotate", "m_vRotation": {"m_Components":[0,0,0]}}},
    {'Scale': {'_class': "CSmartPropOperation_Scale", "m_flScale": 0}},
    {'Translate': {'_class': "CSmartPropOperation_Translate", "m_vPosition": {"m_Components":[0,0,0]}}},
    {'SetTintColor': {'_class': "CSmartPropOperation_SetTintColor", "m_Mode": "MULTIPLY_OBJECT", "m_ColorChoices": []}},
    {'RandomOffset': {'_class': "CSmartPropOperation_RandomOffset", "m_vRandomPositionMin": {"m_Components":[0,0,0]}, "m_vRandomPositionMax": {"m_Components":[0,0,0]}}},
    {'RandomScale': {'_class': "CSmartPropOperation_RandomScale", "m_flRandomScaleMin": 0, "m_flRandomScaleMax": 0}},
    {'RandomRotation': {'_class': "CSmartPropOperation_RandomRotation", "m_vRandomRotationMin": {"m_Components":[0,0,0]}, "m_vRandomRotationMax": {"m_Components":[0,0,0]}}},
    {'CreateSizer': {'_class': "CSmartPropOperation_CreateSizer", "m_flInitialMinX": 0, "m_flInitialMaxX": 0, "m_flInitialMinY": 0, "m_flInitialMaxY": 0, "m_flInitialMinZ": 0, "m_flInitialMaxZ": 0}},
    {'CreateRotator': {'_class': "CSmartPropOperation_CreateRotator"}},
    {'CreateLocator': {'_class': "CSmartPropOperation_CreateLocator"}},
    {'TraceInDirection': {'_class': "CSmartPropOperation_TraceInDirection", 'm_DirectionSpace': 'WORLD', 'm_flSurfaceUpInfluence': 1, 'm_nNoHitResult': 'NOTHING', 'm_flOriginOffset': 500, 'm_flTraceLength': 500}}
]

operators_dict_todo = {
    'TraceToPoint': {},
    'TraceToLine': {},
    'SetVariable': {},
    'SaveState': {},
    'RestoreState': {},
    'SavePosition': {},
    'SaveDirection': {},
    'SaveScale': {},
    'SaveSurfaceNormal': {},
    'ComputeDotProduct3D': {},
    'ComputeCrossProduct3D': {},
    'ComputeDistance3D': {},
    'ComputeVectorBetweenPoints3D': {},
    'ComputeNormalizedVector3D': {},
    'ComputeProjectVector3D': {},
    'ResetScale': {},
    'RotateTowards': {},
    'Trace': {},
    'ResetRotation': {},
    'SetOrientation': {},
    'SetPosition': {},
}

selection_criteria_prefix = "CSmartPropSelectionCriteria_"
selection_criteria_list = [
    {"Endcap": {'_class': 'CSmartPropSelectionCriteria_EndCap', 'm_bStart':False, 'm_bEnd': False}},
    {"ChoiceWeight": {'_class': 'CSmartPropSelectionCriteria_ChoiceWeight', 'm_flWeight': 0}},
    {"IsValid": {'_class': 'CSmartPropSelectionCriteria_IsValid', 'm_sLabel': ''}},
    {"LinearLength": {'_class': 'CSmartPropSelectionCriteria_LinearLength', 'm_flLength': 0, 'm_bAllowScale': False, 'm_flMinLength': 0, 'm_flMaxLength': 0}},
    {"PathPosition": {'_class': 'CSmartPropSelectionCriteria_PathPosition', 'm_PlaceAtPositions': 'ALL', 'm_nPlaceEveryNthPosition': 0, 'm_nNthPositionIndexOffset': 0, 'm_bAllowAtStart': False, 'm_bAllowAtEnd': False}},
]
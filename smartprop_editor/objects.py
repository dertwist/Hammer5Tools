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
elements_dict = {
    'ModifyState': {},
    'Group': {},
    'SmartProp': {},
    'PlaceInSphere': {},
    'PlaceMultiple': {},
    'PlaceOnPath': {},
    'FitOnLine': {},
    'PickOne': {}
}
filter_prefix = 'CSmartPropFilter_'
filters_dict = {
    'Probability': {'m_flProbability': 0},
    'SurfaceAngle': {'m_flSurfaceSlopeMin': 90, 'm_flSurfaceSlopeMax': 180},
    'VariableValue': {'m_Expression': 0},
    'Expression': {'m_Expression': 0},
    'SurfaceProperties': {'m_AllowedSurfaceProperties': "", "m_DisallowedSurfaceProperties": ""},
}

operator_prefix = 'CSmartPropOperation_'
operators_list = [
    {'Rotate': {},},
    {'Scale': {},},
    {'Translate': {'_class': "CSmartPropOperation_Translate", 'm_vPosition': [120, -12, 0]}},
    {'SetTintColor': {'m_ColorChoices': []}},
    {'CreateLocator': {}},
    {'CreateSizer': {}},
    {'CreateRotator': {}},
    {'RandomRotation': {}},
    {'RandomScale': {}},
    {'RandomOffset': {}},
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
    'TraceInDirection': {},
    'ResetRotation': {},
    'SetOrientation': {},
    'SetPosition': {},
}

selection_criteria_prefix = "CSmartPropSelectionCriteria_"
selection_criteria_dict = {
    "EndCap": {"m_bStart": False, "m_bEnd": False},
    "IsValid": {},
    "ChoiceWeight": {"m_flWeight": 0},
    "LinearLength": {'m_flLength': 0, 'm_bAllowScale': False, 'm_flMinLength': 0, 'm_flMaxLength': 0},
    "PathPosition": {'m_PlaceAtPositions': "ALL", "m_nPlaceEveryNthPosition": 0, "m_nNthPositionIndexOffset": 0, "m_bAllowAtStart": False, "m_bAllowAtEnd": False},
}
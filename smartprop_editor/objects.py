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
    'ModifyState',
    'Group',
    'SmartProp',
    'PlaceInSphere',
    'PlaceMultiple',
    'PlaceOnPath',
    'FitOnLine',
    'PickOne'
]
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
    'TraceToPoint',
    'TraceToLine',
    'SetTintColor',
    'SetVariable',
    'SaveState',
    'RestoreState',
    'SavePosition',
    'SaveDirection',
    'SaveScale',
    'SaveSurfaceNormal',
    'SaveDirection',
    'ComputeDotProduct3D',
    'ComputeCrossProduct3D',
    'ComputeDistance3D',
    'ComputeVectorBetweenPoints3D',
    'ComputeNormalizedVector3D',
    'ComputeProjectVector3D',
    'CreateLocator',
    'CreateSizer',
    'CreateRotator',
    'ResetRotation',
    'SetOrientation',
    'SetPosition',
    'ResetScale',
    'Rotate',
    'Translate',
    'RotateTowards',
    'Scale',
    'RandomOffset',
    'RandomRotation',
    'RandomScale',
    'Trace',
    'TraceInDirection'
]
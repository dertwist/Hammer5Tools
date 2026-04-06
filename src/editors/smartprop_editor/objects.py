from win32comext.shell.shellcon import NSTCS_NOEDITLABELS

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
    'Material',
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
    {'PlaceInSphere': {
        '_class': 'CSmartPropElement_PlaceInSphere',
        'm_flRandomness': None,
        'm_nCountMin': 1,
        'm_nCountMax': 1,
        'm_flPositionRadiusInner': 0.0,
        'm_flPositionRadiusOuter': 0.0,
        'm_bAlignOrientation': False,
        'm_PlacementMode': 'SPHERE',
        'm_DistributionMode': 'RANDOM',
        'm_vAlignDirection': None,
        'm_vPlaneUpDirection': None,
        'm_Modifiers': [],
        'm_SelectionCriteria': []
    }},
    {'PlaceMultiple': {'_class': 'CSmartPropElement_PlaceMultiple', 'm_nCount': None, 'm_Modifiers': [], 'm_SelectionCriteria': []}},
    {'PlaceOnPath': {
        '_class': 'CSmartPropElement_PlaceOnPath',
        'm_PathName': 'path',
        'm_vPathOffset': None,
        'm_flOffsetAlongPath': None,
        'm_PathSpace': None,
        'm_flSpacing': 128.0,
        'm_SpacingSpace': 'WORLD',
        'm_bContinuousSpline': True,
        'm_Modifiers': [],
        'm_SelectionCriteria': [],
        'm_bUseFixedUpDirection': True,
        'm_bUseProjectedDistance': True,
        'm_vUpDirection': None,
        'm_UpDirectionSpace': 'WORLD',
        'm_DefaultPath': [[-400.0, 0.0, 0.0], [-200.0, 32, 0.0], [200.0, -32, 0.0], [400.0, 0.0, 0.0]]
    }},
    {'FitOnLine': {
        '_class': 'CSmartPropElement_FitOnLine',
        'm_vStart': None,
        'm_vEnd': None,
        'm_PointSpace': 'ELEMENT',
        'm_bOrientAlongLine': False,
        'm_vUpDirection': None,
        'm_UpDirectionSpace': 'WORLD',
        'm_bPrioritizeUp': False,
        'm_nScaleMode': 'NONE',
        'm_nPickMode': 'SEQUENCE',
        'm_Modifiers': [],
        'm_SelectionCriteria': []
    }},
    {'PickOne': {
        '_class': 'CSmartPropElement_PickOne',
        'm_SelectionMode': 'RANDOM',
        'm_SpecificChildIndex': 0,
        'm_OutputChoiceVariableName': '',
        'm_bConfigurable': False,
        'm_vHandleOffset': None,
        'm_HandleColor': None,
        'm_HandleSize': 32,
        'm_HandleShape': None,
        'm_Modifiers': [],
        'm_SelectionCriteria': []
    }},
    {'Model': {
        '_class': 'CSmartPropElement_Model',
        'm_sModelName': '',
        'm_bForceStatic': True,
        'm_vModelScale': None,
        'm_MaterialGroupName': None,
        'm_bDetailObject': False,
        'm_bRigidDeformation': False,
        'm_nLodLevel': -1,
        'm_DetailObjectFadeLevel': None,
        'm_nDeformableAttachmentMode': None,
        'm_nDeformableOrientationMode': None,
        'm_bCastShadows': True,
        'm_flUniformModelScale': None,
        'm_SurfacePropertyOverride': None,
        'm_Modifiers': [],
        'm_SelectionCriteria': []
    }},
    {'ModelEntity': {
        '_class': 'CSmartPropElement_ModelEntity',
        'm_sModelName': '',
        'm_vModelScale': None,
        'm_MaterialGroupName': None,
        'm_bDetailObject': False,
        'm_bRigidDeformation': False,
        'm_nLodLevel': -1,
        'm_bCastShadows': True,
        'm_bForceStatic': False,
        'm_nDeformableAttachmentMode': None,
        'm_nDeformableOrientationMode': None,
        'm_Modifiers': [],
        'm_SelectionCriteria': []
    }},
    {'BendDeformer': {
        '_class': 'CSmartPropElement_BendDeformer',
        'm_bDeformationEnabled': True,
        'm_vOrigin': None,
        'm_vAngles': None,
        'm_vSize': None,
        'm_flBendAngle': 0.0,
        'm_flBendPoint': 0.0,
        'm_flBendRadius': 0.0,
        'm_Modifiers': [],
        'm_SelectionCriteria': []
    }},
    {'PropPhysics': {
        '_class': 'CSmartPropElement_PropPhysics',
        'm_sModelName': '',
        'm_vModelScale': None,
        'm_MaterialGroupName': None,
        'm_flMass': 50.0,
        'm_bStartAsleep': False,
        'm_nHealth': 100,
        'm_bEnableMotion': True,
        'm_sPhysicsType': 'normal',
        'm_Modifiers': [],
        'm_SelectionCriteria': []
    }},
    {'PropDynamic': {
        '_class': 'CSmartPropElement_PropDynamic',
        'm_sModelName': '',
        'm_sAnimationSequence': '',
        'm_sDefaultAnimation': '',
        'm_vModelScale': None,
        'm_MaterialGroupName': None,
        'm_Modifiers': [],
        'm_SelectionCriteria': []
    }},
    {'MidpointDeformer': {
        '_class': 'CSmartPropElement_MidpointDeformer',
        'm_bDeformationEnabled': True,
        'm_vStart': None,
        'm_vEnd': None,
        'm_fRadius': 50.0,
        'm_bContinuousSpline': True,
        'm_vOffset': None,
        'm_vAngles': None,
        'm_vScale': None,
        'm_fFalloff': 0.5,
        'm_OutputVariable': '',
        'm_Modifiers': [],
        'm_SelectionCriteria': []
    }},
    {'Grid': {
        '_class': 'CSmartPropElement_Layout2DGrid',
        'm_flWidth': 512.0,
        'm_flLength': 512.0,
        'm_bVerticalLength': False,
        'm_GridArrangement': 'SEGMENT',
        'm_GridOriginMode': 'CENTER',
        'm_nCountW': 4,
        'm_nCountL': 4,
        'm_flSpacingWidth': 128.0,
        'm_flSpacingLength': 128.0,
        'm_bAlternateShift': False,
        'm_flAlternateShiftWidth': 0.0,
        'm_flAlternateShiftLength': 0.0,
        'm_Modifiers': [],
        'm_SelectionCriteria': []
    }}
]

filter_prefix = 'CSmartPropFilter_'
filters_list = [
    {'Expression': {'_class': 'CSmartPropFilter_Expression', 'm_Expression': ''}},
    {'Probability': {'_class': 'CSmartPropFilter_Probability', 'm_flProbability': 1}},
    {'SurfaceAngle': {'_class': 'CSmartPropFilter_SurfaceAngle', 'm_flSurfaceSlopeMin': 0, 'm_flSurfaceSlopeMax': 0}},
    {'SurfaceProperties': {'_class': 'CSmartPropFilter_SurfaceProperties', 'm_AllowedSurfaceProperties': [], "m_DisallowedSurfaceProperties": []}},
    {'VariableValue': {'_class': 'CSmartPropFilter_VariableValue', 'm_VariableComparison': {'m_Name': '', 'm_Value': 0, 'm_Comparison': 'EQUAL'}}}
]

operator_prefix = 'CSmartPropOperation_'
operators_list = [
    {'Rotate': {'_class': "CSmartPropOperation_Rotate", "m_vRotation": {"m_Components":[0,0,0]}}},
    {'Scale': {'_class': "CSmartPropOperation_Scale", "m_flScale": 1}},
    {'Translate': {'_class': "CSmartPropOperation_Translate", "m_vPosition": {"m_Components":[0,0,0]}}},
    {'SetTintColor': {'_class': "CSmartPropOperation_SetTintColor", "m_Mode": "MULTIPLY_OBJECT", "m_ColorChoices": []}},
    {'MaterialOverride': {'_class': "CSmartPropOperation_MaterialOverride", "m_bClearCurrentOverrides": False, "m_MaterialReplacements": []}},
    {'MaterialTint': {'_class': "CSmartPropOperation_MaterialTint", "m_Material": "", "m_SelectionMode": "SPECIFIC_COLOR", "m_Color": [255, 255, 255], "m_ColorPosition": 0.0}},
    {'RandomOffset': {'_class': "CSmartPropOperation_RandomOffset", "m_vRandomPositionMin": None, "m_vRandomPositionMax": None, "m_vSnapIncrement": None}},
    {'RandomScale': {'_class': "CSmartPropOperation_RandomScale", "m_flRandomScaleMin": 1.0, "m_flRandomScaleMax": 1.0, "m_flSnapIncrement": 0.0}},
    {'RandomRotation': {'_class': "CSmartPropOperation_RandomRotation", "m_vRandomRotationMin": None, "m_vRandomRotationMax": None, "m_vSnapIncrement": None}},
    {'RandomColorTintColor': {'_class': "CSmartPropOperation_RandomColorTintColor", "m_SelectionMode": "RANDOM", "m_Color": [255, 255, 255], "m_ColorPosition": 0.0, "m_Mode": "MULTIPLY_OBJECT"}},
    {'CreateSizer': {'_class': "CSmartPropOperation_CreateSizer", "m_Name": "", "m_bDisplayModel": False}},
    {'CreateRotator': {'_class': "CSmartPropOperation_CreateRotator", "m_Name": "", "m_vOffset": None, "m_vRotationAxis": None, "m_CoordinateSpace": "WORLD", "m_flDisplayRadius": 16.0, "m_DisplayColor": None, "m_bApplyToCurrentTransform": True, "m_flSnappingIncrement": 0.0, "m_flInitialAngle": 0.0, "m_bEnforceLimits": False, "m_flMinAngle": 0.0, "m_flMaxAngle": 0.0, "m_OutputVariable": ""}},
    {'CreateLocator': {'_class': "CSmartPropOperation_CreateLocator", "m_LocatorName": "", "m_vOffset": None, "m_flDisplayScale": 1.0, "m_bConfigurable": True, "m_bAllowTranslation": True, "m_bAllowRotation": True, "m_bAllowScale": True}},
    {'RestoreState': {'_class': "CSmartPropOperation_RestoreState", 'm_bDiscardIfUknown': True}},
    {'TraceInDirection': {'_class': "CSmartPropOperation_TraceInDirection", 'm_DirectionSpace': 'WORLD', 'm_flSurfaceUpInfluence': 1, 'm_nNoHitResult': 'NOTHING', 'm_flOriginOffset': -500, 'm_flTraceLength': 500}},
    {'SaveState': {'_class': 'CSmartPropOperation_SaveState', 'm_StateName': 'State'}},
    {'SetVariable': {'_class': 'CSmartPropOperation_SetVariable', 'm_VariableValue': {'m_TargetName': None, 'm_DataType': None, 'm_Value':None}}},
    {'RandomRotationSnapped': {'_class': 'CSmartPropOperation_RandomRotationSnapped', 'm_vMinAngles': None, 'm_vMaxAngles': None, 'm_flSnapIncrement': 45.0, 'm_RotationAxes': 'Z'}},
    {'ResetRotation': {'_class': 'CSmartPropOperation_ResetRotation', 'm_bIgnoreObjectRotation': False, 'm_bResetPitch': True, 'm_bResetYaw': True, 'm_bResetRoll': True}},
    {'ResetScale': {'_class': 'CSmartPropOperation_ResetScale', 'm_bIgnoreObjectScale': False}},
    {'RotateTowards': {'_class': 'CSmartPropOperation_RotateTowards', 'm_vOriginPos': None, 'm_vTargetPos': None, 'm_vUpPos': None, 'm_flWeight': 1.0, 'm_OriginSpace': 'WORLD', 'm_TargetSpace': 'WORLD', 'm_UpSpace': 'WORLD'}},
    {'SaveColor': {'_class': 'CSmartPropOperation_SaveColor', 'm_VariableName': ''}},
    {'SaveDirection': {'_class': 'CSmartPropOperation_SaveDirection', 'm_DirectionVector': 'FORWARD', 'm_CoordinateSpace': 'WORLD', 'm_VariableName': ''}},
    {'SavePosition': {'_class': 'CSmartPropOperation_SavePosition', 'm_CoordinateSpace': 'WORLD', 'm_VariableName': ''}},
    {'SaveScale': {'_class': 'CSmartPropOperation_SaveScale', 'm_VariableName': ''}},
    {'SaveSurfaceNormal': {'_class': 'CSmartPropOperation_SaveSurfaceNormal', 'm_CoordinateSpace': 'WORLD', 'm_VariableName': ''}},
    {'SetMateraialGroupChoice': {'_class': 'CSmartPropOperation_SetMateraialGroupChoice', 'm_VariableName': '', 'm_SelectionMode': 'RANDOM', 'm_ChoiceSelection': 0, 'm_MaterialGroupChoices': []}},
    {'SetOrientation': {'_class': 'CSmartPropOperation_SetOrientation', 'm_vForwardVector': None, 'm_ForwardDirectionSpace': 'WORLD', 'm_vUpVector': None, 'm_UpDirectionSpace': 'WORLD', 'm_bPrioritizeUp': False}},
    {'SetPosition': {'_class': 'CSmartPropOperation_SetPosition', 'm_vPosition': None, 'm_CoordinateSpace': 'WORLD'}},
    {'Trace': {'_class': 'CSmartPropOperation_Trace', 'm_Origin': None, 'm_OriginSpace': 'WORLD', 'm_flOriginOffset': 0.0, 'm_flSurfaceUpInfluence': 1.0, 'm_nNoHitResult': 'NOTHING', 'm_bIgnoreToolMaterials': False, 'm_bIgnoreSky': False, 'm_bIgnoreNoDraw': False, 'm_bIgnoreTranslucent': False, 'm_bIgnoreModels': False, 'm_bIgnoreEntities': False, 'm_bIgnoreCables': False}},
    {'Comment': {'_class': 'Hammer5Tools_Comment', 'm_Comment': None}}
]

operators_dict_todo = {
    'TraceToPoint': {},
    'TraceToLine': {},
    'ComputeDotProduct3D': {},
    'ComputeCrossProduct3D': {},
    'ComputeDistance3D': {},
    'ComputeVectorBetweenPoints3D': {},
    'ComputeNormalizedVector3D': {},
    'ComputeProjectVector3D': {}
}

selection_criteria_prefix = "CSmartPropSelectionCriteria_"
selection_criteria_list = [
    {"EndCap": {'_class': 'CSmartPropSelectionCriteria_EndCap', 'm_bStart':False, 'm_bEnd': False}},
    {"ChoiceWeight": {'_class': 'CSmartPropSelectionCriteria_ChoiceWeight', 'm_flWeight': 0}},
    {"IsValid": {'_class': 'CSmartPropSelectionCriteria_IsValid'}},
    {"LinearLength": {'_class': 'CSmartPropSelectionCriteria_LinearLength', 'm_flLength': 0, 'm_bAllowScale': False, 'm_flMinLength': 0, 'm_flMaxLength': 0}},
    {"PathPosition": {'_class': 'CSmartPropSelectionCriteria_PathPosition', 'm_PlaceAtPositions': 'ALL', 'm_nPlaceEveryNthPosition': 0, 'm_nNthPositionIndexOffset': 0, 'm_bAllowAtStart': False, 'm_bAllowAtEnd': False}},
    {'Comment': {'_class': 'Hammer5Tools_Comment', 'm_Comment': None}}
]

surfaces_list = [{'default': {}}, {'solidmetal': {}}, {'metal': {}}, {'metal_barrelSoundOverride': {}}, {'metal_vehicleSoundOverride': {}}, {'metal_survivalCase': {}}, {'metal_survivalCase_unpunchable': {}}, {'metaldogtags': {}}, {'metalgrate': {}}, {'Metal_Box': {}}, {'metal_bouncy': {}}, {'slipperymetal': {}}, {'grate': {}}, {'metalvent': {}}, {'metalpanel': {}}, {'dirt': {}}, {'mud': {}}, {'slipperyslime': {}}, {'grass': {}}, {'slowgrass': {}}, {'sugarcane': {}}, {'tile': {}}, {'tile_survivalCase': {}}, {'tile_survivalCase_GIB': {}}, {'Wood': {}}, {'Wood_lowdensity': {}}, {'Wood_Box': {}}, {'Wood_Basket': {}}, {'Wood_Crate': {}}, {'Wood_Plank': {}}, {'Wood_Solid': {}}, {'Wood_Furniture': {}}, {'Wood_Panel': {}}, {'Wood_Dense': {}}, {'water': {}}, {'wet': {}}, {'puddle': {}}, {'slime': {}}, {'quicksand': {}}, {'wade': {}}, {'ladder': {}}, {'Wood_Ladder': {}}, {'glass': {}}, {'glassfloor': {}}, {'computer': {}}, {'weapon_magazine': {}}, {'concrete': {}}, {'asphalt': {}}, {'rock': {}}, {'porcelain': {}}, {'boulder': {}}, {'brick': {}}, {'concrete_block': {}}, {'stucco': {}}, {'chainlink': {}}, {'chain': {}}, {'flesh': {}}, {'bloodyflesh': {}}, {'alienflesh': {}}, {'armorflesh': {}}, {'ice': {}}, {'carpet': {}}, {'dufflebag_survivalCase': {}}, {'upholstery': {}}, {'plaster': {}}, {'sheetrock': {}}, {'cardboard': {}}, {'plastic_barrel': {}}, {'Plastic_Box': {}}, {'plastic': {}}, {'plastic_survivalCase': {}}, {'sand': {}}, {'rubber': {}}, {'rubbertire': {}}, {'jeeptire': {}}, {'slidingrubbertire': {}}, {'brakingrubbertire': {}}, {'slidingrubbertire_front': {}}, {'slidingrubbertire_rear': {}}, {'glassbottle': {}}, {'pottery': {}}, {'clay': {}}, {'canister': {}}, {'metal_barrel': {}}, {'metal_barrel_explodingSurvival': {}}, {'floating_metal_barrel': {}}, {'plastic_barrel_buoyant': {}}, {'roller': {}}, {'popcan': {}}, {'paintcan': {}}, {'paper': {}}, {'papercup': {}}, {'ceiling_tile': {}}, {'foliage': {}}, {'slipperyslide': {}}, {'strongman_bell': {}}, {'watermelon': {}}, {'item': {}}, {'floatingstandable': {}}, {'grenade': {}}, {'weapon': {}}, {'metal_shield': {}}, {'default_silent': {}}, {'player': {}}, {'player_control_clip': {}}, {'no_decal': {}}, {'soccerball': {}}, {'gravel': {}}, {'snow': {}}, {'metalvehicle': {}}, {'brass_bell_large': {}}, {'brass_bell_medium': {}}, {'brass_bell_small': {}}, {'brass_bell_smallest': {}}, {'metal_sand_barrel': {}}, {'blockbullets': {}}, {'jalopytire': {}}, {'slidingrubbertire_jalopyfront': {}}, {'slidingrubbertire_jalopyrear': {}}, {'jalopy': {}}, {'Balloon': {}}, {'metal_ventslat': {}}, {'metal_sheetmetal': {}}, {'plasticbottle': {}}, {'concrete_polished': {}}, {'plastic_dumpster': {}}, {'metal_dumpster': {}}, {'Cloth': {}}, {'plaster_drywall': {}}, {'Wood_Tree': {}}, {'beans': {}}, {'WeaponHeavy': {}}, {'WeaponPistol': {}}, {'WeaponSMG': {}}, {'WeaponRifle': {}}, {'WeaponC4': {}}, {'WeaponShotgun': {}}, {'Defuser': {}}, {'WeaponMolotov': {}}, {'WeaponFlashbang': {}}, {'WeaponSniper': {}}, {'WeaponHEGrenade': {}}, {'WeaponIncendiary': {}}, {'cardboard_smallbox': {}}, {'papertowel': {}}, {'potterylarge': {}}, {'plastic_tape': {}}, {'playerflesh': {}}, {'fruit': {}}, {'WeaponMagazine': {}}, {'audioblocker': {}}, {'wet_sand': {}}, {'plastic_autoCover': {}}, {'plastic_milkCrate': {}}, {'WeaponKnife': {}}, {'brass_bell_smallest_g': {}}, {'metalrailing': {}}, {'plastic_solid': {}}]

expression_completer = ['InstanceIndex()', 'var ? true : false', 'LinearScale()',' Tan( Deg2rad( variable ) )', 'InstanceCount()', 'RandomInt(0,10)', 'RandomFloat(0,10)']
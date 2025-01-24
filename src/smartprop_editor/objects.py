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
    {'PlaceInSphere': {'_class': 'CSmartPropElement_PlaceInSphere', 'm_flRandomness': None, 'm_nCountMin': 0, 'm_nCountMax': 0, 'm_flPositionRadiusInner': 0, 'm_flPositionRadiusOuter': 0, 'm_bAlignOrientation': False, 'm_Modifiers': [], 'm_SelectionCriteria': []}},
    {'PlaceMultiple': {'_class': 'CSmartPropElement_PlaceMultiple', 'm_nCount': None, 'm_Modifiers': [], 'm_SelectionCriteria': []}},
    {'PlaceOnPath': {'_class': 'CSmartPropElement_PlaceOnPath', 'm_PathName': 'path', 'm_vPathOffset': None, 'm_flOffsetAlongPath': None, 'm_PathSpace': None, 'm_Modifiers': [], 'm_SelectionCriteria': []}},
    {'FitOnLine': {'_class': 'CSmartPropElement_FitOnLine', 'm_vStart': None, 'm_vEnd': None, 'm_PointSpace': None, 'm_bOrientAlongLine': None, 'm_vUpDirection': None, 'm_Modifiers': [], 'm_SelectionCriteria': []}},
    {'PickOne': {'_class': 'CSmartPropElement_PickOne', 'm_SelectionMode': 'RANDOM', 'm_vHandleOffset': None, 'm_HandleShape': None, 'm_Modifiers': [], 'm_SelectionCriteria': []}},
    {'Model': {'_class': 'CSmartPropElement_Model', 'm_sModelName': '', 'm_vModelScale': None, 'm_MaterialGroupName': '', 'm_Modifiers': [], 'm_SelectionCriteria': []}},
    {'BendDeformer': {'_class': 'CSmartPropElement_BendDeformer', 'm_Modifiers': [], 'm_SelectionCriteria': []}}
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
    {'RandomOffset': {'_class': "CSmartPropOperation_RandomOffset", "m_vRandomPositionMin": {"m_Components":[0,0,0]}, "m_vRandomPositionMax": {"m_Components":[0,0,0]}}},
    {'RandomScale': {'_class': "CSmartPropOperation_RandomScale", "m_flRandomScaleMin": 0, "m_flRandomScaleMax": 0}},
    {'RandomRotation': {'_class': "CSmartPropOperation_RandomRotation", "m_vRandomRotationMin": {"m_Components":[0,0,0]}, "m_vRandomRotationMax": {"m_Components":[0,0,0]}}},
    {'CreateSizer': {'_class': "CSmartPropOperation_CreateSizer"}},
    {'CreateRotator': {'_class': "CSmartPropOperation_CreateRotator"}},
    {'CreateLocator': {'_class': "CSmartPropOperation_CreateLocator"}},
    {'TraceInDirection': {'_class': "CSmartPropOperation_TraceInDirection", 'm_DirectionSpace': 'WORLD', 'm_flSurfaceUpInfluence': 1, 'm_nNoHitResult': 'NOTHING', 'm_flOriginOffset': -500, 'm_flTraceLength': 500}},
    # {'SetVariableBool': {'_class': 'CSmartPropOperation_SetVariableBool', 'm_VariableName': None, 'm_VariableValue': None}},
    {'SaveState': {'_class': 'CSmartPropOperation_SaveState', 'm_StateName': 'State'}},
    # {'SetVariableFloat': {'_class': 'CSmartPropOperation_SetVariableFloat', 'm_VariableName': None, 'm_VariableValue': None}},
    {'SetVariable': {'_class': 'CSmartPropOperation_SetVariable', 'm_VariableValue': {'m_TargetName': None, 'm_DataType': None, 'm_Value':None}},}
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
    {"IsValid": {'_class': 'CSmartPropSelectionCriteria_IsValid'}},
    {"LinearLength": {'_class': 'CSmartPropSelectionCriteria_LinearLength', 'm_flLength': 0, 'm_bAllowScale': False, 'm_flMinLength': 0, 'm_flMaxLength': 0}},
    {"PathPosition": {'_class': 'CSmartPropSelectionCriteria_PathPosition', 'm_PlaceAtPositions': 'ALL', 'm_nPlaceEveryNthPosition': 0, 'm_nNthPositionIndexOffset': 0, 'm_bAllowAtStart': False, 'm_bAllowAtEnd': False}},
]

surfaces_list = [{'default': {}}, {'solidmetal': {}}, {'metal': {}}, {'metal_barrelSoundOverride': {}}, {'metal_vehicleSoundOverride': {}}, {'metal_survivalCase': {}}, {'metal_survivalCase_unpunchable': {}}, {'metaldogtags': {}}, {'metalgrate': {}}, {'Metal_Box': {}}, {'metal_bouncy': {}}, {'slipperymetal': {}}, {'grate': {}}, {'metalvent': {}}, {'metalpanel': {}}, {'dirt': {}}, {'mud': {}}, {'slipperyslime': {}}, {'grass': {}}, {'slowgrass': {}}, {'sugarcane': {}}, {'tile': {}}, {'tile_survivalCase': {}}, {'tile_survivalCase_GIB': {}}, {'Wood': {}}, {'Wood_lowdensity': {}}, {'Wood_Box': {}}, {'Wood_Basket': {}}, {'Wood_Crate': {}}, {'Wood_Plank': {}}, {'Wood_Solid': {}}, {'Wood_Furniture': {}}, {'Wood_Panel': {}}, {'Wood_Dense': {}}, {'water': {}}, {'wet': {}}, {'puddle': {}}, {'slime': {}}, {'quicksand': {}}, {'wade': {}}, {'ladder': {}}, {'Wood_Ladder': {}}, {'glass': {}}, {'glassfloor': {}}, {'computer': {}}, {'weapon_magazine': {}}, {'concrete': {}}, {'asphalt': {}}, {'rock': {}}, {'porcelain': {}}, {'boulder': {}}, {'brick': {}}, {'concrete_block': {}}, {'stucco': {}}, {'chainlink': {}}, {'chain': {}}, {'flesh': {}}, {'bloodyflesh': {}}, {'alienflesh': {}}, {'armorflesh': {}}, {'ice': {}}, {'carpet': {}}, {'dufflebag_survivalCase': {}}, {'upholstery': {}}, {'plaster': {}}, {'sheetrock': {}}, {'cardboard': {}}, {'plastic_barrel': {}}, {'Plastic_Box': {}}, {'plastic': {}}, {'plastic_survivalCase': {}}, {'sand': {}}, {'rubber': {}}, {'rubbertire': {}}, {'jeeptire': {}}, {'slidingrubbertire': {}}, {'brakingrubbertire': {}}, {'slidingrubbertire_front': {}}, {'slidingrubbertire_rear': {}}, {'glassbottle': {}}, {'pottery': {}}, {'clay': {}}, {'canister': {}}, {'metal_barrel': {}}, {'metal_barrel_explodingSurvival': {}}, {'floating_metal_barrel': {}}, {'plastic_barrel_buoyant': {}}, {'roller': {}}, {'popcan': {}}, {'paintcan': {}}, {'paper': {}}, {'papercup': {}}, {'ceiling_tile': {}}, {'foliage': {}}, {'slipperyslide': {}}, {'strongman_bell': {}}, {'watermelon': {}}, {'item': {}}, {'floatingstandable': {}}, {'grenade': {}}, {'weapon': {}}, {'metal_shield': {}}, {'default_silent': {}}, {'player': {}}, {'player_control_clip': {}}, {'no_decal': {}}, {'soccerball': {}}, {'gravel': {}}, {'snow': {}}, {'metalvehicle': {}}, {'brass_bell_large': {}}, {'brass_bell_medium': {}}, {'brass_bell_small': {}}, {'brass_bell_smallest': {}}, {'metal_sand_barrel': {}}, {'blockbullets': {}}, {'jalopytire': {}}, {'slidingrubbertire_jalopyfront': {}}, {'slidingrubbertire_jalopyrear': {}}, {'jalopy': {}}, {'Balloon': {}}, {'metal_ventslat': {}}, {'metal_sheetmetal': {}}, {'plasticbottle': {}}, {'concrete_polished': {}}, {'plastic_dumpster': {}}, {'metal_dumpster': {}}, {'Cloth': {}}, {'plaster_drywall': {}}, {'Wood_Tree': {}}, {'beans': {}}, {'WeaponHeavy': {}}, {'WeaponPistol': {}}, {'WeaponSMG': {}}, {'WeaponRifle': {}}, {'WeaponC4': {}}, {'WeaponShotgun': {}}, {'Defuser': {}}, {'WeaponMolotov': {}}, {'WeaponFlashbang': {}}, {'WeaponSniper': {}}, {'WeaponHEGrenade': {}}, {'WeaponIncendiary': {}}, {'cardboard_smallbox': {}}, {'papertowel': {}}, {'potterylarge': {}}, {'plastic_tape': {}}, {'playerflesh': {}}, {'fruit': {}}, {'WeaponMagazine': {}}, {'audioblocker': {}}, {'wet_sand': {}}, {'plastic_autoCover': {}}, {'plastic_milkCrate': {}}, {'WeaponKnife': {}}, {'brass_bell_smallest_g': {}}, {'metalrailing': {}}, {'plastic_solid': {}}]
# surfaces_list = ['default', 'solidmetal', 'metal', 'metal_barrelSoundOverride', 'metal_vehicleSoundOverride', 'metal_survivalCase', 'metal_survivalCase_unpunchable', 'metaldogtags', 'metalgrate', 'Metal_Box', 'metal_bouncy', 'slipperymetal', 'grate', 'metalvent', 'metalpanel', 'dirt', 'mud', 'slipperyslime', 'grass', 'slowgrass', 'sugarcane', 'tile', 'tile_survivalCase', 'tile_survivalCase_GIB', 'Wood', 'Wood_lowdensity', 'Wood_Box', 'Wood_Basket', 'Wood_Crate', 'Wood_Plank', 'Wood_Solid', 'Wood_Furniture', 'Wood_Panel', 'Wood_Dense', 'water', 'wet', 'puddle', 'slime', 'quicksand', 'wade', 'ladder', 'Wood_Ladder', 'glass', 'glassfloor', 'computer', 'weapon_magazine', 'concrete', 'asphalt', 'rock', 'porcelain', 'boulder', 'brick', 'concrete_block', 'stucco', 'chainlink', 'chain', 'flesh', 'bloodyflesh', 'alienflesh', 'armorflesh', 'ice', 'carpet', 'dufflebag_survivalCase', 'upholstery', 'plaster', 'sheetrock', 'cardboard', 'plastic_barrel', 'Plastic_Box', 'plastic', 'plastic_survivalCase', 'sand', 'rubber', 'rubbertire', 'jeeptire', 'slidingrubbertire', 'brakingrubbertire', 'slidingrubbertire_front', 'slidingrubbertire_rear', 'glassbottle', 'pottery', 'clay', 'canister', 'metal_barrel', 'metal_barrel_explodingSurvival', 'floating_metal_barrel', 'plastic_barrel_buoyant', 'roller', 'popcan', 'paintcan', 'paper', 'papercup', 'ceiling_tile', 'foliage', 'slipperyslide', 'strongman_bell', 'watermelon', 'item', 'floatingstandable', 'grenade', 'weapon', 'metal_shield', 'default_silent', 'player', 'player_control_clip', 'no_decal', 'soccerball', 'gravel', 'snow', 'metalvehicle', 'brass_bell_large', 'brass_bell_medium', 'brass_bell_small', 'brass_bell_smallest', 'metal_sand_barrel', 'blockbullets', 'jalopytire', 'slidingrubbertire_jalopyfront', 'slidingrubbertire_jalopyrear', 'jalopy', 'Balloon', 'metal_ventslat', 'metal_sheetmetal', 'plasticbottle', 'concrete_polished', 'plastic_dumpster', 'metal_dumpster', 'Cloth', 'plaster_drywall', 'Wood_Tree', 'beans', 'WeaponHeavy', 'WeaponPistol', 'WeaponSMG', 'WeaponRifle', 'WeaponC4', 'WeaponShotgun', 'Defuser', 'WeaponMolotov', 'WeaponFlashbang', 'WeaponSniper', 'WeaponHEGrenade', 'WeaponIncendiary', 'cardboard_smallbox', 'papertowel', 'potterylarge', 'plastic_tape', 'playerflesh', 'fruit', 'WeaponMagazine', 'audioblocker', 'wet_sand', 'plastic_autoCover', 'plastic_milkCrate', 'WeaponKnife', 'brass_bell_smallest_g', 'metalrailing', 'plastic_solid']
expression_completer = ['InstanceIndex()', 'var ? true : false', 'LinearScale()',' Tan( Deg2rad( variable ) )', 'InstanceCount()']
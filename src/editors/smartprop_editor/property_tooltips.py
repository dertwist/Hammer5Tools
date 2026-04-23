property_tooltips = {
    # Base Element Properties (CSmartPropElement)
    "m_bEnabled": "Is this element enabled? If not enabled, this element will not be evaluated and will have no effect on the result.",
    "m_sLabel": "Optional text that will appear in the outliner to help organize Smart Prop elements and communicate their purpose to other users.",
    "m_nElementID": "Unique monotonic integer identifier for editor state. Suppressed from standard properties.",
    "m_SelectionCriteria": "Collection of logical conditions and filters that must be met for the element to be processed.",
    "m_Modifiers": "Array of state alterations (transforms, orienting, etc.) applied to the element.",

    # Root and Children (CSmartPropRoot, CSmartPropElement_Group)
    "m_Choices": "A collection of user-facing permutation options. Defines configuration parameters in Hammer.",
    "m_Children": "List of child elements which will appear if this element appears.",

    # Model Element (CSmartPropElement_Model)
    "m_sModelName": "Name of the model resource (.vmdl) to place.",
    "m_MaterialGroupName": "Specifies the name of the material group (skin) to use when displaying the specified model.",
    "m_bDetailObject": "If enabled, the model will be rendered as a detail object. This is faster for placing many small objects and includes fade-out functionality, but may have different lighting characteristics. Detail object models support only uniform scale and will use the largest component of the scale value.",
    "m_vModelScale": "Scale factor (may be non-uniform) to be applied directly to the model (in the model's local space).",
    "m_flUniformModelScale": "Uniform scale to be applied to the model. Certain properties (like being a detail object) mean only uniform scale may be applied.",
    "m_nLodLevel": "Selects the model LOD (Level of Detail) level. The default 'Auto LOD' (-1) means the LOD will be picked based on the size of the model on screen. If a specific level is selected, that level will always be used regardless of screen size.",
    "m_SurfacePropertyOverride": "If non-empty, specifies the name of a surface property to use for all physics shapes of the specified model, overriding any surface properties specified within the model itself.",
    "m_nDetailObjectFadeLevel": "Controls the size at which a model marked as a detail object will fade out.",
    "m_bCastShadows": "Determines if the model should cast shadows.",
    "m_bRigidDeformation": "If enabled, only the transform of the model will be modified by any active deformer; the vertices of the model will not be changed by the deformer.",
    "m_bDisableDynamicDeformable": "If checked, this model will not deform in-game when the smart prop is placed inside a dynamic deformable entity (such as a func_deformable_brush).",

    # Place Multiple (CSmartPropElement_PlaceMultiple)
    "m_nCount": "Number of instances of this object and its children to be placed.",
    "m_Expression": "Stop placing copies of the children when this expression evaluates to true.",

    # Pick One (CSmartPropElement_PickOne)
    "m_SelectionMode": "Specifies how the initial selection of a choice should be handled.",
    "m_SpecificChildIndex": "Specifies the index of the child to pick.",
    "m_OutputChoiceVariableName": "If a variable name is specified, sets the value of that variable to the index of the selected choice.",
    "m_bConfigurable": "Should a control to select the specific choice be shown when this prop is placed in Hammer.",
    "m_vHandleOffset": "Specifies an offset in the local space of the element to apply to the configuration handle.",
    "m_HandleColor": "Color to use to display the configuration handle.",
    "m_HandleSize": "Size of the configuration handle.",
    "m_HandleShape": "Shape of the configuration handle to display.",

    # Place In Sphere (CSmartPropElement_PlaceInSphere)
    "m_PlacementMode": "Specifies how the positions are computed based on the radius.",
    "m_DistributionMode": "Specifies the method to be used to distribute the instances.",
    "m_flRandomness": "A 0 to 1 value indicating the amount of random offset that should be applied to the regularly spaced positions.",
    "m_vPlaneUpDirection": "Vector up direction of the plane of the circle. This is defined in the local space of the current element.",
    "m_nCountMin": "The minimum number of instances of this object and its children to be placed.",
    "m_nCountMax": "The maximum number of instances of this object and its children to be placed.",
    "m_flPositionRadiusInner": "The inner radius from the placement position where the model can appear.",
    "m_flPositionRadiusOuter": "The outer radius from the placement position where the model can appear.",
    "m_bAlignOrientation": "Determines whether to align the initial orientation of each placed object based on its position on the sphere or circle.",
    "m_vAlignDirection": "Vector in the local space of the child element to be aligned with the sphere or circle.",

    # Layout 2D Grid (CSmartPropElement_Layout2DGrid)
    "m_flWidth": "Overall grid dimension along X axis.",
    "m_flLength": "Overall grid dimension along Y axis.",
    "m_bVerticalLength": "Layout length vertically (Along Z axis instead of Y).",
    "m_GridArrangement": "ARRAY: Grid is a specific number of grid divisions. FILL: The boundary is filled with as many as will fit at the specified cell spacing.",
    "m_GridOriginMode": "Specifies the overall grid origin location. Corner origin grids default to quadrant I, but may be expressed in others using negative values for Width and/or Length.",
    "m_nCountW": "Grid segments along width axis.",
    "m_nCountL": "Grid segments along Length axis.",
    "m_flSpacingWidth": "Minimum Width of filled grid cells.",
    "m_flSpacingLength": "Minimum Length of filled grid cells.",
    "m_bAlternateShift": "Shifts every other cell row and/or column.",
    "m_flAlternateShiftWidth": "Vary cell shift in X.",
    "m_flAlternateShiftLength": "Vary cell shift in Y.",

    # Fit On Line (CSmartPropElement_FitOnLine)
    "m_vStart": "Specifies the starting point of the line within the designated coordinate space.",
    "m_vEnd": "Specifies the ending point of the line within the designated coordinate space.",
    "m_PointSpace": "Defines the coordinate space used for specifying the end point values.",
    "m_bOrientAlongLine": "A boolean attribute determining if child elements should be oriented based on the line. If enabled, child elements are oriented so that their +x axis points along the line toward the end point.",
    "m_vUpDirection": "An up vector used to calculate the rotation of every element around the line.",
    "m_UpDirectionSpace": "Defines the coordinate space in which the up direction vector is defined.",
    "m_bPrioritizeUp": "A boolean flag used when the up direction is not orthogonal to the line direction. Normally, the up vector is adjusted to be orthogonal; however, if this is set to true, the up direction is maintained and the forward direction is adjusted instead.",
    "m_nScaleMode": "Determines how scaling is applied to each selected element to ensure they fit the line.",
    "m_nPickMode": "Specifies the method for applying scale to selected elements to fit them to the line.",

    # Bend Deformer (CSmartPropElement_BendDeformer)
    "m_bDeformationEnabled": "Determines if the deformation should be applied. If disabled, the children will still be placed but will not be deformed, effectively making the element behave like a group.",
    "m_vOrigin": "A local offset to apply to the base volume of the deformer that does not apply to its children.",
    "m_vAngles": "A local rotation applied to the base volume of the deformer that does not apply to its children. This can be used to alter the direction of the deformation.",
    "m_vSize": "The size of the base volume to be deformed.",
    "m_flBendAngle": "The bend amount to apply, specified in degrees. The bend occurs along the local x-axis and bends around the local z-axis.",
    "m_flBendPoint": "A value between 0 and 1 specifying the location along the local x-axis where the bend will occur.",
    "m_flBendRadius": "The radius of the bend. If set to 0, the radius is computed automatically to preserve the length of the inner edge of the x-axis. If a non-zero value is specified, the inner edge maintains this radius, but its length will change.",

    # Place On Path (CSmartPropElement_PlaceOnPath)
    "m_PathName": "Specifies the target path name that will show up in the properties.",
    "m_flSpacing": "Interval spacing metric determining distance between placement along the path.",
    "m_flOffsetAlongPath": "Determines the initial offset starting distance along the path.",
    "m_vPathOffset": "Dictates a 2D vector offset mapped perpendicularly from the center trajectory of the path.",
    "m_PathSpace": "Defines the coordinate space context the path vectors operate within.",
    "m_bUseFixedUpDirection": "Toggles the use of a predefined stationary up-direction vector.",
    "m_bUseProjectedDistance": "Alters calculation logic to use projected topography distance.",
    "m_vUpDirection": "Vector specifying the up direction for alignment.",
    "m_UpDirectionSpace": "Defines the coordinate space for the up direction vector.",
    
    # Operations
    "m_Material": "Target material file binding for tinting operations (.vmat).",
    "m_OutputVariable": "Maps operation results explicitly to a configured output Float variable.",
    "m_LocatorName": "Unique identifier string for the locator.",
    "m_flDisplayScale": "Visual bounding size for the generated locator model.",
    "m_StateName": "The name of the state to save or restore. This allows for returning to a previously saved state at a later point in the evaluation.",
}

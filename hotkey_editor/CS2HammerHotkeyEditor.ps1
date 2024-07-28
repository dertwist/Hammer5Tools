function New-InputBinding_t() {
    param (
        [Parameter(Mandatory = $true)]
        [string]$m_Context,
        [Parameter(Mandatory = $true)]
        [string]$m_Command,
        [Parameter(Mandatory = $true)]
        [string]$m_Input
    )

    return [PSCustomObject]@{
        m_Context = $m_Context
        m_Command = $m_Command
        m_Input   = $m_Input
        type      = "InputBinding_t"
    }
}

function New-InputMacro_t() {
    param (
        [Parameter(Mandatory = $true)]
        [string]$m_Name,
        [Parameter(Mandatory = $true)]
        [string]$m_Input
    )

    return [PSCustomObject]@{
        m_Name  = $m_Name
        m_Input = $m_Input
        type    = "InputMacro_t"
    }
}

function ParseLine() {
    <#
    .SYNOPSIS
    Parses a line that would be inside the KV3. Then returns the relevant InputBinding_t or InputMacro_t object
    #>
    param (
        [Parameter(Mandatory = $true)]
        [string]$line
    )
    [regex]$pattern = '"(.*?)"'
    
    $lineMatches = $pattern.Matches($line)

    if ($lineMatches.count -eq 3) {
        #m_bindings
        return New-InputBinding_t $lineMatches[0].Value.replace('"', '') $lineMatches[1].Value.replace('"', '') $lineMatches[2].Value.replace('"', '')
    }
    elseif ($lineMatches.count -eq 2) {
        #m_InputMacros
        return New-InputMacro_t $lineMatches[0].Value.replace('"', '') $lineMatches[1].Value.replace('"', '')
    }
}
function Convertfrom-KV3() {
    <#
    .SYNOPSIS
    Hardly a real KV3 Parser. This literally only parses the hotkey KV3 files.
    #>
    param (
        [Parameter(Mandatory = $true)]
        [Object[]]$kv3Content
    )

    $m_InputMacros = @()
    $m_Bindings = @()
    
    foreach ($line in $kv3Content) {

        $line = $line.Trim()
        if($line.StartsWith("//")) {continue}

        if ($null -eq $line -or $line.Length -eq 0) { continue }

        $parsed = ParseLine $line

        if ($parsed.type -eq "InputBinding_t") {
            $m_Bindings += $parsed
        }
        elseif ($parsed.type -eq "InputMacro_t") {
            $m_InputMacros += $parsed
        }
    }

    return @{
        InputBindingList_t = @{
            m_InputMacros = $m_InputMacros
            m_Bindings    = $m_Bindings
        }
    }
}

function ConvertTo-KV3() {
    <#
    .SYNOPSIS
    Also not a real KV3 converted. Only exports to the hotkey KV3 format
    #>
    param (
        [Parameter(Mandatory = $true)]
        [Hashtable]$kv3
    )
    $output = "<!-- schema text {2CC83121-F14F-4A36-ABB8-62F4C2799689} generic {198980D8-3A93-4919-B4C6-DD1FB07A3A4B} -->`nInputBindingList_t`n{`n"

    #Handle the m_InputMacros
    if ($kv3.InputBindingList_t.m_InputMacros.count -gt 0) {
        $output += "`tm_InputMacros =`n`t[`n"

        foreach ($i in $kv3.InputBindingList_t.m_InputMacros) {
            $output += "`t`tInputMacro_t { m_Name = `"$($i.m_Name)`"    m_Input = `"$($i.m_Input)`"},`n"
        }
        $output += "`t]`n"
    }

    $output += "`tm_Bindings =`n`t[`n"
    foreach ($i in $kv3.InputBindingList_t.m_Bindings) {

        if($null -eq $i.m_Input -or $i.m_Input -eq ""){continue} #Skip empty binds

        $output += "`t`tInputBinding_t { m_Context = `"$($i.m_Context)`"  m_Command = `"$($i.m_Command)`"    m_Input = `"$($i.m_Input)`"},`n"
    }
    $output += "`t]`n}"

    return $output
}

Function Merge-UnboundKeys()
{
    <#
    .SYNOPSIS
    After reading in the hotkeys from the txt file, this will merge all known unbound actions
    #>

    #Already merged, don't waste time
    if($Global:mergeCompleted){return}

    $merged = @()
    $hammer5AllCommands = ConvertFrom-Csv @'
"m_Context","m_Command"
"ToolSelection","BakeTransform"
"ToolSelection","MergeMeshesByEdge"
"ToolSelection","ReplaceSelectionWithInstance"
"ToolSelection","RandomizeConfiguration"
"ToolSelection","BakeTransform"
"ToolSelection","BakeTransform"

"Camera","MoveCameraForward3D"
"Camera","MoveCameraBackward3D"
"Camera","MoveCameraLeft3D"
"Camera","MoveCameraRight3D"
"Camera","MoveCameraUp3D"
"Camera","MoveCameraDown3D"
"Camera","PitchCameraUp"
"Camera","PitchCameraDown"
"Camera","YawCameraLeft"
"Camera","YawCameraRight"
"Camera","IncreaseMoveSpeed"
"Camera","DecreaseMoveSpeed"
"Camera","ResetMoveSpeed"
"Camera","ZoomCameraIn"
"Camera","ZoomCameraOug"
"Camera","ZoomAlCamerasIn"
"Camera","ZoomAllCamerasOut"
"Camera","MouseControlCamera"
"Camera","MouseControlCamera3D"
"Camera","MouseControlCamera2D"
"Camera","MouseControlCamera3D_Toggle"
"Camera","HorizontalStrafeCamera"
"Camera","VerticalStrafeCamera"
"Camera","ToggleLockCameraHeight"
"Camera","ZoomForwardBack3D"
"Camera","ZoomForwardBack2D"
"Camera","PanCamera3D"
"Camera","RotateAboutTarget3D"
"Camera","MouseLook3D"
"Camera","SnapCameraToSelection"
"Camera","CameraLookAtSelection"

"MapView","ModelTraceLift"
"MapView","RefreshRaytracedScene"
"MapView","WriteRaytracedImage"

"PaneContainer","3D_Wireframe"
"PaneContainer","3D_HighContrastLighting"
"PaneContainer","3D_DirectLightingOnly"
"PaneContainer","3D_IndirectLightingOnly"
"PaneContainer","3D_DirectPlusAmbientLighting"
"PaneContainer","3D_TagVis"
"PaneContainer","EngineView"
"PaneContainer","AssetView"
"PaneContainer","ObjectProperties"
"PaneContainer","EntityIO"
"PaneContainer","TerrainGraph"
"PaneContainer","RTX_Visualization"
"PaneContainer","ToggleLightingOnly"
"PaneContainer","ToggleParticles"
"PaneContainer","ToggleFog"
"PaneContainer","ToggleSkybox"
"PaneContainer","ToggleReflections"
"PaneContainer","ToggleSSAO"
"PaneContainer","ToggleWorklight"
"PaneContainer","ToggleFOW"
"PaneContainer","ToggleWaterFlow"
"PaneContainer","ToggleFogFlow"
"PaneContainer","ToggleResolutionGate"
"PaneContainer","ToggleToggleGridOfThirds"
"PaneContainer","ToggleHighlightDeprecated"
"PaneContainer","CreateFloatingCopy"

"HammerEditorSession","PasteKeys"
"HammerEditorSession","ConvertObjectsToModel"
"HammerEditorSession","ConvertObjectsToSmartProp"
"HammerEditorSession","ConvertToStaticCables"
"HammerEditorSession","ConcertCablesToMesh"
"HammerEditorSession","SeperatePathSegments"
"HammerEditorSession","SeperatePathNodes"
"HammerEditorSession","MergePaths"
"HammerEditorSession","ReversePaths"
"HammerEditorSession","ExportParticleSnapShot"
"HammerEditorSession","SendSelectedToModo"
"HammerEditorSession","InsertNewImagePlane"
"HammerEditorSession","RemovePaintData"
"HammerEditorSession","RemovePoseData"
"HammerEditorSession","AttachObjectToView"
"HammerEditorSession","DetachObjectFromView"
"HammerEditorSession","SetHierarchyFromCurrentTransform"
"HammerEditorSession","SetTransformFromHierarchy"
"HammerEditorSession","ToggleNaveAlwaysVisible"
"HammerEditorSession","ToggleLightingPreviewLock"
"HammerEditorSession","ToggleCordonsVisible"
"HammerEditorSession","SetManipulationModeTranslate"
"HammerEditorSession","SetManipulationModeRotate"
"HammerEditorSession","SetManipulationModeScale"
"HammerEditorSession","SetManipulationModePivot"
"HammerEditorSession","ToolPolygon"
"HammerEditorSession","ToolAssetSpray"
"HammerEditorSession","ToolStaticOVerlay"
"HammerEditorSession","ToolTextureProjection"
"HammerEditorSession","HideUnselected"
"HammerEditorSession","ToggleEntityNames"
"HammerEditorSession","ToggleShowLightOverlap"
"HammerEditorSession","AddNewKey"
"HammerEditorSession","UpdateToCurrentVersion"
"HammerEditorSession","ConvertToStaticOVerlay"
"HammerEditorSession","RemapBlendData"
"HammerEditorSession","ToggleShow3DGrid"
"HammerEditorSession","ToggleShow2DGrid"
"HammerEditorSession","GotoCoords"
"HammerEditorSession","TogglePrefabVisibility"
"HammerEditorSession","TogglePrefabWireframColor"
"HammerEditorSession","ImportPrefab"
"HammerEditorSession","CollapseAllPrefabs"
"HammerEditorSession","CollapseSelectedPrefabs"
"HammerEditorSession","CreatePrefabFromSelection"
"HammerEditorSession","CreatePrefabFromSelectionCentered"
"HammerEditorSession","ConvertInstanceToPrefab"
"HammerEditorSession","ReplaceInstanceWithPrefab"
"HammerEditorSession","EditSelectedPrefab"
"HammerEditorSession","OpenPrefabs"
"HammerEditorSession","ReloadPrefabs"
"HammerEditorSession","SavePrefabs"
"HammerEditorSession","AddPrefabsToVersionControl"
"HammerEditorSession","CheckoutPrefabs"
"HammerEditorSession","CreateWorldLayerFromSelection"
"HammerEditorSession","CreateTestNode"
"HammerEditorSession","CreateIsoSurface"
"HammerEditorSession","BakeAllLighting"
"HammerEditorSession","BakeAllCubemaps"
"HammerEditorSession","ClearAllLighting"
"HammerEditorSession","BakeLightingOnSelection"
"HammerEditorSession","BakeCubemapsOnSelection"
"HammerEditorSession","ClearLightingOnSelection"
"HammerEditorSession","ToggleBakedLightingUseRenderFarm"
"HammerEditorSession","CleanupUnusedBakeResources"
"HammerEditorSession","WriteCustomCubemap"
"HammerEditorSession","EstimateLightingFromHDRSkybox"
"HammerEditorSession","ConvertToBarnDoorLights"
"HammerEditorSession","AddEdgeFadeToEnvProbes"
"HammerEditorSession","ShowRemapVertexDataDialog"
"HammerEditorSession","ShowScreenshotDialog"
"HammerEditorSession","AlignCameraToSelection"
"HammerEditorSession","AlignSelectionToCamera"
"HammerEditorSession","LoadMapInEngine"
"HammerEditorSession","ReloadMapInEngine"
"HammerEditorSession","LoadVisClusters"
"HammerEditorSession","DeleteVisClusters"
"HammerEditorSession","OpenAssetPaneDockWidget"
"HammerEditorSession","OpenMapViewPaneDockWidget"
"HammerEditorSession","SteamAudioPreviewScene"
"HammerEditorSession","SteamAudioExportScene"
"HammerEditorSession","SteamAudioCreateProbeBox"
"HammerEditorSession","SteamAudioGenerateProbes"
"HammerEditorSession","SteamAudioBakeReverb"
"HammerEditorSession","SteamAudioBakePaths"
"HammerEditorSession","ToggleSnapRotation"

"HammerApp","FileClose"
"HammerApp","ClearRecentFiles"
"HammerApp","VersionControlAdd"
"HammerApp","VersionControlCheckIn"
"HammerApp","VersionControlCheckOut"
"HammerApp","VersionControlCheckInAll"
"HammerApp","VersionControlStatus"
"HammerApp","ActivateNextEditorSession"
"HammerApp","ActivatePreviousEditorSession"
"HammerApp","ReloadKeyBindings"
"HammerApp","ResetLayout"
"HammerApp","ToggleDisableUndoRedo"
"HammerApp","ToggleTransformSpace"
"HammerApp","ToggleTextureLock"
"HammerApp","ToggleTextureLockComponent"
"HammerApp","ToggleSelectIntersecting"
"HammerApp","ToggleDisplacementMapping"
"HammerApp","ToggleFog"
"HammerApp","EditReplace"
"HammerApp","CheckMapForProblems"
"HammerApp","MapInformation"
"HammerApp","EntityGallery"
"HammerApp","NewMapFromTemplate"
"HammerApp","SaveAsText"
"HammerApp","ReloadFGDFiles"
"HammerApp","ImportFile"
"HammerApp","ExportFile"
"HammerApp","ExportSelected"
"HammerApp","ToggleShowVisContributorsOnly"
"HammerApp","ShowOutputsPopup"
"HammerApp","ShowInputsPopup"
"HammerApp","ShowMapRelaysPopup"
"HammerApp","PauseGame"
"HammerApp","UnpauseGame"
"HammerApp","ToggleModelAnimation"
"HammerApp","ToggleForceLightsOn"
"HammerApp","CycleViewDistance"
"HammerApp","ToggleShowGrass"
"HammerApp","ToggleShowParticles"
"HammerApp","ToggleShowLPVSampleGrid"
"HammerApp","SetEditUVSet_All"
"HammerApp","SetEditUVSet_UV1"
"HammerApp","SetEditUVSet_UV2"

"GlobalHotkeys","FocusChainDebug_More"
"GlobalHotkeys","FocusChainDebug_Less"
"GlobalHotkeys","FocusChainDebug_Forward"
"GlobalHotkeys","FocusChainDebug_Back"
"GlobalHotkeys","FocusChainDebug_Toggle"






"HammerApp","FileOpen"
"HammerApp","FileSave"
"HammerApp","FileSaveAs"
"HammerApp","SaveActivePrefab"
"HammerApp","FileReload"
"HammerApp","FileNew"
"HammerApp","NextSession"
"HammerApp","PreviousSession"
"HammerApp","BuildMap"
"HammerApp","ToggleShowHelpers"
"HammerApp","ToggleTextureLockScale"
"HammerApp","TogglePropertiesPopup"
"HammerApp","TogglePropertiesPopup"
"HammerApp","ShowMapVariablesPopup"
"HammerApp","ShowMapPropertiesPopup"
"HammerApp","ToggleShowGameObjectsOnly"
"HammerApp","ToggleSelectThrough"
"HammerApp","ViewDistanceNext"
"HammerApp","ViewDistancePrev"
"HammerApp","ShowMapManifestWidget"
"HammerApp","ToggleGridNav"
"HammerApp","ToggleToolsMaterials"
"HammerApp","ToggleSelectionOverlay"
"HammerApp","ToggleInstanceOverlay"
"HammerApp","ToggleMeshSubdivision"
"HammerApp","ToggleMeshTiles3D"
"HammerApp","ToggleMeshTiles2D"
"HammerApp","ToggleSelectBackfacing"
"HammerApp","ToggleFullscreenLayout"
"HammerApp","ShowEntityReport"
"HammerApp","CycleEditUVSet"
"SessionCycleWidget","KeepActive"
"SessionCycleWidget","NextSession"
"SessionCycleWidget","PreviousSession"
"MapManifestWidget","RefreshView"
"HammerObjectPropertyPopup","HidePropertyWindow"
"HammerObjectPropertyPopup","HidePropertyWindow"
"HammerObjectPropertyPopup","HidePropertyWindow"
"MapView","PitchCameraUp"
"MapView","PitchCameraDown"
"MapView","YawCameraLeft"
"MapView","YawCameraRight"
"MapView","ShowContextMenu"
"MapView","MaterialTraceLift"
"MapView","MaterialTraceLift"
"MapView","ActivateObject"
"MapView","SnapCameraToTargetUnderMouse"
"MapView","DetachViewFromObject"
"PaneContainer","2D_Top"
"PaneContainer","2D_Front"
"PaneContainer","2D_Side"
"PaneContainer","3D_FullBrightNoLighting"
"PaneContainer","3D_AllLighting"
"PaneContainer","Rtx_Path_Tracing"
"PaneContainer","3D_ToolsVis"
"PaneContainer","ToggleWireframeOverlay"
"PaneContainer","ToggleShadows"
"HammerEditorSession","SelectionModeVertices"
"HammerEditorSession","SelectionModeEdges"
"HammerEditorSession","SelectionModeFaces"
"HammerEditorSession","SelectionModeMeshes"
"HammerEditorSession","SelectionModeObjects"
"HammerEditorSession","SelectionModeGroups"
"HammerEditorSession","SelectionModeNav"
"HammerEditorSession","CycleSelectionModes"
"HammerEditorSession","CycleSelectionTopLevelModes"
"HammerEditorSession","ClearSelection"
"HammerEditorSession","SelectAll"
"HammerEditorSession","InvertSelection"
"HammerEditorSession","DeleteSelection"
"HammerEditorSession","Cut"
"HammerEditorSession","Copy"
"HammerEditorSession","Paste"
"HammerEditorSession","PasteSpecial"
"HammerEditorSession","GroupSelection"
"HammerEditorSession","UngroupSelection"
"HammerEditorSession","UngroupSelectionRecursive"
"HammerEditorSession","ReparentSelection"
"HammerEditorSession","UnparentSelection"
"HammerEditorSession","CreateInstanceFromSelection"
"HammerEditorSession","BakeSelectedInstances"
"HammerEditorSession","MovePropsToWorld"
"HammerEditorSession","CreateTile"
"HammerEditorSession","CreateTileMesh"
"HammerEditorSession","MirrorHorizontal"
"HammerEditorSession","MirrorVertical"
"HammerEditorSession","SelectSimilar"
"HammerEditorSession","Undo"
"HammerEditorSession","Undo"
"HammerEditorSession","Redo"
"HammerEditorSession","Redo"
"HammerEditorSession","Redo"
"HammerEditorSession","FindEntities"
"HammerEditorSession","TieToEntity"
"HammerEditorSession","MoveToWorld"
"HammerEditorSession","SnapToGrid"
"HammerEditorSession","SnapToGridIndividually"
"HammerEditorSession","QuickHideSelection"
"HammerEditorSession","QuickHideUnselected"
"HammerEditorSession","ShowQuickHide"
"HammerEditorSession","SelectionSetFromQuickHide"
"HammerEditorSession","ToggleSnapping"
"HammerEditorSession","ToggleSnapToVertices"
"HammerEditorSession","ToggleSnapToGrid"
"HammerEditorSession","MapGridLower"
"HammerEditorSession","MapGridHigher"
"HammerEditorSession","DecreaseRotationSnapping"
"HammerEditorSession","IncreaseRotationSnapping"
"HammerEditorSession","CenterViews"
"HammerEditorSession","Center2DViews"
"HammerEditorSession","FrameAllViews"
"HammerEditorSession","ToggleSingleView"
"HammerEditorSession","CycleViews"
"HammerEditorSession","CycleAndFrameViews"
"HammerEditorSession","ActivateViewUnderCursor"
"HammerEditorSession","ToggleNavMarkupVisibility"
"HammerEditorSession","ToggleOverlayShapes"
"HammerEditorSession","SetManipulationModeSelection"
"HammerEditorSession","ManipulationModeSelection"
"HammerEditorSession","ManipulationModeTranslate"
"HammerEditorSession","ManipulationModeRotate"
"HammerEditorSession","ManipulationModeScale"
"HammerEditorSession","ManipulationModePivot"
"HammerEditorSession","ToolPivotPicker"
"HammerEditorSession","ToolBlock"
"HammerEditorSession","ToolPhysics"
"HammerEditorSession","ToolEntity"
"HammerEditorSession","ToolDisplacement"
"HammerEditorSession","ToolClipper"
"HammerEditorSession","ToolPath"
"HammerEditorSession","ToolPaint"
"HammerEditorSession","ToolMirror"
"HammerEditorSession","ToolWorkPlane"
"HammerEditorSession","ResetWorkPlane"
"HammerEditorSession","CreateSelectionSet"
"HammerEditorSession","HideUnselected"
"HammerEditorSession","SelectionConvert"
"HammerEditorSession","SelectionConnected"
"HammerEditorSession","SelectionBoundry"
"HammerEditorSession","ToggleCordoning"
"HammerEditorSession","NewCordon"
"HammerEditorSession","RepeatCommand"
"HammerEditorSession","ExitActiveEditScope"
"HammerEditorSession","ToggleCollisionModels"
"HammerEditorSession","RestartParticleEffects"
"HammerEditorSession","UpdateAllIsoSurfaces"
"HammerEditorSession","AttachViewToObject"
"HammerEditorSession","RandomizeChoices"
"ToolPivotPicker","PlacePivot"
"ToolPivotPicker","ToggleSnapping"
"SelectionSetEditor","DeleteSelectionSet"
"SelectionSetEditor","SelectionAddModifier"
"SelectionSetEditor","SelectionRemoveModifier"
"SelectionSetEditor","RenameSelectionSet"
"MapVariablesEditor","DeleteSelected"
"ToolBlock","DragBlock"
"ToolBlock","Finish"
"ToolBlock","Finish"
"ToolBlock","Apply"
"ToolBlock","CancelCreate"
"ToolBlock","ToggleSnapping"
"ToolBlock","AlignToSurface"
"ToolPolygon","AddPoint"
"ToolPolygon","Finish"
"ToolPolygon","Finish"
"ToolPolygon","Apply"
"ToolPolygon","Apply"
"ToolPolygon","Cancel"
"ToolClipper","DragClip"
"ToolClipper","FinishClip"
"ToolClipper","FinishClip"
"ToolClipper","DoClip"
"ToolClipper","CancelClip"
"ToolClipper","ToggleCreateCaps"
"ToolClipper","ToggleSnapping"
"ToolTextureProjection","Finish"
"ToolTextureProjection","Finish"
"ToolTextureProjection","Finish"
"ToolTextureProjection","Cancel"
"ToolTextureProjection","ToggleSnapping"
"ToolTextureProjection","Translate"
"ToolTextureProjection","Rotate"
"ToolMirror","DragPlane"
"ToolMirror","Finish"
"ToolMirror","Finish"
"ToolMirror","Apply"
"ToolMirror","Cancel"
"ToolMirror","ToggleSnapping"
"ToolEntity","DragCreatePoint"
"ToolEntity","TraceAndCreate"
"ToolEntity","Create"
"ToolEntity","Create"
"ToolEntity","CancelCreate"
"ToolEntity","ToggleSnapping"
"GizmoManipulator","Drag"
"GizmoManipulator","StampClone"
"GizmoManipulator","SetBoxManipulateAboutCenter"
"GizmoManipulator","SetBoxManipulateApplyUniformScaling"
"GizmoManipulator","LockedManipulation"
"GizmoManipulator","ToggleSnapping"
"GizmoManipulator","GizmoApplyValue"
"SphereManipulator","Drag"
"AxisRotatorManipulator","Drag"
"AxisRotatorManipulator","ToggleSnapping"
"BoxManipulator","Drag"
"BoxManipulator","ToggleSnapping"
"BoxManipulator","ToggleEditEdgeFades"
"RectangleManipulator","Drag"
"RectangleManipulator","ToggleSnapping"
"PointManipulator","SelectPoint"
"PointOnLineManipulator","Drag"
"StaticPointManipulator","Click"
"StaticPointManipulator","MouseWheelUp"
"StaticPointManipulator","MouseWheelDown"
"BarnLightManipulator","Drag"
"BarnLightManipulator","ToggleSnapping"
"BarnLightManipulator","ResizeNear"
"BarnLightManipulator","ConstrainProportions"
"ToolFaceSelection","ShrinkSelection"
"ToolFaceSelection","ShrinkSelection"
"ToolFaceSelection","GrowSelection"
"ToolFaceSelection","GrowSelection"
"ToolFaceSelection","AddToSelection"
"ToolFaceSelection","RemoveFromSelection"
"ToolFaceSelection","RemoveFromSelectionOldest"
"ToolFaceSelection","FlipNormals"
"ToolFaceSelection","SelectLoop"
"ToolFaceSelection","CutTool"
"ToolFaceSelection","QuadSlice"
"ToolFaceSelection","JustifyCenter"
"ToolFaceSelection","JustifyLeft"
"ToolFaceSelection","JustifyRight"
"ToolFaceSelection","JustifyTop"
"ToolFaceSelection","JustifyBottom"
"ToolFaceSelection","JustifyFit"
"ToolFaceSelection","AlignWorld"
"ToolFaceSelection","AlignFace"
"ToolFaceSelection","AlignView"
"ToolFaceSelection","Select"
"ToolFaceSelection","LassoSelect"
"ToolFaceSelection","TranslateLasso"
"ToolFaceSelection","SelectionAddModifier"
"ToolFaceSelection","SelectionRemoveModifier"
"ToolFaceSelection","Extrude"
"ToolFaceSelection","SelectContiguous"
"ToolFaceSelection","SelectContiguousFiltered"
"ToolFaceSelection","WrapTexture"
"ToolFaceSelection","WrapTextureToSelection"
"ToolFaceSelection","TraceAndLiftMaterial"
"ToolFaceSelection","PaintMaterial"
"ToolFaceSelection","NudgeUp"
"ToolFaceSelection","NudgeRotateUp"
"ToolFaceSelection","NudgeDown"
"ToolFaceSelection","NudgeRotateDown"
"ToolFaceSelection","NudgeLeft"
"ToolFaceSelection","NudgeRotateLeft"
"ToolFaceSelection","NudgeRight"
"ToolFaceSelection","NudgeRotateRight"
"ToolFaceSelection","ApplyMaterialToSelection"
"ToolFaceSelection","ToggleSnapping"
"ToolFaceSelection","Bridge"
"ToolFaceSelection","BridgeTool"
"ToolFaceSelection","Thicken"
"ToolFaceSelection","Mirror"
"ToolFaceSelection","NudgeTextureRight"
"ToolFaceSelection","NudgeTextureLeft"
"ToolFaceSelection","NudgeTextureUp"
"ToolFaceSelection","NudgeTextureDown"
"ToolFaceSelection","JustifyRight"
"ToolFaceSelection","JustifyLeft"
"ToolFaceSelection","JustifyTop"
"ToolFaceSelection","JustifyBottom"
"ToolFaceSelection","Combine"
"ToolFaceSelection","Collapse"
"ToolFaceSelection","Detach"
"ToolFaceSelection","Extract"
"ToolFaceSelection","ClearPivot"
"ToolFaceSelection","CenterPivotInView"
"ToolFaceSelection","SetPivotToWorldOrigin"
"ToolFaceSelection","EndPivotManipulation"
"ToolFaceSelection","IncreaseSubdivisionLevel"
"ToolFaceSelection","DecreaseSubdivisionLevel"
"ToolFaceSelection","MoveObjectDownByTraceLocal"
"ToolFaceSelection","MoveObjectDownByTrace"
"ToolFaceSelection","NextTile"
"ToolFaceSelection","PreviousTile"
"ToolFaceSelection","RandomTile"
"ToolFaceSelection","RotateTexture90CCW"
"ToolFaceSelection","RotateTexture90CW"
"ToolFaceSelection","FlipTextureHorizontal"
"ToolFaceSelection","FlipTextureVertical"
"ToolFaceSelection","ApplyMaterialByHotspot"
"ToolFaceSelection","FastTextureTool"
"ToolFaceSelection","ToggleHotspotApplyMaterial"
"ToolFaceSelection","ToggleHotspotTilingMode"
"ToolFaceSelection","ToggleHotspotAllowRandom"
"ToolFaceSelection","ToggleHotspotPerFace"
"ToolFaceSelection","ToggleHotspotMappingMode"
"ToolFaceSelection","Project"
"ToolFaceSelection","GizmoNumKey0"
"ToolFaceSelection","GizmoNumKey1"
"ToolFaceSelection","GizmoNumKey2"
"ToolFaceSelection","GizmoNumKey3"
"ToolFaceSelection","GizmoNumKey4"
"ToolFaceSelection","GizmoNumKey5"
"ToolFaceSelection","GizmoNumKey6"
"ToolFaceSelection","GizmoNumKey7"
"ToolFaceSelection","GizmoNumKey8"
"ToolFaceSelection","GizmoNumKey9"
"ToolFaceSelection","GizmoNumKeyDecimal"
"ToolFaceSelection","GizmoComma"
"ToolFaceSelection","GizmoNumKeyMinus"
"ToolFaceSelection","GizmoClearValue"
"ToolFaceSelection","GizmoApplyValue"
"ToolVertexSelection","Select"
"ToolVertexSelection","LassoSelect"
"ToolVertexSelection","TranslateLasso"
"ToolVertexSelection","SelectionAddModifier"
"ToolVertexSelection","SelectionRemoveModifier"
"ToolVertexSelection","GrowSelection"
"ToolVertexSelection","GrowSelection"
"ToolVertexSelection","ShrinkSelection"
"ToolVertexSelection","ShrinkSelection"
"ToolVertexSelection","AddToSelection"
"ToolVertexSelection","RemoveFromSelection"
"ToolVertexSelection","RemoveFromSelectionOldest"
"ToolVertexSelection","SelectLoop"
"ToolVertexSelection","SelectContiguous"
"ToolVertexSelection","CutTool"
"ToolVertexSelection","CreateNewEdge"
"ToolVertexSelection","Merge"
"ToolVertexSelection","SnapToVertex"
"ToolVertexSelection","NudgeUp"
"ToolVertexSelection","NudgeRotateUp"
"ToolVertexSelection","NudgeDown"
"ToolVertexSelection","NudgeRotateDown"
"ToolVertexSelection","NudgeLeft"
"ToolVertexSelection","NudgeRotateLeft"
"ToolVertexSelection","NudgeRight"
"ToolVertexSelection","NudgeRotateRight"
"ToolVertexSelection","ToggleSnapping"
"ToolVertexSelection","ClearPivot"
"ToolVertexSelection","CenterPivotInView"
"ToolVertexSelection","SetPivotToWorldOrigin"
"ToolVertexSelection","EndPivotManipulation"
"ToolVertexSelection","Bevel"
"ToolVertexSelection","Extrude"
"ToolVertexSelection","MoveObjectDownByTraceLocal"
"ToolVertexSelection","MoveObjectDownByTrace"
"ToolVertexSelection","WeldUVs"
"ToolVertexSelection","GizmoNumKey0"
"ToolVertexSelection","GizmoNumKey1"
"ToolVertexSelection","GizmoNumKey2"
"ToolVertexSelection","GizmoNumKey3"
"ToolVertexSelection","GizmoNumKey4"
"ToolVertexSelection","GizmoNumKey5"
"ToolVertexSelection","GizmoNumKey6"
"ToolVertexSelection","GizmoNumKey7"
"ToolVertexSelection","GizmoNumKey8"
"ToolVertexSelection","GizmoNumKey9"
"ToolVertexSelection","GizmoNumKeyDecimal"
"ToolVertexSelection","GizmoComma"
"ToolVertexSelection","GizmoNumKeyMinus"
"ToolVertexSelection","GizmoClearValue"
"ToolVertexSelection","GizmoApplyValue"
"ToolEdgeSelection","Select"
"ToolEdgeSelection","LassoSelect"
"ToolEdgeSelection","TranslateLasso"
"ToolEdgeSelection","SelectionAddModifier"
"ToolEdgeSelection","SelectionRemoveModifier"
"ToolEdgeSelection","ShrinkSelection"
"ToolEdgeSelection","ShrinkSelection"
"ToolEdgeSelection","GrowSelection"
"ToolEdgeSelection","GrowSelection"
"ToolEdgeSelection","AddToSelection"
"ToolEdgeSelection","RemoveFromSelection"
"ToolEdgeSelection","RemoveFromSelectionOldest"
"ToolEdgeSelection","CutTool"
"ToolEdgeSelection","ArcTool"
"ToolEdgeSelection","SelectSingleLoop"
"ToolEdgeSelection","SelectLoop"
"ToolEdgeSelection","SelectRing"
"ToolEdgeSelection","SelectRibs"
"ToolEdgeSelection","CreatePolygonFromEdges"
"ToolEdgeSelection","Dissolve"
"ToolEdgeSelection","DissolveAgressive"
"ToolEdgeSelection","Bridge"
"ToolEdgeSelection","BridgeTool"
"ToolEdgeSelection","Merge"
"ToolEdgeSelection","Split"
"ToolEdgeSelection","SnapEdgeToEdge"
"ToolEdgeSelection","Extrude"
"ToolEdgeSelection","Extend"
"ToolEdgeSelection","Connect"
"ToolEdgeSelection","Bevel"
"ToolEdgeSelection","BevelTool"
"ToolEdgeSelection","Collapse"
"ToolEdgeSelection","SetNormalsHard"
"ToolEdgeSelection","SetNormalsSoft"
"ToolEdgeSelection","SetNormalsDefault"
"ToolEdgeSelection","ToggleSnapping"
"ToolEdgeSelection","TransformExtrude"
"ToolEdgeSelection","ClearPivot"
"ToolEdgeSelection","CenterPivotInView"
"ToolEdgeSelection","SetPivotToWorldOrigin"
"ToolEdgeSelection","EndPivotManipulation"
"ToolEdgeSelection","MoveObjectDownByTraceLocal"
"ToolEdgeSelection","MoveObjectDownByTrace"
"ToolEdgeSelection","WeldUVs"
"ToolEdgeSelection","NudgeUp"
"ToolEdgeSelection","NudgeRotateUp"
"ToolEdgeSelection","NudgeDown"
"ToolEdgeSelection","NudgeRotateDown"
"ToolEdgeSelection","NudgeLeft"
"ToolEdgeSelection","NudgeRotateLeft"
"ToolEdgeSelection","NudgeRight"
"ToolEdgeSelection","NudgeRotateRight"
"ToolEdgeSelection","GizmoNumKey0"
"ToolEdgeSelection","GizmoNumKey1"
"ToolEdgeSelection","GizmoNumKey2"
"ToolEdgeSelection","GizmoNumKey3"
"ToolEdgeSelection","GizmoNumKey4"
"ToolEdgeSelection","GizmoNumKey5"
"ToolEdgeSelection","GizmoNumKey6"
"ToolEdgeSelection","GizmoNumKey7"
"ToolEdgeSelection","GizmoNumKey8"
"ToolEdgeSelection","GizmoNumKey9"
"ToolEdgeSelection","GizmoNumKeyDecimal"
"ToolEdgeSelection","GizmoComma"
"ToolEdgeSelection","GizmoNumKeyMinus"
"ToolEdgeSelection","GizmoClearValue"
"ToolEdgeSelection","GizmoApplyValue"
"ToolEdgeCut","CutEdge"
"ToolEdgeCut","Finish"
"ToolEdgeCut","Finish"
"ToolEdgeCut","Apply"
"ToolEdgeCut","Cancel"
"ToolEdgeCut","ToggleSnapping"
"ToolEdgeCut","AlignedSnap"
"ToolEdgeCut","PlaceCut"
"ToolEdgeCut","PlaceCut"
"ToolEdgeCut","ToggleLoopCut"
"ToolEdgeCut","ToggleLoopCutEven"
"ToolEdgeCut","ToggleLoopCutFlip"
"ToolVertexNormalPaint","Paint"
"ToolVertexNormalPaint","Erase"
"ToolVertexNormalPaint","ScaleBrush"
"ToolVertexNormalPaint","FreezeNormal"
"ToolEdgeArc","AdjustParameters"
"ToolEdgeArc","Finish"
"ToolEdgeArc","Finish"
"ToolEdgeArc","Apply"
"ToolEdgeArc","Cancel"
"ToolEdgeArc","LockToAxis"
"ToolEdgeArc","IncreaseNumSteps"
"ToolEdgeArc","DecreaseNumSteps"
"ToolEdgeArc","ToggleSnapping"
"ToolFastTexture","Finish"
"ToolFastTexture","Finish"
"ToolFastTexture","Finish"
"ToolFastTexture","Finish"
"ToolFastTexture","Cancel"
"ToolFastTexture","ToggleFlipHorizontal"
"ToolFastTexture","ToggleFlipVertical"
"ToolFastTexture","TogglePrimaryAxis"
"ToolFastTexture","MappingUnwrapSquare"
"ToolFastTexture","MappingUnwrapConforming"
"ToolFastTexture","MappingUnwrapQuads"
"ToolFastTexture","MappingPlanar"
"ToolFastTexture","MappingUseExisting"
"ToolFastTexture","SmallerGrid"
"ToolFastTexture","BiggerGrid"
"ToolFastTexture","DecreaseInset"
"ToolFastTexture","IncreaseInset"
"ToolFastTexture","DecreaseInset"
"ToolFastTexture","IncreaseInset"
"ToolFastTexture_UVWidget","ResetMappingBounds"
"ToolFastTexture_UVWidget","PickRectangle"
"ToolFastTexture_UVWidget","Drag"
"ToolFastTexture_UVWidget","Drag"
"ToolFastTexture_UVWidget","NudgeUp"
"ToolFastTexture_UVWidget","NudgeDown"
"ToolFastTexture_UVWidget","NudgeLeft"
"ToolFastTexture_UVWidget","NudgeRight"
"ToolFastTexture_UVWidget","BeginPickEdge"
"ToolFastTexture_UVWidget","CancelPickEdge"
"ToolFastTexture_UVWidget","PickEdge"
"ToolFastTexture_UVWidget","DrawRectangle"
"ToolFastTexture_UVWidget","DisableSnapping"
"ToolBridge","AdjustParameters"
"ToolBridge","Finish"
"ToolBridge","Finish"
"ToolBridge","Apply"
"ToolBridge","Cancel"
"ToolBridge","IncreaseNumSteps"
"ToolBridge","DecreaseNumSteps"
"ToolBridge","FreeDrag"
"ToolBridge","LockPoints"
"ToolBevel","Finish"
"ToolBevel","Finish"
"ToolBevel","Finish"
"ToolBevel","Apply"
"ToolBevel","Cancel"
"ToolBevel","AdjustSteps"
"ToolBevel","AdjustWidth"
"ToolBevel","AdjustShape"
"ToolBevel","ToggleSnapping"
"ToolPainting","CycleChannelsForward"
"ToolPainting","CycleChannelsBackward"
"ToolPainting","CycleChannelsForward"
"ToolPainting","CycleChannelsBackward"
"ToolPainting","PaintSecondaryBlend"
"ToolPainting","Erase"
"ToolPainting","Paint"
"ToolPainting","ScaleBrush"
"ToolPainting","AdjustHardness"
"ToolPainting","TraceAndLiftMaterial"
"ToolPainting","DropTool"
"ToolPainting","NoOpDoubleClick"
"ToolPainting","FloodFill"
"ToolPainting","SampleVertexColor"
"ToolStaticOverlay","BrushScaleUp"
"ToolStaticOverlay","BrushScaleDn"
"ToolStaticOverlay","BrushRotCW"
"ToolStaticOverlay","BrushRotCCW"
"ToolStaticOverlay","BrushDepthUp"
"ToolStaticOverlay","BrushDepthDn"
"ToolStaticOverlay","BrushAspectUp"
"ToolStaticOverlay","BrushAspectDn"
"ToolStaticOverlay","PosOffsetUp"
"ToolStaticOverlay","PosOffsetDn"
"ToolStaticOverlay","ResetTransforms"
"ToolStaticOverlay","CreateMode"
"ToolStaticOverlay","DeleteMode"
"ToolStaticOverlay","LocalizeMode"
"ToolStaticOverlay","CycleHotspotUp"
"ToolStaticOverlay","CycleHotspotDn"
"ToolStaticOverlay","ApplyTool"
"ToolStaticOverlay","ApplyAndCloseTool"
"ToolStaticOverlay","DropTool"
"ToolStaticOverlay","LMouse"
"ToolStaticOverlay","LMouseAdd"
"ToolStaticOverlay","LMouseRemove"
"ToolStaticOverlay","IncrementRenderOrder"
"ToolStaticOverlay","DecrementRenderOrder"
"ToolAssetSpray","Spray"
"ToolAssetSpray","Erase"
"ToolAssetSpray","ScaleBrush"
"ToolPhysics","Select"
"ToolPhysics","Select"
"ToolPhysics","Grab"
"ToolPhysics","BoxSelect"
"ToolPhysics","LassoSelect"
"ToolPhysics","TranslateLasso"
"ToolPhysics","AddObjectToSelection"
"ToolPhysics","RemoveObjectFromSelection"
"ToolPhysics","ToggleSnapping"
"ToolPhysics","ToggleSimulation"
"ToolPhysics","SnapshotSimulation"
"ToolPhysics","ClearSelection"
"ToolPhysics","BeginPinPlacement"
"ToolPhysics","AbortPinPlacement"
"ToolPhysics","PlacePin"
"ToolPhysics","TranslateMode"
"ToolPhysics","RotateMode"
"ToolPhysics","ScaleMode"
"ToolPath","PlacePathNode"
"ToolPath","Finish"
"ToolPath","Finish"
"ToolPath","Apply"
"ToolPath","Cancel"
"ToolSelection","Select"
"ToolSelection","BoxSelect"
"ToolSelection","LassoSelect"
"ToolSelection","TranslateLasso"
"ToolSelection","MoveSelected"
"ToolSelection","SelectAndMove2D"
"ToolSelection","AddObjectToSelection"
"ToolSelection","RemoveObjectFromSelection"
"ToolSelection","ToggleSnapping"
"ToolSelection","StampClone"
"ToolSelection","CloneSelection"
"ToolSelection","ToggleAlignToSurface"
"ToolSelection","SelectNext"
"ToolSelection","SelectPrev"
"ToolSelection","CancelSelectOperation"
"ToolSelection","ShrinkGizmo"
"ToolSelection","EnlargeGizmo"
"ToolSelection","NextPivotTap"
"ToolSelection","NextPivotCycle"
"ToolSelection","PrevPivotCycle"
"ToolSelection","ClearPivot"
"ToolSelection","CenterPivotInView"
"ToolSelection","SetPivotToWorldOrigin"
"ToolSelection","EndPivotManipulation"
"ToolSelection","FlipNormals"
"ToolSelection","MergeSelectedMeshes"
"ToolSelection","SeparateMeshComponents"
"ToolSelection","NudgeUp"
"ToolSelection","NudgeRotateUp"
"ToolSelection","NudgeDown"
"ToolSelection","NudgeRotateDown"
"ToolSelection","NudgeLeft"
"ToolSelection","NudgeRotateLeft"
"ToolSelection","NudgeRight"
"ToolSelection","NudgeRotateRight"
"ToolSelection","ApplyMaterial"
"ToolSelection","GizmoDebugHook"
"ToolSelection","SetOriginToCenter"
"ToolSelection","ClearRotationAndScale"
"ToolSelection","MoveObjectDownByTraceLocal"
"ToolSelection","MoveObjectDownByTrace"
"ToolSelection","ShowObjectProperties"
"ToolSelection","GrowSelection"
"ToolSelection","GrowSelection"
"ToolSelection","ShrinkSelection"
"ToolSelection","ShrinkSelection"
"ToolSelection","SetOriginToPivot"
"ToolSelection","AlignObjects"
"ToolSelection","AlignObjectsRotation"
"ToolSelection","AlignObjectsToWorkplane"
"ToolSelection","AlignWorkplaneToObject"
"ToolSelection","NextVariation"
"ToolSelection","PreviousVariation"
"ToolSelection","HideElement"
"ToolSelection","ResetConfiguration"
"ToolSelection","ReevaluateConfiguration"
"ToolSelection","GizmoNumKey0"
"ToolSelection","GizmoNumKey1"
"ToolSelection","GizmoNumKey2"
"ToolSelection","GizmoNumKey3"
"ToolSelection","GizmoNumKey4"
"ToolSelection","GizmoNumKey5"
"ToolSelection","GizmoNumKey6"
"ToolSelection","GizmoNumKey7"
"ToolSelection","GizmoNumKey8"
"ToolSelection","GizmoNumKey9"
"ToolSelection","GizmoNumKeyDecimal"
"ToolSelection","GizmoComma"
"ToolSelection","GizmoNumKeyMinus"
"ToolSelection","GizmoClearValue"
"ToolSelection","GizmoApplyValue"
"ToolmeshDisplacement","ModePushPull"
"ToolmeshDisplacement","ModeFlatten"
"ToolmeshDisplacement","ModeMove"
"ToolmeshDisplacement","ModeInflate"
"ToolmeshDisplacement","ModeClay"
"ToolmeshDisplacement","ModePinch"
"ToolmeshDisplacement","ModeErase"
"ToolmeshDisplacement","ModeSmooth"
"ToolmeshDisplacement","PickNormal"
"ToolmeshDisplacement","ResetNormal"
"ToolmeshDisplacement","Paint"
"ToolmeshDisplacement","AdjustRadius"
"ToolmeshDisplacement","SmoothModifier"
"ToolmeshDisplacement","EraseModifer"
"ToolmeshDisplacement","ReverseModifier"
"ToolmeshDisplacement","DropTool"
"ToolmeshDisplacement","DropTool"
"ToolPickEntity","Pick"
"ToolPickEntity","SelectionAddModifier"
"ToolPickEntity","SelectionRemoveModifier"
"ToolPickEntity","CancelTool"
"ToolPickEntity","FinishTool"
"ToolPlaceNavWalkable","Place"
"ToolPlaceNavWalkable","CancelTool"
"ToolWorkPlane","PickWorkPlaneFromSurface"
"ToolWorkPlane","PickWorkPlaneFromObject"
"ToolWorkPlane","WorkPlaneModeTranslate"
"ToolWorkPlane","WorkPlaneModeRotate"
"ToolWorkPlane","ToggleSnapping"
"ToolWorkPlane","ResetWorkPlaneAndDropTool"
"ToolWorkPlane","DropTool"
"ToolWorkPlane","DropTool"
"ToolTerrain","AdjustBrush"
"ToolTerrain","AdjustBrushPressure"
"ToolTerrain","ApplyBrush"
"ToolTerrain","ApplyBrushErase"
"ToolTerrain","ApplyBrushSmooth"
"ToolTerrain","ApplyBrushAlternate"
"TerrainGraphEditor","DeleteSelected"
"TerrainGraphEditorView","PanView"
"TerrainGraphEditorView","PanView"
"TerrainGraphEditorView","ZoomView"
"TerrainGraphEditorView","ZoomViewInStep"
"TerrainGraphEditorView","ZoomViewOutStep"
"TerrainGraphEditorView","FitSelectionInView"
"TerrainGraphEditorView","FitSelectionInView"
"TerrainGraphEditorView","FitAllInView"
"ToolDotaTileEditor","ModeBrushHeight"
"ToolDotaTileEditor","ModeBrushWater"
"ToolDotaTileEditor","ModeBrushPath"
"ToolDotaTileEditor","ModeBrushTrees"
"ToolDotaTileEditor","ModeBrushPlants"
"ToolDotaTileEditor","ModeBrushBlends"
"ToolDotaTileEditor","ModeEditObjects"
"ToolDotaTileEditor","ModeSelect"
"ToolDotaTileEditor","ModeEnableDisableTiles"
"ToolDotaTileEditor","CycleModeForward"
"ToolDotaTileEditor","CycleModeBack"
"ToolDotaTileEditor","NextVariation"
"ToolDotaTileEditor","PreviousVariation"
"ToolDotaTileEditor","SelectNextTileSet"
"ToolDotaTileEditor","AssignCurrentTileSet"
"ToolDotaTileEditor","AssignNextTileSet"
"ToolDotaTileEditor","AssignPreviousTileSet"
"ToolDotaTileEditor","DeleteObject"
"ToolDotaTileEditor","Select"
"ToolDotaTileEditor","LassoSelect"
"ToolDotaTileEditor","BoxSelect"
"ToolDotaTileEditor","ClearSelection"
"ToolDotaTileEditor","RandomVariation"
"ToolDotaTileEditor","CollapseTiles"
"ToolDotaTileEditor","RaiseTiles"
"ToolDotaTileEditor","LowerTiles"
"ToolDotaTileEditor","SelectionAddModifier"
"ToolDotaTileEditor","SelectionRemoveModifier"
"ToolDotaTileEditor","CopyItems"
"ToolDotaTileEditor","PasteItems"
"ToolDotaTileEditor","BeginPaste"
"ToolDotaTileEditor","ApplyPaste"
"ToolDotaTileEditor","ApplyPaste"
"ToolDotaTileEditor","ApplyPaste"
"ToolDotaTileEditor","FinishPaste"
"ToolDotaTileEditor","CancelPaste"
"ToolDotaTileEditor","EnableDisableTile"
"ToolDotaTileEditor","EnableTileModifier"
"ToolDotaTileEditor","LassoEnableDisable"
"ToolDotaTileEditor","BoxEnableDisable"
"ToolDotaTileEditor","EnableDisableCutDummy"
"ToolDotaTileEditor","AdjustRadius"
"ToolDotaTileEditor","ApplyBrush"
"ToolDotaTileEditor","StampBrush"
"ToolDotaTileEditor","RaiseVertex"
"ToolDotaTileEditor","LowerVertex"
"ToolDotaTileEditor","EraseBrush"
"ToolDotaTileEditor","BrushAlternateMode"
"ToolDotaTileEditor","BrushHeightOffsetMode"
"ToolDotaTileEditor","BrushTilesetMode"
"ToolDotaTileEditor","BrushAdjustDensity"
"ToolDotaTileEditor","BrushIncreaseTreeHeight"
"ToolDotaTileEditor","BrushDecreaseTreeHeight"
"ToolDotaTileEditor","BrushChangeObjectType"
"ToolDotaTileEditor","BrushChangeTreePitch"
"ToolDotaTileEditor","BrushCutDummy"
"ToolDotaTileEditor","BrushRotateObjects"
"ToolDotaTileEditor","BlendAdjustRadius"
"ToolDotaTileEditor","BlendApplyBrush"
"ToolDotaTileEditor","BlendStampBrush"
"ToolDotaTileEditor","BlendEraseBrush"
"ToolDotaTileEditor","BlendBrushAdjustPressure"
"ToolDotaTileEditor","BlendBrushSharpness"
"ToolDotaTileEditor","BlendBrushSmooth"
"ToolDotaTileEditor","BlendBrushMaterialSet"
"ToolDotaTileEditor","SelectNextMaterialSet"
"ToolDotaTileEditor","SetBlendModeLayer0"
"ToolDotaTileEditor","SetBlendModeLayer1"
"ToolDotaTileEditor","SetBlendModeLayer2"
"ToolDotaTileEditor","SetBlendModeLayer3"
"ToolDotaTileEditor","SetBlendModeColor"
"ToolDotaTileEditor","AddObject"
"ToolDotaTileEditor","AddObject"
"ToolDotaTileEditor","ToggleRemoveObject"
"ToolDotaTileEditor","ModifyObject"
"ToolDotaTileEditor","ModifyObject"
"ToolDotaTileEditor","RandomObjectVariation"
"ToolDotaTileEditor","DragObject"
"ToolDotaTileEditor","RotateObject"
"ToolDotaTileEditor","RotateObject"
"ToolDotaTileEditor","PitchObject"
"ToolDotaTileEditor","PitchObject"
"ToolDotaTileEditor","DragClone"
"ToolDotaTileEditor","StampObject"
"ToolDotaTileEditor","ToggleSnapping"
'@

    $allKnownCommands = $null

    #TODO: Get addational Hammer5 tool hotkeys. Such as ModelDoc.
    if($Global:filePath.Contains("hammer_key_bindings"))
    {
        $allKnownCommands = $hammer5AllCommands
    }
    else {
        return #Bail, don't have merge data.
    }

    foreach ($knownCommand in $allKnownCommands)
    {
        $add = $true
        foreach ($bind in $Global:allBinds.InputBindingList_t.m_Bindings)
        {
            if($knownCommand.m_Command -eq $bind.m_Command -and $knownCommand.m_Context -eq $bind.m_Context)
            {
                $add = $false
                break
            }
        }
        if($add)
        {
            $knownCommand | Add-Member -NotePropertyName m_Input -NotePropertyValue ""
            $merged += $knownCommand
        }
    }

    $Global:allBinds.InputBindingList_t.m_Bindings += $merged
    $Global:mergeCompleted = $true
}

Function Update-Tables() {
    <#
    .SYNOPSIS
    Refreshes the table data and displays all binds or searched for binds
    #>
    $Global:dataTable = New-Object System.Data.DataTable 'm_Bindings'
    $newcol = New-Object system.Data.DataColumn m_Context, ([string]); ($Global:dataTable.columns.add($newcol))
    $newcol = New-Object system.Data.DataColumn m_Command, ([string]); ($Global:dataTable.columns.add($newcol))
    $newcol = New-Object system.Data.DataColumn m_Input, ([string]); ($Global:dataTable.columns.add($newcol))

    Merge-UnboundKeys

    $count = 0
    foreach ($bind in $Global:allBinds.InputBindingList_t.m_Bindings) {
        if ($null -ne $m_ContextSearch.Text -and $m_ContextSearch.Text.Length -ne 0 -and !$bind.m_Context.toLower().contains($m_ContextSearch.Text.ToLower())) {
            continue
        }

        if ($null -ne $m_CommandSearch.Text -and $m_CommandSearch.Text.Length -ne 0 -and !$bind.m_Command.toLower().contains($m_CommandSearch.Text.ToLower())) {
            continue
        }

        if ($null -ne $bind.m_Input -and $null -ne $m_InputSearch.Text -and $m_InputSearch.Text.Length -ne 0 -and !$bind.m_Input.toLower().contains($m_InputSearch.Text.ToLower())) {
            continue
        }

        $row = $Global:dataTable.NewRow()
        $row.m_Context = $bind.m_Context
        $row.m_Command = $bind.m_Command
        $row.m_Input = $bind.m_Input
        $Global:dataTable.Rows.Add($row)
        $count++
    }
    $dataGrid.DataSource = $Global:dataTable
    $mainForm.Text = "CS2 Hammer Hotkey Editor. Showing: $count of $($Global:allBinds.InputBindingList_t.m_Bindings.count)"
}

Function DisplayDuplicates() {
    <#
    .SYNOPSIS
    Updates the display to only show binds that are duplicates and are searched for
    #>
    $allBinds = $Global:allBinds.InputBindingList_t.m_Bindings
    $dupeBinds = @()

    foreach ($b in $allBinds) {
        $dupeResult = Search-DuplicateBinds $b.m_Input

        if ($dupeResult -and $dupeResult.GetType().Name -eq "Object[]") {
            foreach ($d in $dupeResult) {
                #Only add if we aren't already in the list.
                if (!$dupeBinds.Contains($d)) {
                    $dupeBinds += $d
                }
            }
        }
    }

    $Global:dataTable = New-Object System.Data.DataTable 'm_Bindings'
    $newcol = New-Object system.Data.DataColumn m_Context, ([string]); ($Global:dataTable.columns.add($newcol))
    $newcol = New-Object system.Data.DataColumn m_Command, ([string]); ($Global:dataTable.columns.add($newcol))
    $newcol = New-Object system.Data.DataColumn m_Input, ([string]); ($Global:dataTable.columns.add($newcol))

    $count = 0
    #Only read in the binds with known dupe inputs, then search on them
    foreach ($bind in $dupeBinds) {
        if ($null -ne $m_ContextSearch.Text -and $m_ContextSearch.Text.Length -ne 0 -and !$bind.m_Context.toLower().contains($m_ContextSearch.Text.ToLower())) {
            continue
        }

        if ($null -ne $m_CommandSearch.Text -and $m_CommandSearch.Text.Length -ne 0 -and !$bind.m_Command.toLower().contains($m_CommandSearch.Text.ToLower())) {
            continue
        }

        if ($null -ne $m_InputSearch.Text -and $m_InputSearch.Text.Length -ne 0 -and !$bind.m_Input.toLower().contains($m_InputSearch.Text.ToLower())) {
            continue
        }

        $row = $Global:dataTable.NewRow()
        $row.m_Context = $bind.m_Context
        $row.m_Command = $bind.m_Command
        $row.m_Input = $bind.m_Input
        $Global:dataTable.Rows.Add($row)
        $count++
    }
    $dataGrid.DataSource = $Global:dataTable
    $mainForm.Text = "CS2 Hammer Hotkey Editor. DUPES ONLY Showing: $count of $($Global:allBinds.InputBindingList_t.m_Bindings.count)"
}

Function Update-KeypressValue() {
    <#
    .SYNOPSIS
    Valve uses different key identifiers than what .net captures - here we convert the ones we need
    Also have some handing for reserved and escaped characters
    #>
    param (
        [Parameter()]
        [string]$value
    )

    if ($value.StartsWith("NumPad")) { $value = $value.Replace("NumPad", "Num") }
    elseif ($value -eq "Decimal") { $value = "NumDec" }
    elseif ($value -eq "Add") { $value = "NumAdd" }
    elseif ($value -eq "Subtract") { $value = "NumSub" }
    elseif ($value -eq "Back") { $value = "Backspace" }
    elseif ($value -eq "OemMinus") { $value = "-" }
    elseif ($value -eq "Oemplus") { $value = "=" }
    elseif ($value -eq "OemOpenBrackets") { $value = "[" }
    elseif ($value -eq "Oem6") { $value = "]" }
    elseif ($value -eq "Oem1") { $value = ";" }
    elseif ($value -eq "Oem7") { $value = "\`"" }
    elseif ($value -eq "Oemcomma") { $value = "," }
    elseif ($value -eq "OemPeriod") { $value = "," }
    elseif ($value -eq "OemQuestion") { $value = "\/" } #Unsure if this works...
    elseif ($value -eq "Oem5") { $value = "\\" } #Escape char!
    elseif ($value -eq "Oemtilde") { $value = "`` RESERVED" } 
    elseif ($value -eq "F1") { $value = "F1 RESERVED" } 

    #Don't allow binds to reserved keys
    if ($value.Contains("RESERVED")) {
        $bindAcceptButton.Enabled = $false
    }
    else {
        $bindAcceptButton.Enabled = $true
    }

    return $value
}

Function Open-File() {
    <#
    .SYNOPSIS
    Opens the specified file and then updates the table
    #>
    param (
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $Global:mergeCompleted = $false

    $content = Get-Content $Path 
    $Global:allBinds = Convertfrom-KV3 $content

    Update-Tables
}

Function Search-DuplicateBinds() {
    <#
    .SYNOPSIS
    Reports all existing binds with the same m_Input
    
    .PARAMETER newbind
    string of the m_Input to check for dupes, such as "Ctrl+Shift+D"
    #>
    param (
        [Parameter()]
        [string]$newbind
    )

    $dupes = @()
    
    foreach ($bind in $global:allBinds.InputBindingList_t.m_bindings) {
        if($null -eq $bind.m_Input -or $bind.m_Input.length -eq 0) {continue}

        if ($bind.m_Input.ToLower() -eq $newbind.ToLower()) { $dupes += $bind }
    }

    return @($dupes)
}

#Globals
$Global:ConsumeKeyPress = $true #Should we consume the keypress in the bind collection form?
$Global:gridSelection = $null #What did we last select?
$Global:lastKey = $null #What was the last key we pressed in the bind collection from?
$Global:filePath = "c:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game\core\tools\keybindings\hammer_key_bindings.txt"
$Global:showingDupes = $false
$Global:mergeCompleted = $false

#Setup main form
Add-Type -Assembly System.Windows.Forms
$mainForm = New-Object System.Windows.Forms.Form
$mainForm.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedDialog
$mainForm.AutoSize = $true

#File Menu setup
$menuMain = New-Object System.Windows.Forms.MenuStrip
$menuFile = New-Object System.Windows.Forms.ToolStripMenuItem
$mainForm.MainMenuStrip = $menuMain
[void]$mainForm.Controls.Add($mainToolStrip)
[void]$mainForm.Controls.Add($menuMain)
$menuFile.Text = "File"
[void]$menuMain.Items.Add($menuFile)

#File > Open
$menuOpen = New-Object System.Windows.Forms.ToolStripMenuItem
$menuOpen.ShortcutKeys = "Control, O"
$menuOpen.Text = "Open Keybind File"
[void]$menuFile.DropDownItems.Add($menuOpen)
$menuOpen.Add_Click({
        $selectOpenForm = New-Object System.Windows.Forms.OpenFileDialog
        $selectOpenForm.Filter = "Hammer 5 Keybinds|*.txt"

        $dir = "c:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game\core\tools\keybindings"
        if (!(Test-Path $dir)) { $dir = "C:\" }
        $selectOpenForm.InitialDirectory = $dir
        $selectOpenForm.Title = "Select a File to Open"
        $getKey = $selectOpenForm.ShowDialog()
        If ($getKey -eq "OK") {
            $inputFileName = $selectOpenForm.FileName
        }
        Open-File $inputFileName
        $Global:filePath = $inputFileName
    })

#File > SaveAs
$menuSaveAs = New-Object System.Windows.Forms.ToolStripMenuItem
$menuSaveAs.ShortcutKeys = "Control, S"
$menuSaveAs.Text = "Save As"
[void]$menuFile.DropDownItems.Add($menuSaveAs)
$menuSaveAs.Add_Click({
        $selectSaveAsForm = New-Object System.Windows.Forms.SaveFileDialog
        $selectSaveAsForm.Filter = "Hammer 5 Keybinds|*.txt"
        $selectSaveAsForm.InitialDirectory = Split-Path -Path $Global:filePath
        $selectSaveAsForm.Title = "Select a File to Save"
        $selectSaveAsForm.FileName = Split-Path -Leaf $Global:filePath
        $getKey = $selectSaveAsForm.ShowDialog()
        If ($getKey -eq "OK") {
            $outputFileName = $selectSaveAsForm.FileName
            $result = ConvertTo-KV3 $Global:allBinds

            $path = Split-Path -path $outputFileName
            $file = ([io.fileinfo]$outputFileName).basename

            # $result | Out-File $outputFileName
            # $result | Out-File "$path\$file$(get-date -Format "MMddyyyy_HHmm").txt"

            $backupPath = "$path\$file$(get-date -Format "MMddyyyy_HHmm").txt"

            $Utf8NoBomEncoding = New-Object System.Text.UTF8Encoding $False
            [System.IO.File]::WriteAllLines($outputFileName, $result, $Utf8NoBomEncoding)
            [System.IO.File]::WriteAllLines($backupPath, $result, $Utf8NoBomEncoding)
        }
    })

#File > Toggle Show Duplicates
$menuShowDupes = New-Object System.Windows.Forms.ToolStripMenuItem
$menuShowDupes.Text = "Toggle Show Duplicates"
$menuShowDupes.ShortcutKeys = "Control, D"
[void]$menuFile.DropDownItems.Add($menuShowDupes)
$menuShowDupes.Add_Click({
        if (!$Global:showingDupes) {
            $Global:showingDupes = $true
            DisplayDuplicates
        }
        else {
            $Global:showingDupes = $false
            Update-Tables
        }
    })

#File > Restore Defauts
$restoreDefaultMenu = New-Object System.Windows.Forms.ToolStripMenuItem
$restoreDefaultMenu.Text = "Restore Default Binds"
[void]$menuFile.DropDownItems.Add($restoreDefaultMenu)
$restoreDefaultMenu.Add_Click({
    #Defaults as of Aug 14th 2023
    $defaultBinds = @'
    <!-- schema text {2CC83121-F14F-4A36-ABB8-62F4C2799689} generic {198980D8-3A93-4919-B4C6-DD1FB07A3A4B} -->
    InputBindingList_t
    {
        m_InputMacros =
        [
            InputMacro_t { m_Name = "SELECTION_ADD_KEY"				m_Input = "Shift"	},
            InputMacro_t { m_Name = "SELECTION_REMOVE_KEY"			m_Input = "Ctrl"	},
            InputMacro_t { m_Name = "TOGGLE_SNAPPING_KEY"			m_Input = "Ctrl"	},
        ]

        m_Bindings =
        [
            InputBinding_t { m_Context = "HammerApp" 		m_Command = "FileOpen"						m_Input = "Ctrl+O"			},
            InputBinding_t { m_Context = "HammerApp" 		m_Command = "FileSave"						m_Input = "Ctrl+S"			},
            InputBinding_t { m_Context = "HammerApp" 		m_Command = "FileSaveAs"					m_Input = "Ctrl+Shift+S"	},
            InputBinding_t { m_Context = "HammerApp" 		m_Command = "SaveActivePrefab"				m_Input = "Shift+Alt+S"		},		
            InputBinding_t { m_Context = "HammerApp" 		m_Command = "FileReload"					m_Input = "Ctrl+Shift+F12"	},
            InputBinding_t { m_Context = "HammerApp" 		m_Command = "FileNew"						m_Input = "Ctrl+N"			},
            InputBinding_t { m_Context = "HammerApp" 		m_Command = "NextSession"					m_Input = "Ctrl+Tab"		},
            InputBinding_t { m_Context = "HammerApp" 		m_Command = "PreviousSession"				m_Input = "Ctrl+Shift+Tab"	},
            InputBinding_t { m_Context = "HammerApp" 		m_Command = "BuildMap"						m_Input = "F9"				},
            InputBinding_t { m_Context = "HammerApp" 		m_Command = "ToggleShowHelpers"				m_Input = "Ctrl+Shift+H"	},
            InputBinding_t { m_Context = "HammerApp" 		m_Command = "ToggleTextureLockScale"		m_Input = "Ctrl+Shift+Y"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "TogglePropertiesPopup"			m_Input = "Alt+Enter"		},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "TogglePropertiesPopup"			m_Input = "Alt+NumEnter"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ShowMapVariablesPopup"			m_Input = "Ctrl+Shift+M"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ShowMapPropertiesPopup"		m_Input = "Ctrl+Shift+P"	},		
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ToggleShowGameObjectsOnly"		m_Input = "Shift+O"			},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ToggleSelectThrough"			m_Input = "Ctrl+Shift+L"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ViewDistanceNext"				m_Input = "Alt+MWheelUp"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ViewDistancePrev"				m_Input = "Alt+MWheelDn"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ShowMapManifestWidget"			m_Input = "Ctrl+Alt+M"		},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ToggleGridNav"					m_Input = "Ctrl+Q"			},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ToggleToolsMaterials"			m_Input = "Ctrl+Shift+F2"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ToggleSelectionOverlay"		m_Input = "Ctrl+Shift+F4"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ToggleInstanceOverlay"			m_Input = "Ctrl+Shift+F5"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ToggleMeshSubdivision"			m_Input = "Ctrl+Shift+F6"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ToggleMeshTiles3D"				m_Input = "Ctrl+Shift+F7"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ToggleMeshTiles2D"				m_Input = "Ctrl+Shift+F8"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ToggleSelectBackfacing"		m_Input = "Ctrl+Shift+F9"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ToggleFullscreenLayout"		m_Input = "Shift+Alt+Z"		},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ShowEntityReport"				m_Input = "Ctrl+Alt+R"		},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "CycleEditUVSet"				m_Input = "Alt+Y"			},


            InputBinding_t { m_Context = "SessionCycleWidget" 	m_Command = "KeepActive"				m_Input = "Ctrl"			},
            InputBinding_t { m_Context = "SessionCycleWidget" 	m_Command = "NextSession"				m_Input = "Ctrl+Tab"		},
            InputBinding_t { m_Context = "SessionCycleWidget" 	m_Command = "PreviousSession"			m_Input = "Ctrl+Shift+Tab"	},

            InputBinding_t { m_Context = "MapManifestWidget" 	m_Command = "RefreshView"				m_Input = "F5"	},

            InputBinding_t { m_Context = "HammerObjectPropertyPopup"	m_Command = "HidePropertyWindow"	m_Input = "Alt+Enter"	},
            InputBinding_t { m_Context = "HammerObjectPropertyPopup"	m_Command = "HidePropertyWindow"	m_Input = "Alt+NumEnter"},
            InputBinding_t { m_Context = "HammerObjectPropertyPopup"	m_Command = "HidePropertyWindow"	m_Input = "Esc"			},

    // Nudge is using these bindings.
    //		InputBinding_t { m_Context = "MapView" 			m_Command = "PitchCameraUp"					m_Input = "Up"				},
    //		InputBinding_t { m_Context = "MapView" 			m_Command = "PitchCameraDown"				m_Input = "Down"			},
    //		InputBinding_t { m_Context = "MapView" 			m_Command = "YawCameraLeft"					m_Input = "Left"			},
    //		InputBinding_t { m_Context = "MapView" 			m_Command = "YawCameraRight"				m_Input = "Right"			},

            InputBinding_t { m_Context = "MapView" 			m_Command = "ShowContextMenu"				m_Input = "RMouse"			},
            InputBinding_t { m_Context = "MapView" 			m_Command = "MaterialTraceLift"				m_Input = "Shift+RMouse"	},
            InputBinding_t { m_Context = "MapView" 			m_Command = "MaterialTraceLift"				m_Input = "Ctrl+M"			},		
            InputBinding_t { m_Context = "MapView"			m_Command = "ActivateObject"				m_Input = "LMouseDoubleClick"},
            InputBinding_t { m_Context = "MapView"			m_Command = "SnapCameraToTargetUnderMouse"	m_Input = "Shift+Alt+A"		},
            InputBinding_t { m_Context = "MapView"			m_Command = "DetachViewFromObject"			m_Input = "Ctrl+Backspace"	},

            InputBinding_t { m_Context = "PaneContainer" 	m_Command = "2D_Top"						m_Input = "F2"				},
            InputBinding_t { m_Context = "PaneContainer" 	m_Command = "2D_Front"						m_Input = "F3"				},
            InputBinding_t { m_Context = "PaneContainer" 	m_Command = "2D_Side"						m_Input = "F4"				},
            InputBinding_t { m_Context = "PaneContainer" 	m_Command = "3D_FullBrightNoLighting"		m_Input = "F5"				},
            InputBinding_t { m_Context = "PaneContainer" 	m_Command = "3D_AllLighting"				m_Input = "F6"				},
            InputBinding_t { m_Context = "PaneContainer" 	m_Command = "Rtx_Path_Tracing"				m_Input = "Alt+F6"			},
            InputBinding_t { m_Context = "PaneContainer" 	m_Command = "3D_ToolsVis"					m_Input = "F7"				},
            InputBinding_t { m_Context = "PaneContainer" 	m_Command = "ToggleWireframeOverlay"		m_Input = "F8"				},
            InputBinding_t { m_Context = "PaneContainer" 	m_Command = "ToggleShadows"					m_Input = "F10"				},

            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "SelectionModeVertices"			m_Input = "1"				},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "SelectionModeEdges"			m_Input = "2"				},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "SelectionModeFaces"			m_Input = "3"				},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "SelectionModeMeshes"			m_Input = "4"				},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "SelectionModeObjects"			m_Input = "5"				},		
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "SelectionModeGroups"			m_Input = "6"				},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "SelectionModeNav"				m_Input = "8"				},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "CycleSelectionModes"			m_Input = "Space"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "CycleSelectionTopLevelModes"	m_Input = "Shift+Space"		},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ClearSelection"				m_Input = "Esc"				},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "SelectAll"						m_Input = "Ctrl+A"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "InvertSelection"				m_Input = "Ctrl+I"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "DeleteSelection"				m_Input = "Del"				},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "Cut"							m_Input = "Ctrl+X"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "Copy"							m_Input = "Ctrl+C"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "Paste"							m_Input = "Ctrl+V"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "PasteSpecial"					m_Input = "Ctrl+Shift+V"	},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "GroupSelection"				m_Input = "Ctrl+G"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "UngroupSelection"				m_Input = "Ctrl+U"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "UngroupSelectionRecursive"		m_Input = "Ctrl+Alt+U"		},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ReparentSelection"				m_Input = "P"				},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "UnparentSelection"				m_Input = "Ctrl+P"			},
            InputBinding_t { m_Context = "HammerEditorSession"	m_Command = "CreateInstanceFromSelection"	m_Input = "Ctrl+Shift+G"	},
            InputBinding_t { m_Context = "HammerEditorSession"	m_Command = "BakeSelectedInstances"			m_Input = "Ctrl+Shift+U"	},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "MovePropsToWorld"				m_Input = "Ctrl+Shift+T"	},
            InputBinding_t { m_Context = "HammerEditorSession"	m_Command = "CreateTile"					m_Input = "Ctrl+Shift+O"	},
            InputBinding_t { m_Context = "HammerEditorSession"	m_Command = "CreateTileMesh"				m_Input = "Ctrl+Shift+I"	},
            InputBinding_t { m_Context = "HammerEditorSession"	m_Command = "MirrorHorizontal"				m_Input = "Ctrl+Shift+J"	},
            InputBinding_t { m_Context = "HammerEditorSession"	m_Command = "MirrorVertical"				m_Input = "Ctrl+Shift+K"	},
            InputBinding_t { m_Context = "HammerEditorSession"	m_Command = "SelectSimilar"					m_Input = "Ctrl+Alt+O"		},


            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "Undo"							m_Input = "Ctrl+Z"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "Undo"							m_Input = "Alt+Backspace"	},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "Redo"							m_Input = "Ctrl+Y"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "Redo"							m_Input = "Ctrl+Shift+Z"	},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "Redo"							m_Input = "Shift+Alt+Backspace"	},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "FindEntities"					m_Input = "Ctrl+Shift+F"	},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "TieToEntity"					m_Input = "Ctrl+T"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "MoveToWorld"					m_Input = "Ctrl+Shift+W"	},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "SnapToGrid"					m_Input = "Ctrl+B"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "SnapToGridIndividually"		m_Input = "Ctrl+Shift+B"	},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "QuickHideSelection"			m_Input = "H"				},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "QuickHideUnselected"			m_Input = "Ctrl+H"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ShowQuickHide"					m_Input = "U"				},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "SelectionSetFromQuickHide"		m_Input = "Shift+R"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ToggleSnapping"				m_Input = "Shift+W"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ToggleSnapToVertices"			m_Input = "Ctrl+Shift+X"	},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ToggleSnapToGrid"				m_Input = "Ctrl+Shift+Q"	},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "MapGridLower"					m_Input = "["				},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "MapGridHigher"					m_Input = "]"				},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "DecreaseRotationSnapping"		m_Input = "Ctrl+["			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "IncreaseRotationSnapping"		m_Input = "Ctrl+]"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "CenterViews"					m_Input = "Ctrl+Shift+E"	},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "Center2DViews"					m_Input = "Ctrl+E"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "FrameAllViews"					m_Input = "Ctrl+Shift+A"	},
            InputBinding_t { m_Context = "HammerEditorSession"  m_Command = "ToggleSingleView"				m_Input = "Shift+Z"			},	
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "CycleViews"					m_Input = "Ctrl+Space"		},	
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "CycleAndFrameViews"			m_Input = "Ctrl+Shift+Space"},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ActivateViewUnderCursor"		m_Input = "Alt+LMouse"		},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ToggleNavMarkupVisibility"		m_Input = "Ctrl+Shift+D"	},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ToggleOverlayShapes"			m_Input = "Shift+N"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "SetManipulationModeSelection"	m_Input = "Shift+S"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ManipulationModeSelection"		m_Input = "Q"				},	
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ManipulationModeTranslate"		m_Input = "T"				},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ManipulationModeRotate"		m_Input = "R"				},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ManipulationModeScale"			m_Input = "E"				},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ManipulationModePivot"			m_Input = "Ins"				},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ToolPivotPicker"				m_Input = "TAB"				},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ToolBlock"						m_Input = "Shift+B"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ToolPhysics"					m_Input = "Shift+C"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ToolEntity"					m_Input = "Shift+E"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ToolDisplacement"				m_Input = "Shift+D"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ToolClipper"					m_Input = "Shift+X"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ToolPath"						m_Input = "Shift+P"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ToolPaint"						m_Input = "Shift+V"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ToolMirror"					m_Input = "Shift+F"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ToolWorkPlane"					m_Input = "Shift+Q"			},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "ResetWorkPlane"				m_Input = "Shift+Alt+Q"		},
            InputBinding_t { m_Context = "HammerEditorSession"	m_Command = "CreateSelectionSet"			m_Input = "Ctrl+R"			},
            InputBinding_t { m_Context = "HammerEditorSession"	m_Command = "HideUnselected"				m_Input = "Ctrl+Shift+R"	},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "SelectionConvert"				m_Input = "Alt"				},	
            InputBinding_t { m_Context = "HammerEditorSession"	m_Command = "SelectionConnected"			m_Input = "Shift"			},
            InputBinding_t { m_Context = "HammerEditorSession"	m_Command = "SelectionBoundry"				m_Input = "Ctrl"			},
            InputBinding_t { m_Context = "HammerEditorSession"	m_Command = "ToggleCordoning"				m_Input = "Ctrl+Shift+C"	},
            InputBinding_t { m_Context = "HammerEditorSession"	m_Command = "NewCordon"						m_Input = "Ctrl+Shift+N"	},
            InputBinding_t { m_Context = "HammerEditorSession"	m_Command = "RepeatCommand"					m_Input = "Shift+G"			},
            InputBinding_t { m_Context = "HammerEditorSession"	m_Command = "ExitActiveEditScope"			m_Input = "Ctrl+Backspace"	},
            InputBinding_t { m_Context = "HammerEditorSession"	m_Command = "ToggleCollisionModels"			m_Input = "Ctrl+Shift+F3"	},
            InputBinding_t { m_Context = "HammerEditorSession"	m_Command = "RestartParticleEffects"		m_Input = "Ctrl+Shift+F11"	},
            InputBinding_t { m_Context = "HammerEditorSession"	m_Command = "UpdateAllIsoSurfaces"			m_Input = "Ctrl+Alt+I"		},
            InputBinding_t { m_Context = "HammerEditorSession"	m_Command = "AttachViewToObject"			m_Input = "Ctrl+Shift+Ins"	},
            InputBinding_t { m_Context = "HammerEditorSession" 	m_Command = "RandomizeChoices"				m_Input = "Alt+G"			},


            
            InputBinding_t { m_Context = "ToolPivotPicker"		m_Command = "PlacePivot"					m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolPivotPicker"		m_Command = "ToggleSnapping"				m_Input = "TOGGLE_SNAPPING_KEY"	},
            
            InputBinding_t { m_Context = "SelectionSetEditor"	m_Command = "DeleteSelectionSet"		m_Input = "Del"					},
            InputBinding_t { m_Context = "SelectionSetEditor" 	m_Command = "SelectionAddModifier"		m_Input = "SELECTION_ADD_KEY"	},
            InputBinding_t { m_Context = "SelectionSetEditor" 	m_Command = "SelectionRemoveModifier"	m_Input = "SELECTION_REMOVE_KEY"},
            InputBinding_t { m_Context = "SelectionSetEditor" 	m_Command = "RenameSelectionSet"		m_Input = "F2"					},

            InputBinding_t { m_Context = "MapVariablesEditor"	m_Command = "DeleteSelected"			m_Input = "Del"					},

            InputBinding_t { m_Context = "ToolBlock" 		m_Command = "DragBlock"						m_Input = "LMouse"			},
            InputBinding_t { m_Context = "ToolBlock" 		m_Command = "Finish"						m_Input = "Enter"			},
            InputBinding_t { m_Context = "ToolBlock" 		m_Command = "Finish"						m_Input = "NumEnter"		},
            InputBinding_t { m_Context = "ToolBlock" 		m_Command = "Apply"							m_Input = "Space"			},
            InputBinding_t { m_Context = "ToolBlock" 		m_Command = "CancelCreate"					m_Input = "Esc"				},
            InputBinding_t { m_Context = "ToolBlock" 		m_Command = "ToggleSnapping"				m_Input = "TOGGLE_SNAPPING_KEY" },
            InputBinding_t { m_Context = "ToolBlock" 		m_Command = "AlignToSurface"				m_Input = "Shift"			},

            InputBinding_t { m_Context = "ToolPolygon" 		m_Command = "AddPoint"						m_Input = "LMouse"			},
            InputBinding_t { m_Context = "ToolPolygon" 		m_Command = "Finish"						m_Input = "Enter"			},
            InputBinding_t { m_Context = "ToolPolygon" 		m_Command = "Finish"						m_Input = "NumEnter"		},
            InputBinding_t { m_Context = "ToolPolygon"		m_Command = "Apply"							m_Input = "LMouseDoubleClick"},
            InputBinding_t { m_Context = "ToolPolygon"		m_Command = "Apply"							m_Input = "Space"			},
            InputBinding_t { m_Context = "ToolPolygon" 		m_Command = "Cancel"						m_Input = "Esc"				},

            InputBinding_t { m_Context = "ToolClipper" 		m_Command = "DragClip"						m_Input = "LMouse"			},
            InputBinding_t { m_Context = "ToolClipper" 		m_Command = "FinishClip"					m_Input = "Enter"			},
            InputBinding_t { m_Context = "ToolClipper" 		m_Command = "FinishClip"					m_Input = "NumEnter"		},
            InputBinding_t { m_Context = "ToolClipper" 		m_Command = "DoClip"						m_Input = "Space"			},
            InputBinding_t { m_Context = "ToolClipper" 		m_Command = "CancelClip"					m_Input = "Esc"				},
            InputBinding_t { m_Context = "ToolClipper" 		m_Command = "ToggleCreateCaps"				m_Input = "Ctrl+Shift+X"	},
            InputBinding_t { m_Context = "ToolClipper" 		m_Command = "ToggleSnapping"				m_Input = "TOGGLE_SNAPPING_KEY" },

            InputBinding_t { m_Context = "ToolTextureProjection"	m_Command = "Finish"				m_Input = "Enter"			},
            InputBinding_t { m_Context = "ToolTextureProjection"	m_Command = "Finish"				m_Input = "NumEnter"		},
            InputBinding_t { m_Context = "ToolTextureProjection"	m_Command = "Finish"				m_Input = "Space"			},
            InputBinding_t { m_Context = "ToolTextureProjection"	m_Command = "Cancel"				m_Input = "Esc"				},
            InputBinding_t { m_Context = "ToolTextureProjection"	m_Command = "ToggleSnapping"		m_Input = "TOGGLE_SNAPPING_KEY"	},
            InputBinding_t { m_Context = "ToolTextureProjection"	m_Command = "Translate"				m_Input = "Shift+T"				},
            InputBinding_t { m_Context = "ToolTextureProjection"	m_Command = "Rotate"				m_Input = "Shift+R"				},

            InputBinding_t { m_Context = "ToolMirror" 		m_Command = "DragPlane"						m_Input = "LMouse"			},
            InputBinding_t { m_Context = "ToolMirror" 		m_Command = "Finish"						m_Input = "Enter"			},
            InputBinding_t { m_Context = "ToolMirror" 		m_Command = "Finish"						m_Input = "NumEnter"		},
            InputBinding_t { m_Context = "ToolMirror" 		m_Command = "Apply"							m_Input = "Space"			},
            InputBinding_t { m_Context = "ToolMirror" 		m_Command = "Cancel"						m_Input = "Esc"				},
            InputBinding_t { m_Context = "ToolMirror" 		m_Command = "ToggleSnapping"				m_Input = "TOGGLE_SNAPPING_KEY" },

            InputBinding_t { m_Context = "ToolEntity" 		m_Command = "DragCreatePoint"				m_Input = "LMouse"			},
            InputBinding_t { m_Context = "ToolEntity" 		m_Command = "TraceAndCreate"				m_Input = "LMouse"			},
            InputBinding_t { m_Context = "ToolEntity" 		m_Command = "Create"						m_Input = "Enter"			},
            InputBinding_t { m_Context = "ToolEntity" 		m_Command = "Create"						m_Input = "NumEnter"		},
            InputBinding_t { m_Context = "ToolEntity" 		m_Command = "CancelCreate"					m_Input = "Esc"				},
            InputBinding_t { m_Context = "ToolEntity" 		m_Command = "ToggleSnapping"				m_Input = "TOGGLE_SNAPPING_KEY" },

            InputBinding_t { m_Context = "GizmoManipulator" 	m_Command = "Drag"									m_Input = "LMouse"			},
            InputBinding_t { m_Context = "GizmoManipulator" 	m_Command = "StampClone"							m_Input = "Shift"			},
            InputBinding_t { m_Context = "GizmoManipulator"		m_Command = "SetBoxManipulateAboutCenter"			m_Input = "K"				},
            InputBinding_t { m_Context = "GizmoManipulator"		m_Command = "SetBoxManipulateApplyUniformScaling"	m_Input = "J"				},
            InputBinding_t { m_Context = "GizmoManipulator"		m_Command = "LockedManipulation"					m_Input = "Shift"			},
            InputBinding_t { m_Context = "GizmoManipulator"		m_Command = "ToggleSnapping"						m_Input = "TOGGLE_SNAPPING_KEY"	},
            // private bindings not to be remapped by user. These should match ones ones in ToolSelection
            InputBinding_t { m_Context = "GizmoManipulator" 	m_Command = "GizmoApplyValue"				m_Input = "NumEnter"				},
            // End private

            InputBinding_t { m_Context = "SphereManipulator"	m_Command = "Drag"						m_Input = "LMouse"			},

            InputBinding_t { m_Context = "AxisRotatorManipulator"		m_Command = "Drag"				m_Input = "LMouse"			},
            InputBinding_t { m_Context = "AxisRotatorManipulator" 		m_Command = "ToggleSnapping"	m_Input = "TOGGLE_SNAPPING_KEY"			},

            InputBinding_t { m_Context = "BoxManipulator"		m_Command = "Drag"						m_Input = "LMouse"			},
            InputBinding_t { m_Context = "BoxManipulator"		m_Command = "ToggleSnapping"			m_Input = "TOGGLE_SNAPPING_KEY" },
            InputBinding_t { m_Context = "BoxManipulator"		m_Command = "ToggleEditEdgeFades"       m_Input = "Shift"             },

            InputBinding_t { m_Context = "RectangleManipulator"	m_Command = "Drag"						m_Input = "LMouse"			},
            InputBinding_t { m_Context = "RectangleManipulator"	m_Command = "ToggleSnapping"			m_Input = "TOGGLE_SNAPPING_KEY" },

            InputBinding_t { m_Context = "PointManipulator"		m_Command = "SelectPoint"				m_Input = "LMouse"			},

            InputBinding_t { m_Context = "PointOnLineManipulator" m_Command = "Drag"					m_Input = "LMouse"			},

            InputBinding_t { m_Context = "StaticPointManipulator" m_Command = "Click"					m_Input = "LMouse"			},
            InputBinding_t { m_Context = "StaticPointManipulator" m_Command = "MouseWheelUp"			m_Input = "MWheelUp"		},
            InputBinding_t { m_Context = "StaticPointManipulator" m_Command = "MouseWheelDown"			m_Input = "MWheelDn"		},

            InputBinding_t { m_Context = "BarnLightManipulator"		m_Command = "Drag"					m_Input = "LMouse"				},
            InputBinding_t { m_Context = "BarnLightManipulator"		m_Command = "ToggleSnapping"		m_Input = "TOGGLE_SNAPPING_KEY"	},
            InputBinding_t { m_Context = "BarnLightManipulator"		m_Command = "ResizeNear"			m_Input = "Shift"				},
            InputBinding_t { m_Context = "BarnLightManipulator"		m_Command = "ConstrainProportions"	m_Input = "Alt"				},

            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "ShrinkSelection"				m_Input = "NumSub"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "ShrinkSelection"				m_Input = "-"					},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "GrowSelection"					m_Input = "NumAdd"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "GrowSelection"					m_Input = "="					},			
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "AddToSelection"				m_Input = "Ctrl+Up"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "RemoveFromSelection"			m_Input = "Ctrl+Down"			},	
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "RemoveFromSelectionOldest"		m_Input = "Ctrl+Alt+Down"		},			
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "FlipNormals"					m_Input = "F"					},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "SelectLoop"					m_Input = "L"					},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "CutTool"						m_Input = "C"					},		
            InputBinding_t { m_Context = "ToolFaceSelection"	m_Command = "QuadSlice"						m_Input = "Ctrl+D"				},
            InputBinding_t { m_Context = "ToolFaceSelection"	m_Command = "JustifyCenter"					m_Input = "Ctrl+Shift+Ins"		},
            InputBinding_t { m_Context = "ToolFaceSelection"	m_Command = "JustifyLeft"					m_Input = "Ctrl+Shift+Home"		},
            InputBinding_t { m_Context = "ToolFaceSelection"	m_Command = "JustifyRight"					m_Input = "Ctrl+Shift+End"		},
            InputBinding_t { m_Context = "ToolFaceSelection"	m_Command = "JustifyTop"					m_Input = "Ctrl+Shift+PgUp"		},
            InputBinding_t { m_Context = "ToolFaceSelection"	m_Command = "JustifyBottom"					m_Input = "Ctrl+Shift+PgDn"		},
            InputBinding_t { m_Context = "ToolFaceSelection"	m_Command = "JustifyFit"					m_Input = "Ctrl+Shift+Del"		},
            InputBinding_t { m_Context = "ToolFaceSelection"	m_Command = "AlignWorld"					m_Input = "Ctrl+Shift+T"		},
            InputBinding_t { m_Context = "ToolFaceSelection"	m_Command = "AlignFace"						m_Input = "Ctrl+Shift+F"		},
            InputBinding_t { m_Context = "ToolFaceSelection"	m_Command = "AlignView"						m_Input = "V"					},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "Select"						m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "LassoSelect"					m_Input = "MMouse"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "TranslateLasso"				m_Input = "Space"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "SelectionAddModifier"			m_Input = "SELECTION_ADD_KEY"	},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "SelectionRemoveModifier"		m_Input = "SELECTION_REMOVE_KEY"},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "Extrude"						m_Input = "Shift"				},		
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "SelectContiguous"				m_Input = "LMouseDoubleClick"	},		
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "SelectContiguousFiltered"		m_Input = "Alt+LMouseDoubleClick" },		
            InputBinding_t { m_Context = "ToolFaceSelection"	m_Command = "WrapTexture"					m_Input = "Alt+RMouse"			},
            InputBinding_t { m_Context = "ToolFaceSelection"	m_Command = "WrapTextureToSelection"		m_Input = "Shift+Alt+RMouse"	},
            InputBinding_t { m_Context = "ToolFaceSelection"	m_Command = "TraceAndLiftMaterial"			m_Input = "Shift+RMouse"		},
            InputBinding_t { m_Context = "ToolFaceSelection"	m_Command = "PaintMaterial"					m_Input = "Ctrl+RMouse"			},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "NudgeUp"						m_Input = "Up"					},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "NudgeRotateUp"					m_Input = "Alt+Up"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "NudgeDown"						m_Input = "Down"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "NudgeRotateDown"				m_Input = "Alt+Down"			},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "NudgeLeft"						m_Input = "Left"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "NudgeRotateLeft"				m_Input = "Alt+Left"			},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "NudgeRight"					m_Input = "Right"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "NudgeRotateRight"				m_Input = "Alt+Right"			},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "ApplyMaterialToSelection"		m_Input = "Shift+T"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "ToggleSnapping"				m_Input = "TOGGLE_SNAPPING_KEY" },
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "Bridge"						m_Input = "B"					},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "BridgeTool"					m_Input = "Alt+B"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "Thicken"						m_Input = "G"					},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "Mirror"						m_Input = "M"					},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "NudgeTextureRight"				m_Input = "Mouse5"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "NudgeTextureLeft"				m_Input = "Mouse4"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "NudgeTextureUp"				m_Input = "Shift+Mouse5"		},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "NudgeTextureDown"				m_Input = "Shift+Mouse4"		},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "JustifyRight"					m_Input = "Ctrl+Mouse5"			},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "JustifyLeft"					m_Input = "Ctrl+Mouse4"			},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "JustifyTop"					m_Input = "Ctrl+Shift+Mouse5"	},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "JustifyBottom"					m_Input = "Ctrl+Shift+Mouse4"	},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "Combine"						m_Input = "Backspace"			},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "Collapse"						m_Input = "O"					},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "Detach"						m_Input = "N"					},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "Extract"						m_Input = "Alt+N"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "ClearPivot"					m_Input = "Home"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "CenterPivotInView"				m_Input = "Ctrl+Home"			},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "SetPivotToWorldOrigin"			m_Input = "Ctrl+End"			},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "EndPivotManipulation"			m_Input = "Ins"					},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "IncreaseSubdivisionLevel"		m_Input = ","					},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "DecreaseSubdivisionLevel"		m_Input = "."					},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "MoveObjectDownByTraceLocal"	m_Input = "Ctrl+Num1"			},	
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "MoveObjectDownByTrace"			m_Input = "Ctrl+Num2"			},	
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "NextTile"						m_Input = "Alt+F"				},	
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "PreviousTile"					m_Input = "Alt+V"				},	
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "RandomTile"					m_Input = "Alt+G"				},	
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "RotateTexture90CCW"			m_Input = "Alt+Q"				},	
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "RotateTexture90CW"				m_Input = "Alt+A"				},	
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "FlipTextureHorizontal"			m_Input = "Alt+D"				},	
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "FlipTextureVertical"			m_Input = "Alt+E"				},	
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "ApplyMaterialByHotspot"		m_Input = "Alt+H"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "FastTextureTool"				m_Input = "Ctrl+G"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "ToggleHotspotApplyMaterial"	m_Input = "Shift+Alt+G"			},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "ToggleHotspotTilingMode"		m_Input = "Shift+Alt+T"			},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "ToggleHotspotAllowRandom"		m_Input = "Shift+Alt+R"			},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "ToggleHotspotPerFace"			m_Input = "Shift+Alt+F"			},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "ToggleHotspotMappingMode"		m_Input = "Shift+Alt+D"			},


            // Private bindings not to be remapped by user. These should match ones ones in GizmoManipulator
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "GizmoNumKey0"					m_Input = "Num0"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "GizmoNumKey1"					m_Input = "Num1"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "GizmoNumKey2"					m_Input = "Num2"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "GizmoNumKey3"					m_Input = "Num3"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "GizmoNumKey4"					m_Input = "Num4"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "GizmoNumKey5"					m_Input = "Num5"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "GizmoNumKey6"					m_Input = "Num6"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "GizmoNumKey7"					m_Input = "Num7"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "GizmoNumKey8"					m_Input = "Num8"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "GizmoNumKey9"					m_Input = "Num9"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "GizmoNumKeyDecimal"			m_Input = "NumDec"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "GizmoComma"					m_Input = ","					},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "GizmoNumKeyMinus"				m_Input = "NumSub"				},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "GizmoClearValue"				m_Input = "Backspace"			},
            InputBinding_t { m_Context = "ToolFaceSelection" 	m_Command = "GizmoApplyValue"				m_Input = "NumEnter"			},
            // End private

            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "Select"					m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "LassoSelect"				m_Input = "MMouse"				},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "TranslateLasso"			m_Input = "Space"				},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "SelectionAddModifier"		m_Input = "SELECTION_ADD_KEY"	},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "SelectionRemoveModifier"	m_Input = "SELECTION_REMOVE_KEY"},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "GrowSelection"				m_Input = "NumAdd"				},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "GrowSelection"				m_Input = "="					},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "ShrinkSelection"			m_Input = "NumSub"				},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "ShrinkSelection"			m_Input = "-"					},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "AddToSelection"			m_Input = "Ctrl+Up"				},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "RemoveFromSelection"		m_Input = "Ctrl+Down"			},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "RemoveFromSelectionOldest"	m_Input = "Ctrl+Alt+Down"		},			
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "SelectLoop"				m_Input = "L"					},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "SelectContiguous"			m_Input = "LMouseDoubleClick"	},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "CutTool"					m_Input = "C"					},		
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "CreateNewEdge"				m_Input = "V"					},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "Merge"						m_Input = "M"					},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "SnapToVertex"				m_Input = "B"					},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "NudgeUp"					m_Input = "Up"					},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "NudgeRotateUp"				m_Input = "Alt+Up"				},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "NudgeDown"					m_Input = "Down"				},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "NudgeRotateDown"			m_Input = "Alt+Down"			},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "NudgeLeft"					m_Input = "Left"				},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "NudgeRotateLeft"			m_Input = "Alt+Left"			},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "NudgeRight"				m_Input = "Right"				},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "NudgeRotateRight"			m_Input = "Alt+Right"			},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "ToggleSnapping"			m_Input = "TOGGLE_SNAPPING_KEY" },
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "ClearPivot"				m_Input = "Home"				},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "CenterPivotInView"			m_Input = "Ctrl+Home"			},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "SetPivotToWorldOrigin"		m_Input = "Ctrl+End"			},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "EndPivotManipulation"		m_Input = "Ins"					},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "Bevel"						m_Input = "F"					},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "Extrude"					m_Input = "Shift"				},		
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "MoveObjectDownByTraceLocal" m_Input = "Ctrl+Num1"			},	
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "MoveObjectDownByTrace"		m_Input = "Ctrl+Num2"			},	
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "WeldUVs"					m_Input = "Ctrl+F"				},	

            // Private bindings not to be remapped by user. These should match ones ones in GizmoManipulator
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "GizmoNumKey0"					m_Input = "Num0"				},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "GizmoNumKey1"					m_Input = "Num1"				},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "GizmoNumKey2"					m_Input = "Num2"				},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "GizmoNumKey3"					m_Input = "Num3"				},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "GizmoNumKey4"					m_Input = "Num4"				},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "GizmoNumKey5"					m_Input = "Num5"				},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "GizmoNumKey6"					m_Input = "Num6"				},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "GizmoNumKey7"					m_Input = "Num7"				},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "GizmoNumKey8"					m_Input = "Num8"				},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "GizmoNumKey9"					m_Input = "Num9"				},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "GizmoNumKeyDecimal"			m_Input = "NumDec"				},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "GizmoComma"					m_Input = ","					},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "GizmoNumKeyMinus"				m_Input = "NumSub"				},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "GizmoClearValue"				m_Input = "Backspace"			},
            InputBinding_t { m_Context = "ToolVertexSelection" 	m_Command = "GizmoApplyValue"				m_Input = "NumEnter"			},
            // End private

            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "Select"					m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "LassoSelect"				m_Input = "MMouse"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "TranslateLasso"			m_Input = "Space"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "SelectionAddModifier"		m_Input = "SELECTION_ADD_KEY"	},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "SelectionRemoveModifier"	m_Input = "SELECTION_REMOVE_KEY"},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "ShrinkSelection"			m_Input = "NumSub"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "ShrinkSelection"			m_Input = "-"					},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "GrowSelection"				m_Input = "NumAdd"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "GrowSelection"				m_Input = "="					},				
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "AddToSelection"			m_Input = "Ctrl+Up"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "RemoveFromSelection"		m_Input = "Ctrl+Down"			},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "RemoveFromSelectionOldest"	m_Input = "Ctrl+Alt+Down"		},			
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "CutTool"					m_Input = "C"					},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "ArcTool"					m_Input = "Y"					},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "SelectSingleLoop"			m_Input = "LMouseDoubleClick"	},	
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "SelectLoop"				m_Input = "L"					},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "SelectRing"				m_Input = "G"					},	
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "SelectRibs"				m_Input = "Ctrl+G"				},	
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "CreatePolygonFromEdges"	m_Input = "P"					},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "Dissolve"					m_Input = "Backspace"			},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "DissolveAgressive"			m_Input = "Shift+Backspace"		},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "Bridge"					m_Input = "B"					},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "BridgeTool"				m_Input = "Alt+B"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "Merge"						m_Input = "M"					},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "Split"						m_Input = "Alt+N"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "SnapEdgeToEdge"			m_Input = "I"					},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "Extrude"					m_Input = "X"					},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "Extend"					m_Input = "N"					},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "Connect"					m_Input = "V"					},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "Bevel"						m_Input = "Alt+F"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "BevelTool"					m_Input = "F"					},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "Collapse"					m_Input = "O"					},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "SetNormalsHard"			m_Input = "H"					},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "SetNormalsSoft"			m_Input = "J"					},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "SetNormalsDefault"			m_Input = "K"					},		
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "ToggleSnapping"			m_Input = "TOGGLE_SNAPPING_KEY" },
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "TransformExtrude"			m_Input = "Shift"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "ClearPivot"				m_Input = "Home"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "CenterPivotInView"			m_Input = "Ctrl+Home"			},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "SetPivotToWorldOrigin"		m_Input = "Ctrl+End"			},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "EndPivotManipulation"		m_Input = "Ins"					},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "MoveObjectDownByTraceLocal" m_Input = "Ctrl+Num1"			},	
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "MoveObjectDownByTrace"		m_Input = "Ctrl+Num2"			},	
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "WeldUVs"					m_Input = "Ctrl+F"				},	


            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "NudgeUp"					m_Input = "Up"					},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "NudgeRotateUp"				m_Input = "Alt+Up"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "NudgeDown"					m_Input = "Down"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "NudgeRotateDown"			m_Input = "Alt+Down"			},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "NudgeLeft"					m_Input = "Left"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "NudgeRotateLeft"			m_Input = "Alt+Left"			},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "NudgeRight"				m_Input = "Right"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "NudgeRotateRight"			m_Input = "Alt+Right"			},
            // Private bindings not to be remapped by user. These should match ones ones in GizmoManipulator
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "GizmoNumKey0"				m_Input = "Num0"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "GizmoNumKey1"				m_Input = "Num1"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "GizmoNumKey2"				m_Input = "Num2"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "GizmoNumKey3"				m_Input = "Num3"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "GizmoNumKey4"				m_Input = "Num4"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "GizmoNumKey5"				m_Input = "Num5"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "GizmoNumKey6"				m_Input = "Num6"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "GizmoNumKey7"				m_Input = "Num7"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "GizmoNumKey8"				m_Input = "Num8"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "GizmoNumKey9"				m_Input = "Num9"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "GizmoNumKeyDecimal"		m_Input = "NumDec"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "GizmoComma"				m_Input = ","					},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "GizmoNumKeyMinus"			m_Input = "NumSub"				},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "GizmoClearValue"			m_Input = "Backspace"			},
            InputBinding_t { m_Context = "ToolEdgeSelection" 	m_Command = "GizmoApplyValue"			m_Input = "NumEnter"			},
            // End private

            InputBinding_t { m_Context = "ToolEdgeCut" 			m_Command = "CutEdge"					m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolEdgeCut" 			m_Command = "Finish"					m_Input = "Enter"				},
            InputBinding_t { m_Context = "ToolEdgeCut" 			m_Command = "Finish"					m_Input = "NumEnter"			},
            InputBinding_t { m_Context = "ToolEdgeCut" 			m_Command = "Apply"						m_Input = "Space"				},
            InputBinding_t { m_Context = "ToolEdgeCut" 			m_Command = "Cancel"					m_Input = "Esc"					},
            InputBinding_t { m_Context = "ToolEdgeCut" 			m_Command = "ToggleSnapping"			m_Input = "TOGGLE_SNAPPING_KEY" },
            InputBinding_t { m_Context = "ToolEdgeCut" 			m_Command = "AlignedSnap"				m_Input = "Shift"				},
            InputBinding_t { m_Context = "ToolEdgeCut" 			m_Command = "PlaceCut"					m_Input = "B"					},
            InputBinding_t { m_Context = "ToolEdgeCut" 			m_Command = "PlaceCut"					m_Input = "Ctrl+B"				},
            InputBinding_t { m_Context = "ToolEdgeCut" 			m_Command = "ToggleLoopCut"				m_Input = "V"					},
            InputBinding_t { m_Context = "ToolEdgeCut" 			m_Command = "ToggleLoopCutEven"			m_Input = "E"					},
            InputBinding_t { m_Context = "ToolEdgeCut" 			m_Command = "ToggleLoopCutFlip"			m_Input = "F"					},

            InputBinding_t { m_Context = "ToolVertexNormalPaint" 	m_Command = "Paint"					m_Input = "LMouse"		},
            InputBinding_t { m_Context = "ToolVertexNormalPaint" 	m_Command = "Erase"					m_Input = "Ctrl"		},
            InputBinding_t { m_Context = "ToolVertexNormalPaint" 	m_Command = "ScaleBrush"			m_Input = "MMouse"		},
            InputBinding_t { m_Context = "ToolVertexNormalPaint" 	m_Command = "FreezeNormal"			m_Input = "Shift"		},

            InputBinding_t { m_Context = "ToolEdgeArc" 			m_Command = "AdjustParameters"			m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolEdgeArc" 			m_Command = "Finish"					m_Input = "Enter"				},
            InputBinding_t { m_Context = "ToolEdgeArc" 			m_Command = "Finish"					m_Input = "NumEnter"			},
            InputBinding_t { m_Context = "ToolEdgeArc" 			m_Command = "Apply"						m_Input = "Space"				},
            InputBinding_t { m_Context = "ToolEdgeArc" 			m_Command = "Cancel"					m_Input = "Esc"					},
            InputBinding_t { m_Context = "ToolEdgeArc" 			m_Command = "LockToAxis"				m_Input = "Shift"				},
            InputBinding_t { m_Context = "ToolEdgeArc" 			m_Command = "IncreaseNumSteps"			m_Input = "F"					},
            InputBinding_t { m_Context = "ToolEdgeArc" 			m_Command = "DecreaseNumSteps"			m_Input = "V"					},
            InputBinding_t { m_Context = "ToolEdgeArc" 			m_Command = "ToggleSnapping"			m_Input = "TOGGLE_SNAPPING_KEY" },

            InputBinding_t { m_Context = "ToolFastTexture" 		m_Command = "Finish"					m_Input = "Enter"				},
            InputBinding_t { m_Context = "ToolFastTexture" 		m_Command = "Finish"					m_Input = "NumEnter"			},
            InputBinding_t { m_Context = "ToolFastTexture" 		m_Command = "Finish"					m_Input = "Space"				},
            InputBinding_t { m_Context = "ToolFastTexture"		m_Command = "Finish"					m_Input = "Ctrl+G"				},
            InputBinding_t { m_Context = "ToolFastTexture" 		m_Command = "Cancel"					m_Input = "Esc"					},
            InputBinding_t { m_Context = "ToolFastTexture" 		m_Command = "ToggleFlipHorizontal"		m_Input = "F"					},
            InputBinding_t { m_Context = "ToolFastTexture" 		m_Command = "ToggleFlipVertical"		m_Input = "V"					},
            InputBinding_t { m_Context = "ToolFastTexture" 		m_Command = "TogglePrimaryAxis"			m_Input = "X"					},
            InputBinding_t { m_Context = "ToolFastTexture" 		m_Command = "MappingUnwrapSquare"		m_Input = "1"					},
            InputBinding_t { m_Context = "ToolFastTexture" 		m_Command = "MappingUnwrapConforming"	m_Input = "2"					},
            InputBinding_t { m_Context = "ToolFastTexture" 		m_Command = "MappingUnwrapQuads"		m_Input = "3"					},
            InputBinding_t { m_Context = "ToolFastTexture" 		m_Command = "MappingPlanar"				m_Input = "4"					},
            InputBinding_t { m_Context = "ToolFastTexture" 		m_Command = "MappingUseExisting"		m_Input = "5"					},
            InputBinding_t { m_Context = "ToolFastTexture" 		m_Command = "SmallerGrid"				m_Input = "["					},
            InputBinding_t { m_Context = "ToolFastTexture" 		m_Command = "BiggerGrid"				m_Input = "]"					},
            InputBinding_t { m_Context = "ToolFastTexture" 		m_Command = "DecreaseInset"				m_Input = "NumSub"				},
            InputBinding_t { m_Context = "ToolFastTexture" 		m_Command = "IncreaseInset"				m_Input = "NumAdd"				},
            InputBinding_t { m_Context = "ToolFastTexture" 		m_Command = "DecreaseInset"				m_Input = "-"					},
            InputBinding_t { m_Context = "ToolFastTexture" 		m_Command = "IncreaseInset"				m_Input = "="					},
            
            InputBinding_t { m_Context = "ToolFastTexture_UVWidget" m_Command = "ResetMappingBounds"	m_Input = "Shift+LMouseDoubleClick"	},
            InputBinding_t { m_Context = "ToolFastTexture_UVWidget" m_Command = "PickRectangle"			m_Input = "LMouseDoubleClick"	},
            InputBinding_t { m_Context = "ToolFastTexture_UVWidget" m_Command = "Drag"					m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolFastTexture_UVWidget" m_Command = "Drag"					m_Input = "Alt+LMouse"			},
            InputBinding_t { m_Context = "ToolFastTexture_UVWidget" m_Command = "NudgeUp"				m_Input = "Up"					},
            InputBinding_t { m_Context = "ToolFastTexture_UVWidget" m_Command = "NudgeDown"				m_Input = "Down"				},
            InputBinding_t { m_Context = "ToolFastTexture_UVWidget" m_Command = "NudgeLeft"				m_Input = "Left"				},
            InputBinding_t { m_Context = "ToolFastTexture_UVWidget" m_Command = "NudgeRight"			m_Input = "Right"				},
            InputBinding_t { m_Context = "ToolFastTexture_UVWidget" m_Command = "BeginPickEdge"			m_Input = "E"					},
            InputBinding_t { m_Context = "ToolFastTexture_UVWidget" m_Command = "CancelPickEdge"		m_Input = "Esc"					},
            InputBinding_t { m_Context = "ToolFastTexture_UVWidget" m_Command = "PickEdge"				m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolFastTexture_UVWidget" m_Command = "DrawRectangle"			m_Input = "Alt"					},
            InputBinding_t { m_Context = "ToolFastTexture_UVWidget" m_Command = "DisableSnapping"		m_Input = "TOGGLE_SNAPPING_KEY"	},
            
            InputBinding_t { m_Context = "ToolBridge" 			m_Command = "AdjustParameters"			m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolBridge" 			m_Command = "Finish"					m_Input = "Enter"				},
            InputBinding_t { m_Context = "ToolBridge" 			m_Command = "Finish"					m_Input = "NumEnter"			},
            InputBinding_t { m_Context = "ToolBridge" 			m_Command = "Apply"						m_Input = "Space"				},
            InputBinding_t { m_Context = "ToolBridge" 			m_Command = "Cancel"					m_Input = "Esc"					},
            InputBinding_t { m_Context = "ToolBridge" 			m_Command = "IncreaseNumSteps"			m_Input = "F"					},
            InputBinding_t { m_Context = "ToolBridge" 			m_Command = "DecreaseNumSteps"			m_Input = "V"					},
            InputBinding_t { m_Context = "ToolBridge" 			m_Command = "FreeDrag"					m_Input = "Shift"				},
            InputBinding_t { m_Context = "ToolBridge" 			m_Command = "LockPoints"				m_Input = "Ctrl"				},


            InputBinding_t { m_Context = "ToolBevel" 			m_Command = "Finish"					m_Input = "Enter"				},
            InputBinding_t { m_Context = "ToolBevel" 			m_Command = "Finish"					m_Input = "NumEnter"			},
            InputBinding_t { m_Context = "ToolBevel" 			m_Command = "Finish"					m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolBevel" 			m_Command = "Apply"						m_Input = "Space"				},
            InputBinding_t { m_Context = "ToolBevel" 			m_Command = "Cancel"					m_Input = "Esc"					},
            InputBinding_t { m_Context = "ToolBevel" 			m_Command = "AdjustSteps"				m_Input = "C"					},
            InputBinding_t { m_Context = "ToolBevel" 			m_Command = "AdjustWidth"				m_Input = "F"					},
            InputBinding_t { m_Context = "ToolBevel" 			m_Command = "AdjustShape"				m_Input = "V"					},
            InputBinding_t { m_Context = "ToolBevel"			m_Command = "ToggleSnapping"			m_Input = "TOGGLE_SNAPPING_KEY"	},

            InputBinding_t { m_Context = "ToolPainting" 		m_Command = "CycleChannelsForward"		m_Input = "C"					},
            InputBinding_t { m_Context = "ToolPainting" 		m_Command = "CycleChannelsBackward"		m_Input = "Shift+C"				},
            InputBinding_t { m_Context = "ToolPainting" 		m_Command = "CycleChannelsForward"		m_Input = "Mouse5"				},
            InputBinding_t { m_Context = "ToolPainting" 		m_Command = "CycleChannelsBackward"		m_Input = "Mouse4"				},
            InputBinding_t { m_Context = "ToolPainting" 		m_Command = "PaintSecondaryBlend"		m_Input = "Shift"				},
            InputBinding_t { m_Context = "ToolPainting" 		m_Command = "Erase"						m_Input = "Ctrl"				},
            InputBinding_t { m_Context = "ToolPainting" 		m_Command = "Paint"						m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolPainting" 		m_Command = "ScaleBrush"				m_Input = "MMouse"				},
            InputBinding_t { m_Context = "ToolPainting" 		m_Command = "AdjustHardness"			m_Input = "Shift"				},
            InputBinding_t { m_Context = "ToolPainting"			m_Command = "TraceAndLiftMaterial"		m_Input = "Shift+RMouse"		},
            InputBinding_t { m_Context = "ToolPainting"			m_Command = "DropTool"					m_Input = "Esc"					},
            InputBinding_t { m_Context = "ToolPainting"			m_Command = "NoOpDoubleClick"			m_Input = "LMouseDoubleClick"	},
            InputBinding_t { m_Context = "ToolPainting"			m_Command = "FloodFill"					m_Input = "Backspace"			},
            InputBinding_t { m_Context = "ToolPainting" 		m_Command = "SampleVertexColor"			m_Input = "V"					},

            InputBinding_t { m_Context = "ToolStaticOverlay"	m_Command = "BrushScaleUp"				m_Input = "MWheelUp"			},
            InputBinding_t { m_Context = "ToolStaticOverlay"	m_Command = "BrushScaleDn"				m_Input = "MWheelDn"			},
            InputBinding_t { m_Context = "ToolStaticOverlay"	m_Command = "BrushRotCW"				m_Input = "Ctrl+MWheelUp"		},
            InputBinding_t { m_Context = "ToolStaticOverlay"	m_Command = "BrushRotCCW"				m_Input = "Ctrl+MWheelDn"		},
            InputBinding_t { m_Context = "ToolStaticOverlay"	m_Command = "BrushDepthUp"				m_Input = "Shift+MWheelUp"		},
            InputBinding_t { m_Context = "ToolStaticOverlay"	m_Command = "BrushDepthDn"				m_Input = "Shift+MWheelDn"		},
            InputBinding_t { m_Context = "ToolStaticOverlay"	m_Command = "BrushAspectUp"				m_Input = "Ctrl+Shift+MWheelUp"	},
            InputBinding_t { m_Context = "ToolStaticOverlay"	m_Command = "BrushAspectDn"				m_Input = "Ctrl+Shift+MWheelDn"	},
            InputBinding_t { m_Context = "ToolStaticOverlay"	m_Command = "PosOffsetUp"				m_Input = "Up"					},
            InputBinding_t { m_Context = "ToolStaticOverlay"	m_Command = "PosOffsetDn"				m_Input = "Down"				},
            InputBinding_t { m_Context = "ToolStaticOverlay"	m_Command = "ResetTransforms"			m_Input = "Ctrl+R"				},
            InputBinding_t { m_Context = "ToolStaticOverlay"	m_Command = "CreateMode"				m_Input = "1"					},
            InputBinding_t { m_Context = "ToolStaticOverlay"	m_Command = "DeleteMode"				m_Input = "2"					},
            InputBinding_t { m_Context = "ToolStaticOverlay"	m_Command = "LocalizeMode"				m_Input = "3"					},
            InputBinding_t { m_Context = "ToolStaticOverlay"	m_Command = "CycleHotspotUp"			m_Input = "Ctrl+Up"				},
            InputBinding_t { m_Context = "ToolStaticOverlay"	m_Command = "CycleHotspotDn"			m_Input = "Ctrl+Down"			},
            InputBinding_t { m_Context = "ToolStaticOverlay"	m_Command = "ApplyTool"					m_Input = "Space"				},
            InputBinding_t { m_Context = "ToolStaticOverlay"	m_Command = "ApplyAndCloseTool"			m_Input = "Enter"				},
            InputBinding_t { m_Context = "ToolStaticOverlay"	m_Command = "DropTool"					m_Input = "Esc"					},
            InputBinding_t { m_Context = "ToolStaticOverlay"	m_Command = "LMouse"					m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolStaticOverlay"	m_Command = "LMouseAdd"					m_Input = "Shift+LMouse"		},
            InputBinding_t { m_Context = "ToolStaticOverlay"	m_Command = "LMouseRemove"				m_Input = "Ctrl+LMouse"			},
            InputBinding_t { m_Context = "ToolStaticOverlay"	m_Command = "ToggleAspect"				m_Input = "X"					},

            InputBinding_t { m_Context = "ToolAssetSpray" 		m_Command = "Spray"						m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolAssetSpray" 		m_Command = "Erase"						m_Input = "Alt+LMouse"			},
            InputBinding_t { m_Context = "ToolAssetSpray" 		m_Command = "ScaleBrush"				m_Input = "MMouse"				},
            
            InputBinding_t { m_Context = "ToolPhysics"		m_Command = "Select"						m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolPhysics" 		m_Command = "Select"						m_Input = "LMouseDoubleClick"	},
            InputBinding_t { m_Context = "ToolPhysics"		m_Command = "Grab"							m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolPhysics"		m_Command = "BoxSelect"						m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolPhysics"		m_Command = "LassoSelect"					m_Input = "MMouse"				},
            InputBinding_t { m_Context = "ToolPhysics"		m_Command = "TranslateLasso"				m_Input = "Space"				},
            InputBinding_t { m_Context = "ToolPhysics"		m_Command = "AddObjectToSelection"			m_Input = "SELECTION_ADD_KEY"	},
            InputBinding_t { m_Context = "ToolPhysics"		m_Command = "RemoveObjectFromSelection"		m_Input = "SELECTION_REMOVE_KEY"},
            InputBinding_t { m_Context = "ToolPhysics" 		m_Command = "ToggleSnapping"				m_Input = "TOGGLE_SNAPPING_KEY" },
            InputBinding_t { m_Context = "ToolPhysics"		m_Command = "ToggleSimulation"				m_Input = "Space"				},
            InputBinding_t { m_Context = "ToolPhysics"		m_Command = "SnapshotSimulation"			m_Input = "G"					},
            InputBinding_t { m_Context = "ToolPhysics" 		m_Command = "ClearSelection"				m_Input = "Esc"					},
            InputBinding_t { m_Context = "ToolPhysics" 		m_Command = "BeginPinPlacement"				m_Input = "F"					},
            InputBinding_t { m_Context = "ToolPhysics" 		m_Command = "AbortPinPlacement"				m_Input = "Esc"					},
            InputBinding_t { m_Context = "ToolPhysics" 		m_Command = "PlacePin"						m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolPhysics" 		m_Command = "TranslateMode"					m_Input = "T"					},
            InputBinding_t { m_Context = "ToolPhysics" 		m_Command = "RotateMode"					m_Input = "R"					},
            InputBinding_t { m_Context = "ToolPhysics" 		m_Command = "ScaleMode"						m_Input = "E"					},
                    
            InputBinding_t { m_Context = "ToolPath"			m_Command = "PlacePathNode"					m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolPath" 		m_Command = "Finish"						m_Input = "Enter"				},
            InputBinding_t { m_Context = "ToolPath" 		m_Command = "Finish"						m_Input = "NumEnter"			},
            InputBinding_t { m_Context = "ToolPath" 		m_Command = "Apply"							m_Input = "Space"				},
            InputBinding_t { m_Context = "ToolPath" 		m_Command = "Cancel"						m_Input = "Esc"					},

            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "Select"						m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "BoxSelect"						m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "LassoSelect"					m_Input = "MMouse"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "TranslateLasso"				m_Input = "Space"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "MoveSelected"					m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "SelectAndMove2D"				m_Input = "Alt+LMouse"			},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "AddObjectToSelection"			m_Input = "SELECTION_ADD_KEY"	},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "RemoveObjectFromSelection"		m_Input = "SELECTION_REMOVE_KEY"},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "ToggleSnapping"				m_Input = "TOGGLE_SNAPPING_KEY" },
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "StampClone"					m_Input = "Shift"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "CloneSelection"				m_Input = "Shift"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "ToggleAlignToSurface"			m_Input = "Alt"					},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "SelectNext"					m_Input = "PgUp"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "SelectPrev"					m_Input = "PgDn"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "CancelSelectOperation"			m_Input = "Esc"					},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "ShrinkGizmo"					m_Input = "Ctrl+NumSub"			},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "EnlargeGizmo"					m_Input = "Ctrl+NumAdd"			},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "NextPivotTap"					m_Input = "N"					},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "NextPivotCycle"				m_Input = "N+MWheelUp"			},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "PrevPivotCycle"				m_Input = "N+MWheelDn"			},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "ClearPivot"					m_Input = "Home"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "CenterPivotInView"				m_Input = "Ctrl+Home"			},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "SetPivotToWorldOrigin"			m_Input = "Ctrl+End"			},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "EndPivotManipulation"			m_Input = "Ins"					},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "FlipNormals"					m_Input = "F"					},
            InputBinding_t { m_Context = "ToolSelection"	m_Command = "MergeSelectedMeshes"			m_Input = "M"					},
            InputBinding_t { m_Context = "ToolSelection"	m_Command = "SeparateMeshComponents"		m_Input = "Alt+N"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "NudgeUp"						m_Input = "Up"					},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "NudgeRotateUp"					m_Input = "Alt+Up"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "NudgeDown"						m_Input = "Down"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "NudgeRotateDown"				m_Input = "Alt+Down"			},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "NudgeLeft"						m_Input = "Left"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "NudgeRotateLeft"				m_Input = "Alt+Left"			},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "NudgeRight"					m_Input = "Right"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "NudgeRotateRight"				m_Input = "Alt+Right"			},
            InputBinding_t { m_Context = "ToolSelection"	m_Command = "ApplyMaterial"					m_Input = "Shift+T"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "GizmoDebugHook"				m_Input = "\\"					},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "SetOriginToCenter"				m_Input = "End"					},	
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "ClearRotationAndScale"			m_Input = "Ctrl+Num0"			},	
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "MoveObjectDownByTraceLocal"	m_Input = "Ctrl+Num1"			},	
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "MoveObjectDownByTrace"			m_Input = "Ctrl+Num2"			},
            InputBinding_t { m_Context = "ToolSelection"	m_Command = "ShowObjectProperties"			m_Input = "Alt+Enter"			},	
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "GrowSelection"					m_Input = "NumAdd"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "GrowSelection"					m_Input = "="					},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "ShrinkSelection"				m_Input = "NumSub"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "ShrinkSelection"				m_Input = "-"					},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "SetOriginToPivot"				m_Input = "Ctrl+D"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "AlignObjects"					m_Input = "Alt+T"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "AlignObjectsRotation"			m_Input = "Alt+R"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "AlignObjectsToWorkplane"		m_Input = "Alt+E"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "AlignWorkplaneToObject"		m_Input = "Alt+Q"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "NextVariation"					m_Input = "Alt+F"				},	
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "PreviousVariation"				m_Input = "Alt+V"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "HideElement"					m_Input = "Alt+B"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "ResetConfiguration"			m_Input = "Alt+M"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "ReevaluateConfiguration"		m_Input = "Ctrl+F"				},


            
            // Private bindings not to be remapped by user. These should match ones ones in GizmoManipulator
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "GizmoNumKey0"					m_Input = "Num0"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "GizmoNumKey1"					m_Input = "Num1"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "GizmoNumKey2"					m_Input = "Num2"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "GizmoNumKey3"					m_Input = "Num3"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "GizmoNumKey4"					m_Input = "Num4"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "GizmoNumKey5"					m_Input = "Num5"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "GizmoNumKey6"					m_Input = "Num6"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "GizmoNumKey7"					m_Input = "Num7"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "GizmoNumKey8"					m_Input = "Num8"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "GizmoNumKey9"					m_Input = "Num9"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "GizmoNumKeyDecimal"			m_Input = "NumDec"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "GizmoComma"					m_Input = ","					},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "GizmoNumKeyMinus"				m_Input = "NumSub"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "GizmoClearValue"				m_Input = "Backspace"				},
            InputBinding_t { m_Context = "ToolSelection" 	m_Command = "GizmoApplyValue"				m_Input = "NumEnter"				},
            // End private
            
            InputBinding_t { m_Context = "ToolmeshDisplacement"		m_Command = "ModePushPull"					m_Input = "F"				},
            InputBinding_t { m_Context = "ToolmeshDisplacement"		m_Command = "ModeFlatten"					m_Input = "G"				},
            InputBinding_t { m_Context = "ToolmeshDisplacement"		m_Command = "ModeMove"						m_Input = "H"				},
            InputBinding_t { m_Context = "ToolmeshDisplacement"		m_Command = "ModeInflate"					m_Input = "Z"				},
            InputBinding_t { m_Context = "ToolmeshDisplacement"		m_Command = "ModeClay"						m_Input = "C"				},
            InputBinding_t { m_Context = "ToolmeshDisplacement"		m_Command = "ModePinch"						m_Input = "V"				},
            InputBinding_t { m_Context = "ToolmeshDisplacement"		m_Command = "ModeErase"						m_Input = "X"				},
            InputBinding_t { m_Context = "ToolmeshDisplacement"		m_Command = "ModeSmooth"					m_Input = "B"				},		
            InputBinding_t { m_Context = "ToolmeshDisplacement"		m_Command = "PickNormal"					m_Input = "Ctrl+RMouse"		},
            InputBinding_t { m_Context = "ToolmeshDisplacement"		m_Command = "ResetNormal"					m_Input = "Ctrl+Alt+RMouse"	},
            InputBinding_t { m_Context = "ToolmeshDisplacement"		m_Command = "Paint"							m_Input = "LMouse"			},
            InputBinding_t { m_Context = "ToolmeshDisplacement"		m_Command = "AdjustRadius"					m_Input = "MMouse"			},
            InputBinding_t { m_Context = "ToolmeshDisplacement"		m_Command = "SmoothModifier"				m_Input = "Shift"			},
            InputBinding_t { m_Context = "ToolmeshDisplacement"		m_Command = "EraseModifer"					m_Input = "Ctrl+Shift"		},
            InputBinding_t { m_Context = "ToolmeshDisplacement"		m_Command = "ReverseModifier"				m_Input = "Ctrl"			},
            InputBinding_t { m_Context = "ToolmeshDisplacement" 	m_Command = "DropTool"						m_Input = "Space"			},
            InputBinding_t { m_Context = "ToolmeshDisplacement" 	m_Command = "DropTool"						m_Input = "Esc"				},
            
            InputBinding_t { m_Context = "ToolPickEntity"			m_Command = "Pick"							m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolPickEntity"			m_Command = "SelectionAddModifier"			m_Input = "SELECTION_ADD_KEY"	},
            InputBinding_t { m_Context = "ToolPickEntity"			m_Command = "SelectionRemoveModifier"		m_Input = "SELECTION_REMOVE_KEY"},
            InputBinding_t { m_Context = "ToolPickEntity"			m_Command = "CancelTool"					m_Input = "Esc"	},
            InputBinding_t { m_Context = "ToolPickEntity"			m_Command = "FinishTool"					m_Input = "Enter" },

            InputBinding_t { m_Context = "ToolPlaceNavWalkable"		m_Command = "Place"							m_Input = "LMouse" },
            InputBinding_t { m_Context = "ToolPlaceNavWalkable"		m_Command = "CancelTool"					m_Input = "Esc"	},

            InputBinding_t { m_Context = "ToolWorkPlane"			m_Command = "PickWorkPlaneFromSurface"		m_Input = "LMouse" },
            InputBinding_t { m_Context = "ToolWorkPlane"			m_Command = "PickWorkPlaneFromObject"		m_Input = "Shift+LMouse" },
            InputBinding_t { m_Context = "ToolWorkPlane"			m_Command = "WorkPlaneModeTranslate"		m_Input = "Shift+T" },
            InputBinding_t { m_Context = "ToolWorkPlane"			m_Command = "WorkPlaneModeRotate"			m_Input = "Shift+R" },
            InputBinding_t { m_Context = "ToolWorkPlane"			m_Command = "ToggleSnapping"				m_Input = "TOGGLE_SNAPPING_KEY" },
            InputBinding_t { m_Context = "ToolWorkPlane"			m_Command = "ResetWorkPlaneAndDropTool"		m_Input = "Esc" },
            InputBinding_t { m_Context = "ToolWorkPlane"			m_Command = "DropTool"						m_Input = "Space" },
            InputBinding_t { m_Context = "ToolWorkPlane"			m_Command = "DropTool"						m_Input = "Enter" },
                
            InputBinding_t { m_Context = "ToolTerrain"				m_Command = "AdjustBrush"					m_Input = "MMouse"				},
            InputBinding_t { m_Context = "ToolTerrain" 				m_Command = "AdjustBrushPressure"			m_Input = "Ctrl"				},
            InputBinding_t { m_Context = "ToolTerrain"				m_Command = "ApplyBrush"					m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolTerrain" 				m_Command = "ApplyBrushErase"				m_Input = "Ctrl"				},
            InputBinding_t { m_Context = "ToolTerrain" 				m_Command = "ApplyBrushSmooth"				m_Input = "Shift"				},
            InputBinding_t { m_Context = "ToolTerrain" 				m_Command = "ApplyBrushAlternate"			m_Input = "Alt"					},

            InputBinding_t { m_Context = "TerrainGraphEditor" 		m_Command = "DeleteSelected"				m_Input = "Del"					},

            InputBinding_t { m_Context = "TerrainGraphEditorView" 	m_Command = "PanView"						m_Input = "RMouse"				},
            InputBinding_t { m_Context = "TerrainGraphEditorView" 	m_Command = "PanView"						m_Input = "Alt+MMouse"			},
            InputBinding_t { m_Context = "TerrainGraphEditorView" 	m_Command = "ZoomView"						m_Input = "Alt+RMouse"			},
            InputBinding_t { m_Context = "TerrainGraphEditorView" 	m_Command = "ZoomViewInStep"				m_Input = "MWheelUp"			},
            InputBinding_t { m_Context = "TerrainGraphEditorView" 	m_Command = "ZoomViewOutStep"				m_Input = "MWheelDn"			},
            InputBinding_t { m_Context = "TerrainGraphEditorView" 	m_Command = "FitSelectionInView"			m_Input = "Shift+A"				},
            InputBinding_t { m_Context = "TerrainGraphEditorView" 	m_Command = "FitSelectionInView"			m_Input = "F"					},
            InputBinding_t { m_Context = "TerrainGraphEditorView" 	m_Command = "FitAllInView"					m_Input = "A"					},

            
            //------------------------------------------------------------------------------------------
            // Tile Editor Bindings				
            //------------------------------------------------------------------------------------------

            // All modes
            InputBinding_t { m_Context = "ToolDotaTileEditor"		m_Command = "ModeBrushHeight"				m_Input = "Q"					},		
            InputBinding_t { m_Context = "ToolDotaTileEditor"		m_Command = "ModeBrushWater"				m_Input = "E"					},
            InputBinding_t { m_Context = "ToolDotaTileEditor"		m_Command = "ModeBrushPath"					m_Input = "R"					},	
            InputBinding_t { m_Context = "ToolDotaTileEditor"		m_Command = "ModeBrushTrees"				m_Input = "T"					},
            InputBinding_t { m_Context = "ToolDotaTileEditor"		m_Command = "ModeBrushPlants"				m_Input = "Y"					},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "ModeBrushBlends"				m_Input = "O"					},	
            InputBinding_t { m_Context = "ToolDotaTileEditor"		m_Command = "ModeEditObjects"				m_Input = "U"					},	
            InputBinding_t { m_Context = "ToolDotaTileEditor"		m_Command = "ModeSelect"					m_Input = "I"					},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "ModeEnableDisableTiles"		m_Input = "H"					},	
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "CycleModeForward"				m_Input = "Space"				},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "CycleModeBack"					m_Input = "Shift+Space"			},

            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "NextVariation"					m_Input = "F"					},	
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "PreviousVariation"				m_Input = "V"					},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "SelectNextTileSet"				m_Input = "N"					},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "AssignCurrentTileSet"			m_Input = "Shift+C"				},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "AssignNextTileSet"				m_Input = "Ctrl+D"				},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "AssignPreviousTileSet"			m_Input = "Ctrl+Shift+D"		},	
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "DeleteObject"					m_Input = "Del"					},
        
            // Item selection mode
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "Select"						m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "LassoSelect"					m_Input = "MMouse"				},		
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "BoxSelect"						m_Input = "X+MMouse"			},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "ClearSelection"				m_Input = "Esc"					},	
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "RandomVariation"				m_Input = "C"					},	
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "CollapseTiles"					m_Input = "Ctrl+F"				},		
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "RaiseTiles"					m_Input = "G"					},	
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "LowerTiles"					m_Input = "B"					},	
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "SelectionAddModifier"			m_Input = "SELECTION_ADD_KEY"	},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "SelectionRemoveModifier"		m_Input = "SELECTION_REMOVE_KEY"},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "CopyItems"						m_Input = "Ctrl+C"				},	
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "PasteItems"					m_Input = "Ctrl+V"				},	
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "BeginPaste"					m_Input = "Ctrl+Shift+V"		},	

            // Paste mode 
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "ApplyPaste"					m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "ApplyPaste"					m_Input = "Ctrl+V"				},	
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "ApplyPaste"					m_Input = "Space"				},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "FinishPaste"					m_Input = "Enter"				},	
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "CancelPaste"					m_Input = "Esc"					},
                                
            // Enable / disable mode
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "EnableDisableTile"				m_Input = "LMouse"				},	
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "EnableTileModifier"			m_Input = "Ctrl"				},	
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "LassoEnableDisable"			m_Input = "MMouse"				},		
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "BoxEnableDisable"				m_Input = "X+MMouse"			},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "EnableDisableCutDummy"			m_Input = "Ctrl+X"				},

            // Brush Modes
            InputBinding_t { m_Context = "ToolDotaTileEditor"		m_Command = "AdjustRadius"					m_Input = "MMouse"				},
            InputBinding_t { m_Context = "ToolDotaTileEditor"		m_Command = "ApplyBrush"					m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "StampBrush"					m_Input = "LMouseDoubleClick"	},		
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "RaiseVertex"					m_Input = "G"					},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "LowerVertex"					m_Input = "B"					},	
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "EraseBrush"					m_Input = "Ctrl"				},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "BrushAlternateMode"			m_Input = "Shift"				},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "BrushHeightOffsetMode"			m_Input = "X"					},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "BrushTilesetMode"				m_Input = "C"					},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "BrushAdjustDensity"			m_Input = "Ctrl"				},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "BrushIncreaseTreeHeight"		m_Input = "G"					},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "BrushDecreaseTreeHeight"		m_Input = "B"					},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "BrushChangeObjectType"			m_Input = "C"					},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "BrushChangeTreePitch"			m_Input = "X"					},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "BrushCutDummy"					m_Input = "Ctrl+X"				},
            InputBinding_t { m_Context = "ToolDotaTileEditor"		m_Command = "BrushRotateObjects"			m_Input = "Shift+MMouse"		},

            // Blend editing
            InputBinding_t { m_Context = "ToolDotaTileEditor"		m_Command = "BlendAdjustRadius"				m_Input = "MMouse"				},
            InputBinding_t { m_Context = "ToolDotaTileEditor"		m_Command = "BlendApplyBrush"				m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "BlendStampBrush"				m_Input = "LMouseDoubleClick"	},		
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "BlendEraseBrush"				m_Input = "Ctrl"				},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "BlendBrushAdjustPressure"		m_Input = "Ctrl"				},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "BlendBrushSharpness"			m_Input = "Shift"				},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "BlendBrushSmooth"				m_Input = "X"					},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "BlendBrushMaterialSet"			m_Input = "C"					},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "SelectNextMaterialSet"			m_Input = "N"					},
            InputBinding_t { m_Context = "ToolDotaTileEditor"		m_Command = "SetBlendModeLayer0"			m_Input = "F"					},
            InputBinding_t { m_Context = "ToolDotaTileEditor"		m_Command = "SetBlendModeLayer1"			m_Input = "G"					},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "SetBlendModeLayer2"			m_Input = "V"					},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "SetBlendModeLayer3"			m_Input = "B"					},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "SetBlendModeColor"				m_Input = "Alt+C"				},
            
            // Object editing		
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "AddObject"						m_Input = "LMouse"				},	
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "AddObject"						m_Input = "LMouseDoubleClick"	},		
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "ToggleRemoveObject"			m_Input = "Ctrl"				},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "ModifyObject"					m_Input = "LMouse"				},	
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "ModifyObject"					m_Input = "LMouseDoubleClick"	},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "RandomObjectVariation"			m_Input = "C"					},			
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "DragObject"					m_Input = "LMouse"				},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "RotateObject"					m_Input = "X+LMouse"			},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "RotateObject"					m_Input = "MMouse"				},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "PitchObject"					m_Input = "B+LMouse"			},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "PitchObject"					m_Input = "Shift+MMouse"		},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "DragClone"						m_Input = "Shift"				},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "StampObject"					m_Input = "Shift"				},
            InputBinding_t { m_Context = "ToolDotaTileEditor" 		m_Command = "ToggleSnapping"				m_Input = "TOGGLE_SNAPPING_KEY" },
        ]
    }
'@
    $defaultBinds = $defaultBinds.Split("`n")
    
    $Global:allBinds = Convertfrom-KV3 $defaultBinds
    $Global:mergeCompleted = $false
    Update-Tables
    })

#File > About info
$aboutMenu = New-Object System.Windows.Forms.ToolStripMenuItem
$aboutMenu.Text = "By TopHATTwaffle"
[void]$menuFile.DropDownItems.Add($aboutMenu)
$aboutMenu.Add_Click({
        Start-Process "https://github.com/tophattwaffle"
    })

#Populate the datagrid
$dataGrid = New-Object System.Windows.Forms.DataGridView
$dataGrid.ScrollBars = [System.Windows.Forms.ScrollBars]::Vertical
$dataGrid.Size = New-Object System.Drawing.Size(600, 900)
$dataGrid.Location = New-Object System.Drawing.Point(0, 20)
$dataGrid.AutoSizeColumnsMode = [System.Windows.Forms.DataGridViewAutoSizeColumnMode]::Fill
$dataGrid.SelectionMode = [System.Windows.Forms.DataGridViewSelectionMode]::FullRowSelect
$dataGrid.MultiSelect = $false
$dataGrid.ReadOnly = $true
$mainForm.Controls.Add($dataGrid)

#Event for changing selection
$dataGrid.add_SelectionChanged({
        $Global:gridSelection = $dataGrid.SelectedCells
        if ($Global:gridSelection.count -eq 0) {
            $changeButton.Enabled = $false
        }
        else {
            $changeButton.Enabled = $true
        }
    })

#Now that the data grid exists, set the main window size since we can just use that
$mainForm.Width = $dataGrid.Width + 20
$mainForm.Height = $dataGrid.Height + 90

#Try opening the default file, if it exists
if (Test-Path $Global:filePath) {
    Open-File $Global:filePath
}

$changeButton = New-Object System.Windows.Forms.Button
$changeButton.Location = New-Object System.Drawing.Point(10, ($mainForm.Height - 65))
$changeButton.AutoSize = $true
$changeButton.Text = 'Change Hotkey'
$mainForm.Controls.Add($changeButton)

$m_ContextSearch = New-Object System.Windows.Forms.TextBox
$m_ContextSearch.Location = New-Object System.Drawing.Point(150, ($mainForm.Height - 65))
$m_ContextSearch.Size = New-Object System.Drawing.Size(100, 20)
$mainForm.Controls.Add($m_ContextSearch)
$m_ContextSearch.Add_KeyUp({
        Update-Tables
    })

$m_CommandSearch = New-Object System.Windows.Forms.TextBox
$m_CommandSearch.Location = New-Object System.Drawing.Point(300, ($mainForm.Height - 65))
$m_CommandSearch.Size = New-Object System.Drawing.Size(100, 20)
$mainForm.Controls.Add($m_CommandSearch)
$m_CommandSearch.Add_KeyUp({
        Update-Tables
    })

$m_InputSearch = New-Object System.Windows.Forms.TextBox
$m_InputSearch.Location = New-Object System.Drawing.Point(450, ($mainForm.Height - 65))
$m_InputSearch.Size = New-Object System.Drawing.Size(100, 20)
$mainForm.Controls.Add($m_InputSearch)
$m_InputSearch.Add_KeyUp({
        Update-Tables
    })

$keyBindForm = New-Object System.Windows.Forms.Form
$keyBindForm.Text = 'New Hotkey'
$keyBindForm.Size = New-Object System.Drawing.Size(300, 175)
$keyBindForm.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedSingle
$keyBindForm.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterParent
$keyBindForm.TopMost = $true
$keyBindForm.KeyPreview = $true
$keyBindForm.Add_KeyDown({

        #Bail if we are using the dropdown selection
        if (!$Global:ConsumeKeyPress) { return }

        if ($_.KeyCode -eq "LWin" -or $_.KeyCode -eq "RWin" -or $_.KeyCode -eq "ControlKey" -or $_.KeyCode -eq "Menu" -or $_.KeyCode -eq "ShiftKey") {
            return
        }

        #The built in converted handles some basic key conversions for us
        $converter = New-Object System.Windows.Forms.KeysConverter
        $key = $converter.ConvertToString($_.KeyCode)

        #Re-map the remaining keys that the built in converted can't do
        $key = Update-KeypressValue $key

        $Global:lastKey = $key
        $keyBindLabel.Text = "Key: $Global:lastKey"
    })

$specialKeys = New-Object System.Windows.Forms.ComboBox
$specialKeys.Location = New-Object System.Drawing.Point(125, 17)
$specialKeys.Size = New-Object System.Drawing.Size(150, 20)
$specialKeys.DropDownStyle = [System.Windows.Forms.ComboBoxStyle]::DropDownList
$specialKeys.Enabled = $false
#Special keys / binds that we can't capture easily
#Marked as VOID to not display output on add
[void] $specialKeys.Items.Add("")
[void] $specialKeys.Items.Add("NumEnter")
[void] $specialKeys.Items.Add("Enter")
[void] $specialKeys.Items.Add("Esc")
[void] $specialKeys.Items.Add("Space")
[void] $specialKeys.Items.Add("LMouse")
[void] $specialKeys.Items.Add("RMouse")
[void] $specialKeys.Items.Add("MMouse")
[void] $specialKeys.Items.Add("MWheelUp")
[void] $specialKeys.Items.Add("MWheelDn")
[void] $specialKeys.Items.Add("LMouseDoubleClick")
[void] $specialKeys.Items.Add("Up")
[void] $specialKeys.Items.Add("Down")
[void] $specialKeys.Items.Add("Left")
[void] $specialKeys.Items.Add("Right")
[void] $specialKeys.Items.Add("SELECTION_ADD_KEY")
[void] $specialKeys.Items.Add("SELECTION_REMOVE_KEY")
[void] $specialKeys.Items.Add("TOGGLE_SNAPPING_KEY")
$keyBindForm.Controls.Add($specialKeys)

$specialKeysCheckbox = New-Object System.Windows.Forms.CheckBox
$specialKeysCheckbox.Location = New-Object System.Drawing.Point(100, 17)
$specialKeys.AutoSize = $true
$keyBindForm.Controls.Add($specialKeysCheckbox)
$specialKeysCheckbox.Add_CheckedChanged({
        if ($specialKeysCheckbox.Checked) {
            $bindAcceptButton.Enabled = $true #Enable the accept button incase it was disabled
            $specialKeys.Enabled = $true
            $Global:ConsumeKeyPress = $false
            $keyBindLabel.Text = "Select from list..."
        }
        else {
            $specialKeys.Enabled = $false
            $Global:ConsumeKeyPress = $true
            $specialKeys.SelectedIndex = 0
            $keyBindLabel.Text = "Press a key..."
        }
    })

$keyBindLabel = New-Object System.Windows.Forms.Label
$keyBindLabel.Location = New-Object System.Drawing.Point(10, 20)
$keyBindLabel.Size = New-Object System.Drawing.Size(280, 20)
$keyBindForm.Controls.Add($keyBindLabel)

$checkBox1 = New-Object System.Windows.Forms.CheckBox
$checkBox1.Location = New-Object System.Drawing.Point(20, 50)
$checkBox1.Size = New-Object System.Drawing.Size(90, 20)
$checkBox1.Text = 'CTRL'
$keyBindForm.Controls.Add($checkBox1)

$checkBox2 = New-Object System.Windows.Forms.CheckBox
$checkBox2.Location = New-Object System.Drawing.Point(110, 50)
$checkBox2.Size = New-Object System.Drawing.Size(90, 20)
$checkBox2.Text = 'SHIFT'
$keyBindForm.Controls.Add($checkBox2)

$checkBox3 = New-Object System.Windows.Forms.CheckBox
$checkBox3.Location = New-Object System.Drawing.Point(210, 50)
$checkBox3.Size = New-Object System.Drawing.Size(90, 20)
$checkBox3.Text = 'ALT'
$keyBindForm.Controls.Add($checkBox3)

$bindAcceptButton = New-Object System.Windows.Forms.Button
$bindAcceptButton.Location = New-Object System.Drawing.Point(150, 90)
$bindAcceptButton.AutoSize = $true
$bindAcceptButton.Text = 'Accept'
$bindAcceptButton.DialogResult = [System.Windows.Forms.DialogResult]::OK
$keyBindForm.AcceptButton = $bindAcceptButton
$keyBindForm.Controls.Add($bindAcceptButton)

$bindCancelButton = New-Object System.Windows.Forms.Button
$bindCancelButton.Location = New-Object System.Drawing.Point(50, 90)
$bindCancelButton.AutoSize = $true
$bindCancelButton.Text = 'Cancel'
$bindCancelButton.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
$keyBindForm.CancelButton = $bindCancelButton
$keyBindForm.Controls.Add($bindCancelButton)

#Changed Press event
$changeButton.add_Click({
        $keyBindForm.Text = "Editing: $($Global:gridSelection[1].value)"
        $Global:lastKey = $null
        $checkBox1.Checked = $false
        $checkBox2.Checked = $false
        $checkBox3.Checked = $false
        $specialKeysCheckbox.Checked = $false
        $specialKeys.Enabled = $false
        $specialKeys.SelectedIndex = 0
        $keyBindLabel.Text = "Press a key..."
        $result = $keyBindForm.ShowDialog()
        if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
            $result = ""
            $ctrl = $checkBox1.Checked
            $shift = $checkBox2.Checked
            $alt = $checkBox3.Checked

            if ($ctrl) { $result += "Ctrl+" }
            if ($shift) { $result += "Shift+" }
            if ($alt) { $result += "Alt+" }

            if ($Global:ConsumeKeyPress) {
                $result += $Global:lastKey
            }
            else {
                if ($specialKeys.SelectedItem -eq "") { #Handle unbinding a key
                    $result = ""
                }
                else {
                    $result += $specialKeys.SelectedItem
                }
            }

            $dupes = Search-DuplicateBinds $result

            if ($dupes) {
                $dupeStr = "Note: Duplicate binds in different Contexts are typically fine.`n`n"

                foreach ($d in $dupes) {
                    $dupeStr += "$($d.m_Context) | $($d.m_Command) | $($d.m_Input)`n"
                }

                $dupeForm = New-Object System.Windows.Forms.Form
                $dupeForm.Text = 'Duplicate Binds Found'
                
                $dupeForm.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedSingle
                $dupeForm.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterParent
                $dupeFormText = New-Object System.Windows.Forms.Label
                $dupeFormText.Text = $dupeStr
                $dupeFormText.Location = New-Object System.Drawing.Point(20, 20)
                $dupeFormText.AutoSize = $true

                $dupeAcceptButton = New-Object System.Windows.Forms.Button
                $dupeAcceptButton.Location = New-Object System.Drawing.Point(50, ($dupeForm.Height - 20))
                $dupeAcceptButton.AutoSize = $true
                $dupeAcceptButton.Text = 'Accept Dupes'
                $dupeAcceptButton.DialogResult = [System.Windows.Forms.DialogResult]::OK
                $dupeCancelButton = New-Object System.Windows.Forms.Button
                $dupeCancelButton.Location = New-Object System.Drawing.Point(150, ($dupeForm.Height - 20))
                $dupeCancelButton.AutoSize = $true
                $dupeCancelButton.Text = "Do not Accept"
                $dupeCancelButton.DialogResult = [System.Windows.Forms.DialogResult]::Cancel

                $dupeForm.Controls.Add($dupeFormText)
                $dupeForm.CancelButton = $dupeCancelButton
                $dupeForm.Controls.Add($dupeCancelButton)
                $dupeForm.AcceptButton = $dupeAcceptButton
                $dupeForm.Controls.Add($dupeAcceptButton)
                $dupeForm.AutoSize = $True

                $dupeResult = $dupeForm.ShowDialog()

                if ($dupeResult -eq [System.Windows.Forms.DialogResult]::Cancel) { return }
            }

            $result = $result.TrimEnd("+")

            foreach($bind in $global:allBinds.InputBindingList_t.m_bindings)
            {
                if($bind.m_Context -eq $Global:gridSelection[0].Value -and $bind.m_Command -eq $Global:gridSelection[1].Value)
                {
                    $bind.m_Input = $result
                    break
                }
            }

            Update-Tables
        }
        $Global:dataGrid.ClearSelection()
    })

[void]$mainForm.ShowDialog()
using System.Diagnostics.CodeAnalysis;
using System.Numerics;
using System.Text.Json;
using System.Text.Json.Serialization;

using Datamodel;
using Hammer5Tools.Core;
using DM = Datamodel.Datamodel;

namespace Hammer5Tools.Core.Format.Vmap;

/// <summary>The VMAP node shape produced from a normalized Unreal placement.</summary>
[JsonConverter(typeof(JsonStringEnumConverter<UnrealMapPlacementKind>))]
public enum UnrealMapPlacementKind
{
    /// <summary>A point entity with EditGameClassProps.</summary>
    Entity,

    /// <summary>A native CMapSmartProp placement.</summary>
    SmartProp,

    /// <summary>A native CMapStaticOverlay decal.</summary>
    Decal,
}

/// <summary>A UI-neutral transformed Unreal placement ready for VMAP serialization.</summary>
public sealed record UnrealMapPlacement(
    UnrealMapPlacementKind Kind,
    string Name,
    IReadOnlyList<float> Origin,
    IReadOnlyList<float> Angles,
    IReadOnlyList<float> Scales,
    IReadOnlyDictionary<string, string>? Properties,
    string? ResourcePath);

/// <summary>A typed Unreal scene request for VMAP serialization.</summary>
public sealed record UnrealMapWriteRequest(IReadOnlyList<UnrealMapPlacement> Placements);

/// <summary>Summary of a completed Unreal VMAP write.</summary>
public sealed record UnrealMapWriteResult(int PlacementCount, string Encoding, int EncodingVersion);

/// <summary>Source-generated JSON contract for <see cref="UnrealMapWriter.WriteJson"/>, required under NativeAOT
/// (reflection-based serialization is unavailable there).</summary>
[JsonSerializable(typeof(UnrealMapWriteRequest))]
internal sealed partial class UnrealMapWriterJsonContext : JsonSerializerContext;

/// <summary>Writes normalized Unreal placements as a Source 2 VMAP.</summary>
public static class UnrealMapWriter
{
    private static readonly IReadOnlyDictionary<string, string> Worldspawn = new Dictionary<string, string>
    {
        ["classname"] = "worldspawn",
        ["targetname"] = "",
        ["skyname"] = "sky_day01_01",
        ["startdark"] = "0",
        ["startcolor"] = "0 0 0",
        ["pvstype"] = "0",
        ["newunit"] = "0",
        ["maxpropscreenwidth"] = "-1",
        ["minpropscreenwidth"] = "0",
        ["vrchaperone"] = "0",
        ["vrmovement"] = "0",
        ["baked_light_index_min"] = "0",
        ["baked_light_index_max"] = "256",
        ["max_lightmap_resolution"] = "0",
        ["lightmap_queries"] = "1",
        ["steamaudio_reverb_rebake_option"] = "1",
        ["steamaudio_reverb_grid_type"] = "0",
        ["steamaudio_reverb_grid_spacing"] = "6",
        ["steamaudio_reverb_height_above_floor"] = "1.5",
        ["steamaudio_reverb_rays"] = "32768",
        ["steamaudio_reverb_bounces"] = "32",
        ["steamaudio_reverb_ir_duration"] = "1.0",
        ["steamaudio_reverb_ambisonic_order"] = "1",
        ["steamaudio_pathing_rebake_option"] = "1",
        ["steamaudio_pathing_grid_type"] = "0",
        ["steamaudio_pathing_grid_spacing"] = "6",
        ["steamaudio_pathing_height_above_floor"] = "1.5",
        ["steamaudio_pathing_visibility_samples"] = "1",
        ["steamaudio_pathing_visibility_radius"] = "0.0",
        ["steamaudio_pathing_visibility_threshold"] = "0.1",
        ["steamaudio_pathing_visibility_pathrange"] = "100.0",
        ["prefab_has_runtime_entity_by_default"] = "0",
    };

    /// <summary>Deserializes a typed primitive request and writes a VMAP.</summary>
    public static CoreResult<UnrealMapWriteResult> WriteJson(string requestJson, string outputPath)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(requestJson);
        ArgumentException.ThrowIfNullOrWhiteSpace(outputPath);
        try
        {
            var request = JsonSerializer.Deserialize(requestJson, UnrealMapWriterJsonContext.Default.UnrealMapWriteRequest)
                ?? throw new JsonException("The Unreal map request was empty.");
            return Write(request, outputPath);
        }
        catch (Exception exception)
        {
            return CoreResult.Failure<UnrealMapWriteResult>(
                "unreal_vmap_write_failed", $"Could not write '{outputPath}': {exception.Message}");
        }
    }

    /// <summary>Writes typed placements to a binary VMAP, with text fallback.</summary>
    public static CoreResult<UnrealMapWriteResult> Write(UnrealMapWriteRequest request, string outputPath)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentException.ThrowIfNullOrWhiteSpace(outputPath);

        try
        {
            var (document, world) = CreateDocument();
            var children = world["children"] as ElementArray
                ?? throw new InvalidDataException("The generated VMAP world has no children array.");
            var nodeId = 1000;
            foreach (var placement in request.Placements
                ?? throw new InvalidDataException("The Unreal map request has no placements."))
            {
                nodeId++;
                children.Add(placement.Kind switch
                {
                    UnrealMapPlacementKind.Entity => CreateEntity(document, placement, nodeId),
                    UnrealMapPlacementKind.SmartProp => CreateSmartProp(document, placement, nodeId),
                    UnrealMapPlacementKind.Decal => CreateDecal(document, placement, nodeId),
                    _ => throw new InvalidDataException($"Unknown placement kind {placement.Kind}."),
                });
            }

            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(outputPath))!);
            try
            {
                document.Save(outputPath, "binary", 9);
                return CoreResult.Success(new UnrealMapWriteResult(children.Count, "binary", 9));
            }
            catch
            {
                document.Save(outputPath, "keyvalues2", 4);
                return CoreResult.Success(new UnrealMapWriteResult(children.Count, "keyvalues2", 4));
            }
        }
        catch (Exception exception)
        {
            return CoreResult.Failure<UnrealMapWriteResult>(
                "unreal_vmap_write_failed", $"Could not write '{outputPath}': {exception.Message}");
        }
    }

    // Datamodel.Datamodel's static constructor registers its built-in codecs via
    // Activator.CreateInstance(Type). Under NativeAOT that constructor metadata is not
    // preserved unless something declares it needed, so the very first access to DM in
    // an AOT process throws a TypeInitializationException. These dependencies keep both
    // codecs' parameterless constructors reachable.
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.Binary", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.KeyValues2", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, typeof(ElementFactory))]
    private static (DM Document, Element World) CreateDocument()
    {
        var document = new DM("vmap", 40);
        var root = Create(document, "CMapRootElement");
        document.Root = root;

        var plugList = EmptyPlugList(document);
        var worldProperties = Create(document, "EditGameClassProps");
        foreach (var (key, value) in Worldspawn)
            worldProperties[key] = value;

        var world = NodeDefaults(Create(document, "CMapWorld"), 1);
        world["relayPlugData"] = plugList;
        world["connectionsData"] = new ElementArray();
        world["entity_properties"] = worldProperties;
        world["nextDecalID"] = 0;
        world["fixupEntityNames"] = true;
        world["mapUsageType"] = "standard";

        var visibility = NodeDefaults(Create(document, "CVisibilityMgr"), 0);
        visibility["nodes"] = new ElementArray();
        visibility["hiddenFlags"] = new IntArray();

        var variables = Create(document, "CMapVariableSet");
        foreach (var key in new[] { "variableNames", "variableValues", "variableTypeNames", "variableTypeParameters" })
            variables[key] = new StringArray();
        variables["m_ChoiceGroups"] = new ElementArray();

        var selectionSet = Create(document, "CMapSelectionSet");
        selectionSet["children"] = new ElementArray();
        selectionSet["selectionSetName"] = "";
        selectionSet["selectionSetData"] = null;

        var camera = Create(document, "CStoredCamera");
        camera["position"] = new Vector3(0, -1000, 1000);
        camera["lookat"] = Vector3.Zero;
        var cameras = Create(document, "CStoredCameras");
        cameras["activecamera"] = -1;
        cameras["cameras"] = new ElementArray();

        root["isprefab"] = false;
        root["editorbuild"] = 10430;
        root["editorversion"] = 400;
        root["itemFile"] = "";
        root["defaultcamera"] = camera;
        root["3dcameras"] = cameras;
        root["world"] = world;
        root["visbility"] = visibility;
        root["mapVariables"] = variables;
        root["rootSelectionSet"] = selectionSet;
        root["m_ReferencedMeshSnapshots"] = new ElementArray();
        root["m_bIsCordoning"] = false;
        root["m_bCordonsVisible"] = false;
        root["nodeInstanceData"] = new ElementArray();
        return (document, world);
    }

    private static Element CreateEntity(DM document, UnrealMapPlacement placement, int nodeId)
    {
        var properties = Create(document, "EditGameClassProps");
        foreach (var (key, value) in placement.Properties ?? new Dictionary<string, string>())
            properties[key] = value;

        var entity = NodeDefaults(Create(document, "CMapEntity", placement.Name), nodeId, placement);
        entity["referenceID"] = RandomReferenceId();
        entity["relayPlugData"] = EmptyPlugList(document);
        entity["connectionsData"] = new ElementArray();
        entity["entity_properties"] = properties;
        entity["hitNormal"] = Vector3.UnitZ;
        entity["isProceduralEntity"] = false;
        return entity;
    }

    private static Element CreateSmartProp(DM document, UnrealMapPlacement placement, int nodeId)
    {
        var evaluationVersion = Create(document, "DmElement");
        evaluationVersion["m_nDefinitionVersion"] = 1;
        evaluationVersion["m_ClassNames"] = new StringArray
        {
            "CSmartPropElement_Group", "CSmartPropElement_Model", "CSmartPropOperation_Translate", "CSmartPropRoot",
        };
        evaluationVersion["m_ClassVersions"] = new IntArray { 0, 0, 0, 0 };
        var parameters = Create(document, "DmElement");
        parameters["values"] = new ElementArray();
        var nodeData = Create(document, "DmElement");
        nodeData["evaluationVersion"] = evaluationVersion;
        nodeData["parameters"] = parameters;

        var transformPin = Create(document, "DmElement");
        transformPin["referenceName"] = "";
        transformPin["targetReferenceID"] = 0UL;
        transformPin["offsetOrigin"] = Vector3.Zero;
        transformPin["offsetAngles"] = new QAngle(0, 0, 0);
        transformPin["pinAngles"] = true;
        transformPin["twoWay"] = false;

        var entity = NodeDefaults(Create(document, "CMapSmartProp", placement.Name), nodeId, placement);
        entity["referenceID"] = RandomReferenceId();
        entity["transformPin"] = transformPin;
        entity["customVisGroup"] = "";
        entity["randomSeed"] = Random.Shared.Next();
        entity["smartPropFilename"] = placement.ResourcePath ?? "";
        entity["tintColor"] = new Color(255, 255, 255, 255);
        entity["evaluationLocked"] = false;
        entity["constrainToPrefab"] = false;
        entity["shapeReferences"] = new ElementArray();
        entity["alpha"] = 255;
        entity["cullDistance"] = 0f;
        entity["fadeStartDistance"] = -1f;
        entity["lightingOriginName"] = "";
        entity["disableShadows"] = 0;
        entity["bakedLigthtingMode"] = -1;
        entity["lightmapScaleBias"] = 0;
        entity["bakeLightingDoubleSided"] = false;
        entity["emissiveLightingEnabled"] = true;
        entity["emissiveLightingBoost"] = 1f;
        entity["collisionMode"] = -1;
        entity["collisionPropertyOverride"] = "";
        entity["isVisOccluder"] = false;
        entity["renderToCubeMaps"] = true;
        entity["disabledInLowQuality"] = false;
        entity["bakeToWorld"] = false;
        entity["disableMerging"] = false;
        entity["renderWithDynamic"] = false;
        entity["nodeData"] = nodeData;
        return entity;
    }

    private static Element CreateDecal(DM document, UnrealMapPlacement placement, int nodeId)
    {
        var vertexData = DataArray(document, 4,
        [
            Vector3Stream(document, "position",
            [
                new(-128, -128, 34), new(128, -128, 34),
                new(128, 128, 34), new(-128, 128, 34),
            ]),
        ]);
        var faceVertexData = DataArray(document, 8,
        [
            Vector2Stream(document, "texcoord",
            [
                new(1, 1), new(0, 0), new(1, 0), new(0, 0),
                new(0, 0), new(0, 0), new(0, 1), new(0, 0),
            ]),
            Vector3Stream(document, "normal",
            [
                Vector3.UnitZ, Vector3.Zero, Vector3.UnitZ, Vector3.Zero,
                Vector3.UnitZ, Vector3.Zero, Vector3.UnitZ, Vector3.Zero,
            ]),
            Vector4Stream(document, "tangent",
            [
                new(1, 0, 0, -1), Vector4.Zero, new(1, 0, 0, -1), Vector4.Zero,
                new(1, 0, 0, -1), Vector4.Zero, new(1, 0, 0, -1), Vector4.Zero,
            ]),
        ]);
        var edgeData = DataArray(document, 4, [IntStream(document, "flags", [0, 0, 0, 0], 3)]);
        var faceData = DataArray(document, 1,
        [
            Vector2Stream(document, "textureScale", [new(0.25f, 0.25f)]),
            Vector4Stream(document, "textureAxisU", [new(1, 0, 0, 0)]),
            Vector4Stream(document, "textureAxisV", [new(0, -1, 0, 512)]),
            IntStream(document, "materialindex", [0], 8),
            IntStream(document, "flags", [0], 3),
            IntStream(document, "lightmapScaleBias", [0], 1),
        ]);
        var subdivision = Create(document, "CDmePolygonMeshSubdivisionData");
        subdivision["subdivisionLevels"] = Integers([0, 0, 0, 0, 0, 0, 0, 0]);
        subdivision["streams"] = new ElementArray();

        var mesh = Create(document, "CDmePolygonMesh", "meshData");
        mesh["vertexEdgeIndices"] = Integers([0, 2, 4, 6]);
        mesh["vertexDataIndices"] = Integers([0, 1, 2, 3]);
        mesh["edgeVertexIndices"] = Integers([1, 0, 2, 1, 3, 2, 0, 3]);
        mesh["edgeOppositeIndices"] = Integers([1, 0, 3, 2, 5, 4, 7, 6]);
        mesh["edgeNextIndices"] = Integers([2, 7, 4, 1, 6, 3, 0, 5]);
        mesh["edgeFaceIndices"] = Integers([0, -1, 0, -1, 0, -1, 0, -1]);
        mesh["edgeDataIndices"] = Integers([0, 0, 1, 1, 2, 2, 3, 3]);
        mesh["edgeVertexDataIndices"] = Integers([0, 1, 2, 3, 4, 5, 6, 7]);
        mesh["faceEdgeIndices"] = Integers([6]);
        mesh["faceDataIndices"] = Integers([0]);
        mesh["materials"] = new StringArray { placement.ResourcePath ?? "" };
        mesh["vertexData"] = vertexData;
        mesh["faceVertexData"] = faceVertexData;
        mesh["edgeData"] = edgeData;
        mesh["faceData"] = faceData;
        mesh["subdivisionData"] = subdivision;

        var transformPin = Create(document, "DmElement", "transformPin");
        transformPin["referenceName"] = "";
        transformPin["targetReferenceID"] = 0UL;
        transformPin["offsetOrigin"] = Vector3.Zero;
        transformPin["offsetAngles"] = new QAngle(0, 0, 0);
        transformPin["pinAngles"] = true;
        transformPin["twoWay"] = false;

        var adjustment = Create(document, "DmElement", "MaterialAdjustmentParamsStruct");
        adjustment["ColorBrightness"] = 0.5f;
        adjustment["ColorContrast"] = 0.5f;
        adjustment["ColorAlpha"] = 1f;
        adjustment["RoughnessBrightness"] = 0.5f;
        adjustment["RoughnessContrast"] = 0.5f;
        adjustment["ShadingAlpha"] = 1f;
        adjustment["NormalIntensity"] = 0.75f;
        adjustment["RoughnessMetalnessOverride"] = false;
        adjustment["NormalBlendOverride"] = true;

        var overlay = NodeDefaults(Create(document, "CMapStaticOverlay", placement.Name), nodeId, placement);
        overlay["referenceID"] = RandomReferenceId();
        overlay["meshData"] = mesh;
        overlay["projectionTargets"] = new IntArray();
        overlay["transformPin"] = transformPin;
        overlay["disableShadows"] = 0;
        overlay["bakelighting"] = true;
        overlay["cubeMapName"] = "";
        overlay["emissiveLightingEnabled"] = true;
        overlay["emissiveLightingBoost"] = 1f;
        overlay["lightingDummy"] = false;
        overlay["bakeLightDoubleSided"] = false;
        overlay["visexclude"] = false;
        overlay["disablemerging"] = false;
        overlay["renderwithdynamic"] = false;
        overlay["renderToCubemaps"] = true;
        overlay["keep_vertices"] = false;
        overlay["fademindist"] = -1f;
        overlay["fademaxdist"] = 0f;
        overlay["disableHeightDisplacement"] = false;
        overlay["smoothingAngle"] = 40f;
        overlay["renderAmt"] = 255;
        overlay["physicsType"] = "default";
        overlay["physicsCollisionProperty"] = "";
        overlay["physicsGroup"] = "";
        overlay["physicsInteractsAs"] = "";
        overlay["physicsInteractsWith"] = "";
        overlay["physicsInteractsExclude"] = "";
        overlay["physicsSimplificationOverride"] = false;
        overlay["physicsSimplificationError"] = 0f;
        overlay["renderOrder"] = 0;
        overlay["disabledInLowQuality"] = false;
        overlay["useBaseNormals"] = false;
        overlay["projectionFar"] = 128f;
        overlay["projectOnBackFaces"] = false;
        overlay["backFacingAngle"] = 90f;
        overlay["projectionMode"] = 0;
        overlay["randomSeed"] = 0;
        overlay["customVisGroup"] = "";
        overlay["tintColor"] = new Color(255, 255, 255, 255);
        overlay["physicsIncludedDetailLayers"] = new ElementArray();
        overlay["physicsMissingDetailLayers"] = new ElementArray();
        overlay["MaterialAdjustmentParamsStruct"] = adjustment;
        return overlay;
    }

    private static Element DataArray(DM document, int size, IEnumerable<Element> streams)
    {
        var array = Create(document, "CDmePolygonMeshDataArray");
        array["size"] = size;
        var values = new ElementArray();
        foreach (var stream in streams)
            values.Add(stream);
        array["streams"] = values;
        return array;
    }

    private static Element Stream(DM document, string name, int flags = 1)
    {
        var stream = Create(document, "CDmePolygonMeshDataStream", $"{name}:0");
        stream["standardAttributeName"] = name;
        stream["semanticName"] = name;
        stream["semanticIndex"] = 0;
        stream["vertexBufferLocation"] = 0;
        stream["dataStateFlags"] = flags;
        return stream;
    }

    private static Element IntStream(DM document, string name, IEnumerable<int> values, int flags)
    {
        var stream = Stream(document, name, flags);
        stream["data"] = Integers(values);
        return stream;
    }

    private static Element Vector2Stream(DM document, string name, IEnumerable<Vector2> values)
    {
        var stream = Stream(document, name);
        var array = new Vector2Array();
        foreach (var value in values)
            array.Add(value);
        stream["data"] = array;
        return stream;
    }

    private static Element Vector3Stream(DM document, string name, IEnumerable<Vector3> values)
    {
        var stream = Stream(document, name);
        var array = new Vector3Array();
        foreach (var value in values)
            array.Add(value);
        stream["data"] = array;
        return stream;
    }

    private static Element Vector4Stream(DM document, string name, IEnumerable<Vector4> values)
    {
        var stream = Stream(document, name);
        var array = new Vector4Array();
        foreach (var value in values)
            array.Add(value);
        stream["data"] = array;
        return stream;
    }

    private static IntArray Integers(IEnumerable<int> values)
    {
        var array = new IntArray();
        foreach (var value in values)
            array.Add(value);
        return array;
    }

    private static Element NodeDefaults(
        Element element,
        int nodeId,
        UnrealMapPlacement? placement = null)
    {
        element["nodeID"] = nodeId;
        element["referenceID"] = 0UL;
        element["children"] = new ElementArray();
        element["variableTargetKeys"] = new StringArray();
        element["variableNames"] = new StringArray();
        element["origin"] = placement is null ? Vector3.Zero : Vector(placement.Origin, Vector3.Zero);
        element["angles"] = placement is null ? new QAngle(0, 0, 0) : Angles(placement.Angles);
        element["scales"] = placement is null ? Vector3.One : Vector(placement.Scales, Vector3.One);
        element["transformLocked"] = false;
        element["force_hidden"] = false;
        element["editorOnly"] = false;
        return element;
    }

    private static Element EmptyPlugList(DM document)
    {
        var plugList = Create(document, "DmePlugList");
        plugList["names"] = new StringArray();
        plugList["dataTypes"] = new IntArray();
        plugList["plugTypes"] = new IntArray();
        plugList["descriptions"] = new StringArray();
        return plugList;
    }

    private static Element Create(DM document, string className, string name = "") =>
        new(document, name, null, className);

    private static Vector3 Vector(IReadOnlyList<float> values, Vector3 fallback) =>
        values.Count >= 3 ? new Vector3(values[0], values[1], values[2]) : fallback;

    private static QAngle Angles(IReadOnlyList<float> values) =>
        values.Count >= 3 ? new QAngle(values[0], values[1], values[2]) : new QAngle(0, 0, 0);

    private static ulong RandomReferenceId()
    {
        Span<byte> bytes = stackalloc byte[sizeof(ulong)];
        Random.Shared.NextBytes(bytes);
        return BitConverter.ToUInt64(bytes);
    }
}

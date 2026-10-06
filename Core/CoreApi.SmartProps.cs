namespace Hammer5Tools.Core;

/// <summary>Managed SmartProp editor and preview operations.</summary>
public static partial class CoreApi
{
    /// <summary>Creates an empty source SmartProp for the C# editor preview.</summary>
    public static string CreateSmartPropDocument() => Format.SmartProps.SmartPropEditorDocument.Create();

    /// <summary>Finds the installed CS2 game directory through Steam's library folders.</summary>
    public static string? FindCs2GameDirectory() => IO.Domain.Cs2InstallLocator.TryLocate() is { } install ? Path.Combine(install, "game") : null;

    /// <summary>Loads source or compiled SmartProp editor data, including VPK resources.</summary>
    public static string LoadSmartPropResource(string resource, string gameDirectory, string addon = "") => IO.SmartPropPreviewService.Load(resource, gameDirectory, addon);

    /// <summary>Evaluates an edited SmartProp and loads its material-aware preview geometry.</summary>
    public static SmartPropPreviewScene BuildSmartPropPreview(string json, string gameDirectory, string addon = "", string? sourcePath = null, CancellationToken cancellationToken = default) =>
        IO.SmartPropPreviewService.Build(json, gameDirectory, addon, sourcePath, cancellationToken);

    /// <summary>Reads source KV3 into validated editor JSON.</summary>
    public static string ParseSmartPropDocument(string text) => ValidateSmartPropDocument(Format.SmartProps.SmartPropDocumentSerializer.DeserializeText(text));

    /// <summary>Validates source editor JSON while preserving unrecognized fields.</summary>
    public static string ValidateSmartPropDocument(string json) => Format.SmartProps.SmartPropEditorDocument.Validate(json);

    /// <summary>Writes validated source editor JSON as KV3.</summary>
    public static string SerializeSmartPropDocument(string json) => Format.SmartProps.SmartPropDocumentSerializer.SerializeJson(ValidateSmartPropDocument(json));

    /// <summary>Stages, validates and atomically saves source KV3, returning the retained backup path.</summary>
    public static string? SaveSmartPropDocument(string path, string json) => IO.SmartPropDocumentFile.Save(path, json);

    /// <summary>Applies a hierarchy operation or replaces a selected JSON section.</summary>
    public static string EditSmartPropDocument(string json, string[] path, string operation, string valueJson = "null") =>
        Format.SmartProps.SmartPropEditorDocument.Edit(json, path, operation, valueJson);

    /// <summary>Copies selected hierarchy subtrees as source KV3 without duplicating selected descendants.</summary>
    public static string CopySmartPropHierarchy(string json, string[][] paths) =>
        Format.SmartProps.SmartPropHierarchyDocument.Copy(json, paths);

    /// <summary>Inserts source assets from CS2 content folders as hierarchy references in one edit.</summary>
    public static string ImportSmartPropHierarchyFiles(string json, string[] target, string[] paths, string gameDirectory) =>
        IO.SmartPropHierarchyFiles.Import(json, target, paths, gameDirectory);

    /// <summary>Evaluates source editor JSON with bounded placements and cancellation.</summary>
    public static Format.SmartProps.SmartPropEvaluationResult EvaluateSmartPropDocument(string json, CancellationToken cancellationToken = default) =>
        Format.SmartProps.SmartPropEvaluator.EvaluateJson(json, new Format.SmartProps.SmartPropEvaluationOptions(maximumModels: 10_000, cancellationToken: cancellationToken));

    /// <summary>Reads untextured compiled geometry for the C# preview viewport.</summary>
    public static CoreResult<Format.Resources.CompiledModel> ReadSmartPropPreviewModel(string gameDirectory, string addon, string modelPath)
    {
        using var reader = new Format.Resources.CompiledModelReader(gameDirectory, addon);
        return reader.Read(modelPath, geometryOnly: true);
    }

}

/// <summary>An evaluated SmartProp placement and its optional compiled preview geometry.</summary>
public sealed record SmartPropPreviewInstance(Format.SmartProps.EvaluatedSmartPropModel Placement, Format.Resources.CompiledModel? Geometry);

/// <summary>Material-aware SmartProp preview instances and resource/evaluation diagnostics.</summary>
public sealed record SmartPropPreviewScene(IReadOnlyList<SmartPropPreviewInstance> Instances, IReadOnlyList<string> Diagnostics);

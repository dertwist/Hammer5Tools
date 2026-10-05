namespace Hammer5Tools.Core;

/// <summary>
/// Identifies the versioned public contract exposed by Hammer5Tools Core.
/// </summary>
public static class CoreApi
{
    /// <summary>
    /// Gets the version understood by GUI bridge clients.
    /// </summary>
    public static Version Version { get; } = new(2, 0);

    /// <summary>
    /// Verifies that the public Core contract can be invoked by a client.
    /// </summary>
    public static CoreResult<Version> Probe() => CoreResult.Success(Version);

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

    /// <summary>Evaluates source editor JSON with bounded placements and cancellation.</summary>
    public static Format.SmartProps.SmartPropEvaluationResult EvaluateSmartPropDocument(string json, CancellationToken cancellationToken = default) =>
        Format.SmartProps.SmartPropEvaluator.EvaluateJson(json, new Format.SmartProps.SmartPropEvaluationOptions(maximumModels: 10_000, cancellationToken: cancellationToken));

    /// <summary>Reads untextured compiled geometry for the C# preview viewport.</summary>
    public static CoreResult<Format.Resources.CompiledModel> ReadSmartPropPreviewModel(string gameDirectory, string addon, string modelPath)
    {
        using var reader = new Format.Resources.CompiledModelReader(gameDirectory, addon);
        return reader.Read(modelPath, geometryOnly: true);
    }

    /// <summary>Resolves loose source/output paths; relative paths are confined to an addon root.</summary>
    public static string ResolveAssetPath(string path, string? addonRoot = null, bool mustExist = true) =>
        IO.Automation.AssetPathResolver.Resolve(path, addonRoot, mustExist);

    /// <summary>Validates and compiles source assets through the Valve toolchain.</summary>
    public static string CompileAssets(string requestJson)
    {
        using var request = System.Text.Json.JsonDocument.Parse(requestJson);
        return (IO.Automation.CompilerService.Flag(request.RootElement, "background") && !IO.Automation.CompilerService.Flag(request.RootElement, "dry_run")
            ? IO.Automation.CompilationJobs.Start(request.RootElement)
            : IO.Automation.CompilerService.Compile(request.RootElement)).ToJsonString(AutomationJsonContext.Default.Options);
    }

    /// <summary>Reads a bounded character window from an owned compilation log.</summary>
    public static string ReadCompilerLog(string requestJson)
    {
        using var request = System.Text.Json.JsonDocument.Parse(requestJson);
        return IO.Automation.CompilerService.ReadLog(request.RootElement).ToJsonString(AutomationJsonContext.Default.Options);
    }

    /// <summary>Queries a persisted compilation job without waiting for its process.</summary>
    public static string CompilationJobStatus(string jobId) => IO.Automation.CompilationJobs.Status(jobId).ToJsonString(AutomationJsonContext.Default.Options);

    /// <summary>Cancels an owned live job; recovered stale processes are never signalled.</summary>
    public static string CancelCompilationJob(string jobId) => IO.Automation.CompilationJobs.Cancel(jobId).ToJsonString(AutomationJsonContext.Default.Options);

    /// <summary>Authors one material/model or a validated per-format batch with per-file backups.</summary>
    public static string AuthorSourceAssets(string requestJson, string format, bool batch)
    {
        if (format is not ("vmat" or "vmdl")) throw new ArgumentException("Source authoring accepts vmat or vmdl.", nameof(format));
        using var request = System.Text.Json.JsonDocument.Parse(requestJson);
        return (batch ? Format.Authoring.SourceAssetAuthoring.Batch(request.RootElement, format)
            : Format.Authoring.SourceAssetAuthoring.Single(request.RootElement, format)).ToJsonString(AutomationJsonContext.Default.Options);
    }

    /// <summary>Reads stable map node IDs or applies a structured map authoring operation.</summary>
    public static string AuthorMap(string requestJson, string operation)
    {
        using var request = System.Text.Json.JsonDocument.Parse(requestJson);
        return Format.Vmap.MapAuthoring.Execute(request.RootElement, operation).ToJsonString(AutomationJsonContext.Default.Options);
    }

    /// <summary>Inspects compiled render bounds without guessing source-FBX or physics bounds.</summary>
    public static string InspectModel(string requestJson)
    {
        using var request = System.Text.Json.JsonDocument.Parse(requestJson);
        return Format.Resources.ModelInspection.Inspect(request.RootElement).ToJsonString(AutomationJsonContext.Default.Options);
    }

    /// <summary>Splits, packs, or inspects explicitly mapped lossless texture channels.</summary>
    public static string PrepareTexture(string requestJson, string operation)
    {
        using var request = System.Text.Json.JsonDocument.Parse(requestJson);
        return Format.Materials.TexturePreparation.Execute(request.RootElement, operation).ToJsonString(AutomationJsonContext.Default.Options);
    }

    /// <summary>Groups a source filename using affixes appropriate to its file type.</summary>
    public static string NormalizeAssetGroupName(string baseName, string sourceExtension = "", int algorithm = 0) =>
        Format.AssetGroup.AssetGroupTemplate.NormalizeName(baseName, sourceExtension, algorithm);

    /// <summary>Expands Assetgroup template tokens and conditionals from a JSON request.</summary>
    public static string RenderAssetGroupTemplate(string requestJson) =>
        Format.AssetGroup.AssetGroupTemplate.Render(requestJson);

    /// <summary>Reads a VMAP as versioned DCC import JSON, retaining polygons and editor metadata.</summary>
    public static string ReadValveMapImport(string path, string? contentRoot = null, Format.Vmap.ValveMapImportOptions? options = null) =>
        new Format.Vmap.ValveMapImportReader().Read(path, contentRoot, options);

    /// <summary>Deserializes and evaluates a source or compiled SmartProp for DCC import.</summary>
    public static string ReadSmartPropImport(string path, string? contentRoot = null, Format.Vmap.ValveMapImportOptions? options = null, string variablesJson = "{}") =>
        new Format.Vmap.ValveMapImportReader().ReadSmartProp(path, contentRoot, options, variablesJson);
}

/// <summary>A Core-evaluated placement and its compiled preview geometry, when available.</summary>
public sealed record SmartPropPreviewInstance(Format.SmartProps.EvaluatedSmartPropModel Placement, Format.Resources.CompiledModel? Geometry);

/// <summary>Material-aware SmartProp preview instances and resource/evaluation diagnostics.</summary>
public sealed record SmartPropPreviewScene(IReadOnlyList<SmartPropPreviewInstance> Instances, IReadOnlyList<string> Diagnostics);

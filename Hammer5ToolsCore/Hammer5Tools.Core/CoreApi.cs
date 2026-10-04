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
        if (format is not ("vmat" or "vmdl")) throw new ArgumentException("Unsupported source format.");
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
    public static string ReadValveMapImport(string path, string? contentRoot = null) =>
        new Format.Vmap.ValveMapImportReader().Read(path, contentRoot);
}

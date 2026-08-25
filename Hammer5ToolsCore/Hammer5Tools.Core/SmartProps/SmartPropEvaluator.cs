using System.Text.Json;

using ValveResourceFormat.ResourceTypes.SmartProps;
using ValveResourceFormat.Serialization.KeyValues;

namespace Hammer5Tools.Core.SmartProps;

/// <summary>
/// Adapts uncompiled SmartProp document data to the VRF evaluator.
/// </summary>
public static class SmartPropEvaluator
{
    /// <summary>
    /// Evaluates a JSON representation of an uncompiled SmartProp document.
    /// </summary>
    public static SmartPropEvaluationResult EvaluateJson(string json)
        => EvaluateJson(json, SmartPropEvaluationOptions.Default);

    /// <summary>
    /// Evaluates a JSON representation of an uncompiled SmartProp document.
    /// </summary>
    public static SmartPropEvaluationResult EvaluateJson(string json, SmartPropEvaluationOptions options)
    {
        ArgumentNullException.ThrowIfNull(json);
        ArgumentNullException.ThrowIfNull(options);
        options.Validate();

        try
        {
            return Evaluate(SmartPropJsonConverter.Convert(json), null, options);
        }
        catch (JsonException exception)
        {
            return new SmartPropEvaluationResult([], [new CoreDiagnostic(
                CoreDiagnosticSeverity.Error,
                "smartprop.invalid_json",
                exception.Message)]);
        }
    }

    /// <summary>
    /// Evaluates a JSON SmartProp document with nested documents keyed by resource path.
    /// </summary>
    public static SmartPropEvaluationResult EvaluateJson(string json, string nestedDocumentsJson)
        => EvaluateJson(json, nestedDocumentsJson, SmartPropEvaluationOptions.Default);

    /// <summary>
    /// Evaluates a JSON SmartProp document with nested documents keyed by resource path.
    /// </summary>
    public static SmartPropEvaluationResult EvaluateJson(
        string json,
        string nestedDocumentsJson,
        SmartPropEvaluationOptions options)
    {
        ArgumentNullException.ThrowIfNull(json);
        ArgumentNullException.ThrowIfNull(nestedDocumentsJson);
        ArgumentNullException.ThrowIfNull(options);
        options.Validate();

        try
        {
            var nestedDocuments = ReadNestedDocuments(nestedDocumentsJson);
            return Evaluate(
                SmartPropJsonConverter.Convert(json),
                path => nestedDocuments.GetValueOrDefault(NormalizeResourcePath(path)),
                options);
        }
        catch (JsonException exception)
        {
            return new SmartPropEvaluationResult([], [new CoreDiagnostic(
                CoreDiagnosticSeverity.Error,
                "smartprop.invalid_json",
                exception.Message)]);
        }
    }

    /// <summary>
    /// Evaluates an uncompiled SmartProp document encoded as KeyValues3 text.
    /// </summary>
    public static SmartPropEvaluationResult EvaluateText(string text)
        => EvaluateText(text, SmartPropEvaluationOptions.Default);

    /// <summary>
    /// Evaluates an uncompiled SmartProp document encoded as KeyValues3 text.
    /// </summary>
    public static SmartPropEvaluationResult EvaluateText(string text, SmartPropEvaluationOptions options)
    {
        ArgumentNullException.ThrowIfNull(text);
        ArgumentNullException.ThrowIfNull(options);
        options.Validate();

        try
        {
            using var stream = new MemoryStream(System.Text.Encoding.UTF8.GetBytes(text));
            return Evaluate(KVDocumentExtensions.ParseKV3(stream).Root, null, options);
        }
        catch (Exception exception) when (exception is InvalidDataException or InvalidOperationException)
        {
            return new SmartPropEvaluationResult([], [new CoreDiagnostic(
                CoreDiagnosticSeverity.Error,
                "smartprop.invalid_kv3",
                exception.Message)]);
        }
    }

    private static SmartPropEvaluationResult Evaluate(
        ValveKeyValue.KVObject root,
        Func<string, ValveKeyValue.KVObject?>? nestedPropResolver,
        SmartPropEvaluationOptions options)
    {
        try
        {
            options.CancellationToken.ThrowIfCancellationRequested();
            Func<string, ValveKeyValue.KVObject?>? cancellableResolver = nestedPropResolver is null
                ? null
                : path =>
                {
                    options.CancellationToken.ThrowIfCancellationRequested();
                    return nestedPropResolver(path);
                };
            var result = SmartPropEvaluation.Evaluate(root, cancellableResolver, options.MaximumDepth);
            options.CancellationToken.ThrowIfCancellationRequested();
            var models = result.Models.Take(options.MaximumModels).Select(model => new EvaluatedSmartPropModel(
                model.ElementId,
                model.ModelName,
                model.Transform,
                model.MaterialGroup,
                model.TintColor)).ToArray();
            var diagnostics = result.Models.Count > options.MaximumModels
                ? new[] { new CoreDiagnostic(
                    CoreDiagnosticSeverity.Error,
                    "smartprop.model_limit_reached",
                    $"Evaluation produced more than {options.MaximumModels} model placements.") }
                : [];
            return new SmartPropEvaluationResult(models, diagnostics);
        }
        catch (OperationCanceledException)
        {
            return new SmartPropEvaluationResult([], [new CoreDiagnostic(
                CoreDiagnosticSeverity.Warning,
                "smartprop.cancelled",
                "SmartProp evaluation was cancelled.")]);
        }
        catch (Exception exception) when (exception is InvalidDataException or InvalidOperationException or ArgumentException)
        {
            return new SmartPropEvaluationResult([], [new CoreDiagnostic(
                CoreDiagnosticSeverity.Error,
                "smartprop.evaluation_failed",
                exception.Message)]);
        }
    }

    private static Dictionary<string, ValveKeyValue.KVObject> ReadNestedDocuments(string json)
    {
        using var document = JsonDocument.Parse(json);
        var nestedDocuments = new Dictionary<string, ValveKeyValue.KVObject>(StringComparer.OrdinalIgnoreCase);
        foreach (var property in document.RootElement.EnumerateObject())
        {
            nestedDocuments[NormalizeResourcePath(property.Name)] =
                SmartPropJsonConverter.Convert(property.Value.GetRawText());
        }
        return nestedDocuments;
    }

    private static string NormalizeResourcePath(string path)
        => path.Replace('\\', '/').TrimStart('/');
}

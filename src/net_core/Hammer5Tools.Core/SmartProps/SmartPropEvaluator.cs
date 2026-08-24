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
    {
        ArgumentNullException.ThrowIfNull(json);

        try
        {
            return Evaluate(SmartPropJsonConverter.Convert(json), null);
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
    {
        ArgumentNullException.ThrowIfNull(json);
        ArgumentNullException.ThrowIfNull(nestedDocumentsJson);

        try
        {
            var nestedDocuments = ReadNestedDocuments(nestedDocumentsJson);
            return Evaluate(
                SmartPropJsonConverter.Convert(json),
                path => nestedDocuments.GetValueOrDefault(NormalizeResourcePath(path)));
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
    {
        ArgumentNullException.ThrowIfNull(text);

        try
        {
            using var stream = new MemoryStream(System.Text.Encoding.UTF8.GetBytes(text));
            return Evaluate(KVDocumentExtensions.ParseKV3(stream).Root, null);
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
        Func<string, ValveKeyValue.KVObject?>? nestedPropResolver)
    {
        var result = SmartPropEvaluation.Evaluate(root, nestedPropResolver);
        var models = result.Models.Select(model => new EvaluatedSmartPropModel(
            model.ElementId,
            model.ModelName,
            model.Transform,
            model.MaterialGroup,
            model.TintColor)).ToArray();
        return new SmartPropEvaluationResult(models, []);
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

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
            return Evaluate(SmartPropJsonConverter.Convert(json));
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
            return Evaluate(KVDocumentExtensions.ParseKV3(stream).Root);
        }
        catch (Exception exception) when (exception is InvalidDataException or InvalidOperationException)
        {
            return new SmartPropEvaluationResult([], [new CoreDiagnostic(
                CoreDiagnosticSeverity.Error,
                "smartprop.invalid_kv3",
                exception.Message)]);
        }
    }

    private static SmartPropEvaluationResult Evaluate(ValveKeyValue.KVObject root)
    {
        var result = SmartPropEvaluation.Evaluate(root);
        var models = result.Models.Select(model => new EvaluatedSmartPropModel(
            model.ElementId,
            model.ModelName,
            model.Transform,
            model.MaterialGroup,
            model.TintColor)).ToArray();
        return new SmartPropEvaluationResult(models, []);
    }
}

using System.Text.Json;

using ValveKeyValue;
using ValveResourceFormat.ResourceTypes.SmartProps;

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
            using var document = JsonDocument.Parse(json);
            var root = ConvertValue(document.RootElement);
            var result = SmartPropEvaluation.Evaluate(root);
            var models = result.Models.Select(model => new EvaluatedSmartPropModel(
                model.ElementId,
                model.ModelName,
                model.Transform,
                model.MaterialGroup,
                model.TintColor)).ToArray();
            return new SmartPropEvaluationResult(models, []);
        }
        catch (JsonException exception)
        {
            return new SmartPropEvaluationResult([], [new CoreDiagnostic(
                CoreDiagnosticSeverity.Error,
                "smartprop.invalid_json",
                exception.Message)]);
        }
    }

    private static KVObject ConvertValue(JsonElement element)
    {
        return element.ValueKind switch
        {
            JsonValueKind.Object => ConvertObject(element),
            JsonValueKind.Array => ConvertArray(element),
            JsonValueKind.String => new KVObject(element.GetString() ?? string.Empty),
            JsonValueKind.Number when element.TryGetInt32(out var value) => new KVObject(value),
            JsonValueKind.Number => new KVObject(element.GetSingle()),
            JsonValueKind.True => new KVObject(true),
            JsonValueKind.False => new KVObject(false),
            _ => new KVObject(string.Empty),
        };
    }

    private static KVObject ConvertObject(JsonElement element)
    {
        var result = KVObject.Collection();
        foreach (var property in element.EnumerateObject())
        {
            var name = property.Name == "_class" ? "generic_data_type" : property.Name;
            result[name] = ConvertValue(property.Value);
        }
        return result;
    }

    private static KVObject ConvertArray(JsonElement element)
    {
        var result = KVObject.Array(element.GetArrayLength());
        foreach (var item in element.EnumerateArray())
            result.Add(ConvertValue(item));
        return result;
    }
}

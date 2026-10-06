using System.Linq;

using ValveKeyValue;

namespace Hammer5Tools.Core.Format.SmartProps.Evaluation;

/// <summary>
/// Describes one model produced by SmartProp evaluation.
/// </summary>
internal readonly record struct EvaluatedSmartPropModel(
    int ElementId,
    string ModelName,
    Matrix4x4 Transform,
    string? MaterialGroup,
    Vector4? TintColor);

/// <summary>
/// Contains the models produced by SmartProp evaluation.
/// </summary>
internal sealed record EvaluatedSmartProp(IReadOnlyList<EvaluatedSmartPropModel> Models);

/// <summary>
/// Evaluates SmartProp element data without renderer dependencies.
/// </summary>
internal static class SmartPropEvaluation
{
    /// <summary>
    /// Evaluates a SmartProp root object into placed model instances.
    /// </summary>
    public static EvaluatedSmartProp Evaluate(
        KVObject root,
        Func<string, KVObject?>? nestedPropResolver = null,
        int maxDepth = SmartPropEvaluator.DefaultMaxDepth)
    {
        ArgumentNullException.ThrowIfNull(root);
        ArgumentOutOfRangeException.ThrowIfNegativeOrZero(maxDepth);

        var result = SmartPropEvaluator.Evaluate(root, nestedPropResolver: nestedPropResolver, maxDepth: maxDepth);
        var models = result.Models.Select(model => new EvaluatedSmartPropModel(
            model.ElementId,
            model.ModelName,
            model.Transform,
            model.MaterialGroup,
            model.TintColor)).ToArray();
        return new EvaluatedSmartProp(models);
    }
}

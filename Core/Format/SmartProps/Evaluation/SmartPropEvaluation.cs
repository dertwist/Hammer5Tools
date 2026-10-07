using ValveKeyValue;

namespace Hammer5Tools.Core.Format.SmartProps.Evaluation;

/// <summary>
/// Contains the models produced by SmartProp evaluation.
/// </summary>
internal sealed record EvaluatedSmartProp(IReadOnlyList<EvaluatedSmartPropModel> Models, IReadOnlyList<EvaluatedSmartPropWidget> Widgets);

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
        int maxDepth = SmartPropEvaluator.DefaultMaxDepth,
        int maxModels = SmartPropEvaluator.DefaultMaxModels,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(root);
        ArgumentOutOfRangeException.ThrowIfNegativeOrZero(maxDepth);

        var result = SmartPropEvaluator.Evaluate(root, nestedPropResolver: nestedPropResolver, maxDepth: maxDepth, maxModels: maxModels, cancellationToken: cancellationToken);
        return new EvaluatedSmartProp(result.Models, result.Widgets);
    }
}

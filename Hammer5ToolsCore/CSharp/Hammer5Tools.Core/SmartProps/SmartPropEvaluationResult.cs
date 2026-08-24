namespace Hammer5Tools.Core.SmartProps;

/// <summary>
/// Contains evaluated SmartProp models and structured diagnostics.
/// </summary>
public sealed record SmartPropEvaluationResult(
    IReadOnlyList<EvaluatedSmartPropModel> Models,
    IReadOnlyList<CoreDiagnostic> Diagnostics);

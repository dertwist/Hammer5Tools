namespace Hammer5Tools.Core.SmartProps;

/// <summary>
/// Configures bounded SmartProp evaluation behavior.
/// </summary>
public sealed record SmartPropEvaluationOptions
{
    /// <summary>
    /// Initializes bounded SmartProp evaluation options.
    /// </summary>
    public SmartPropEvaluationOptions(
        int maximumDepth = 32,
        int maximumModels = 100_000,
        CancellationToken cancellationToken = default)
    {
        MaximumDepth = maximumDepth;
        MaximumModels = maximumModels;
        CancellationToken = cancellationToken;
    }

    /// <summary>
    /// Gets the default evaluation options.
    /// </summary>
    public static SmartPropEvaluationOptions Default { get; } = new();

    /// <summary>
    /// Gets the maximum recursive evaluation depth, including the root document.
    /// </summary>
    public int MaximumDepth { get; init; }

    /// <summary>
    /// Gets the maximum number of model placements returned to a caller.
    /// </summary>
    public int MaximumModels { get; init; }

    /// <summary>
    /// Gets the cooperative cancellation token for this evaluation.
    /// </summary>
    public CancellationToken CancellationToken { get; init; }

    internal void Validate()
    {
        ArgumentOutOfRangeException.ThrowIfNegativeOrZero(MaximumDepth);
        ArgumentOutOfRangeException.ThrowIfNegativeOrZero(MaximumModels);
    }
}

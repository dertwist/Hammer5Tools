namespace Hammer5Tools.Core.SmartProps;

/// <summary>
/// Describes one typed SmartProp field value without exposing a file-format container.
/// </summary>
public sealed class SmartPropValue
{
    private SmartPropValue(float literal)
    {
        Literal = literal;
    }

    private SmartPropValue(string text, SmartPropValueKind kind)
    {
        Text = text;
        Kind = kind;
    }

    private SmartPropValue(IReadOnlyList<SmartPropValue> components)
    {
        Components = components;
        Kind = SmartPropValueKind.Components;
    }

    internal float Literal { get; }

    internal string? Text { get; }

    internal IReadOnlyList<SmartPropValue>? Components { get; }

    internal SmartPropValueKind Kind { get; }

    /// <summary>
    /// Creates a numeric literal value.
    /// </summary>
    public static SmartPropValue FromLiteral(float value) => new(value);

    /// <summary>
    /// Creates a case-insensitive variable reference.
    /// </summary>
    public static SmartPropValue FromVariable(string name)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(name);
        return new(name, SmartPropValueKind.Variable);
    }

    /// <summary>
    /// Creates a numeric SmartProp expression value.
    /// </summary>
    public static SmartPropValue FromExpression(string expression)
    {
        ArgumentNullException.ThrowIfNull(expression);
        return new(expression, SmartPropValueKind.Expression);
    }

    /// <summary>
    /// Creates a component value, such as a Source 2 vector field.
    /// </summary>
    public static SmartPropValue FromComponents(IReadOnlyList<SmartPropValue> components)
    {
        ArgumentNullException.ThrowIfNull(components);
        return new(components);
    }
}

internal enum SmartPropValueKind
{
    Literal,
    Variable,
    Expression,
    Components,
}

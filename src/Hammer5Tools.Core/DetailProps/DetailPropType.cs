namespace Hammer5Tools.Core.DetailProps;

/// <summary>
/// A detail prop type containing density parameters and a collection of model variations.
/// </summary>
public class DetailPropType
{
    public string Name { get; set; } = string.Empty;

    public float Density { get; set; } = 1.0f;

    public List<DetailPropModel> Models { get; } = [];

    public DetailPropType(string name)
    {
        Name = name;
    }

    public DetailPropType(string name, float density) : this(name)
    {
        Density = density;
    }

    public DetailPropType()
    {
    }
}

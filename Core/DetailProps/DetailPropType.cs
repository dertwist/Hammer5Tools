namespace Hammer5Tools.Core.DetailProps;

/// <summary>
/// A detail prop type containing density parameters and a collection of model variations.
/// </summary>
public class DetailPropType : CommunityToolkit.Mvvm.ComponentModel.ObservableObject
{
    private string NameValue = string.Empty;

    public string Name
    {
        get => NameValue;
        set => SetProperty(ref NameValue, value);
    }

    private float DensityValue = 1.0f;

    public float Density
    {
        get => DensityValue;
        set => SetProperty(ref DensityValue, value);
    }

    public System.Collections.ObjectModel.ObservableCollection<DetailPropModel> Models { get; } = [];

    internal ValveKeyValue.KVObject Original { get; set; } = new();

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

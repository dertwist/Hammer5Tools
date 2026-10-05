namespace Hammer5Tools.Core.SoundEvents;

using System.Collections.ObjectModel;

public class SoundEvent : CommunityToolkit.Mvvm.ComponentModel.ObservableObject
{
    private string NameValue = string.Empty;

    public string Name
    {
        get => NameValue;
        set => SetProperty(ref NameValue, value);
    }

    private string TypeValue = "csgo_mega";

    public string Type
    {
        get => TypeValue;
        set => SetProperty(ref TypeValue, value);
    }

    public ObservableCollection<SoundProperty> Properties { get; } = [];

    public SoundEvent()
    {
    }

    public SoundEvent(string name, string type = "csgo_mega")
    {
        Name = name;
        Type = type;
    }

    public string? GetValue(string key) =>
        Properties.FirstOrDefault(p => p.Key.Equals(key, StringComparison.OrdinalIgnoreCase))?.Value;

    public void SetValue(string key, string value)
    {
        var existing = Properties.FirstOrDefault(p => p.Key.Equals(key, StringComparison.OrdinalIgnoreCase));
        if (existing is not null)
        {
            existing.Value = value;
        }
        else
        {
            Properties.Add(new SoundProperty(key, value));
        }
    }
}

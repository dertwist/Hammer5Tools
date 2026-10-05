namespace Hammer5Tools.Core.SoundEvents;

using System.Collections.ObjectModel;

public class SoundEvent
{
    public string Name { get; set; } = string.Empty;

    public string Type { get; set; } = "csgo_mega";

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

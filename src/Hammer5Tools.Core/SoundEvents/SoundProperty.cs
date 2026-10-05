namespace Hammer5Tools.Core.SoundEvents;

public class SoundProperty
{
    public string Key { get; set; } = string.Empty;

    public string Value { get; set; } = string.Empty;

    public SoundProperty()
    {
    }

    public SoundProperty(string key, string value)
    {
        Key = key;
        Value = value;
    }
}

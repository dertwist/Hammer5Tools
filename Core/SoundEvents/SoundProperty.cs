namespace Hammer5Tools.Core.SoundEvents;

public class SoundProperty : CommunityToolkit.Mvvm.ComponentModel.ObservableObject
{
    private string KeyValue = string.Empty;

    public string Key
    {
        get => KeyValue;
        set => SetProperty(ref KeyValue, value);
    }

    private string ValueValue = string.Empty;

    public string Value
    {
        get => ValueValue;
        set => SetProperty(ref ValueValue, value);
    }

    public SoundProperty()
    {
    }

    public SoundProperty(string key, string value)
    {
        Key = key;
        Value = value;
    }
}

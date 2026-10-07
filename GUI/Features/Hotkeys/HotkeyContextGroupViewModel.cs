namespace Hammer5Tools.App.Features.Hotkeys;

using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;

public class HotkeyContextGroupViewModel : ObservableObject
{
    private bool IsExpandedValue = true;
    private bool IsVisibleValue = true;

    public string ContextName { get; }

    public ObservableCollection<HotkeyCommandRowViewModel> Commands { get; } = [];

    public bool IsExpanded
    {
        get => IsExpandedValue;
        set => SetProperty(ref IsExpandedValue, value);
    }

    public bool IsVisible
    {
        get => IsVisibleValue;
        set => SetProperty(ref IsVisibleValue, value);
    }

    public HotkeyContextGroupViewModel(string contextName)
    {
        ContextName = contextName;
    }
}

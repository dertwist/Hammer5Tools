namespace Hammer5Tools.App.Features.Hotkeys;

using Avalonia.Controls;
using Avalonia.Input;

public partial class HotkeyEditorView : UserControl
{
    public HotkeyEditorView()
    {
        InitializeComponent();
    }

    private void OnPresetDoubleTapped(object? sender, TappedEventArgs e)
    {
        if (DataContext is HotkeyEditorViewModel vm && vm.SelectedPreset is not null)
        {
            vm.OpenPresetFile(vm.SelectedPreset.FilePath);
        }
    }
}

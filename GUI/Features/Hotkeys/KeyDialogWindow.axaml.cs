namespace Hammer5Tools.App.Features.Hotkeys;

using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;

public partial class KeyDialogWindow : Window
{
    private static readonly Dictionary<Key, string> KeyNames = new()
    {
        [Key.Back] = "Backspace",
        [Key.Tab] = "Tab",
        [Key.Enter] = "Enter",
        [Key.Escape] = "Esc",
        [Key.Space] = "Space",
        [Key.Delete] = "Del",
        [Key.Home] = "Home",
        [Key.End] = "End",
        [Key.Insert] = "Ins",
        [Key.PageUp] = "PgUp",
        [Key.PageDown] = "PgDn",
        [Key.Up] = "Up",
        [Key.Down] = "Down",
        [Key.Left] = "Left",
        [Key.Right] = "Right",
        [Key.Pause] = "Break",
        [Key.NumPad0] = "Num0",
        [Key.NumPad1] = "Num1",
        [Key.NumPad2] = "Num2",
        [Key.NumPad3] = "Num3",
        [Key.NumPad4] = "Num4",
        [Key.NumPad5] = "Num5",
        [Key.NumPad6] = "Num6",
        [Key.NumPad7] = "Num7",
        [Key.NumPad8] = "Num8",
        [Key.NumPad9] = "Num9",
        [Key.Add] = "NumAdd",
        [Key.Subtract] = "NumSub",
        [Key.Decimal] = "NumDec",
    };

    public KeyDialogWindow()
    {
        InitializeComponent();
        KeyLineBox.AddHandler(KeyDownEvent, OnKeyLineKeyDown, RoutingStrategies.Tunnel | RoutingStrategies.Bubble);
    }

    public KeyDialogWindow(KeyDialogViewModel viewModel) : this()
    {
        DataContext = viewModel;
    }

    protected override void OnOpened(EventArgs e)
    {
        base.OnOpened(e);
        if (DataContext is KeyDialogViewModel vm && !vm.IsSelectFromList)
        {
            KeyLineBox.Focus();
        }
        else
        {
            SpecialInputCombo.Focus();
        }
    }

    private void OnKeyLineKeyDown(object? sender, KeyEventArgs e)
    {
        if (DataContext is not KeyDialogViewModel vm) return;

        if (e.KeyModifiers.HasFlag(KeyModifiers.Control)) vm.IsCtrl = true;
        if (e.KeyModifiers.HasFlag(KeyModifiers.Shift)) vm.IsShift = true;
        if (e.KeyModifiers.HasFlag(KeyModifiers.Alt)) vm.IsAlt = true;

        if (e.Key is Key.LeftCtrl or Key.RightCtrl or Key.LeftShift or Key.RightShift or Key.LeftAlt or Key.RightAlt)
        {
            vm.KeyText = string.Empty;
            vm.RecomputeResult();
            e.Handled = true;
            return;
        }

        string keyName;
        if (e.Key >= Key.F1 && e.Key <= Key.F24)
        {
            keyName = $"F{e.Key - Key.F1 + 1}";
        }
        else if (KeyNames.TryGetValue(e.Key, out var mapped))
        {
            keyName = mapped;
        }
        else if (e.Key >= Key.A && e.Key <= Key.Z)
        {
            keyName = e.Key.ToString().ToUpperInvariant();
        }
        else if (e.Key >= Key.D0 && e.Key <= Key.D9)
        {
            keyName = ((int)e.Key - (int)Key.D0).ToString();
        }
        else
        {
            keyName = e.Key.ToString();
        }

        vm.KeyText = keyName;
        vm.RecomputeResult();
        e.Handled = true;
    }

    private void OnOkClick(object? sender, RoutedEventArgs e)
    {
        if (DataContext is KeyDialogViewModel vm)
        {
            Close(vm.ResultValue);
        }
        else
        {
            Close(null);
        }
    }

    private void OnCancelClick(object? sender, RoutedEventArgs e)
    {
        Close(null);
    }
}

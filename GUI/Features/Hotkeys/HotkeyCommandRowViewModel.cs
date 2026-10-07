namespace Hammer5Tools.App.Features.Hotkeys;

using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.Core.Hotkeys;

public class HotkeyCommandRowViewModel : ObservableObject
{
    private string InputValue = string.Empty;
    private bool IsVisibleValue = true;

    public string Context { get; }

    public string Command { get; }

    public HotkeyBinding Binding { get; }

    public Action<HotkeyCommandRowViewModel>? OnChanged { get; set; }

    public Func<HotkeyCommandRowViewModel, Task>? OnEditRequested { get; set; }

    public string Input
    {
        get => InputValue;
        set
        {
            if (SetProperty(ref InputValue, value))
            {
                Binding.Input = value;
                OnPropertyChanged(nameof(DisplayInput));
                OnChanged?.Invoke(this);
            }
        }
    }

    public string DisplayInput => string.IsNullOrWhiteSpace(Input) ? "Press a key" : Input;

    public bool IsVisible
    {
        get => IsVisibleValue;
        set => SetProperty(ref IsVisibleValue, value);
    }

    public IRelayCommand EditKeyCommand { get; }

    public HotkeyCommandRowViewModel(HotkeyBinding binding, Action<HotkeyCommandRowViewModel>? onChanged = null, Func<HotkeyCommandRowViewModel, Task>? onEditRequested = null)
    {
        Binding = binding;
        Context = binding.Context;
        Command = binding.Command;
        InputValue = binding.Input;
        OnChanged = onChanged;
        OnEditRequested = onEditRequested;

        EditKeyCommand = new AsyncRelayCommand(async () =>
        {
            if (OnEditRequested is not null)
            {
                await OnEditRequested(this);
            }
        });
    }
}

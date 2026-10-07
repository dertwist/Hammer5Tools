namespace Hammer5Tools.App.Features.Hotkeys;

using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;

public partial class KeyDialogViewModel : ObservableObject
{
    public static readonly string[] SpecialInputs =
    [
        "",
        "NumEnter", "Enter", "Esc", "Space", "Tab", "Backspace", "Del",
        "Home", "End", "Ins", "PgUp", "PgDn", "Break",
        "LMouse", "RMouse", "MMouse", "Mouse4", "Mouse5",
        "LMouseDoubleClick", "RMouseDoubleClick",
        "MWheelUp", "MWheelDn", "MWheelLeft", "MWheelRight",
        "Up", "Down", "Left", "Right",
        "Num0", "Num1", "Num2", "Num3", "Num4", "Num5", "Num6", "Num7",
        "Num8", "Num9", "NumAdd", "NumSub", "NumDec",
        "Ctrl", "Shift", "Alt",
        "SELECTION_ADD_KEY", "SELECTION_REMOVE_KEY", "SELECTION_ADJUST_KEY",
        "TOGGLE_SNAPPING_KEY",
    ];

    private bool IsSelectFromListValue;
    private string KeyTextValue = string.Empty;
    private string SelectedSpecialInputValue = string.Empty;
    private bool IsCtrlValue;
    private bool IsShiftValue;
    private bool IsAltValue;
    private string ResultValueInternal = string.Empty;

    public bool IsSelectFromList
    {
        get => IsSelectFromListValue;
        set
        {
            if (SetProperty(ref IsSelectFromListValue, value))
            {
                RecomputeResult();
            }
        }
    }

    public string KeyText
    {
        get => KeyTextValue;
        set
        {
            if (SetProperty(ref KeyTextValue, value))
            {
                RecomputeResult();
            }
        }
    }

    public string SelectedSpecialInput
    {
        get => SelectedSpecialInputValue;
        set
        {
            if (SetProperty(ref SelectedSpecialInputValue, value ?? string.Empty))
            {
                RecomputeResult();
            }
        }
    }

    public bool IsCtrl
    {
        get => IsCtrlValue;
        set
        {
            if (SetProperty(ref IsCtrlValue, value))
            {
                RecomputeResult();
            }
        }
    }

    public bool IsShift
    {
        get => IsShiftValue;
        set
        {
            if (SetProperty(ref IsShiftValue, value))
            {
                RecomputeResult();
            }
        }
    }

    public bool IsAlt
    {
        get => IsAltValue;
        set
        {
            if (SetProperty(ref IsAltValue, value))
            {
                RecomputeResult();
            }
        }
    }

    public string ResultValue => ResultValueInternal;

    public KeyDialogViewModel(string? initialBinding = null)
    {
        InitializeFrom(initialBinding);
    }

    public void InitializeFrom(string? binding)
    {
        if (string.IsNullOrWhiteSpace(binding))
        {
            IsCtrl = false;
            IsShift = false;
            IsAlt = false;
            KeyText = string.Empty;
            SelectedSpecialInput = string.Empty;
            RecomputeResult();
            return;
        }

        var parts = binding.Split('+', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        var baseParts = new List<string>();

        foreach (var part in parts)
        {
            if (string.Equals(part, "Ctrl", StringComparison.OrdinalIgnoreCase))
            {
                IsCtrlValue = true;
            }
            else if (string.Equals(part, "Shift", StringComparison.OrdinalIgnoreCase))
            {
                IsShiftValue = true;
            }
            else if (string.Equals(part, "Alt", StringComparison.OrdinalIgnoreCase))
            {
                IsAltValue = true;
            }
            else
            {
                baseParts.Add(part);
            }
        }

        var keyPart = string.Join("+", baseParts);
        KeyTextValue = keyPart;
        SelectedSpecialInputValue = keyPart;

        if (SpecialInputs.Contains(keyPart, StringComparer.OrdinalIgnoreCase))
        {
            IsSelectFromListValue = true;
        }

        OnPropertyChanged(nameof(IsCtrl));
        OnPropertyChanged(nameof(IsShift));
        OnPropertyChanged(nameof(IsAlt));
        OnPropertyChanged(nameof(KeyText));
        OnPropertyChanged(nameof(SelectedSpecialInput));
        OnPropertyChanged(nameof(IsSelectFromList));

        RecomputeResult();
    }

    public void RecomputeResult()
    {
        var rawKey = IsSelectFromList ? SelectedSpecialInput.Trim() : KeyText.Trim();

        var parts = new List<string>();
        if (IsCtrl) parts.Add("Ctrl");
        if (IsShift) parts.Add("Shift");
        if (IsAlt) parts.Add("Alt");

        var known = new HashSet<string>(parts, StringComparer.OrdinalIgnoreCase);
        foreach (var keyPart in rawKey.Split('+', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
        {
            if (known.Add(keyPart))
            {
                parts.Add(keyPart);
            }
        }

        ResultValueInternal = string.Join("+", parts);
        OnPropertyChanged(nameof(ResultValue));
    }
}

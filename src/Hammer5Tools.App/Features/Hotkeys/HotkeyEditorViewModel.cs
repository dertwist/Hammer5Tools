namespace Hammer5Tools.App.Features.Hotkeys;

using System.Collections.ObjectModel;
using System.IO;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.Hotkeys;

public class HotkeyEditorViewModel : DocumentViewModel
{
    public override string IconUri => "avares://Hammer5Tools.App/Assets/Icons/hotkey_editor.png";

    private readonly ICs2Locator Cs2Locator;
    private readonly string? FilePath;
    private HotkeyDocument Document;

    private string FilterTextValue = string.Empty;
    private string? SelectedContextValue;
    private HotkeyBinding? SelectedBindingValue;
    private string NewKeyInputValue = string.Empty;

    public ObservableCollection<string> Contexts { get; } = [];

    public ObservableCollection<HotkeyBinding> FilteredBindings { get; } = [];

    public string FilterText
    {
        get => FilterTextValue;
        set
        {
            if (SetProperty(ref FilterTextValue, value))
            {
                ApplyFilter();
            }
        }
    }

    public string? SelectedContext
    {
        get => SelectedContextValue;
        set
        {
            if (SetProperty(ref SelectedContextValue, value))
            {
                ApplyFilter();
            }
        }
    }

    public HotkeyBinding? SelectedBinding
    {
        get => SelectedBindingValue;
        set
        {
            if (SetProperty(ref SelectedBindingValue, value))
            {
                NewKeyInput = value?.Input ?? string.Empty;
            }
        }
    }

    public string NewKeyInput
    {
        get => NewKeyInputValue;
        set => SetProperty(ref NewKeyInputValue, value);
    }

    public IRelayCommand ApplyBindingCommand { get; }

    public IRelayCommand ApplyToCs2Command { get; }

    public HotkeyEditorViewModel(ICs2Locator cs2Locator, string? filePath = null)
    {
        Cs2Locator = cs2Locator;
        FilePath = filePath;
        Title = string.IsNullOrWhiteSpace(filePath) ? "Hotkey Editor" : Path.GetFileName(filePath);

        if (!string.IsNullOrWhiteSpace(filePath) && File.Exists(filePath))
        {
            Document = HotkeyDocument.Load(filePath);
        }
        else
        {
            Document = new HotkeyDocument();
            Document.SetBinding("HammerApp", "FileSave", "Ctrl+S");
            Document.SetBinding("HammerApp", "FileOpen", "Ctrl+O");
            Document.SetBinding("HammerApp", "FileNew", "Ctrl+N");
            Document.SetBinding("HammerEditorSession", "ClearSelection", "Esc");
            Document.SetBinding("HammerEditorSession", "SelectAll", "Ctrl+A");
        }

        ApplyBindingCommand = new RelayCommand(OnApplyBinding);
        ApplyToCs2Command = new RelayCommand(OnApplyToCs2);

        RefreshContexts();
    }

    private void RefreshContexts()
    {
        Contexts.Clear();
        Contexts.Add("All");
        foreach (var ctx in Document.Contexts)
        {
            Contexts.Add(ctx);
        }

        SelectedContext = "All";
    }

    private void ApplyFilter()
    {
        FilteredBindings.Clear();
        var query = FilterText.Trim();

        foreach (var binding in Document.Bindings)
        {
            if (SelectedContext != "All" && !string.IsNullOrEmpty(SelectedContext) && !string.Equals(binding.Context, SelectedContext, StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            if (!string.IsNullOrEmpty(query) &&
                !binding.Command.Contains(query, StringComparison.OrdinalIgnoreCase) &&
                !binding.Input.Contains(query, StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            FilteredBindings.Add(binding);
        }
    }

    private void OnApplyBinding()
    {
        if (SelectedBinding is null || string.IsNullOrWhiteSpace(NewKeyInput))
        {
            return;
        }

        SelectedBinding.Input = NewKeyInput.Trim();
        MarkDirty();
        ApplyFilter();
    }

    private void OnApplyToCs2()
    {
        var cs2Path = Cs2Locator.ResolvedCs2Path;
        if (string.IsNullOrWhiteSpace(cs2Path))
        {
            return;
        }

        var keybindingsDir = Cs2Paths.GetKeybindingsPath(cs2Path);
        var targetFile = Path.Combine(keybindingsDir, "keybindings_hammer.txt");
        Document.Save(targetFile);
        Save();
    }

    public override void Save()
    {
        if (!string.IsNullOrWhiteSpace(FilePath))
        {
            Document.Save(FilePath);
        }

        base.Save();
    }
}

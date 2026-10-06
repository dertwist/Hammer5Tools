namespace Hammer5Tools.App.Features.Hotkeys;

using System.Collections.ObjectModel;
using System.IO;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.Hotkeys;

public class HotkeyEditorViewModel : DocumentViewModel
{
    public override string IconUri => "avares://Hammer5Tools/Assets/Icons/hotkey_editor.png";

    private readonly ICs2Locator Cs2Locator;
    private readonly Services.IDialogService DialogService;
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

    public IRelayCommand NewPresetCommand { get; }

    public IRelayCommand OpenPresetCommand { get; }

    public IRelayCommand ApplyAndRestartCommand { get; }

    public IRelayCommand ApplyBindingCommand { get; }

    public IRelayCommand ApplyToCs2Command { get; }

    public HotkeyEditorViewModel(ICs2Locator cs2Locator, Services.IDialogService dialogService, ICs2Launcher? launcher = null, string? filePath = null)
    {
        Cs2Locator = cs2Locator;
        DocumentPath = filePath;
        DialogService = dialogService;
        ReportSaveFailure = dialogService.ShowErrorAsync;
        Title = string.IsNullOrWhiteSpace(filePath) ? "Hotkey Editor" : Path.GetFileName(filePath);

        var installedPath = cs2Locator.ResolvedCs2Path is { } root
            ? Path.Combine(Cs2Paths.GetKeybindingsPath(root), "keybindings_hammer.txt") : null;
        if (string.IsNullOrWhiteSpace(filePath) && File.Exists(installedPath))
        {
            Document = HotkeyDocument.Load(installedPath!);
        }
        else if (!string.IsNullOrWhiteSpace(filePath) && File.Exists(filePath))
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
        ApplyToCs2Command = new AsyncRelayCommand(OnApplyToCs2Async);

        NewPresetCommand = new AsyncRelayCommand(async () =>
        {
            if (await DialogService.ConfirmCloseAsync([this]))
            {
                Document = HotkeyDocument.Parse(Document.Serialize());
                DocumentPath = null;
                Title = "Hotkey Editor";
                RefreshContexts();
                ObserveModels(Document.Bindings);
                MarkDirty();
            }
        });
        OpenPresetCommand = new AsyncRelayCommand(async () =>
        {
            if (!await DialogService.ConfirmCloseAsync([this]))
            {
                return;
            }

            var path = await DialogService.OpenFileAsync("Open hotkey preset", "*.txt");
            if (path is not null)
            {
                Document = HotkeyDocument.Load(path);
                DocumentPath = path;
                Title = Path.GetFileName(path);
                RefreshContexts();
                ObserveModels(Document.Bindings);
                InitializeHistory(() => Document.Serialize(), RestoreHistory);
            }
        });
        ApplyAndRestartCommand = new AsyncRelayCommand(async () =>
        {
            if (await ApplyToCs2Async() && launcher is not null)
            {
                await launcher.RestartAsync();
            }
        });
        RefreshContexts();
        InitializeHistory(() => Document.Serialize(), RestoreHistory);
        ObserveModels(Document.Bindings);
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

    private async Task OnApplyToCs2Async()
    {
        await ApplyToCs2Async();
    }

    private async Task<bool> ApplyToCs2Async()
    {
        var cs2Path = Cs2Locator.ResolvedCs2Path;
        if (string.IsNullOrWhiteSpace(cs2Path))
        {
            await DialogService.ShowErrorAsync("CS2 installation not found.");
            return false;
        }

        if (!await DialogService.ConfirmCloseAsync([this]))
        {
            return false;
        }

        var targetFile = Path.Combine(Cs2Paths.GetKeybindingsPath(cs2Path), "keybindings_hammer.txt");
        try
        {
            Document.Save(targetFile);
            return true;
        }
        catch (Exception ex)
        {
            await DialogService.ShowErrorAsync(ex.Message);
            return false;
        }
    }

    protected override async Task<bool> SaveCoreAsync()
    {
        DocumentPath ??= await DialogService.SaveFileAsync("Save hotkey preset", "keybindings_hammer.txt");
        if (DocumentPath is null)
        {
            return false;
        }

        Document.Save(DocumentPath);
        Title = Path.GetFileName(DocumentPath);
        return true;
    }
    private void RestoreHistory(string text)
    {
        Document = HotkeyDocument.Parse(text);
        RefreshContexts();
        ObserveModels(Document.Bindings);
    }
}

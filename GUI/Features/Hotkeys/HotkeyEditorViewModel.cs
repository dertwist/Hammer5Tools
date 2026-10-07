namespace Hammer5Tools.App.Features.Hotkeys;

using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.Hotkeys;

public class HotkeyEditorViewModel : DocumentViewModel
{
    public override string IconUri => "avares://Hammer5Tools/Assets/Icons/hotkey_editor.png";

    private readonly ICs2Locator Cs2Locator;
    private readonly Services.IDialogService DialogService;
    private readonly ICs2Launcher? Launcher;

    private HotkeyDocument Document;
    private string SelectedEditorNameValue = "Hammer";
    private string SelectedEditorStemValue = "hammer";
    private string PresetFilterTextValue = string.Empty;
    private HotkeyPresetItemViewModel? SelectedPresetValue;
    private string CommandFilterTextValue = string.Empty;
    private string? KeyFilterInputValue;
    private string? SelectedContextValue;
    private HotkeyBinding? SelectedBindingValue;
    private string NewKeyInputValue = string.Empty;

    public static IReadOnlyList<string> EditorDisplayNames => HotkeyCatalogService.EditorDisplayNames;

    public ObservableCollection<HotkeyPresetItemViewModel> Presets { get; } = [];

    public ObservableCollection<HotkeyPresetItemViewModel> FilteredPresets { get; } = [];

    public ObservableCollection<HotkeyContextGroupViewModel> ContextGroups { get; } = [];

    public ObservableCollection<HotkeyContextGroupViewModel> FilteredContextGroups { get; } = [];

    // Backward compatibility collections and properties for test suites
    public ObservableCollection<string> Contexts { get; } = [];

    public ObservableCollection<HotkeyBinding> FilteredBindings { get; } = [];

    public string SelectedEditorName
    {
        get => SelectedEditorNameValue;
        set
        {
            if (SetProperty(ref SelectedEditorNameValue, value))
            {
                SelectedEditorStemValue = HotkeyCatalogService.GetStem(value);
                OnPropertyChanged(nameof(SelectedEditorStem));
                OnEditorSwitched();
            }
        }
    }

    public string SelectedEditorStem => SelectedEditorStemValue;

    public string PresetFilterText
    {
        get => PresetFilterTextValue;
        set
        {
            if (SetProperty(ref PresetFilterTextValue, value))
            {
                ApplyPresetFilter();
            }
        }
    }

    public HotkeyPresetItemViewModel? SelectedPreset
    {
        get => SelectedPresetValue;
        set => SetProperty(ref SelectedPresetValue, value);
    }

    public string CommandFilterText
    {
        get => CommandFilterTextValue;
        set
        {
            if (SetProperty(ref CommandFilterTextValue, value))
            {
                ApplyCommandFilter();
            }
        }
    }

    public string FilterText
    {
        get => CommandFilterText;
        set => CommandFilterText = value;
    }

    public string? KeyFilterInput
    {
        get => KeyFilterInputValue;
        set
        {
            if (SetProperty(ref KeyFilterInputValue, value))
            {
                OnPropertyChanged(nameof(KeyFilterButtonText));
                ApplyCommandFilter();
            }
        }
    }

    public string KeyFilterButtonText => string.IsNullOrWhiteSpace(KeyFilterInput) ? "Press a key" : KeyFilterInput;

    public string? SelectedContext
    {
        get => SelectedContextValue;
        set
        {
            if (SetProperty(ref SelectedContextValue, value))
            {
                ApplyCommandFilter();
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

    public IRelayCommand SetCurrentCommand { get; }

    public IRelayCommand NewPresetCommand { get; }

    public IRelayCommand OpenPresetCommand { get; }

    public IRelayCommand SetSaveRestartCommand { get; }

    public IRelayCommand FilterKeyCommand { get; }

    public IRelayCommand OpenFolderCommand { get; }

    public IRelayCommand ToggleRecentCommand { get; }

    public IRelayCommand ToggleFavoritesCommand { get; }

    public IRelayCommand ApplyBindingCommand { get; }

    public IRelayCommand ApplyToCs2Command { get; }

    public IRelayCommand ApplyAndRestartCommand { get; }

    public HotkeyEditorViewModel(ICs2Locator cs2Locator, Services.IDialogService dialogService, ICs2Launcher? launcher = null, string? filePath = null)
    {
        Cs2Locator = cs2Locator;
        DialogService = dialogService;
        Launcher = launcher;
        DocumentPath = filePath;
        ReportSaveFailure = dialogService.ShowErrorAsync;
        Title = string.IsNullOrWhiteSpace(filePath) ? "Hotkey Editor" : Path.GetFileName(filePath);

        // Commands
        SetCurrentCommand = new AsyncRelayCommand(OnSetCurrentAsync);
        NewPresetCommand = new AsyncRelayCommand(OnNewPresetAsync);
        OpenPresetCommand = new AsyncRelayCommand(OnOpenPresetAsync);
        SetSaveRestartCommand = new AsyncRelayCommand(OnSetSaveRestartAsync);
        FilterKeyCommand = new AsyncRelayCommand(OnFilterKeyAsync);
        OpenFolderCommand = new RelayCommand(OnOpenFolder);
        ToggleRecentCommand = new RelayCommand(OnToggleRecent);
        ToggleFavoritesCommand = new RelayCommand(OnToggleFavorites);

        // Backward compatibility commands
        ApplyBindingCommand = new RelayCommand(OnApplyBinding);
        ApplyToCs2Command = new AsyncRelayCommand(OnApplyToCs2Async);
        ApplyAndRestartCommand = new AsyncRelayCommand(OnSetSaveRestartAsync);

        if (!string.IsNullOrWhiteSpace(filePath) && File.Exists(filePath))
        {
            Document = HotkeyDocument.Load(filePath);
            DetectEditorFromFileName(filePath);
        }
        else
        {
            Document = HotkeyCatalogService.CreateDefaultDocument(SelectedEditorStem);
        }

        HotkeyCatalogService.PopulateEditor(Document, SelectedEditorStem, Cs2Locator.ResolvedCs2Path);

        RefreshPresetsList();
        BuildTreeFromDocument();
        InitializeHistory(() => Document.Serialize(), RestoreHistory);
        ObserveModels(Document.Bindings);
    }

    public void OpenPresetFile(string path)
    {
        if (!File.Exists(path)) return;

        Document = HotkeyDocument.Load(path);
        DocumentPath = path;
        Title = Path.GetFileName(path);
        DetectEditorFromFileName(path);

        HotkeyCatalogService.PopulateEditor(Document, SelectedEditorStem, Cs2Locator.ResolvedCs2Path);
        BuildTreeFromDocument();
        InitializeHistory(() => Document.Serialize(), RestoreHistory);
        ObserveModels(Document.Bindings);
    }

    private void DetectEditorFromFileName(string path)
    {
        var fileName = Path.GetFileName(path).ToLowerInvariant();
        foreach (var (display, stem) in HotkeyCatalogService.Stems)
        {
            if (fileName.StartsWith(stem, StringComparison.OrdinalIgnoreCase))
            {
                SelectedEditorNameValue = display;
                SelectedEditorStemValue = stem;
                OnPropertyChanged(nameof(SelectedEditorName));
                OnPropertyChanged(nameof(SelectedEditorStem));
                return;
            }
        }
    }

    private void OnEditorSwitched()
    {
        RefreshPresetsList();

        // Presets belong to the editor they were written for, so start clean matching Python editor_switch()
        Document = HotkeyCatalogService.CreateDefaultDocument(SelectedEditorStem);
        DocumentPath = null;
        Title = "Hotkey Editor";
        HotkeyCatalogService.PopulateEditor(Document, SelectedEditorStem, Cs2Locator.ResolvedCs2Path);

        BuildTreeFromDocument();
        InitializeHistory(() => Document.Serialize(), RestoreHistory);
        ObserveModels(Document.Bindings);
    }

    private void RefreshPresetsList()
    {
        Presets.Clear();
        var seenFiles = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        var dirs = HotkeyCatalogService.GetPresetDirectories(SelectedEditorStem);
        foreach (var dir in dirs)
        {
            if (!Directory.Exists(dir)) continue;

            foreach (var file in Directory.EnumerateFiles(dir, "*.*", SearchOption.TopDirectoryOnly))
            {
                var ext = Path.GetExtension(file);
                if (ext.Equals(".keybindings", StringComparison.OrdinalIgnoreCase) || ext.Equals(".txt", StringComparison.OrdinalIgnoreCase))
                {
                    if (seenFiles.Add(file))
                    {
                        Presets.Add(new HotkeyPresetItemViewModel(file));
                    }
                }
            }
        }

        ApplyPresetFilter();
    }

    private void ApplyPresetFilter()
    {
        FilteredPresets.Clear();
        var query = PresetFilterText.Trim();

        foreach (var preset in Presets)
        {
            if (string.IsNullOrEmpty(query) || preset.DisplayName.Contains(query, StringComparison.OrdinalIgnoreCase))
            {
                FilteredPresets.Add(preset);
            }
        }
    }

    private void BuildTreeFromDocument()
    {
        ContextGroups.Clear();
        Contexts.Clear();
        Contexts.Add("All");

        var groupsByContext = new Dictionary<string, HotkeyContextGroupViewModel>(StringComparer.OrdinalIgnoreCase);

        foreach (var binding in Document.Bindings)
        {
            if (string.IsNullOrWhiteSpace(binding.Context) || string.IsNullOrWhiteSpace(binding.Command))
            {
                continue;
            }

            if (!groupsByContext.TryGetValue(binding.Context, out var group))
            {
                group = new HotkeyContextGroupViewModel(binding.Context);
                groupsByContext[binding.Context] = group;
                ContextGroups.Add(group);
                Contexts.Add(binding.Context);
            }

            var row = new HotkeyCommandRowViewModel(binding, OnRowChanged, EditBindingAsync);
            group.Commands.Add(row);
        }

        SelectedContext = "All";
        ApplyCommandFilter();
    }

    private void OnRowChanged(HotkeyCommandRowViewModel row)
    {
        MarkDirty();
    }

    private async Task EditBindingAsync(HotkeyCommandRowViewModel row)
    {
        var activeWindow = GetActiveWindow();
        if (activeWindow is null)
        {
            return;
        }

        var vm = new KeyDialogViewModel(row.Input);
        var dialog = new KeyDialogWindow(vm);
        var result = await dialog.ShowDialog<string?>(activeWindow);

        if (result is not null)
        {
            row.Input = result;
            row.Binding.Input = result;
            MarkDirty();
            ApplyCommandFilter();
        }
    }

    private void ApplyCommandFilter()
    {
        FilteredContextGroups.Clear();
        FilteredBindings.Clear();

        var query = CommandFilterText.Trim();
        var keyQuery = KeyFilterInput?.Trim();

        foreach (var group in ContextGroups)
        {
            var anyMatch = false;

            if (SelectedContext != "All" && !string.IsNullOrEmpty(SelectedContext) && !string.Equals(group.ContextName, SelectedContext, StringComparison.OrdinalIgnoreCase))
            {
                group.IsVisible = false;
                continue;
            }

            foreach (var cmd in group.Commands)
            {
                var cmdMatch = string.IsNullOrEmpty(query) || cmd.Command.Contains(query, StringComparison.OrdinalIgnoreCase);
                var keyMatch = string.IsNullOrEmpty(keyQuery) || cmd.Input.Contains(keyQuery, StringComparison.OrdinalIgnoreCase);

                cmd.IsVisible = cmdMatch && keyMatch;
                if (cmd.IsVisible)
                {
                    anyMatch = true;
                    FilteredBindings.Add(cmd.Binding);
                }
            }

            group.IsVisible = anyMatch;
            if (anyMatch)
            {
                if (!string.IsNullOrEmpty(query) || !string.IsNullOrEmpty(keyQuery))
                {
                    group.IsExpanded = true;
                }

                FilteredContextGroups.Add(group);
            }
        }
    }

    private async Task OnFilterKeyAsync()
    {
        var activeWindow = GetActiveWindow();
        if (activeWindow is null)
        {
            KeyFilterInput = null;
            return;
        }

        var vm = new KeyDialogViewModel(KeyFilterInput);
        var dialog = new KeyDialogWindow(vm);
        var result = await dialog.ShowDialog<string?>(activeWindow);

        KeyFilterInput = string.IsNullOrWhiteSpace(result) ? null : result;
    }

    private async Task OnSetCurrentAsync()
    {
        var cs2Path = Cs2Locator.ResolvedCs2Path;
        if (string.IsNullOrWhiteSpace(cs2Path))
        {
            await DialogService.ShowErrorAsync("CS2 installation path is not set. Please set it in Settings.");
            return;
        }

        var sourcePath = SelectedPreset?.FilePath ?? DocumentPath;
        var keybindingsDir = Cs2Paths.GetKeybindingsPath(cs2Path);
        Directory.CreateDirectory(keybindingsDir);
        var destFile = Path.Combine(keybindingsDir, $"{SelectedEditorStem}_key_bindings.txt");

        try
        {
            if (!string.IsNullOrEmpty(sourcePath) && File.Exists(sourcePath))
            {
                File.Copy(sourcePath, destFile, overwrite: true);
            }
            else
            {
                Document.Save(destFile);
            }
        }
        catch (Exception ex)
        {
            await DialogService.ShowErrorAsync($"Failed to apply keybindings: {ex.Message}");
            return;
        }

        var restart = await DialogService.ConfirmAsync(
            "Confirmation",
            "Would you like to restart the editor? Keybindings will be applied upon restart.");

        if (restart && Launcher is not null)
        {
            await Launcher.RestartAsync();
        }
    }

    private async Task OnNewPresetAsync()
    {
        var primaryDir = HotkeyCatalogService.GetPrimaryPresetDirectory(SelectedEditorStem);
        var dateStr = DateTime.Now.ToString("MM_dd_yyyy");
        var baseName = $"{SelectedEditorStem}_new_keybindings_{dateStr}";
        var path = Path.Combine(primaryDir, $"{baseName}.keybindings");

        var counter = 1;
        while (File.Exists(path))
        {
            path = Path.Combine(primaryDir, $"{baseName}_{counter}.keybindings");
            counter++;
        }

        var defaultDoc = HotkeyCatalogService.CreateDefaultDocument(SelectedEditorStem);
        defaultDoc.Save(path);

        RefreshPresetsList();
        SelectedPreset = Presets.FirstOrDefault(p => string.Equals(p.FilePath, path, StringComparison.OrdinalIgnoreCase));
        OpenPresetFile(path);
    }

    private async Task OnOpenPresetAsync()
    {
        if (SelectedPreset is not null)
        {
            OpenPresetFile(SelectedPreset.FilePath);
            return;
        }

        var path = await DialogService.OpenFileAsync("Open hotkey preset", "*.keybindings;*.txt");
        if (path is not null)
        {
            OpenPresetFile(path);
        }
    }

    private async Task OnSetSaveRestartAsync()
    {
        if (await SaveAsync())
        {
            var cs2Path = Cs2Locator.ResolvedCs2Path;
            if (!string.IsNullOrWhiteSpace(cs2Path) && !string.IsNullOrWhiteSpace(DocumentPath))
            {
                var keybindingsDir = Cs2Paths.GetKeybindingsPath(cs2Path);
                Directory.CreateDirectory(keybindingsDir);
                var destFile = Path.Combine(keybindingsDir, $"{SelectedEditorStem}_key_bindings.txt");
                try
                {
                    File.Copy(DocumentPath, destFile, overwrite: true);
                }
                catch (Exception ex)
                {
                    await DialogService.ShowErrorAsync($"Failed to copy keybindings: {ex.Message}");
                    return;
                }
            }

            if (Launcher is not null)
            {
                await Launcher.RestartAsync();
            }
        }
    }

    private void OnOpenFolder()
    {
        var primaryDir = HotkeyCatalogService.GetPrimaryPresetDirectory(SelectedEditorStem);
        if (Directory.Exists(primaryDir))
        {
            try
            {
                Process.Start(new ProcessStartInfo(primaryDir) { UseShellExecute = true });
            }
            catch
            {
                // Ignore process launch failures
            }
        }
    }

    private void OnToggleRecent()
    {
        // Cycles or opens recent preset if available
        if (Presets.Count > 0)
        {
            SelectedPreset = Presets[0];
            OpenPresetFile(Presets[0].FilePath);
        }
    }

    private void OnToggleFavorites()
    {
        // Filter by twist or first preset if available
        if (string.IsNullOrEmpty(PresetFilterText))
        {
            PresetFilterText = "twist";
        }
        else
        {
            PresetFilterText = string.Empty;
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
        ApplyCommandFilter();
    }

    private async Task OnApplyToCs2Async()
    {
        var cs2Path = Cs2Locator.ResolvedCs2Path;
        if (string.IsNullOrWhiteSpace(cs2Path))
        {
            await DialogService.ShowErrorAsync("CS2 installation not found.");
            return;
        }

        if (!await DialogService.ConfirmCloseAsync([this]))
        {
            return;
        }

        var targetFile = Path.Combine(Cs2Paths.GetKeybindingsPath(cs2Path), $"{SelectedEditorStem}_key_bindings.txt");
        try
        {
            Document.Save(targetFile);
        }
        catch (Exception ex)
        {
            await DialogService.ShowErrorAsync(ex.Message);
        }
    }

    protected override async Task<bool> SaveCoreAsync()
    {
        if (DocumentPath is null)
        {
            var primaryDir = HotkeyCatalogService.GetPrimaryPresetDirectory(SelectedEditorStem);
            var suggested = Path.Combine(primaryDir, $"{SelectedEditorStem}_keybindings.keybindings");
            DocumentPath = await DialogService.SaveFileAsync("Save hotkey preset", suggested);
        }

        if (DocumentPath is null)
        {
            return false;
        }

        Document.Save(DocumentPath);
        Title = Path.GetFileName(DocumentPath);
        RefreshPresetsList();
        return true;
    }

    private void RestoreHistory(string text)
    {
        Document = HotkeyDocument.Parse(text);
        BuildTreeFromDocument();
        ObserveModels(Document.Bindings);
    }

    private static Window? GetActiveWindow()
    {
        var desktop = Application.Current?.ApplicationLifetime as IClassicDesktopStyleApplicationLifetime;
        return desktop?.Windows.FirstOrDefault(w => w.IsActive)
            ?? desktop?.Windows.FirstOrDefault(w => w.IsVisible)
            ?? desktop?.MainWindow;
    }
}

namespace Hammer5Tools.App.Features.GitSync;

using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.GitSync;

public class GitSyncViewModel : DocumentViewModel
{
    private readonly IAddonService AddonService;
    private readonly IGitSyncService GitSyncService;
    private readonly Core.Settings.ISettingsService? SettingsService;

    private string BranchNameValue = "main";
    private string CommitMessageValue = string.Empty;
    private string StatusValue = "Ready";
    private bool IsRepoValue;

    public ObservableCollection<string> ChangedFiles { get; } = [];

    public string BranchName
    {
        get => BranchNameValue;
        set => SetProperty(ref BranchNameValue, value);
    }

    public string CommitMessage
    {
        get => CommitMessageValue;
        set => SetProperty(ref CommitMessageValue, value);
    }

    public string Status
    {
        get => StatusValue;
        set => SetProperty(ref StatusValue, value);
    }

    public bool IsRepo
    {
        get => IsRepoValue;
        set => SetProperty(ref IsRepoValue, value);
    }

    public IRelayCommand RefreshStatusCommand { get; }

    public IRelayCommand PullCommand { get; }

    public IRelayCommand PushCommand { get; }

    public IRelayCommand CommitCommand { get; }

    public GitSyncViewModel(IAddonService addonService, IGitSyncService gitSyncService, Core.Settings.ISettingsService? settingsService = null)
    {
        AddonService = addonService;
        GitSyncService = gitSyncService;
        SettingsService = settingsService;
        Title = "Git Sync (Prototype)";

        RefreshStatusCommand = new AsyncRelayCommand(OnRefreshStatusAsync);
        PullCommand = new AsyncRelayCommand(OnPullAsync);
        PushCommand = new AsyncRelayCommand(OnPushAsync);
        CommitCommand = new AsyncRelayCommand(OnCommitAsync);

        _ = OnRefreshStatusAsync();
    }

    private async Task OnRefreshStatusAsync()
    {
        ChangedFiles.Clear();
        var addon = AddonService.ActiveAddon;
        if (addon is null)
        {
            Status = "No active addon.";
            IsRepo = false;
            return;
        }

        var result = await GitSyncService.GetStatusAsync(addon.ContentPath);
        IsRepo = result.IsGitRepository;
        BranchName = result.Branch;

        foreach (var file in result.ModifiedFiles)
        {
            ChangedFiles.Add($"M  {file}");
        }
        foreach (var file in result.UntrackedFiles)
        {
            ChangedFiles.Add($"?  {file}");
        }

        if (SettingsService?.Settings.Editor.GenerateGitCommitMessages == true && string.IsNullOrWhiteSpace(CommitMessage) && ChangedFiles.Count > 0)
        {
            CommitMessage = $"chore(assets): update {ChangedFiles.Count} addon file(s)";
        }

        Status = IsRepo
            ? $"Git repository detected on branch '{BranchName}'. {ChangedFiles.Count} pending file change(s)."
            : "Active addon directory is not a Git repository.";
    }

    private async Task OnPullAsync()
    {
        var addon = AddonService.ActiveAddon;
        if (addon is null)
        {
            return;
        }

        Status = "Pulling latest changes...";
        var success = await GitSyncService.PullAsync(addon.ContentPath);
        Status = success ? "Successfully pulled changes." : "Pull failed or conflicts detected.";
        await OnRefreshStatusAsync();
    }

    private async Task OnPushAsync()
    {
        var addon = AddonService.ActiveAddon;
        if (addon is null)
        {
            return;
        }

        Status = "Pushing changes to remote...";
        var success = await GitSyncService.PushAsync(addon.ContentPath);
        Status = success ? "Successfully pushed changes." : "Push failed.";
        await OnRefreshStatusAsync();
    }

    private async Task OnCommitAsync()
    {
        var addon = AddonService.ActiveAddon;
        if (addon is null || string.IsNullOrWhiteSpace(CommitMessage))
        {
            Status = "Please enter a commit message.";
            return;
        }

        Status = "Committing changes...";
        var success = await GitSyncService.CommitAsync(addon.ContentPath, CommitMessage);
        Status = success ? "Committed successfully." : "Commit failed.";
        CommitMessage = string.Empty;
        await OnRefreshStatusAsync();
    }
}

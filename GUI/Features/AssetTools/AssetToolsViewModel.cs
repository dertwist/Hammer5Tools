namespace Hammer5Tools.App.Features.AssetTools;

using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.Workshop;

public class AssetToolsViewModel : DocumentViewModel
{
    public override string IconUri => "avares://Hammer5Tools/Assets/Icons/folder_sm.png";

    private readonly IAddonService AddonService;
    private readonly IAssetToolsService AssetToolsService;

    private string OldPathValue = string.Empty;
    private string NewPathValue = string.Empty;
    private string StatusValue = "Ready";

    public string OldPath
    {
        get => OldPathValue;
        set => SetProperty(ref OldPathValue, value);
    }

    public string NewPath
    {
        get => NewPathValue;
        set => SetProperty(ref NewPathValue, value);
    }

    public string Status
    {
        get => StatusValue;
        set => SetProperty(ref StatusValue, value);
    }

    public Explorer.AssetExplorerViewModel Explorer { get; }

    public IRelayCommand MoveAssetCommand { get; }

    public AssetToolsViewModel(IAddonService addonService, IAssetToolsService assetToolsService)
    {
        AddonService = addonService;
        AssetToolsService = assetToolsService;
        Title = "Asset Tools";
        Explorer = new Explorer.AssetExplorerViewModel(addonService, path =>
        {
            if (addonService.ActiveAddon is { } addon)
            {
                OldPath = Path.GetRelativePath(addon.ContentPath, path);
            }
        });

        MoveAssetCommand = new AsyncRelayCommand(OnMoveAssetAsync);
    }

    public override void Dispose()
    {
        Explorer.Dispose();
        base.Dispose();
        GC.SuppressFinalize(this);
    }

    private async Task OnMoveAssetAsync()
    {
        var addon = AddonService.ActiveAddon;
        if (addon is null || string.IsNullOrWhiteSpace(OldPath) || string.IsNullOrWhiteSpace(NewPath))
        {
            Status = "Please provide an active addon and valid asset paths.";
            return;
        }

        Status = "Moving asset and updating references...";
        var count = await AssetToolsService.MoveAssetAndRewriteReferencesAsync(addon.ContentPath, OldPath, NewPath);
        Status = $"Asset moved. Updated {count} reference(s) across addon maps/materials.";
    }
}

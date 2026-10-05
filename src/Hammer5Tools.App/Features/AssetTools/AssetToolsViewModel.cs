namespace Hammer5Tools.App.Features.AssetTools;

using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.Workshop;

public class AssetToolsViewModel : DocumentViewModel
{
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

    public IRelayCommand MoveAssetCommand { get; }

    public AssetToolsViewModel(IAddonService addonService, IAssetToolsService assetToolsService)
    {
        AddonService = addonService;
        AssetToolsService = assetToolsService;
        Title = "Asset Tools";

        MoveAssetCommand = new AsyncRelayCommand(OnMoveAssetAsync);
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

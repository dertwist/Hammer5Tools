namespace Hammer5Tools.App.Features.Shell;

using Hammer5Tools.App.Features.DetailProps;
using Hammer5Tools.App.Features.Hotkeys;
using Hammer5Tools.App.Features.LoadingScreens;
using Hammer5Tools.App.Features.MapBuilder;
using Hammer5Tools.App.Features.SmartProps;
using Hammer5Tools.App.Features.SoundEvents;
using Hammer5Tools.App.ViewModels;

internal static class EditorMenus
{
    internal static void AddDocumentActions(DocumentViewModel? document, List<EditorMenuAction> file,
        List<EditorMenuAction> edit, List<EditorMenuAction> view,
        out List<EditorMenuAction>? elements, out (string Header, List<EditorMenuAction> Items)? editorMenu)
    {
        elements = null;
        editorMenu = null;
        switch (document)
        {
            case SmartPropEditorViewModel smartProp:
                file.Add(new("Save as...", smartProp.SaveAsCommand));
                file.Add(new("Load cargo van", smartProp.LoadCargoVanCommand));
                file.Add(new("Example", smartProp.LoadExampleCommand));
                edit.Add(new("Cut", smartProp.CutCommand));
                edit.Add(new("Copy", smartProp.CopyCommand));
                edit.Add(new("Paste", smartProp.PasteCommand));
                edit.Add(new("Paste with replacement...", smartProp.PasteWithReplacementCommand));
                edit.Add(new("Group selected", smartProp.GroupSelectedCommand));
                view.Add(new("Frame all", smartProp.FrameAllCommand));
                elements =
                [
                    new("Add group", smartProp.AddGroupCommand),
                    new("Add model", smartProp.AddModelCommand),
                    new("Duplicate", smartProp.DuplicateCommand),
                    new("Delete", smartProp.DeleteCommand),
                    new("Move up", smartProp.MoveUpCommand),
                    new("Move down", smartProp.MoveDownCommand),
                ];
                break;
            case MapBuilderViewModel mapBuilder:
                file.Add(new("Add VMAP...", mapBuilder.AddMapCommand));
                file.Add(new("Save build preset", mapBuilder.SavePresetCommand));
                editorMenu = ("Build",
                [
                    new("Start build", mapBuilder.StartBuildCommand),
                    new("Cancel build", mapBuilder.CancelBuildCommand),
                    new("Run map", mapBuilder.RunMapCommand),
                    new("Remove map", mapBuilder.RemoveMapCommand),
                    new("New build preset", mapBuilder.NewPresetCommand),
                ]);
                break;
            case LoadingEditorViewModel loading:
                editorMenu = ("Loading Screens",
                [
                    new("Refresh screenshots", loading.RefreshScreenshotsCommand),
                    new("Take history screenshots", loading.CaptureHistoryShotsCommand),
                    new("Take loading screen screenshots", loading.CaptureScreenshotCommand),
                    new("Set loading images", loading.GenerateLoadingScreenCommand),
                    new("Create animations", loading.ExportAnimationsCommand),
                    new("Refresh cameras", loading.RefreshCamerasCommand),
                    new("Browse map icon...", loading.BrowseIconCommand),
                    new("Apply map icon", loading.ApplyIconCommand),
                ]);
                break;
            case SoundEventEditorViewModel soundEvents:
                editorMenu = ("Sound Events",
                [
                    new("Add event", soundEvents.AddEventCommand),
                    new("Delete event", soundEvents.DeleteEventCommand),
                    new("Add property", soundEvents.AddPropertyCommand),
                    new("Search VPK sounds...", soundEvents.SearchVpkCommand),
                    new("Reload", soundEvents.ReloadCommand),
                ]);
                break;
            case HotkeyEditorViewModel hotkeys:
                editorMenu = ("Hotkeys",
                [
                    new("New preset", hotkeys.NewPresetCommand),
                    new("Open preset...", hotkeys.OpenPresetCommand),
                    new("Apply binding", hotkeys.ApplyBindingCommand),
                    new("Apply to CS2", hotkeys.ApplyToCs2Command),
                    new("Apply and restart CS2", hotkeys.ApplyAndRestartCommand),
                ]);
                break;
            case DetailPropEditorViewModel detailProps:
                editorMenu = ("Detail Props",
                [
                    new("Add type", detailProps.AddTypeCommand),
                    new("Delete type", detailProps.DeleteTypeCommand),
                    new("Add model", detailProps.AddModelCommand),
                    new("Delete model", detailProps.DeleteModelCommand),
                ]);
                break;
        }

    }
}

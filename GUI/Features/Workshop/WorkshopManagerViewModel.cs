namespace Hammer5Tools.App.Features.Workshop;

using Hammer5Tools.App.ViewModels;

public sealed class WorkshopManagerViewModel : DocumentViewModel
{
    private GUI.WorkshopManagerView? view;

    public GUI.WorkshopManagerView View => view ??= new();

    public override string IconUri => "avares://CS2WorkshopManager-GUI/assets/icon.png";

    public WorkshopManagerViewModel()
    {
        Title = "Workshop Manager";
    }
}

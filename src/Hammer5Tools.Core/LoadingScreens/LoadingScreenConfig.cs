namespace Hammer5Tools.Core.LoadingScreens;

public class LoadingScreenConfig
{
    public string AddonName { get; set; } = string.Empty;

    public string MapName { get; set; } = string.Empty;

    public string Title { get; set; } = string.Empty;

    public string Author { get; set; } = string.Empty;

    public string Description { get; set; } = string.Empty;

    public string? SelectedImagePath { get; set; }

    public List<CameraInfo> Cameras { get; set; } = [];
}

namespace Hammer5Tools.Core.Workshop;

public class WorkshopPackConfig
{
    public string AddonName { get; set; } = string.Empty;

    public string Title { get; set; } = string.Empty;

    public string Description { get; set; } = string.Empty;

    public bool ExcludeUnusedContent { get; set; } = true;

    public List<string> Tags { get; } = [];

    public string OutputVpkPath { get; set; } = string.Empty;
}

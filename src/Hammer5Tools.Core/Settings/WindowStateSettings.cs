namespace Hammer5Tools.Core.Settings;

/// <summary>
/// Window geometry and state preferences.
/// </summary>
public class WindowStateSettings
{
    public double? X { get; set; }

    public double? Y { get; set; }

    public double Width { get; set; } = 1280;

    public double Height { get; set; } = 800;

    public bool IsMaximized { get; set; }
}

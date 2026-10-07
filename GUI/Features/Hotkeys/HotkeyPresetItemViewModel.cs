namespace Hammer5Tools.App.Features.Hotkeys;

using CommunityToolkit.Mvvm.ComponentModel;

public class HotkeyPresetItemViewModel : ObservableObject
{
    public string FilePath { get; }

    public string FileName { get; }

    public string DisplayName { get; }

    public long FileSizeBytes { get; }

    public string DisplaySize { get; }

    public DateTime LastModified { get; }

    public HotkeyPresetItemViewModel(string filePath)
    {
        FilePath = filePath;
        FileName = Path.GetFileName(filePath);
        DisplayName = Path.GetFileNameWithoutExtension(filePath);

        try
        {
            var info = new FileInfo(filePath);
            FileSizeBytes = info.Length;
            LastModified = info.LastWriteTime;
            DisplaySize = FormatSize(info.Length);
        }
        catch
        {
            DisplaySize = "0 B";
        }
    }

    private static string FormatSize(long bytes)
    {
        if (bytes < 1024)
        {
            return $"{bytes} B";
        }

        var kib = bytes / 1024.0;
        if (kib < 1024)
        {
            return $"{kib:F2} KiB";
        }

        var mib = kib / 1024.0;
        return $"{mib:F2} MiB";
    }
}

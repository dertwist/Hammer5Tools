namespace Hammer5Tools.App.Features.Explorer;

using System.Collections.ObjectModel;
using System.IO;
using Hammer5Tools.App.ViewModels;

public class FileItemViewModel : ViewModelBase
{
    private bool IsExpandedValue;
    private bool IsSelectedValue;

    public string Name { get; }

    public string FullPath { get; }

    public bool IsDirectory { get; }

    public long FileSizeBytes { get; }

    public string FormattedSize => IsDirectory ? string.Empty : FormatSize(FileSizeBytes);

    public string IconUri { get; }

    public ObservableCollection<FileItemViewModel> Children { get; } = [];

    public bool IsExpanded
    {
        get => IsExpandedValue;
        set => SetProperty(ref IsExpandedValue, value);
    }

    public bool IsSelected
    {
        get => IsSelectedValue;
        set => SetProperty(ref IsSelectedValue, value);
    }

    public FileItemViewModel(string fullPath, bool isDirectory)
    {
        FullPath = fullPath;
        IsDirectory = isDirectory;
        Name = Path.GetFileName(fullPath);

        if (isDirectory)
        {
            IconUri = "avares://Hammer5Tools.App/Assets/Icons/folder_sm.png";
            FileSizeBytes = 0;
        }
        else
        {
            var ext = Path.GetExtension(fullPath).ToLowerInvariant();
            IconUri = ext switch
            {
                ".vmap" => "avares://Hammer5Tools.App/Assets/Icons/map_sm.png",
                ".vmdl" => "avares://Hammer5Tools.App/Assets/Icons/model_sm.png",
                ".vmat" => "avares://Hammer5Tools.App/Assets/Icons/material_sm.png",
                ".vtex" => "avares://Hammer5Tools.App/Assets/Icons/texture_sm.png",
                ".vsndevts" or ".vsnd" or ".wav" or ".mp3" => "avares://Hammer5Tools.App/Assets/Icons/vmix_sm.png",
                ".vdata" or ".vsmart" => "avares://Hammer5Tools.App/Assets/Icons/detailprop_editor.png",
                _ => "avares://Hammer5Tools.App/Assets/Icons/hammer_icon.png"
            };

            try
            {
                var info = new FileInfo(fullPath);
                FileSizeBytes = info.Exists ? info.Length : 0;
            }
            catch
            {
                FileSizeBytes = 0;
            }
        }
    }

    private static string FormatSize(long bytes)
    {
        if (bytes < 1024)
        {
            return $"{bytes} B";
        }

        if (bytes < 1024 * 1024)
        {
            return $"{bytes / 1024.0:F1} KB";
        }

        return $"{bytes / (1024.0 * 1024.0):F1} MB";
    }
}

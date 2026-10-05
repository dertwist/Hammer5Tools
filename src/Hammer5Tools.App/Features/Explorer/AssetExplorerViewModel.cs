namespace Hammer5Tools.App.Features.Explorer;

using System;
using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using System.Linq;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Addons;

public class AssetExplorerViewModel : ViewModelBase
{
    private readonly IAddonService AddonService;
    private readonly Action<string> OnOpenFileAction;
    private string FilterTextValue = string.Empty;

    public ObservableCollection<FileItemViewModel> RootItems { get; } = [];

    public string FilterText
    {
        get => FilterTextValue;
        set
        {
            if (SetProperty(ref FilterTextValue, value))
            {
                ApplyFilter();
            }
        }
    }

    public IRelayCommand RefreshCommand { get; }

    public IRelayCommand CollapseAllCommand { get; }

    public IRelayCommand OpenDirectoryCommand { get; }

    public IRelayCommand<FileItemViewModel> FileActivatedCommand { get; }

    public AssetExplorerViewModel(IAddonService addonService, Action<string> onOpenFileAction)
    {
        AddonService = addonService;
        OnOpenFileAction = onOpenFileAction;

        RefreshCommand = new RelayCommand(Refresh);
        CollapseAllCommand = new RelayCommand(CollapseAll);
        OpenDirectoryCommand = new RelayCommand(OpenCurrentDirectory);
        FileActivatedCommand = new RelayCommand<FileItemViewModel>(OnFileActivated);

        AddonService.ActiveAddonChanged += (_, _) => Refresh();
        Refresh();
    }

    public void Refresh()
    {
        RootItems.Clear();

        var addon = AddonService.ActiveAddon;
        if (addon is null || !Directory.Exists(addon.ContentPath))
        {
            return;
        }

        try
        {
            var contentDir = new DirectoryInfo(addon.ContentPath);
            foreach (var subDir in contentDir.EnumerateDirectories().OrderBy(d => d.Name))
            {
                var dirVm = CreateDirectoryNode(subDir.FullName);
                if (dirVm is not null)
                {
                    RootItems.Add(dirVm);
                }
            }

            foreach (var file in contentDir.EnumerateFiles().OrderBy(f => f.Name))
            {
                RootItems.Add(new FileItemViewModel(file.FullName, false));
            }
        }
        catch
        {
            // Ignore directory enumeration errors
        }
    }

    private static FileItemViewModel? CreateDirectoryNode(string dirPath)
    {
        try
        {
            var dirVm = new FileItemViewModel(dirPath, true);
            var dirInfo = new DirectoryInfo(dirPath);

            foreach (var subDir in dirInfo.EnumerateDirectories().OrderBy(d => d.Name))
            {
                var child = CreateDirectoryNode(subDir.FullName);
                if (child is not null)
                {
                    dirVm.Children.Add(child);
                }
            }

            foreach (var file in dirInfo.EnumerateFiles().OrderBy(f => f.Name))
            {
                dirVm.Children.Add(new FileItemViewModel(file.FullName, false));
            }

            return dirVm;
        }
        catch
        {
            return null;
        }
    }

    private void ApplyFilter()
    {
        // Re-read or filter tree based on FilterText
        Refresh();
        if (string.IsNullOrWhiteSpace(FilterText))
        {
            return;
        }

        // Filter and auto-expand nodes matching filter
        FilterCollection(RootItems, FilterText.Trim().ToLowerInvariant());
    }

    private static bool FilterCollection(ObservableCollection<FileItemViewModel> items, string query)
    {
        var anyMatch = false;
        var toRemove = items.Where(item =>
        {
            var matchSelf = item.Name.Contains(query, StringComparison.OrdinalIgnoreCase);
            var matchChild = false;
            if (item.IsDirectory)
            {
                matchChild = FilterCollection(item.Children, query);
                if (matchChild)
                {
                    item.IsExpanded = true;
                }
            }

            var keep = matchSelf || matchChild;
            if (keep)
            {
                anyMatch = true;
            }
            return !keep;
        }).ToList();

        foreach (var item in toRemove)
        {
            items.Remove(item);
        }

        return anyMatch;
    }

    public void CollapseAll()
    {
        void CollapseNode(FileItemViewModel node)
        {
            node.IsExpanded = false;
            foreach (var child in node.Children)
            {
                CollapseNode(child);
            }
        }

        foreach (var root in RootItems)
        {
            CollapseNode(root);
        }
    }

    private void OpenCurrentDirectory()
    {
        var addon = AddonService.ActiveAddon;
        if (addon is not null && Directory.Exists(addon.ContentPath))
        {
            try
            {
                Process.Start(new ProcessStartInfo { FileName = addon.ContentPath, UseShellExecute = true });
            }
            catch
            {
                // Ignore
            }
        }
    }

    private void OnFileActivated(FileItemViewModel? item)
    {
        if (item is null)
        {
            return;
        }

        if (item.IsDirectory)
        {
            item.IsExpanded = !item.IsExpanded;
            return;
        }

        OnOpenFileAction(item.FullPath);
    }
}

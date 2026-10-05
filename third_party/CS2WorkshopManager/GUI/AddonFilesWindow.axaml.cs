using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using CS2WorkshopManager;

namespace GUI;

/// <summary>A user rule as the rules list shows it.</summary>
public sealed record RuleRow(AddonRules.Rule Rule)
{
    public string Kind => Rule.Exclude ? "Exclude" : "Include";

    public string Pattern => Rule.Pattern;
}

/// <summary>
/// A file or folder under the addon as the tree shows it. A folder's tick is that of the files under it, all, none or some,
/// and a rescan updates the ticks in place so the tree keeps its nodes and what is expanded.
/// </summary>
public sealed class FileNode(string relativePath, bool isFolder) : INotifyPropertyChanged
{
    private bool? packed;
    private long size;
    private bool isExpanded;

    public event PropertyChangedEventHandler? PropertyChanged;

    /// <summary>The path under the addon, forward slashes and no trailing slash.</summary>
    public string RelativePath { get; } = relativePath;

    public string Name { get; } = Path.GetFileName(relativePath);

    public bool IsFolder { get; } = isFolder;

    public string Icon { get; } = isFolder ? SvgIcon.Folder : SvgIcon.ForFile(relativePath);

    /// <summary>A folder's folders first and then its files, the largest first.</summary>
    public List<FileNode> Children { get; } = [];

    /// <summary>What a rule for this node matches: a folder's path ends in a slash so it only matches what is under it.</summary>
    public string Pattern => IsFolder ? RelativePath + "/" : RelativePath;

    public long Size
    {
        get => size;
        set => Set(ref size, value, nameof(Size), nameof(SizeText));
    }

    public string SizeText => AddonContents.FormatSize(Size);

    /// <summary>Whether the upload takes it, or null for a folder it takes only some of.</summary>
    public bool? Packed
    {
        get => packed;
        set => Set(ref packed, value, nameof(Packed));
    }

    public bool IsExpanded
    {
        get => isExpanded;
        set => Set(ref isExpanded, value, nameof(IsExpanded));
    }

    /// <summary>Works out a folder's size and tick from what is under it, all the way down.</summary>
    public void Refresh()
    {
        if (!IsFolder)
        {
            return;
        }

        foreach (var child in Children)
        {
            child.Refresh();
        }

        Size = Children.Sum(child => child.Size);
        Packed = Children.All(child => child.Packed == true) ? true : Children.All(child => child.Packed == false) ? false : null;
    }

    private void Set<T>(ref T field, T value, params string[] names)
    {
        if (EqualityComparer<T>.Default.Equals(field, value))
        {
            return;
        }

        field = value;

        foreach (var name in names)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
        }
    }
}

/// <summary>
/// What an addon uploads: its asset types, every folder and file under it, and the user's own include and exclude rules, which are changed here and saved as they change.
/// </summary>
public partial class AddonFilesWindow : Window
{
    private readonly WorkshopManager manager;

    /// <summary>How many generated rules are listed before the rest are only counted, there being far too many to read.</summary>
    private const int MaxShownAutoRules = 100;

    /// <summary>How tall the user's own rules grow to before they scroll, leaving the rest of the panel to the generated ones.</summary>
    private const double MaxUserRulesHeight = 220;

    private AddonRules rules = new();
    private string? addon;

    /// <summary>Every file under the addon in path order, the leaves of the trees.</summary>
    private List<FileNode> files = [];

    /// <summary>The whole addon as a tree.</summary>
    private List<FileNode> tree = [];

    /// <summary>What the tree shows: the whole addon, or only what the search found.</summary>
    private List<FileNode> shown = [];

    /// <summary>Whether a change is still being saved and scanned, during which what is shown is about to change.</summary>
    private bool changing;

    /// <summary>Whether the map box is being filled from the addon, which is not a pick to generate from.</summary>
    private bool showingMaps;

    public AddonFilesWindow(WorkshopManager manager, string? addon)
    {
        this.manager = manager;

        InitializeComponent();

        try
        {
            var addons = manager.GetAddonNames().Order(StringComparer.OrdinalIgnoreCase).ToList();

            AddonBox.ItemsSource = addons;
            AddonBox.SelectedItem = addon == null ? null : addons.Find(name => name.Equals(addon, StringComparison.OrdinalIgnoreCase));
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            Status.Text = exception.Message;
        }
    }

    // the XAML loader wants a constructor without parameters
    public AddonFilesWindow()
        : this(new WorkshopManager(string.Empty), null)
    {
    }

    private async void OnAddonChanged(object? sender, SelectionChangedEventArgs e)
    {
        await ReloadAsync();
    }

    /// <summary>
    /// Reads the rules and scans the addon again, which is where everything shown comes from.
    /// </summary>
    private async Task ReloadAsync()
    {
        if (AddonBox.SelectedItem is not string name)
        {
            addon = null;
            files = tree = shown = [];
            Contents.Contents = null;
            RulesList.ItemsSource = null;
            FilesTree.ItemsSource = null;
            ShowAutoRules(new AddonRules(), 0);
            return;
        }

        // a rescan after a rule change keeps the last count up until the new one is ready, instead of flashing through "Scanning"
        var switched = addon != name;

        if (switched)
        {
            Status.Text = $"Scanning {name}...";
        }

        addon = name;

        var addonPath = Path.Combine(manager.AddonsRoot, name);
        var gameInfoPath = manager.GameInfoPath;

        try
        {
            rules = manager.LoadRules(name);
            ShowMaps(addonPath, switched ? null : SelectedMap);

            var own = rules;

            // what the addon is packed by, the same way a publish works it out. A map to keep unused content out by is crawled here, and again only once it is rebuilt
            var (packed, all, autoRules) = await Task.Run(() =>
            {
                var unused = own.ExcludeUnused == null ? new AddonRules() : manager.BuildUnusedRules(name, own.ExcludeUnused).Rules;
                var packedFiles = AddonPackager.CollectFiles(addonPath, gameInfoPath, manager.LoadPackingRules(name));
                var packedPaths = packedFiles.Select(file => file.FullName).ToHashSet(StringComparer.OrdinalIgnoreCase);
                var every = AddonPackager.ListFiles(addonPath)
                    .Select(file => (Path: AddonPackager.GetRelativePath(addonPath, file.FullName), file.Length, Packed: packedPaths.Contains(file.FullName)))
                    .OrderBy(entry => entry.Path, StringComparer.OrdinalIgnoreCase)
                    .ToList();

                return (packedFiles, every, unused);
            });

            // the selection moved on while this addon was scanned
            if (addon != name)
            {
                return;
            }

            Contents.Contents = AddonContents.FromFiles(packed);
            RulesList.ItemsSource = rules.Rules.Select(rule => new RuleRow(rule)).ToList();

            // a rule is only made for a file the user's rules pack, so what they take out is exactly the files they name
            var unusedPaths = autoRules.Rules.Select(rule => rule.Pattern).ToHashSet(StringComparer.OrdinalIgnoreCase);
            ShowAutoRules(autoRules, all.Where(entry => unusedPaths.Contains(entry.Path)).Sum(entry => entry.Length));

            // the same files as before only change their ticks and sizes, which the game rewrites as it runs, so the tree keeps its nodes, its scroll and what is expanded
            if (files.Count == all.Count && files.Zip(all).All(pair => pair.First.RelativePath == pair.Second.Path))
            {
                foreach (var (node, entry) in files.Zip(all))
                {
                    node.Size = entry.Length;
                    node.Packed = entry.Packed;
                }

                foreach (var root in tree)
                {
                    root.Refresh();
                }

                if (shown != tree)
                {
                    foreach (var root in shown)
                    {
                        root.Refresh();
                    }
                }
            }
            else
            {
                // files came or went, so the tree is built again, with the folders that were open still open
                var expanded = Folders(tree).Where(folder => folder.IsExpanded).Select(folder => folder.RelativePath).ToHashSet(StringComparer.OrdinalIgnoreCase);

                files = all.Select(entry => new FileNode(entry.Path, false) { Size = entry.Length, Packed = entry.Packed }).ToList();
                tree = BuildTree(files);

                foreach (var folder in Folders(tree))
                {
                    folder.IsExpanded = expanded.Contains(folder.RelativePath);
                }

                ShowFiles();
            }

            Status.Text = $"{packed.Count} of {all.Count} files are packed";
        }
        catch (Exception exception)
        {
            // the rules file is hand editable too, so its parser's own errors are reported like the file system's
            Status.Text = exception.Message;
        }
    }

    /// <summary>
    /// Fills the map box with the addon's compiled maps and turns the whole thing off when the addon has none. What is picked is what
    /// <paramref name="keep"/> asks for, then the map the addon keeps unused content out by, and otherwise the one carrying the addon's name.
    /// </summary>
    /// <param name="keep">The map to stay on, for a rescan of the same addon, or null when the addon has changed under it.</param>
    private void ShowMaps(string addonPath, string? keep)
    {
        var maps = AddonUsage.FindMaps(addonPath);

        var picked = new[] { keep, rules.ExcludeUnused }
            .FirstOrDefault(map => map != null && maps.Contains(map, StringComparer.OrdinalIgnoreCase)) ?? maps.FirstOrDefault();

        showingMaps = true;
        MapBox.ItemsSource = maps;
        MapBox.SelectedItem = picked;
        showingMaps = false;

        MapBox.IsEnabled = maps.Count > 0;
        ExcludeUnused.IsEnabled = maps.Count > 0;
        ExcludeUnused.IsChecked = rules.ExcludeUnused != null;

        if (maps.Count == 0)
        {
            UnusedNotice.Text = "This addon has no compiled map under maps, so there is nothing to tell the content it uses from the content it does not.";
        }
    }

    /// <summary>The map to crawl, as the box has it.</summary>
    private string? SelectedMap => MapBox.SelectedItem as string;

    private async void OnMapChanged(object? sender, SelectionChangedEventArgs e)
    {
        // a different map only matters when unused content is being kept out
        if (!showingMaps && ExcludeUnused.IsChecked == true)
        {
            await GenerateAsync();
        }
    }

    private async void OnExcludeUnusedChanged(object? sender, RoutedEventArgs e)
    {
        await GenerateAsync();
    }

    /// <summary>
    /// Saves the picked map as the one to keep unused content out by, or clears it when the box is unticked, then shows the addon as it now packs.
    /// The crawl that follows reads every resource the map reaches and takes a while, so the box and the map are out of reach until it is done.
    /// </summary>
    private async Task GenerateAsync()
    {
        if (addon == null || changing)
        {
            return;
        }

        var map = ExcludeUnused.IsChecked == true ? SelectedMap : null;

        ExcludeUnused.IsEnabled = false;
        MapBox.IsEnabled = false;
        Status.Text = map == null ? "Taking unused content back in..." : $"Reading {map}...";

        await ChangeRulesAsync(changed => changed.ExcludeUnused = map);
    }

    /// <summary>
    /// Shows the rules made from the map and what they take out of the upload, or nothing at all when the addon does not keep unused content out.
    /// Only the first of them are listed, since a crawl makes a rule per file and there can be thousands.
    /// </summary>
    private void ShowAutoRules(AddonRules autoRules, long takenSize)
    {
        AutoSection.IsVisible = autoRules.Rules.Count > 0;

        // the user's own rules give up room only when there is a generated list to show underneath them
        RulesScroller.MaxHeight = AutoSection.IsVisible ? MaxUserRulesHeight : double.PositiveInfinity;

        if (!AutoSection.IsVisible)
        {
            AutoRulesList.ItemsSource = null;
            return;
        }

        AutoSummary.Text = $"{autoRules.Rules.Count} rules, {AddonContents.FormatSize(takenSize)} kept out";
        AutoRulesList.ItemsSource = autoRules.Rules.Take(MaxShownAutoRules).Select(rule => new RuleRow(rule)).ToList();
        AutoMore.Text = autoRules.Rules.Count > MaxShownAutoRules ? $"{autoRules.Rules.Count - MaxShownAutoRules} more" : string.Empty;
    }

    /// <summary>
    /// The folders and files as a tree with <paramref name="files"/> as its leaves, at every level the folders first and then the files, the largest first.
    /// </summary>
    private static List<FileNode> BuildTree(IEnumerable<FileNode> files)
    {
        var root = new FileNode(string.Empty, true);
        var folders = new Dictionary<string, FileNode>(StringComparer.OrdinalIgnoreCase) { [string.Empty] = root };

        foreach (var file in files)
        {
            Folder(Parent(file.RelativePath)).Children.Add(file);
        }

        root.Refresh();
        Sort(root);

        return root.Children;

        FileNode Folder(string path)
        {
            if (!folders.TryGetValue(path, out var folder))
            {
                folder = new FileNode(path, true);
                folders[path] = folder;
                Folder(Parent(path)).Children.Add(folder);
            }

            return folder;
        }

        static string Parent(string path)
        {
            var slash = path.LastIndexOf('/');

            return slash < 0 ? string.Empty : path[..slash];
        }

        static void Sort(FileNode folder)
        {
            folder.Children.Sort((a, b) =>
            {
                var order = b.IsFolder.CompareTo(a.IsFolder);

                if (order == 0)
                {
                    order = b.Size.CompareTo(a.Size);
                }

                return order == 0 ? string.Compare(a.Name, b.Name, StringComparison.OrdinalIgnoreCase) : order;
            });

            foreach (var child in folder.Children)
            {
                Sort(child);
            }
        }
    }

    /// <summary>Every folder in the tree, at every level.</summary>
    private static IEnumerable<FileNode> Folders(List<FileNode> nodes)
    {
        foreach (var node in nodes.Where(node => node.IsFolder))
        {
            yield return node;

            foreach (var folder in Folders(node.Children))
            {
                yield return folder;
            }
        }
    }

    private void OnSearchChanged(object? sender, TextChangedEventArgs e)
    {
        ShowFiles();
    }

    /// <summary>Shows the whole tree, or with something searched for only the files whose path contains it, in their folders opened up.</summary>
    private void ShowFiles()
    {
        var search = SearchBox.Text?.Trim() ?? string.Empty;

        if (search.Length == 0)
        {
            shown = tree;
        }
        else
        {
            shown = BuildTree(files.Where(file => file.RelativePath.Contains(search, StringComparison.OrdinalIgnoreCase)));
            Expand(shown);
        }

        FilesTree.ItemsSource = shown;

        static void Expand(List<FileNode> nodes)
        {
            foreach (var node in nodes)
            {
                node.IsExpanded = true;
                Expand(node.Children);
            }
        }
    }

    /// <summary>Applies a change to the rules, saves them and scans again, or says why it could not save.</summary>
    private async Task ChangeRulesAsync(Action<AddonRules> change)
    {
        if (addon == null || changing)
        {
            return;
        }

        changing = true;

        try
        {
            change(rules);
            manager.SaveRules(addon, rules);
            await ReloadAsync();
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            Status.Text = exception.Message;
        }
        finally
        {
            changing = false;
        }
    }

    private async void OnRemoveRule(object? sender, RoutedEventArgs e)
    {
        if ((sender as Button)?.DataContext is RuleRow row)
        {
            await ChangeRulesAsync(current => current.Rules.Remove(row.Rule));
        }
    }

    /// <summary>Two quick ticks are two ticks, not the double click that folds a folder.</summary>
    private void OnNodeDoubleTapped(object? sender, TappedEventArgs e)
    {
        e.Handled = true;
    }

    /// <summary>
    /// A tick undoes the user's own rule for that file or folder when there is one. Otherwise unticking keeps it out by its path,
    /// and ticking, which for a folder with only some of its files in brings in the rest, brings it in ahead of whatever else keeps it out.
    /// </summary>
    private async void OnNodeClick(object? sender, RoutedEventArgs e)
    {
        if ((sender as CheckBox)?.DataContext is not FileNode node)
        {
            return;
        }

        var bringIn = node.Packed != true;

        await ChangeRulesAsync(current =>
        {
            // a rule the user made for this very path, in the direction being undone
            var removed = current.Rules.RemoveAll(rule => rule.Exclude == bringIn && rule.Pattern.Equals(node.Pattern, StringComparison.OrdinalIgnoreCase));

            if (removed > 0)
            {
                return;
            }

            // the newest rule goes first, since the first matching rule wins, so it beats whatever else the user has
            current.Rules.Insert(0, new AddonRules.Rule(!bringIn, node.Pattern));
        });
    }
}

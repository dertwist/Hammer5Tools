using System.Collections.ObjectModel;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Media;
using Avalonia.VisualTree;
using CS2WorkshopManager;
using Steamworks;

namespace GUI;

public partial class MainWindow : Window
{
    /// <summary>Thumbnails are decoded at the tile size at the largest zoom and drawn smaller elsewhere.</summary>
    private const int ThumbnailSize = 360;

    /// <summary>A tile in the tiles view including its margins, before the zoom.</summary>
    private const double TileWidth = 264;

    /// <summary>The sizes the tiles can be shown at, as a fraction of their drawn size.</summary>
    private static readonly double[] ZoomLevels = [0.2, 0.4, 0.6, 0.8, 1, 1.25, 1.5, 1.75, 2];

    /// <summary>The zoom the tiles are at, as an index into <see cref="ZoomLevels"/>.</summary>
    private int zoomLevel = 4;

    /// <summary>The width the tiles have to fit in, kept for refitting them when the zoom changes.</summary>
    private double tilesViewportWidth;

    /// <summary>The workshop manager's own wording.</summary>
    private const string DeleteConfirmation = "This will delete the submission from the workshop and users subscribed to it will no longer be able to access it.\n\nThis action cannot be undone!\n\nAre you sure you want to delete the submission?";

    private static readonly HttpClient Http = new();

    /// <summary>How many thumbnails are downloaded at once.</summary>
    private static readonly SemaphoreSlim ThumbnailDownloads = new(6);

    private readonly ObservableCollection<WorkshopItemRow> rows = [];

    /// <summary>The rows the search leaves, which is what both views show.</summary>
    private readonly ObservableCollection<WorkshopItemRow> shown = [];

    /// <summary>The game install, found when the first publish form needs it.</summary>
    private WorkshopManager? manager;

    public MainWindow()
    {
        InitializeComponent();

        PublishedItems.ItemsSource = shown;
        TileItems.ItemsSource = shown;
        Loaded += OnLoaded;

        // before the right click menu opens, the item under the pointer is the selected one, and a double click opens it for re-upload
        PublishedItems.AddHandler(PointerPressedEvent, OnItemPressed, RoutingStrategies.Tunnel);
        TileItems.AddHandler(PointerPressedEvent, OnItemPressed, RoutingStrategies.Tunnel);
        PublishedItems.AddHandler(DoubleTappedEvent, OnItemDoubleTapped, handledEventsToo: true);
        TileItems.AddHandler(DoubleTappedEvent, OnItemDoubleTapped, handledEventsToo: true);

        // Ctrl and the wheel zoom the tiles, seen before the scroll viewer takes the wheel
        Tiles.AddHandler(PointerWheelChangedEvent, OnTilesWheel, RoutingStrategies.Tunnel);
    }

    /// <summary>
    /// A click selects the item under the pointer, even on its selectable text, which would otherwise keep the click for selecting text, and a right click likewise so the menu's actions apply to it.
    /// </summary>
    private void OnItemPressed(object? sender, PointerPressedEventArgs e)
    {
        var properties = e.GetCurrentPoint(this).Properties;

        if (!(properties.IsLeftButtonPressed || properties.IsRightButtonPressed) || e.Source is not Visual source || ItemOf(sender, source) is not { } row)
        {
            return;
        }

        if (sender == PublishedItems)
        {
            PublishedItems.SelectedItem = row;
        }
        else
        {
            TileItems.SelectedItem = row;
        }
    }

    /// <summary>
    /// A double click on an item opens it for re-upload, the click before it having selected it. The list's headers and empty space are left to what they do.
    /// </summary>
    private async void OnItemDoubleTapped(object? sender, TappedEventArgs e)
    {
        if (e.Source is not Visual source || ItemOf(sender, source) is not { } row)
        {
            return;
        }

        e.Handled = true;
        await OpenSubmissionAsync(SubmissionMode.ReUpload, row);
    }

    /// <summary>The item that a visual in the list or in the tiles belongs to, null for a visual outside the items, like a column header.</summary>
    private WorkshopItemRow? ItemOf(object? sender, Visual source)
    {
        var container = sender == PublishedItems ? source.FindAncestorOfType<DataGridRow>() : (Control?)source.FindAncestorOfType<ListBoxItem>();

        return container?.DataContext as WorkshopItemRow;
    }

    private void OnTilesViewportSizeChanged(object? sender, SizeChangedEventArgs e)
    {
        tilesViewportWidth = e.NewSize.Width;
        SizeTiles();
    }

    /// <summary>
    /// Sizes the tiles to the whole columns that fit the viewport at the zoom, so their centering splits the leftover width evenly.
    /// </summary>
    private void SizeTiles()
    {
        var columns = Math.Max(1, (int)((tilesViewportWidth / ZoomLevels[zoomLevel] - TileItems.Margin.Left - TileItems.Margin.Right) / TileWidth));

        TileItems.Width = columns * TileWidth;
    }

    /// <summary>Ctrl and the wheel move the tiles' zoom a level, scaling the tiles whole and refitting the columns.</summary>
    private void OnTilesWheel(object? sender, PointerWheelEventArgs e)
    {
        if (!e.KeyModifiers.HasFlag(KeyModifiers.Control))
        {
            return;
        }

        e.Handled = true;
        zoomLevel = Math.Clamp(zoomLevel + Math.Sign(e.Delta.Y), 0, ZoomLevels.Length - 1);

        var zoom = ZoomLevels[zoomLevel];

        TileZoom.LayoutTransform = new ScaleTransform(zoom, zoom);
        SizeTiles();
    }

    private async void OnSettings(object? sender, RoutedEventArgs e)
    {
        await new SettingsWindow().ShowDialog(this);
    }

    private void OnViewToggle(object? sender, RoutedEventArgs e)
    {
        var tiles = sender == TilesToggle;

        ListToggle.IsChecked = !tiles;
        TilesToggle.IsChecked = tiles;
        PublishedItems.IsVisible = !tiles;
        Tiles.IsVisible = tiles;
    }

    private async void OnLoaded(object? sender, RoutedEventArgs e)
    {
        await WarnOfNewerSettingsAsync();
        await LoadItemsAsync();
    }

    /// <summary>Says so when the settings were saved by a newer app than this, since it may not know all that is in them.</summary>
    private async Task WarnOfNewerSettingsAsync()
    {
        AppSettings settings;

        try
        {
            settings = AppSettings.Load();
        }
        catch (Exception)
        {
            // a settings file that can not be read is reported in the settings window, where it can be dealt with
            return;
        }

        if (settings.SavedByNewerApp)
        {
            await MessageDialog.ShowAsync(this, MessageKind.Warning, "Newer Settings", $"The settings were saved by version {settings.SavedBy} of the app, and this is version {AppSettings.AppVersion}.\n\nWhat that version added is kept as it is, but this one can not use it.");
        }
    }

    private async void OnRefresh(object? sender, RoutedEventArgs e)
    {
        await LoadItemsAsync();
    }

    private async void OnNew(object? sender, RoutedEventArgs e)
    {
        await OpenSubmissionAsync(SubmissionMode.New, null);
    }

    private async void OnReUpload(object? sender, RoutedEventArgs e)
    {
        if (SelectedRow("re-upload") is { } row)
        {
            await OpenSubmissionAsync(SubmissionMode.ReUpload, row);
        }
    }

    private async void OnEdit(object? sender, RoutedEventArgs e)
    {
        if (SelectedRow("edit") is { } row)
        {
            await OpenSubmissionAsync(SubmissionMode.Edit, row);
        }
    }

    /// <summary>
    /// Swaps the item list for the publish form until that is done, then reloads the list when something was published.
    /// </summary>
    private async Task OpenSubmissionAsync(SubmissionMode mode, WorkshopItemRow? row)
    {
        if (await FindGameAsync() is not { } game)
        {
            return;
        }

        Main.IsVisible = false;
        Submission.IsVisible = true;

        SubmissionView.PublishedSubmission? published;

        try
        {
            published = await Submission.ShowAsync(mode, game, row, mode == SubmissionMode.Edit ? null : DefaultAddon(row));
        }
        finally
        {
            Submission.IsVisible = false;
            Main.IsVisible = true;
        }

        if (published != null)
        {
            // the workshop manager opens the published item's page, here in Steam
            await Launcher.LaunchUriAsync(published.Result.SteamUrl);
            await LoadItemsAsync();

            if (published.Result.NeedsWorkshopAgreement)
            {
                await MessageDialog.ShowAsync(this, MessageKind.Warning, "Published", $"Published \"{published.Title}\" ({published.Result.PublishedFileId}), but the Steam Workshop legal agreement must be accepted before it becomes visible.");
            }
            else
            {
                await MessageDialog.ShowAsync(this, MessageKind.Info, "Published", $"Published \"{published.Title}\" ({published.Result.PublishedFileId})");
            }
        }
    }

    /// <summary>The game install, found once, or null after telling the user it is not there.</summary>
    private async Task<WorkshopManager?> FindGameAsync()
    {
        try
        {
            return manager ??= WorkshopManager.FromSteamInstall();
        }
        catch (DirectoryNotFoundException exception)
        {
            await MessageDialog.ShowAsync(this, MessageKind.Warning, "Game Not Found", exception.Message);
            return null;
        }
    }

    /// <summary>The files and rules of any addon, starting from the selected item's.</summary>
    private async void OnFiles(object? sender, RoutedEventArgs e)
    {
        if (await FindGameAsync() is { } game)
        {
            var selected = (Tiles.IsVisible ? TileItems.SelectedItem : PublishedItems.SelectedItem) as WorkshopItemRow;

            await new AddonFilesWindow(game, DefaultAddon(selected)).ShowDialog(this);
        }
    }

    /// <summary>
    /// The addon to start from, like the workshop manager the one the tools have open. Without the tools it is the one <paramref name="row"/>'s item was last published from, or the last updated item's when there is no row.
    /// </summary>
    private string? DefaultAddon(WorkshopItemRow? row)
    {
        var item = row ?? rows.MaxBy(candidate => candidate.Item.TimeUpdated);

        return WorkshopManager.GetRunningToolsAddon() ?? (item == null ? null : WorkshopManager.GetPublishedSourceFolder(item.Item.PublishedFileId));
    }

    private async void OnView(object? sender, RoutedEventArgs e)
    {
        if (SelectedRow("view") is not { } row)
        {
            return;
        }

        if (!await Launcher.LaunchUriAsync(row.Item.SteamUrl))
        {
            await MessageDialog.ShowAsync(this, MessageKind.Warning, "View", $"Could not open {row.Item.Title} in Steam.");
        }
    }

    private async void OnDelete(object? sender, RoutedEventArgs e)
    {
        if (SelectedRow("delete") is not { } row)
        {
            return;
        }

        if (!await MessageDialog.AskAsync(this, MessageKind.Danger, "Delete Submission", DeleteConfirmation, "Delete"))
        {
            return;
        }

        DeleteButton.IsEnabled = false;

        try
        {
            await WorkshopManager.DeleteItemAsync(row.PublishedFileId);

            rows.Remove(row);
            shown.Remove(row);
            Status.Text = $"Deleted {row.Title}, {rows.Count} published maps";
        }
        catch (SteamUnavailableException exception)
        {
            await MessageDialog.ShowAsync(this, MessageKind.Warning, "Steam Not Running", exception.Message);
        }
        catch (Exception exception) when (exception is InvalidOperationException or IOException)
        {
            await MessageDialog.ShowAsync(this, MessageKind.Warning, "Delete Submission", exception.Message);
        }
        finally
        {
            DeleteButton.IsEnabled = true;
        }
    }

    /// <summary>
    /// The map selected in whichever view is showing, or null after telling the user to select one for the action.
    /// </summary>
    private WorkshopItemRow? SelectedRow(string action)
    {
        var selected = Tiles.IsVisible ? TileItems.SelectedItem : PublishedItems.SelectedItem;

        if (selected is WorkshopItemRow row)
        {
            return row;
        }

        _ = MessageDialog.ShowAsync(this, MessageKind.Warning, "No Map Selected", $"Select a map to {action}.");
        return null;
    }

    /// <summary>Whether the search box lets a row through: its title, tags, description or workshop id contain the text, or there is no text.</summary>
    private bool Matches(WorkshopItemRow row)
    {
        var search = SearchBox.Text?.Trim() ?? string.Empty;

        return search.Length == 0
            || row.Title.Contains(search, StringComparison.OrdinalIgnoreCase)
            || row.Tags.Contains(search, StringComparison.OrdinalIgnoreCase)
            || row.Summary.Contains(search, StringComparison.OrdinalIgnoreCase)
            || row.PublishedFileId.ToString(CultureInfo.InvariantCulture).Contains(search, StringComparison.Ordinal);
    }

    private void OnSearchChanged(object? sender, TextChangedEventArgs e)
    {
        shown.Clear();

        foreach (var row in rows.Where(Matches))
        {
            shown.Add(row);
        }

        ShowCount();
    }

    /// <summary>How many items there are, and how many the search leaves when it leaves fewer.</summary>
    private void ShowCount()
    {
        Status.Text = shown.Count == rows.Count ? $"{rows.Count} published maps" : $"{shown.Count} of {rows.Count} published maps";
    }

    /// <summary>
    /// Replaces the list with the account's published items as Steam returns them.
    /// </summary>
    private async Task LoadItemsAsync()
    {
        // a refresh while a load is still streaming in would add to a list that was just cleared
        RefreshButton.IsEnabled = false;
        rows.Clear();
        shown.Clear();

        var thumbnails = new List<Task>();

        try
        {
            await foreach (var item in WorkshopManager.GetPublishedItemsAsync())
            {
                var row = new WorkshopItemRow(item);

                rows.Add(row);

                if (Matches(row))
                {
                    shown.Add(row);
                }

                ShowCount();

                thumbnails.Add(LoadThumbnailAsync(row));
            }
        }
        catch (SteamUnavailableException exception)
        {
            // the empty list says why until a refresh gets through
            Status.Text = "Steam is not running, start it and refresh";
            await MessageDialog.ShowAsync(this, MessageKind.Warning, "Steam Not Running", exception.Message);
        }
        catch (Exception exception) when (exception is InvalidOperationException or IOException)
        {
            await MessageDialog.ShowAsync(this, MessageKind.Warning, "Workshop", exception.Message);
        }
        finally
        {
            RefreshButton.IsEnabled = true;
        }

        await Task.WhenAll(thumbnails);
    }

    private static async Task LoadThumbnailAsync(WorkshopItemRow row)
    {
        if (row.Item.PreviewUrl == null)
        {
            return;
        }

        await ThumbnailDownloads.WaitAsync();

        try
        {
            var preview = await Http.GetByteArrayAsync(row.Item.PreviewUrl);

            row.Preview = preview;
            row.Thumbnail = PreviewImage.Decode(preview, ThumbnailSize);
        }
        catch (Exception)
        {
            // no thumbnail is shown for items whose preview can not be fetched or decoded, whatever the decoder throws
        }
        finally
        {
            ThumbnailDownloads.Release();
        }
    }
}

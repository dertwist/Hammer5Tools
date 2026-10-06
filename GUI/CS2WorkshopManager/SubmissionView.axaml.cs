using System.Collections.ObjectModel;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Media;
using Avalonia.Platform.Storage;
using CS2WorkshopManager;
using SkiaSharp;
using Steamworks;

namespace GUI;

public enum SubmissionMode
{
    /// <summary>Upload an addon as a new workshop item.</summary>
    New,

    /// <summary>Upload an addon over an existing workshop item.</summary>
    ReUpload,

    /// <summary>Change an existing workshop item's info without uploading.</summary>
    Edit,
}

/// <summary>
/// One entry of the gallery as the form shows it: one the item has, or a screenshot or video added here that goes up with the submission.
/// </summary>
public sealed class GalleryEntry : INotifyPropertyChanged
{
    private object? thumbnail;

    public event PropertyChangedEventHandler? PropertyChanged;

    /// <summary>Its index among the item's previews, or null when it was added here.</summary>
    public int? Index { get; init; }

    /// <summary>What it is, shown where there is no picture of it.</summary>
    public string Kind { get; init; } = string.Empty;

    public string Caption { get; init; } = string.Empty;

    /// <summary>The picture to upload, for a screenshot added here.</summary>
    public string? Path { get; init; }

    /// <summary>The video to add, for a video added here.</summary>
    public string? VideoId { get; init; }

    /// <summary>Whether it is a YouTube video, the item's or added here, which the tile marks with a play badge.</summary>
    public bool IsVideo { get; init; }

    public object? Thumbnail
    {
        get => thumbnail;
        set
        {
            thumbnail = value;
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(Thumbnail)));
        }
    }
}

/// <summary>
/// The workshop manager's publish form for a new submission, a re-upload or an info edit, shown in place of the item list.
/// </summary>
public partial class SubmissionView : UserControl
{
    /// <summary>Fetches gallery pictures, the item's own and YouTube's thumbnails of its videos.</summary>
    private static readonly HttpClient Http = new();

    /// <summary>The workshop manager refuses descriptions and update notes of this many characters or more.</summary>
    private const int MaxTextLength = 8000;

    /// <summary>The visibilities as the dropdown lists them, with the workshop manager's wording.</summary>
    private static readonly VisibilityChoice[] VisibilityChoices =
    [
        new(WorkshopVisibility.Public, "Public"),
        new(WorkshopVisibility.FriendsOnly, "Friends Only"),
        new(WorkshopVisibility.Private, "Private"),
        new(WorkshopVisibility.Unlisted, "Unlisted"),
    ];

    private readonly List<CheckBox> gameModeBoxes = [];

    private SubmissionMode mode;
    private WorkshopManager? manager;
    private WorkshopItem? item;

    /// <summary>What the chosen addon folder holds, null while it is being scanned or when there is none.</summary>
    private AddonContents? contents;

    /// <summary>The image picked for the preview, null keeps whatever the item has.</summary>
    private string? thumbnailPath;

    /// <summary>Whether the slot holds the drawn default thumbnail, which follows the addon until a picture is picked or the slot cleared.</summary>
    private bool defaultThumbnail;

    /// <summary>Which drawing of the default thumbnail is the latest asked for, so an earlier one still under way does not land after it.</summary>
    private int defaultThumbnailRun;

    /// <summary>The gallery as shown: the item's entries that were not removed, and the ones added here, in the order they are to have.</summary>
    private readonly ObservableCollection<GalleryEntry> gallery = [];

    /// <summary>The gallery entry being held, while it is dragged into a new place, and where in its tile the pointer took hold.</summary>
    private GalleryEntry? draggedEntry;
    private Point grabOffset;

    private TaskCompletionSource<PublishedSubmission?>? finished;

    public SubmissionView()
    {
        InitializeComponent();

        VisibilityBox.ItemsSource = VisibilityChoices;

        foreach (var tag in WorkshopManager.GameModeTags)
        {
            var box = new CheckBox { Content = tag == "Armsrace" ? "Arms Race" : tag, Tag = tag };
            box.IsCheckedChanged += OnGameModeChanged;

            gameModeBoxes.Add(box);
            GameModesList.Children.Add(box);
        }

        PreviewDrop.AddHandler(DragDrop.DragOverEvent, OnDragOver);
        PreviewDrop.AddHandler(DragDrop.DropEvent, OnDrop);

        Gallery.ItemsSource = gallery;
        gallery.CollectionChanged += (_, _) => GalleryHint.IsVisible = gallery.Count == 0;

        // mouse 4 goes back wherever it is pressed in the view, seen before any control takes the press
        AddHandler(PointerPressedEvent, OnViewPressed, RoutingStrategies.Tunnel);
    }

    /// <summary>
    /// Fills the form for a new submission or for <paramref name="row"/>'s item, with <paramref name="addon"/> chosen, and waits until it is submitted or cancelled.
    /// </summary>
    /// <returns>What was published, or null when the form was cancelled.</returns>
    public Task<PublishedSubmission?> ShowAsync(SubmissionMode mode, WorkshopManager manager, WorkshopItemRow? row, string? addon)
    {
        this.mode = mode;
        this.manager = manager;
        item = row?.Item;
        thumbnailPath = null;
        PreviewPath.IsVisible = false;

        Heading.Text = mode switch
        {
            SubmissionMode.ReUpload => $"Re-Upload of \"{item!.Title}\" ({item.PublishedFileId})",
            SubmissionMode.Edit => $"Edit Info of \"{item!.Title}\" ({item.PublishedFileId})",
            _ => "New Submission",
        };

        var uploads = mode != SubmissionMode.Edit;

        ChangeNoteLabel.IsVisible = ChangeNoteBox.IsVisible = mode == SubmissionMode.ReUpload;
        AddonLabel.IsVisible = AddonPanel.IsVisible = uploads;

        ChangeNoteBox.Text = string.Empty;
        TitleBox.Text = item?.Title ?? string.Empty;
        DescriptionBox.Text = item?.Description ?? string.Empty;
        // an item that has a description opens on how it reads, a new one on where to type it
        ShowDescription(preview: !string.IsNullOrWhiteSpace(item?.Description));

        VisibilityBox.SelectedItem = Array.Find(VisibilityChoices, choice => choice.Value == (item?.Visibility ?? WorkshopVisibility.Private));
        Status.Text = string.Empty;

        foreach (var box in gameModeBoxes)
        {
            box.IsChecked = item != null && item.Tags.Contains((string)box.Tag!, StringComparer.OrdinalIgnoreCase);
        }

        SetPreview(row?.Preview == null ? null : PreviewImage.Decode(row.Preview));
        defaultThumbnail = mode == SubmissionMode.New;

        gallery.Clear();

        if (item != null)
        {
            // videos first, the way the workshop page shows the gallery, then the rest in their order
            foreach (var index in Enumerable.Range(0, item.Previews.Count).OrderBy(index => item.Previews[index].Kind != WorkshopPreviewKind.YouTubeVideo))
            {
                var preview = item.Previews[index];
                var entry = new GalleryEntry
                {
                    Index = index,
                    Kind = preview.Kind switch
                    {
                        WorkshopPreviewKind.YouTubeVideo => "YouTube video",
                        WorkshopPreviewKind.Image => "Screenshot",
                        _ => "Preview",
                    },
                    Caption = preview.Kind == WorkshopPreviewKind.Image && preview.FileName.Length > 0 ? preview.FileName : preview.Value,
                    IsVideo = preview.Kind == WorkshopPreviewKind.YouTubeVideo,
                };

                gallery.Add(entry);
                _ = LoadGalleryImageAsync(entry, preview.ImageUrl);
            }
        }

        if (uploads)
        {
            try
            {
                var addons = manager.GetAddonNames().Order(StringComparer.OrdinalIgnoreCase).ToList();

                AddonBox.ItemsSource = addons;
                AddonBox.SelectedItem = addon == null ? null : addons.Find(name => name.Equals(addon, StringComparison.OrdinalIgnoreCase));

                // with an addon chosen its change draws the thumbnail, without one it is drawn here over the gradient
                if (defaultThumbnail && AddonBox.SelectedItem == null)
                {
                    _ = ShowDefaultThumbnailAsync();
                }
            }
            catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
            {
                _ = MessageDialog.ShowAsync(OwnerWindow, MessageKind.Warning, "Addon Folders", exception.Message);
            }
        }

        TitleBox.Focus();

        finished = new TaskCompletionSource<PublishedSubmission?>();
        return finished.Task;
    }

    private void OnDescriptionViewToggle(object? sender, RoutedEventArgs e)
    {
        ShowDescription(sender == PreviewToggle);
    }

    /// <summary>Shows the description as typed, or laid out the way the workshop page would show it.</summary>
    private void ShowDescription(bool preview)
    {
        EditToggle.IsChecked = !preview;
        PreviewToggle.IsChecked = preview;
        FormatButtons.IsEnabled = !preview;
        DescriptionBox.IsVisible = !preview;
        DescriptionPreview.IsVisible = preview;

        if (preview)
        {
            DescriptionRendered.Text = DescriptionBox.Text;
        }
    }

    /// <summary>
    /// Wraps the selected description text in the button's Steam formatting tag, or opens a tag at the caret to type into.
    /// </summary>
    private void OnFormat(object? sender, RoutedEventArgs e)
    {
        var tag = (string)((Button)sender!).Tag!;
        var selected = DescriptionBox.SelectedText;
        var from = Math.Min(DescriptionBox.SelectionStart, DescriptionBox.SelectionEnd);

        var (open, close) = tag switch
        {
            "url" => ("[url=https://]", "[/url]"),
            "list" => ("[list]\n[*]", "\n[/list]"),
            _ => ($"[{tag}]", $"[/{tag}]"),
        };

        DescriptionBox.SelectedText = open + selected + close;

        if (tag == "url")
        {
            // the address placeholder is selected so it is typed over
            DescriptionBox.SelectionStart = from + "[url=".Length;
            DescriptionBox.SelectionEnd = from + "[url=https://".Length;
        }
        else
        {
            // the caret lands inside empty tags, and after tags wrapped around a selection
            var caret = selected.Length == 0 ? from + open.Length : from + open.Length + selected.Length + close.Length;

            DescriptionBox.SelectionStart = DescriptionBox.SelectionEnd = caret;
        }

        DescriptionBox.Focus();
    }

    private void OnGameModeChanged(object? sender, RoutedEventArgs e)
    {
        var picked = gameModeBoxes.Where(box => box.IsChecked == true).Select(box => box.Content).ToList();

        GameModesButton.Content = picked.Count == 0 ? "None" : string.Join(", ", picked);
    }

    private async void OnAddonChanged(object? sender, SelectionChangedEventArgs e)
    {
        if (defaultThumbnail)
        {
            _ = ShowDefaultThumbnailAsync();
        }

        await ScanAddonAsync();
    }

    /// <summary>Opens the addon's files and rules, and scans again afterwards since they may have changed.</summary>
    private async void OnFiles(object? sender, RoutedEventArgs e)
    {
        if (manager == null)
        {
            return;
        }

        await new AddonFilesWindow(manager, AddonBox.SelectedItem as string).ShowDialog(OwnerWindow);
        await ScanAddonAsync();
    }

    /// <summary>Scans what the chosen addon would upload, with the user's rules, and shows it in the graph.</summary>
    private async Task ScanAddonAsync()
    {
        contents = null;
        Contents.Contents = null;

        if (AddonBox.SelectedItem is not string addon || manager == null)
        {
            return;
        }

        Status.Text = $"Scanning {addon}...";

        var addonPath = Path.Combine(manager.AddonsRoot, addon);
        var gameInfoPath = manager.GameInfoPath;

        try
        {
            // off the window's thread, an addon that keeps unused content out having its map crawled to work out its rules
            var scanned = await Task.Run(() => AddonPackager.GetContents(addonPath, gameInfoPath, manager.LoadPackingRules(addon)));

            // the selection moved on while this folder was scanned
            if (!Equals(AddonBox.SelectedItem, addon))
            {
                return;
            }

            contents = scanned;
            Contents.Contents = scanned;
            Status.Text = string.Empty;
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            Status.Text = string.Empty;
            await MessageDialog.ShowAsync(OwnerWindow, MessageKind.Warning, "Addon Folder", exception.Message);
        }
    }

    /// <summary>The window the form sits in, which owns its dialogs.</summary>
    private Window OwnerWindow => (Window)TopLevel.GetTopLevel(this)!;

    private void SetPreview(object? source)
    {
        Preview.Source = source;
        PreviewHint.IsVisible = source == null;
    }

    /// <summary>
    /// Puts the drawn default thumbnail in the slot, as a picked file would go: over a look at the chosen addon's map when it has one with a cubemap,
    /// otherwise over the gradient. Leaves the slot as it is when the drawing can not be written.
    /// </summary>
    private async Task ShowDefaultThumbnailAsync()
    {
        var run = ++defaultThumbnailRun;
        var addon = AddonBox.SelectedItem as string;
        var manager = this.manager;
        SKBitmap? map = null;

        try
        {
            if (manager != null && addon != null)
            {
                // the map is read and drawn off the window's thread, and dropped for the gradient when it can not be
                map = await Task.Run(() =>
                {
                    try
                    {
                        // the addon's maps in order, until one has a view that is not obviously bad
                        foreach (var mapPath in MapCubemap.FindMaps(manager, addon))
                        {
                            try
                            {
                                if (MapCubemap.View(mapPath, DefaultThumbnail.Width, DefaultThumbnail.Height) is SKBitmap view)
                                {
                                    return view;
                                }
                            }
                            catch (Exception)
                            {
                                // a map that can not be read is passed over for the next
                            }
                        }

                        return null;
                    }
                    catch (Exception)
                    {
                        return null;
                    }
                });
            }

            // the addon moved on, or a picture was picked, while the map was read
            if (run != defaultThumbnailRun || !defaultThumbnail)
            {
                return;
            }

            var path = DefaultThumbnail.Render(map);

            thumbnailPath = path;
            PreviewPath.Text = path;
            PreviewPath.IsVisible = true;
            SetPreview(PreviewImage.Decode(await File.ReadAllBytesAsync(path)));
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            Status.Text = exception.Message;
        }
        finally
        {
            map?.Dispose();
        }
    }

    private void OnClearPreview(object? sender, RoutedEventArgs e)
    {
        defaultThumbnail = false;
        thumbnailPath = null;
        SetPreview(null);
        PreviewPath.IsVisible = false;
    }

    private async void OnBrowse(object? sender, RoutedEventArgs e)
    {
        var files = await TopLevel.GetTopLevel(this)!.StorageProvider.OpenFilePickerAsync(new FilePickerOpenOptions
        {
            Title = "Preview Image",
            AllowMultiple = false,
            FileTypeFilter = [FilePickerFileTypes.ImageAll],
        });

        if (files.Count > 0 && files[0].TryGetLocalPath() is string path)
        {
            await PickThumbnailAsync(path);
        }
    }

    private static void OnDragOver(object? sender, DragEventArgs e)
    {
        e.DragEffects = e.DataTransfer.Contains(DataFormat.File) ? DragDropEffects.Copy : DragDropEffects.None;
    }

    private async void OnDrop(object? sender, DragEventArgs e)
    {
        if (e.DataTransfer.TryGetFile()?.TryGetLocalPath() is string path)
        {
            await PickThumbnailAsync(path);
        }
    }

    private async Task PickThumbnailAsync(string path)
    {
        try
        {
            // the check the upload makes, which decodes the whole image, or walks a gif since those are uploaded unchanged
            await Task.Run(() => WorkshopManager.ValidateThumbnailImage(path));

            var file = await File.ReadAllBytesAsync(path);

            defaultThumbnail = false;
            thumbnailPath = path;
            PreviewPath.Text = path;
            PreviewPath.IsVisible = true;

            try
            {
                SetPreview(PreviewImage.Decode(file));
            }
            catch (Exception)
            {
                // the upload can still convert formats the window can not show, whatever the decoder throws
                SetPreview(null);
                await MessageDialog.ShowAsync(OwnerWindow, MessageKind.Info, "Preview Image", "The image will be uploaded, but can not be shown here.");
            }
        }
        catch (Exception exception) when (exception is InvalidDataException or IOException or UnauthorizedAccessException)
        {
            await MessageDialog.ShowAsync(OwnerWindow, MessageKind.Warning, "Preview Image", exception.Message);
        }
    }

    /// <summary>Puts a picture on a gallery entry once it arrives, or leaves the entry's kind showing when it does not.</summary>
    private static async Task LoadGalleryImageAsync(GalleryEntry entry, Uri? url)
    {
        if (url == null)
        {
            return;
        }

        try
        {
            entry.Thumbnail = PreviewImage.Decode(await Http.GetByteArrayAsync(url), 320);
        }
        catch (Exception)
        {
            // the entry's kind stays in place of the picture, whatever the fetch or the decoder throws
        }
    }

    private async void OnAddScreenshots(object? sender, RoutedEventArgs e)
    {
        var files = await TopLevel.GetTopLevel(this)!.StorageProvider.OpenFilePickerAsync(new FilePickerOpenOptions
        {
            Title = "Gallery Screenshots",
            AllowMultiple = true,
            FileTypeFilter = [FilePickerFileTypes.ImageAll],
        });

        foreach (var file in files)
        {
            if (file.TryGetLocalPath() is not string path)
            {
                continue;
            }

            try
            {
                // the check the upload makes, so a picture Steam would refuse is refused here
                WorkshopManager.ValidateScreenshot(path);

                var entry = new GalleryEntry { Kind = "Screenshot", Caption = Path.GetFileName(path), Path = path };

                try
                {
                    entry.Thumbnail = PreviewImage.Decode(await File.ReadAllBytesAsync(path), 320);
                }
                catch (Exception)
                {
                    // the upload takes formats the window can not show, whatever the decoder throws
                }

                gallery.Add(entry);
            }
            catch (Exception exception) when (exception is InvalidDataException or IOException or UnauthorizedAccessException)
            {
                await MessageDialog.ShowAsync(OwnerWindow, MessageKind.Warning, "Gallery Screenshot", exception.Message);
            }
        }
    }

    private async void OnAddVideo(object? sender, RoutedEventArgs e)
    {
        var text = await MessageDialog.AskTextAsync(OwnerWindow, MessageKind.Info, "Add Video", "Enter the YouTube link or video ID of the video to add to the gallery.", "Add", "https://www.youtube.com/watch?v=...");

        if (text == null)
        {
            return;
        }

        if (WorkshopManager.ParseYouTubeVideoId(text) is not string videoId)
        {
            await MessageDialog.ShowAsync(OwnerWindow, MessageKind.Warning, "Add Video", "That is not a YouTube link or an 11 character video ID.");
            return;
        }

        var entry = new GalleryEntry { Kind = "YouTube video", Caption = videoId, VideoId = videoId, IsVideo = true };

        // after the other videos, ahead of every picture
        gallery.Insert(gallery.Count(existing => existing.IsVideo), entry);

        await LoadGalleryImageAsync(entry, new Uri($"https://img.youtube.com/vi/{videoId}/hqdefault.jpg"));
    }

    /// <summary>Takes hold of a tile. The gallery keeps the pointer rather than the tile, since a reshuffle can replace the tile's control under it.</summary>
    private void OnTilePressed(object? sender, PointerPressedEventArgs e)
    {
        if (sender is not Border tile || tile.DataContext is not GalleryEntry { IsVideo: false } entry || !e.GetCurrentPoint(tile).Properties.IsLeftButtonPressed || Gallery.ContainerFromItem(entry) is not Control container)
        {
            return;
        }

        draggedEntry = entry;
        grabOffset = e.GetPosition(container);
        Gallery.Cursor = new Cursor(StandardCursorType.DragMove);
        e.Pointer.Capture(Gallery);
        Lift(container, e.GetPosition(Gallery.ItemsPanelRoot!));
    }

    /// <summary>
    /// The held tile follows the pointer, and takes the place of whichever other tile the pointer is over, the rest making room as the order changes under it.
    /// </summary>
    private void OnGalleryPointerMoved(object? sender, PointerEventArgs e)
    {
        if (draggedEntry == null || Gallery.ItemsPanelRoot is not Panel panel)
        {
            return;
        }

        var point = e.GetPosition(panel);

        foreach (var container in Gallery.GetRealizedContainers())
        {
            if (container.DataContext is GalleryEntry { IsVideo: false } target && target != draggedEntry && container.Bounds.Contains(point))
            {
                gallery.Move(gallery.IndexOf(draggedEntry), gallery.IndexOf(target));
                panel.UpdateLayout();
                break;
            }
        }

        if (Gallery.ContainerFromItem(draggedEntry) is Control held)
        {
            Lift(held, point);
        }
    }

    /// <summary>Draws the held tile above the others, offset from its slot to sit under the pointer where it was taken hold of.</summary>
    private void Lift(Control container, Point point)
    {
        container.ZIndex = 1;
        container.RenderTransform = new TranslateTransform(point.X - grabOffset.X - container.Bounds.X, point.Y - grabOffset.Y - container.Bounds.Y);
    }

    private void OnGalleryPointerReleased(object? sender, PointerReleasedEventArgs e)
    {
        Drop();
    }

    private void OnGalleryCaptureLost(object? sender, PointerCaptureLostEventArgs e)
    {
        Drop();
    }

    /// <summary>Lets go of the held tile, which settles into the slot it was dragged to.</summary>
    private void Drop()
    {
        if (draggedEntry != null && Gallery.ContainerFromItem(draggedEntry) is Control held)
        {
            held.ZIndex = 0;
            held.RenderTransform = null;
        }

        draggedEntry = null;
        Gallery.Cursor = null;
    }

    /// <summary>Takes an entry out of the gallery: one the item has is removed on submit, one added here is simply not added.</summary>
    private void OnRemovePreview(object? sender, RoutedEventArgs e)
    {
        if ((sender as Button)?.DataContext is GalleryEntry entry)
        {
            gallery.Remove(entry);
        }
    }

    /// <summary>
    /// The tags the workshop manager would submit: an upload starts over from its own tags, an info edit keeps the item's and applies the game mode boxes to them.
    /// </summary>
    private List<string> BuildTags()
    {
        var tags = new List<string>();

        if (mode == SubmissionMode.Edit)
        {
            tags.AddRange(item!.Tags);

            if (!tags.Contains("Map", StringComparer.OrdinalIgnoreCase))
            {
                tags.Add("Map");
            }
        }
        else
        {
            tags.AddRange(WorkshopManager.DefaultTags);
        }

        foreach (var box in gameModeBoxes)
        {
            var tag = (string)box.Tag!;

            if (box.IsChecked == true)
            {
                if (!tags.Contains(tag, StringComparer.OrdinalIgnoreCase))
                {
                    tags.Add(tag);
                }
            }
            else
            {
                tags.RemoveAll(existing => existing.Equals(tag, StringComparison.OrdinalIgnoreCase));
            }
        }

        return tags;
    }

    /// <summary>
    /// The workshop manager's checks before it submits, in its order.
    /// </summary>
    /// <returns>What is wrong, or null when the form can be submitted.</returns>
    private string? Validate(string title, string description, string changeNote, AddonPublishOptions options)
    {
        if (contents?.ExceedsUploadLimit == true)
        {
            return $"Exceeds {AddonContents.FormatSize(AddonPackager.MaxTotalSize)} upload limit! Please optimize your content under this limit.";
        }

        if (mode == SubmissionMode.Edit && options.Title == null && options.Description == null && options.Visibility == null && options.Tags == null && options.ThumbnailImagePath == null && options.Gallery == null)
        {
            return "Nothing was changed.";
        }

        if (title.Length == 0)
        {
            return "Enter a title.";
        }

        if (description.Length == 0)
        {
            return "Enter a description.";
        }

        if (description.Length >= MaxTextLength)
        {
            return $"The description must be shorter than {MaxTextLength} characters.";
        }

        if (mode == SubmissionMode.ReUpload)
        {
            if (changeNote.Length == 0)
            {
                return "Enter update notes for this change.";
            }

            if (changeNote.Length >= MaxTextLength)
            {
                return $"The update notes must be shorter than {MaxTextLength} characters.";
            }
        }

        if (AddonPanel.IsVisible && AddonBox.SelectedItem == null)
        {
            return "Select an addon folder.";
        }

        return Preview.Source == null && thumbnailPath == null ? "Pick a preview image." : null;
    }

    private async void OnSubmit(object? sender, RoutedEventArgs e)
    {
        var title = TitleBox.Text ?? string.Empty;
        var description = DescriptionBox.Text ?? string.Empty;
        var changeNote = ChangeNoteBox.Text ?? string.Empty;
        var visibility = ((VisibilityChoice)VisibilityBox.SelectedItem!).Value;
        var tags = BuildTags();
        var edits = mode == SubmissionMode.Edit;

        // an info edit only sends what changed, like the workshop manager
        var options = new AddonPublishOptions
        {
            AddonName = AddonPanel.IsVisible ? AddonBox.SelectedItem as string : null,
            PublishedFileId = item?.PublishedFileId,
            Title = edits && title == item!.Title ? null : title,
            Description = edits && description == item!.Description ? null : description,
            Visibility = edits && visibility == item!.Visibility ? null : visibility,
            Tags = edits && tags.ToHashSet(StringComparer.OrdinalIgnoreCase).SetEquals(item!.Tags) ? null : tags,
            ThumbnailImagePath = thumbnailPath,
            Gallery = BuildGallery(),
            ChangeNote = mode == SubmissionMode.ReUpload ? changeNote : null,
        };

        if (Validate(title, description, changeNote, options) is string problem)
        {
            await MessageDialog.ShowAsync(OwnerWindow, MessageKind.Warning, "Submission", problem);
            return;
        }

        await PublishAsync(options);
    }

    private async Task PublishAsync(AddonPublishOptions options)
    {
        SetBusy(true);
        UploadProgress.Value = 0;
        Status.Text = options.AddonName == null ? "Updating..." : "Packaging submission...";

        var progress = new Progress<float>(fraction =>
        {
            UploadProgress.Value = fraction;
            Status.Text = $"Submitting {fraction:P0}";
        });

        try
        {
            // packing happens on the calling thread, which would freeze the window
            var result = await Task.Run(() => manager!.PublishAsync(options, progress));

            // an info edit that left the title alone still knows it from the item
            Finish(new PublishedSubmission(result, options.Title ?? item!.Title));
        }
        catch (SourceFolderConflictException exception)
        {
            SetBusy(false);

            var question = $"This item was last published from addon \"{exception.PreviousAddonName}\".\n\nUpload it from \"{exception.AddonName}\" anyway?";

            if (await MessageDialog.AskAsync(OwnerWindow, MessageKind.Warning, "Different Addon Folder", question, "Upload"))
            {
                await PublishAsync(options with { AllowSourceFolderChange = true });
            }
        }
        catch (SteamUnavailableException exception)
        {
            Status.Text = string.Empty;
            await MessageDialog.ShowAsync(OwnerWindow, MessageKind.Warning, "Steam Not Running", exception.Message);
        }
        catch (Exception exception) when (exception is InvalidOperationException or IOException or InvalidDataException or ArgumentException)
        {
            Status.Text = string.Empty;
            await MessageDialog.ShowAsync(OwnerWindow, MessageKind.Warning, "Submission Failed", exception.Message);
        }
        finally
        {
            SetBusy(false);
        }
    }

    /// <summary>
    /// The gallery as shown, for publishing, or null when it is the item's gallery untouched, which the info edit's checks rely on.
    /// The pictures go in the order shown. The item's videos keep the slots they had, since the workshop page puts videos first whatever their slot,
    /// and moving them would only make pictures be sent again. New videos go at the end.
    /// </summary>
    private GalleryUpdate? BuildGallery()
    {
        var current = item?.Previews ?? [];
        var pictures = gallery.Where(entry => !entry.IsVideo).ToList();
        var videos = gallery.Where(entry => entry.IsVideo && entry.Index != null).OrderBy(entry => entry.Index).ToList();
        var ordered = new List<GalleryEntry>();

        while (pictures.Count + videos.Count > 0)
        {
            var video = videos.Count > 0 && (videos[0].Index == ordered.Count || pictures.Count == 0);

            ordered.Add(video ? videos[0] : pictures[0]);
            (video ? videos : pictures).RemoveAt(0);
        }

        ordered.AddRange(gallery.Where(entry => entry.IsVideo && entry.Index == null));

        var untouched = ordered.Count == current.Count && ordered.Select((entry, position) => entry.Index == position).All(same => same);

        if (untouched)
        {
            return null;
        }

        var wanted = ordered.Select(entry => entry.Index is int index ? PreviewSource.Existing(index) : entry.Path != null ? PreviewSource.Screenshot(entry.Path) : PreviewSource.Video(entry.VideoId!)).ToList();

        return new GalleryUpdate(current, wanted);
    }

    private void SetBusy(bool busy)
    {
        Form.IsEnabled = !busy;
        BackButton.IsEnabled = CancelButton.IsEnabled = SubmitButton.IsEnabled = !busy;
        UploadProgress.IsVisible = busy;
    }

    private void OnViewPressed(object? sender, PointerPressedEventArgs e)
    {
        if (e.GetCurrentPoint(this).Properties.IsXButton1Pressed && BackButton.IsEnabled)
        {
            e.Handled = true;
            OnCancel(sender, e);
        }
    }

    private async void OnCancel(object? sender, RoutedEventArgs e)
    {
        if (await MessageDialog.AskAsync(OwnerWindow, MessageKind.Warning, "Leave Submission", "Leave without submitting?\n\nWhat you entered here will be lost.", "Leave"))
        {
            Finish(null);
        }
    }

    private void Finish(PublishedSubmission? published)
    {
        var task = finished;

        finished = null;
        task?.TrySetResult(published);
    }

    /// <summary>What the form published and the title it gave it.</summary>
    public sealed record PublishedSubmission(WorkshopPublishResult Result, string Title);

    /// <summary>A visibility and the label the dropdown shows for it.</summary>
    private sealed record VisibilityChoice(WorkshopVisibility Value, string Label)
    {
        public override string ToString()
        {
            return Label;
        }
    }
}

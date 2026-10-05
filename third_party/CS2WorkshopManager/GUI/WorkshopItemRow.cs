using System.ComponentModel;
using System.Globalization;
using System.Linq;
using Avalonia;
using Avalonia.Controls;
using CS2WorkshopManager;

namespace GUI;

/// <summary>A tag as the lists show it, dimmed when it is one of the two every map carries.</summary>
public sealed record TagPill(string Name, bool Standard);

/// <summary>One of the counts, or the separator between two.</summary>
public sealed record StatPart(string Text, bool Separator);

/// <summary>
/// Wraps the counts between them, and hides a separator that ends up first or last on a line, since the line break already separates.
/// </summary>
public sealed class CountsPanel : WrapPanel
{
    protected override Size ArrangeOverride(Size finalSize)
    {
        var size = base.ArrangeOverride(finalSize);

        for (var index = 1; index < Children.Count - 1; index++)
        {
            var child = Children[index];

            if (child.DataContext is not StatPart { Separator: true })
            {
                continue;
            }

            var trailing = Children[index + 1].Bounds.Top > child.Bounds.Top;
            var leading = Children[index - 1].Bounds.Top < child.Bounds.Top;

            // opacity rather than visibility, so hiding it does not change the wrapping that hid it
            child.Opacity = trailing || leading ? 0 : 1;

            if (!leading)
            {
                continue;
            }

            // the rest of its line moves over the room it took, so the line starts with a count
            var shift = child.DesiredSize.Width;

            for (var follower = index + 1; follower < Children.Count && Children[follower].Bounds.Top == child.Bounds.Top; follower++)
            {
                var moved = Children[follower];
                var margin = moved.Margin;

                moved.Arrange(new Rect(moved.Bounds.X - margin.Left - shift, moved.Bounds.Y - margin.Top, moved.Bounds.Width + margin.Left + margin.Right, moved.Bounds.Height + margin.Top + margin.Bottom));
            }
        }

        return size;
    }
}

/// <summary>
/// A row of the published items list.
/// </summary>
public sealed class WorkshopItemRow(WorkshopItem item) : INotifyPropertyChanged
{
    private object? thumbnail;

    public event PropertyChangedEventHandler? PropertyChanged;

    public WorkshopItem Item { get; } = item;

    public ulong PublishedFileId => Item.PublishedFileId;
    public string Title => Item.Title;

    /// <summary>The tags joined, which the list sorts by.</summary>
    public string Tags => string.Join(",", Item.Tags);

    public IReadOnlyList<TagPill> Pills { get; } = [.. item.Tags.Select(tag => new TagPill(tag, WorkshopManager.DefaultTags.Contains(tag, StringComparer.OrdinalIgnoreCase)))];

    /// <summary>The tags that say something, for the tiles, which have no room for the two every map carries.</summary>
    public IReadOnlyList<TagPill> GameModePills => [.. Pills.Where(pill => !pill.Standard)];

    public string Description => Item.Description;

    /// <summary>The description as plain text, its markup and pictures taken out, for the list.</summary>
    public string Summary { get; } = BbCodeView.ToPlainText(item.Description);

    public WorkshopVisibility Visibility => Item.Visibility;
    public string VisibilityText => Visibility == WorkshopVisibility.FriendsOnly ? "Friends Only" : Visibility.ToString();
    public bool IsPublic => Visibility == WorkshopVisibility.Public;
    public bool IsUnlisted => Visibility == WorkshopVisibility.Unlisted;
    public bool IsFriendsOnly => Visibility == WorkshopVisibility.FriendsOnly;

    public DateTimeOffset LastUpdated => Item.TimeUpdated.ToLocalTime();
    public DateTimeOffset DateCreated => Item.TimeCreated.ToLocalTime();
    public string UpdatedText => "Updated " + LastUpdated.ToString("MMM d, yyyy HH:mm", CultureInfo.CurrentCulture);
    public string CreatedText => "Created " + DateCreated.ToString("MMM d, yyyy", CultureInfo.CurrentCulture);

    public double SizeMegabytes => Item.Size / (1024.0 * 1024.0);
    public string SizeText => AddonContents.FormatSize(Item.Size);

    /// <summary>The counts Steam keeps for the item, rounded the way its list pages round them, so they fit on one line.</summary>
    public string StatsLine => $"{Counted(Item.Subscribers, "sub", compact: true)} | {Counted(Item.Views, "view", compact: true)} | {Counted(Item.Likes, "like", compact: true)} | {Counted(Item.Dislikes, "dislike", compact: true)} | {Counted(Item.Favorites, "fav", compact: true)}";

    /// <summary>The rounded counts with a separator between each two, so they wrap between counts rather than inside one.</summary>
    public IReadOnlyList<StatPart> StatsParts =>
    [
        new(Counted(Item.Subscribers, "sub", compact: true), false),
        new("|", true),
        new(Counted(Item.Views, "view", compact: true), false),
        new("|", true),
        new(Counted(Item.Likes, "like", compact: true), false),
        new("|", true),
        new(Counted(Item.Dislikes, "dislike", compact: true), false),
        new("|", true),
        new(Counted(Item.Favorites, "fav", compact: true), false),
    ];

    /// <summary>Steam's vote score out of five, before any rounding.</summary>
    public double Rating => Item.Score * 5;

    /// <summary>The rating as whole stars, rounded up the way the workshop page shows them.</summary>
    public double Stars => Math.Ceiling(Rating);

    /// <summary>The rating itself, written after the stars, nothing while there are no votes.</summary>
    public string RatingValue => Item.Likes + Item.Dislikes == 0 ? string.Empty : Rating.ToString("0.000", CultureInfo.CurrentCulture);

    /// <summary>The rating in words with the votes behind it, for the tooltip.</summary>
    public string RatingText => Item.Likes + Item.Dislikes == 0 ? "No votes yet" : $"{Rating:0.000} of 5, from {Counted(Item.Likes, "like", compact: false)} and {Counted(Item.Dislikes, "dislike", compact: false)}";

    /// <summary>The same counts in full, for the tooltip.</summary>
    public string StatsExact => $"{Counted(Item.Subscribers, "subscriber", compact: false)} | {Counted(Item.Views, "view", compact: false)} | {Counted(Item.Likes, "like", compact: false)} | {Counted(Item.Dislikes, "dislike", compact: false)} | {Counted(Item.Favorites, "favourite", compact: false)}";

    /// <summary>The preview image file as downloaded, decoded again at full size when the item is opened for editing.</summary>
    public byte[]? Preview { get; set; }

    /// <summary>The preview decoded for the lists, see <see cref="PreviewImage.Decode"/>.</summary>
    public object? Thumbnail
    {
        get => thumbnail;
        set
        {
            thumbnail = value;
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(Thumbnail)));
        }
    }

    private static string Counted(ulong count, string noun, bool compact)
    {
        return count == 1 ? $"1 {noun}" : $"{(compact ? Compact(count) : count.ToString("N0", CultureInfo.CurrentCulture))} {noun}s";
    }

    /// <summary>1,234 as 1.2K and 1,234,567 as 1.23M, with a digit more while the number is short.</summary>
    private static string Compact(ulong count)
    {
        var culture = CultureInfo.CurrentCulture;

        return count switch
        {
            < 1_000 => count.ToString("N0", culture),
            < 10_000 => (count / 1_000.0).ToString("0.#", culture) + "K",
            < 1_000_000 => (count / 1_000.0).ToString("0", culture) + "K",
            < 10_000_000 => (count / 1_000_000.0).ToString("0.##", culture) + "M",
            _ => (count / 1_000_000.0).ToString("0.#", culture) + "M",
        };
    }
}

using System.Buffers.Binary;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using StbImageSharp;
using StbImageWriteSharp;
using Steamworks;
using ValveResourceFormat.IO;

namespace CS2WorkshopManager;

/// <summary>
/// Values of <see cref="ERemoteStoragePublishedFileVisibility"/> because this enum sucks by default and I'm not using these long ass names in a CLI.
/// </summary>
public enum WorkshopVisibility
{
    Public = ERemoteStoragePublishedFileVisibility.k_ERemoteStoragePublishedFileVisibilityPublic,
    FriendsOnly = ERemoteStoragePublishedFileVisibility.k_ERemoteStoragePublishedFileVisibilityFriendsOnly,
    Private = ERemoteStoragePublishedFileVisibility.k_ERemoteStoragePublishedFileVisibilityPrivate,
    Unlisted = ERemoteStoragePublishedFileVisibility.k_ERemoteStoragePublishedFileVisibilityUnlisted,
}

public sealed record AddonPublishOptions
{
    /// <summary> Name of the addon folder under game/csgo_addons to upload, or null to only change the info of the submission in <see cref="PublishedFileId"/>. </summary>
    public string? AddonName { get; init; }

    /// <summary> Workshop ID of an existing submission, if this is provided everything will be treated as updating this submission. </summary>
    public ulong? PublishedFileId { get; init; }

    /// <summary> Title of the workshop item, needed for a new one. Null leaves an existing item's title alone. </summary>
    public string? Title { get; init; }

    /// <summary> Description of the workshop item, empty for a new one when null. Null leaves an existing item's description alone. </summary>
    public string? Description { get; init; }

    /// <summary> Visibility of the Workshop item, see <see cref="WorkshopVisibility"/>, private for a new one when null. Null leaves an existing item's visibility alone. </summary>
    public WorkshopVisibility? Visibility { get; init; }

    /// <summary> The user facing list of submission tags that will show up on the Workshop, <see cref="WorkshopManager.DefaultTags"/> for a new one when null. Null leaves an existing item's tags alone. </summary>
    public IReadOnlyList<string>? Tags { get; init; }

    /// <summary> Disk path for the user facing thumbnail image that will show up on the Workshop. Null leaves the published preview alone. </summary>
    public string? ThumbnailImagePath { get; init; }

    /// <summary> The gallery under the main preview as it should be afterwards, see <see cref="GalleryUpdate"/>. Null leaves the published gallery alone. </summary>
    public GalleryUpdate? Gallery { get; init; }

    /// <summary> Change note that shows up in the "Change Notes" tab. Null gives the workshop manager's "Created {Title}." for a new item, "Edited {Title}." for an upload with a title, and no note otherwise. </summary>
    public string? ChangeNote { get; init; }

    /// <summary> Update the item even when the workshop content was published from a different addon folder, otherwise <see cref="SourceFolderConflictException"/> is thrown. </summary>
    public bool AllowSourceFolderChange { get; init; }

    /// <summary> Packing rules for this publish alone, checked before the addon's own rules and the global ones, for an upload that should leave out or bring in more than they do. Null for none. </summary>
    public AddonRules? Rules { get; init; }
}

public sealed record WorkshopPublishResult(ulong PublishedFileId, bool NeedsWorkshopAgreement)
{
    public Uri Url => new($"https://steamcommunity.com/sharedfiles/filedetails/?id={PublishedFileId}");

    /// <summary>The item's page in the Steam client, which Steam opens when it is running.</summary>
    public Uri SteamUrl => new($"steam://url/CommunityFilePage/{PublishedFileId}");
}

/// <summary>
/// One entry of a gallery as it should be after publishing.
/// </summary>
public sealed record PreviewSource
{
    public int? ExistingIndex { get; private init; }

    public string? ImagePath { get; private init; }

    public string? VideoId { get; private init; }

    public static PreviewSource Existing(int index)
    {
        return new PreviewSource { ExistingIndex = index };
    }

    /// <param name="path">A PNG, JPG or GIF file under 1 MB.</param>
    public static PreviewSource Screenshot(string path)
    {
        return new PreviewSource { ImagePath = path };
    }

    /// <param name="idOrLink">A YouTube video id, or a link to the video.</param>
    public static PreviewSource Video(string idOrLink)
    {
        return new PreviewSource { VideoId = WorkshopManager.ParseYouTubeVideoId(idOrLink) ?? throw new ArgumentException($"\"{idOrLink}\" is not a YouTube video id or link.", nameof(idOrLink)) };
    }
}

/// <summary>
/// The gallery under an item's main preview as it is, and as it should be after publishing, in order. Entries of <paramref name="Current"/> that are not wanted go,
/// and wanted entries can be in any order, with new pictures and videos anywhere among them.
/// </summary>
public sealed record GalleryUpdate(IReadOnlyList<WorkshopPreview> Current, IReadOnlyList<PreviewSource> Wanted);

public enum WorkshopPreviewKind
{
    Image,
    YouTubeVideo,
    Other,
}

/// <summary>
/// One entry of the gallery under an item's main preview: a picture by its url, or a YouTube video by its id.
/// </summary>
public sealed record WorkshopPreview(WorkshopPreviewKind Kind, string Value, string FileName)
{
    /// <summary>A picture of it: the picture itself, or the video's thumbnail from YouTube. Null for what has none.</summary>
    public Uri? ImageUrl => Kind switch
    {
        WorkshopPreviewKind.Image => Absolute(Value),
        WorkshopPreviewKind.YouTubeVideo => Absolute($"https://img.youtube.com/vi/{Value}/hqdefault.jpg"),
        _ => null,
    };

    /// <summary>Where it opens: the picture, or the video on YouTube.</summary>
    public Uri? PageUrl => Kind switch
    {
        WorkshopPreviewKind.Image => Absolute(Value),
        WorkshopPreviewKind.YouTubeVideo => Absolute($"https://www.youtube.com/watch?v={Value}"),
        _ => null,
    };

    private static Uri? Absolute(string url)
    {
        return Uri.TryCreate(url, UriKind.Absolute, out var uri) ? uri : null;
    }
}

/// <summary>
/// A workshop item as the workshop manager lists it.
/// </summary>
public sealed record WorkshopItem(
    ulong PublishedFileId,
    string Title,
    string Description,
    IReadOnlyList<string> Tags,
    WorkshopVisibility Visibility,
    DateTimeOffset TimeCreated,
    DateTimeOffset TimeUpdated,
    long Size,
    ulong Subscribers,
    ulong Favorites,
    ulong Likes,
    ulong Dislikes,
    double Score,
    ulong Views,
    Uri? PreviewUrl,
    IReadOnlyList<WorkshopPreview> Previews)
{
    public Uri Url => new($"https://steamcommunity.com/sharedfiles/filedetails/?id={PublishedFileId}");

    /// <summary>The item's page in the Steam client, which Steam opens when it is running.</summary>
    public Uri SteamUrl => new($"steam://url/CommunityFilePage/{PublishedFileId}");
}

public sealed class SourceFolderConflictException : InvalidOperationException
{
    public ulong PublishedFileId { get; }
    public string? PreviousAddonName { get; }
    public string? AddonName { get; }

    public SourceFolderConflictException() { }
    public SourceFolderConflictException(string message) : base(message) { }
    public SourceFolderConflictException(string message, Exception innerException) : base(message, innerException) { }

    public SourceFolderConflictException(ulong publishedFileId, string previousAddonName, string addonName)
        : base($"Workshop item {publishedFileId} was last published from addon \"{previousAddonName}\", not \"{addonName}\", change AllowSourceFolderChange to allow this.")
    {
        PublishedFileId = publishedFileId;
        PreviousAddonName = previousAddonName;
        AddonName = addonName;
    }
}

/// <summary>
/// Packs a compiled Counter-Strike 2 addon and publishes it to the Steam Workshop.
/// </summary>
public sealed class WorkshopManager
{
    /// <summary>CS2 appid.</summary>
    public const uint AppId = 730;

    public const int ThumbnailJpegQuality = 75;

    /// <summary>The most a thumbnail may weigh, as Steam has it. Only matters for gifs, other images are made into a JPEG that fits.</summary>
    public const long MaxThumbnailSize = 1024 * 1024;

    public static readonly string[] DefaultTags = ["CS2", "Map"];

    /// <summary>The game mode tags the workshop manager offers, added after <see cref="DefaultTags"/>.</summary>
    public static readonly string[] GameModeTags = ["Classic", "Deathmatch", "Armsrace", "Wingman", "Custom"];

    private static SteamClient? steam;

    /// <summary>The crawls made so far by addon and map, each with the time its map was built.</summary>
    private readonly Dictionary<string, (DateTime Built, AddonUsage.Result Found)> crawls = new(StringComparer.OrdinalIgnoreCase);

    private static SteamClient Steam
    {
        get
        {
            InitializeSteam();
            return steam!;
        }
    }

    public string GamePath { get; }
    public string AddonsRoot => Path.Combine(GamePath, "game", "csgo_addons");

    public string GameInfoPath => Path.Combine(GamePath, "game", "csgo", "gameinfo.gi");

    /// <summary>Where the addons' source content lives, and with it their <see cref="AddonRules"/>.</summary>
    public string ContentRoot => Path.Combine(GamePath, "content", "csgo_addons");

    /// <summary>The user's rules for what <paramref name="addonName"/> uploads, none when they have not made any.</summary>
    public AddonRules LoadRules(string addonName)
    {
        return AddonRules.Load(AddonRules.GetPath(ContentRoot, addonName));
    }

    /// <summary>
    /// The rules an upload of <paramref name="addonName"/> is packed by: the ones in <see cref="AppSettings"/> that apply to every addon first, so they win,
    /// then the addon's own, and last, when the addon asks for it, an exclude rule for each file its map does not reach, which every rule the user made wins over.
    /// </summary>
    /// <param name="recrawl">Read the map again even when it has not been rebuilt, as a publish does, since an asset it reaches can change without it.</param>
    public AddonRules LoadPackingRules(string addonName, bool recrawl = false)
    {
        var own = LoadRules(addonName);
        var user = AppSettings.Load().GlobalRules.Then(own);

        return own.ExcludeUnused == null ? user : user.Then(BuildUnusedRules(addonName, own.ExcludeUnused, recrawl).Rules);
    }

    public void SaveRules(string addonName, AddonRules rules)
    {
        ArgumentNullException.ThrowIfNull(rules);

        rules.Save(AddonRules.GetPath(ContentRoot, addonName));
    }

    /// <summary>
    /// An exclude rule for each file a crawl of <paramref name="mapName"/> does not reach that the upload would otherwise take, the biggest first.
    /// A file that is left out anyway gets no rule, one for it saying nothing. None for an addon without that compiled map, there being no way to tell what it uses.
    /// Nothing is saved: a crawl is kept for as long as the map is not rebuilt, so working these out again for the same map is quick.
    /// </summary>
    /// <param name="mapName">The map to crawl, relative to the addon, or null for the addon's own.</param>
    /// <param name="recrawl">Read the map again even when it has not been rebuilt.</param>
    /// <returns>The rules, and what the crawl found, whose unused files are the ones they cover.</returns>
    public (AddonRules Rules, AddonUsage.Result Found) BuildUnusedRules(string addonName, string? mapName = null, bool recrawl = false)
    {
        var addonPath = Path.Combine(AddonsRoot, addonName);
        var found = Crawl(addonPath, mapName, recrawl);

        if (!found.HasCompiledMap)
        {
            return (new AddonRules(), found);
        }

        var packed = AddonPackager.CollectFiles(addonPath, GameInfoPath, AppSettings.Load().GlobalRules.Then(LoadRules(addonName)))
            .ToDictionary(file => AddonPackager.GetRelativePath(addonPath, file.FullName), file => file.Length, StringComparer.OrdinalIgnoreCase);

        var written = found.Unused
            .Where(packed.ContainsKey)
            .OrderByDescending(path => packed[path])
            .ToList();

        var rules = new AddonRules();
        rules.Rules.AddRange(written.Select(path => new AddonRules.Rule(true, path)));

        return (rules, found with { Unused = written });
    }

    /// <summary><see cref="AddonUsage.Detect"/>, or the last crawl of the same map when it has not been built since and <paramref name="recrawl"/> is not asked for.</summary>
    private AddonUsage.Result Crawl(string addonPath, string? mapName, bool recrawl)
    {
        var map = mapName == null ? AddonUsage.FindMaps(addonPath).FirstOrDefault() : AddonRules.Normalize(mapName);
        var mapPath = map == null ? null : Path.Combine(addonPath, map);

        if (mapPath == null || !File.Exists(mapPath))
        {
            return AddonUsage.Detect(addonPath, mapName);
        }

        var key = $"{Path.GetFullPath(addonPath)}|{map}";
        var built = File.GetLastWriteTimeUtc(mapPath);

        lock (crawls)
        {
            if (!recrawl && crawls.TryGetValue(key, out var crawl) && crawl.Built == built)
            {
                return crawl.Found;
            }
        }

        var found = AddonUsage.Detect(addonPath, map);

        lock (crawls)
        {
            crawls[key] = (built, found);
        }

        return found;
    }

    /// <summary>
    /// The addon folders under game/csgo_addons, without the folders the workshop manager keeps there itself.
    /// </summary>
    public IEnumerable<string> GetAddonNames()
    {
        return Directory.EnumerateDirectories(AddonsRoot)
            .Select(path => Path.GetFileName(path))
            .Where(name => !name.Equals("vpks", StringComparison.OrdinalIgnoreCase) && !name.Equals("workshop_items", StringComparison.OrdinalIgnoreCase));
    }

    public WorkshopManager(string gamePath)
    {
        GamePath = gamePath;
    }

    public static WorkshopManager FromSteamInstall()
    {
        var game = GameFolderLocator.FindSteamGameByAppId((int)AppId)
            ?? throw new DirectoryNotFoundException("Counter-Strike 2 is not installed in any Steam library.");

        return new WorkshopManager(game.GamePath);
    }

    /// <summary>
    /// Connects to the running Steam client as Counter-Strike 2.
    /// </summary>
    public static void InitializeSteam()
    {
        steam ??= new SteamClient(AppId);
    }

    public static void ShutdownSteam()
    {
        steam?.Dispose();
        steam = null;
    }

    /// <summary>
    /// The addon the running Counter-Strike 2 workshop tools were started with, read from the game's command line, or null when the tools are not running.
    /// </summary>
    public static string? GetRunningToolsAddon()
    {
        foreach (var process in Process.GetProcessesByName("cs2"))
        {
            using (process)
            {
                var arguments = ProcessCommandLine.Read(process)?.Split(' ', StringSplitOptions.RemoveEmptyEntries);

                if (arguments == null || !arguments.Contains("-tools", StringComparer.OrdinalIgnoreCase))
                {
                    continue;
                }

                var addon = Array.FindIndex(arguments, argument => argument.Equals("-addon", StringComparison.OrdinalIgnoreCase));

                if (addon >= 0 && addon + 1 < arguments.Length)
                {
                    return arguments[addon + 1].Trim('"');
                }
            }
        }

        return null;
    }

    /// <summary>
    /// The addon folder the item's installed workshop content was published from, or null when it is not installed or was not published by a workshop manager.
    /// </summary>
    public static string? GetPublishedSourceFolder(ulong publishedFileId)
    {
        var installDirectory = Steam.UGC.GetItemInstallFolder(publishedFileId);

        return installDirectory == null ? null : AddonPackager.ReadPublishedSourceFolder(installDirectory);
    }

    /// <summary>
    /// The addon the item was last published from.
    /// </summary>
    /// <returns>
    /// Last addon path the item was published from if trying to publish from a different addon, null otherwise.
    /// </returns>
    public static string? GetConflictingSourceFolder(string addonName, ulong publishedFileId)
    {
        var previous = GetPublishedSourceFolder(publishedFileId);

        return previous != null && !previous.Equals(addonName, StringComparison.OrdinalIgnoreCase) ? previous : null;
    }

    /// <summary>
    /// Every map the logged in account has published for Counter-Strike 2, the items with both the CS2 and Map tags, newest first, as Steam's pages of them arrive.
    /// </summary>
    public static async IAsyncEnumerable<WorkshopItem> GetPublishedItemsAsync()
    {
        var client = Steam;
        var ugc = client.UGC;
        var accountId = client.User.GetAccountId();

        var count = 0u;

        for (var page = 1u; ; page++)
        {
            var query = ugc.CreateQueryUserUGCRequest(accountId, EUserUGCList.Published, EUGCMatchingUGCType.Items, EUserUGCListSortOrder.CreationOrderDesc, AppId, AppId, page);

            if (query == SteamUGC.InvalidQueryHandle)
            {
                throw new InvalidOperationException("Failed to create a workshop query.");
            }

            try
            {
                // only items with every tag the workshop manager always sets, which leaves the maps and not the skins and the rest tagged for the game
                foreach (var tag in DefaultTags)
                {
                    ugc.AddRequiredTag(query, tag);
                }
                ugc.SetReturnLongDescription(query, true);
                ugc.SetReturnAdditionalPreviews(query, true);

                var completed = await client.WaitForCallResultAsync<SteamUGCQueryCompleted>(ugc.SendQueryUGCRequest(query)).ConfigureAwait(false);

                if (completed.Result != EResult.OK)
                {
                    throw new InvalidOperationException($"Workshop query failed: {completed.Result}");
                }

                for (var index = 0u; index < completed.NumResultsReturned; index++)
                {
                    if (ugc.GetQueryUGCResult(query, index) is not SteamUGCDetails details)
                    {
                        continue;
                    }

                    count++;

                    yield return new WorkshopItem(
                        details.PublishedFileId,
                        details.Title,
                        details.Description,
                        details.Tags.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries),
                        (WorkshopVisibility)details.Visibility,
                        DateTimeOffset.FromUnixTimeSeconds(details.TimeCreated),
                        DateTimeOffset.FromUnixTimeSeconds(details.TimeUpdated),
                        (long)details.TotalFilesSize,
                        ugc.GetQueryUGCStatistic(query, index, EItemStatistic.NumSubscriptions) ?? 0,
                        ugc.GetQueryUGCStatistic(query, index, EItemStatistic.NumFavorites) ?? 0,
                        details.VotesUp,
                        details.VotesDown,
                        details.Score,
                        ugc.GetQueryUGCStatistic(query, index, EItemStatistic.NumUniqueWebsiteViews) ?? 0,
                        ugc.GetQueryUGCPreviewURL(query, index),
                        ReadPreviews(ugc, query, index));
                }

                if (completed.NumResultsReturned < SteamUGC.ResultsPerPage || count >= completed.TotalMatchingResults)
                {
                    yield break;
                }
            }
            finally
            {
                ugc.ReleaseQueryUGCRequest(query);
            }
        }
    }

    /// <summary>The gallery of one query result, in the order Steam keeps it, which is the order the indices for removing entries refer to.</summary>
    private static List<WorkshopPreview> ReadPreviews(SteamUGC ugc, ulong query, uint index)
    {
        var previews = new List<WorkshopPreview>();
        var count = ugc.GetQueryUGCNumAdditionalPreviews(query, index);

        for (var previewIndex = 0u; previewIndex < count; previewIndex++)
        {
            if (ugc.GetQueryUGCAdditionalPreview(query, index, previewIndex) is { } preview)
            {
                var kind = preview.Type switch
                {
                    EItemPreviewType.Image => WorkshopPreviewKind.Image,
                    EItemPreviewType.YouTubeVideo => WorkshopPreviewKind.YouTubeVideo,
                    _ => WorkshopPreviewKind.Other,
                };

                previews.Add(new WorkshopPreview(kind, preview.Value, preview.FileName));
            }
        }

        return previews;
    }

    /// <summary>
    /// The video id in a YouTube link of any of the usual shapes, or the text itself when it already is an id, or null when it is neither.
    /// </summary>
    public static string? ParseYouTubeVideoId(string text)
    {
        text = text.Trim();

        if (IsVideoId(text))
        {
            return text;
        }

        if (!Uri.TryCreate(text, UriKind.Absolute, out var link))
        {
            return null;
        }

        var segments = link.AbsolutePath.Split('/', StringSplitOptions.RemoveEmptyEntries);

        // youtu.be/ID, and youtube.com/watch?v=ID, /shorts/ID, /embed/ID, /live/ID
        var candidate = link.Host.EndsWith("youtu.be", StringComparison.OrdinalIgnoreCase)
            ? segments.FirstOrDefault()
            : link.Host.EndsWith("youtube.com", StringComparison.OrdinalIgnoreCase)
                ? segments.Length >= 2 && segments[0] is "shorts" or "embed" or "live" ? segments[1] : QueryValue(link.Query, "v")
                : null;

        return candidate != null && IsVideoId(candidate) ? candidate : null;

        static bool IsVideoId(string value)
        {
            return value.Length == 11 && value.All(character => char.IsAsciiLetterOrDigit(character) || character is '-' or '_');
        }

        static string? QueryValue(string query, string name)
        {
            foreach (var pair in query.TrimStart('?').Split('&', StringSplitOptions.RemoveEmptyEntries))
            {
                var separator = pair.IndexOf('=');

                if (separator > 0 && pair[..separator] == name)
                {
                    return pair[(separator + 1)..];
                }
            }

            return null;
        }
    }

    /// <summary>The most a gallery picture may weigh, as Steam has it.</summary>
    public const long MaxScreenshotSize = 1024 * 1024;

    /// <summary>Fetches the pictures of a gallery that move, since Steam takes a picture for a slot only as a file.</summary>
    private static readonly HttpClient Http = new();

    /// <summary>
    /// Makes the gallery what <paramref name="update"/> wants. Kept entries in their order with new ones after them only take removals and additions.
    /// Any other order rewrites the slots that differ, fetching the pictures Steam holds so they can be sent back where they now go.
    /// </summary>
    /// <returns>The files fetched for that, to delete once the update is submitted.</returns>
    private static async Task<List<string>> ApplyGalleryAsync(SteamUGC ugc, ulong handle, GalleryUpdate update)
    {
        var current = update.Current;
        var wanted = update.Wanted;
        var fetched = new List<string>();

        foreach (var source in wanted)
        {
            if (source.ExistingIndex is int index && (index < 0 || index >= current.Count))
            {
                throw new ArgumentException($"There is no gallery entry {index} to keep, the gallery has {current.Count}.", nameof(update));
            }
        }

        var kept = wanted.Where(source => source.ExistingIndex != null).Select(source => source.ExistingIndex!.Value).ToList();
        var keptFirst = kept.Count == 0 || wanted.ToList().FindLastIndex(source => source.ExistingIndex != null) == kept.Count - 1;
        var keptInOrder = kept.Distinct().Count() == kept.Count && kept.SequenceEqual(kept.Order());

        if (keptFirst && keptInOrder)
        {
            // only removals, from the last index down so the earlier indices stay what they were, and additions at the end
            foreach (var index in Enumerable.Range(0, current.Count).Except(kept).OrderDescending())
            {
                ugc.RemoveItemPreview(handle, (uint)index);
            }

            foreach (var source in wanted.Where(source => source.ExistingIndex == null))
            {
                await AddAsync(source).ConfigureAwait(false);
            }

            return fetched;
        }

        for (var slot = 0; slot < wanted.Count; slot++)
        {
            var source = wanted[slot];

            if (slot >= current.Count)
            {
                await AddAsync(source).ConfigureAwait(false);
            }
            else if (source.ExistingIndex != slot)
            {
                if (VideoOf(source) is string video)
                {
                    ugc.UpdateItemPreviewVideo(handle, (uint)slot, video);
                }
                else
                {
                    ugc.UpdateItemPreviewFile(handle, (uint)slot, await FileOfAsync(source).ConfigureAwait(false));
                }
            }
        }

        // the slots past the wanted gallery go, from the last down
        for (var slot = current.Count - 1; slot >= wanted.Count; slot--)
        {
            ugc.RemoveItemPreview(handle, (uint)slot);
        }

        return fetched;

        async Task AddAsync(PreviewSource source)
        {
            if (VideoOf(source) is string video)
            {
                ugc.AddItemPreviewVideo(handle, video);
            }
            else
            {
                ugc.AddItemPreviewFile(handle, await FileOfAsync(source).ConfigureAwait(false), EItemPreviewType.Image);
            }
        }

        string? VideoOf(PreviewSource source)
        {
            return source.VideoId ?? (source.ExistingIndex is int index && current[index].Kind == WorkshopPreviewKind.YouTubeVideo ? current[index].Value : null);
        }

        async Task<string> FileOfAsync(PreviewSource source)
        {
            if (source.ImagePath != null)
            {
                return ValidateScreenshot(source.ImagePath);
            }

            var preview = current[source.ExistingIndex!.Value];

            if (preview.Kind != WorkshopPreviewKind.Image || preview.ImageUrl == null)
            {
                throw new InvalidOperationException("Only pictures and YouTube videos can be moved in the gallery, anything else can stay where it is or be removed.");
            }

            // the picture Steam holds, under the name it was uploaded with, in a folder of this update's own
            var folder = Path.Combine(Path.GetTempPath(), "CS2WorkshopManager", Guid.NewGuid().ToString("N"));
            var name = Path.GetFileName(preview.FileName);
            var path = Path.Combine(folder, name.Length > 0 ? name : $"preview{source.ExistingIndex}.jpg");

            Directory.CreateDirectory(folder);
            await File.WriteAllBytesAsync(path, await Http.GetByteArrayAsync(preview.ImageUrl).ConfigureAwait(false)).ConfigureAwait(false);
            fetched.Add(path);

            return path;
        }
    }

    /// <summary>
    /// Checks a picture for the gallery the way Steam will: a PNG, JPG or GIF file under 1 MB.
    /// </summary>
    /// <returns>The full path, which Steam wants.</returns>
    public static string ValidateScreenshot(string path)
    {
        var file = new FileInfo(path);

        if (!file.Exists)
        {
            throw new InvalidDataException($"Screenshot \"{path}\" does not exist.");
        }

        if (file.Extension is not (".png" or ".jpg" or ".jpeg" or ".gif"))
        {
            throw new InvalidDataException($"Screenshot \"{path}\" must be a PNG, JPG or GIF file.");
        }

        if (file.Length >= MaxScreenshotSize)
        {
            throw new InvalidDataException($"Screenshot \"{path}\" is {AddonContents.FormatSize(file.Length)}, the workshop takes gallery pictures under 1 MB.");
        }

        return file.FullName;
    }

    public async Task<WorkshopPublishResult> PublishAsync(AddonPublishOptions options, IProgress<float>? progress = null)
    {
        InitializeSteam();

        if (options.AddonName == null && options.PublishedFileId == null)
        {
            throw new ArgumentException("A new submission needs an addon folder to upload.", nameof(options));
        }

        // a new item gets the workshop manager's defaults for what is not given, an existing one keeps what it has, since Steam leaves alone what is not set
        var creating = options.PublishedFileId == null;

        if (creating && string.IsNullOrWhiteSpace(options.Title))
        {
            throw new ArgumentException("A new item needs a title.", nameof(options));
        }

        if (options.AddonName != null && options.PublishedFileId is ulong existingFileId && !options.AllowSourceFolderChange)
        {
            var previousAddonName = GetConflictingSourceFolder(options.AddonName, existingFileId);

            if (previousAddonName != null)
            {
                throw new SourceFolderConflictException(existingFileId, previousAddonName, options.AddonName);
            }
        }

        // what can fail without Steam is checked before a new item is created, so a mistake does not leave an empty one behind
        if (options.AddonName != null && !Directory.Exists(Path.Combine(AddonsRoot, options.AddonName)))
        {
            throw new DirectoryNotFoundException($"Addon folder '{Path.Combine(AddonsRoot, options.AddonName)}' does not exist.");
        }

        if (options.ThumbnailImagePath != null)
        {
            ValidateThumbnailImage(options.ThumbnailImagePath);
        }

        var publishedFileId = options.PublishedFileId ?? await CreateItemAsync().ConfigureAwait(false);

        var publishTime = DateTimeOffset.UtcNow;

        // only the info changes when there is no addon to upload. The staged publish data records the title given, or none when the item keeps its own
        var contentPath = options.AddonName == null ? null : AddonPackager.Stage(AddonsRoot, options.AddonName, GameInfoPath, publishedFileId, options.Title ?? string.Empty, publishTime, options.Rules == null ? LoadPackingRules(options.AddonName, recrawl: true) : options.Rules.Then(LoadPackingRules(options.AddonName, recrawl: true)));

        var ugc = Steam.UGC;
        var handle = ugc.StartItemUpdate(AppId, publishedFileId);

        if (options.Title != null)
        {
            ugc.SetItemTitle(handle, options.Title);
        }

        if ((options.Description ?? (creating ? string.Empty : null)) is string description)
        {
            ugc.SetItemDescription(handle, description);
        }

        if ((options.Visibility ?? (creating ? WorkshopVisibility.Private : null)) is WorkshopVisibility visibility)
        {
            ugc.SetItemVisibility(handle, (ERemoteStoragePublishedFileVisibility)visibility);
        }

        if (options.ThumbnailImagePath != null)
        {
            ugc.SetItemPreview(handle, WriteThumbnail(options.ThumbnailImagePath, publishedFileId, publishTime));
        }

        var fetched = options.Gallery == null ? [] : await ApplyGalleryAsync(ugc, handle, options.Gallery).ConfigureAwait(false);

        if (contentPath != null)
        {
            ugc.SetItemContent(handle, contentPath);
        }

        if ((options.Tags ?? (creating ? DefaultTags : null)) is { } tags)
        {
            ugc.SetItemTags(handle, tags);
        }

        var changeNote = options.ChangeNote ?? (creating ? $"Created {options.Title}." : options.AddonName != null && options.Title != null ? $"Edited {options.Title}." : string.Empty);

        SubmitItemUpdateResult result;

        try
        {
            result = await Steam.WaitForCallResultAsync<SubmitItemUpdateResult>(ugc.SubmitItemUpdate(handle, changeNote), () =>
            {
                var update = ugc.GetItemUpdateProgress(handle);

                if (update.BytesTotal > 0)
                {
                    progress?.Report((float)update.BytesProcessed / update.BytesTotal);
                }
            }).ConfigureAwait(false);
        }
        finally
        {
            // the gallery pictures fetched to move them are only needed until they are sent
            foreach (var path in fetched)
            {
                try
                {
                    Directory.Delete(Path.GetDirectoryName(path)!, recursive: true);
                }
                catch (IOException)
                {
                    // a folder that will not go can stay in the temp folder
                }
            }
        }

        if (result.Result != EResult.OK)
        {
            throw new InvalidOperationException($"SubmitItemUpdate failed: {result.Result}");
        }

        return new WorkshopPublishResult(publishedFileId, result.UserNeedsToAcceptWorkshopLegalAgreement);
    }

    /// <summary>
    /// Deletes a published item from the workshop, which can not be undone.
    /// </summary>
    public static async Task DeleteItemAsync(ulong publishedFileId)
    {
        var result = await Steam.WaitForCallResultAsync<DeleteItemResult>(Steam.UGC.DeleteItem(publishedFileId)).ConfigureAwait(false);

        if (result.Result != EResult.OK)
        {
            throw new InvalidOperationException($"DeleteItem failed: {result.Result}");
        }
    }

    private static async Task<ulong> CreateItemAsync()
    {
        var result = await Steam.WaitForCallResultAsync<CreateItemResult>(Steam.UGC.CreateItem(AppId, EWorkshopFileType.Community)).ConfigureAwait(false);

        if (result.Result != EResult.OK)
        {
            throw new InvalidOperationException($"CreateItem failed: {result.Result}");
        }

        return result.PublishedFileId;
    }

    /// <summary>
    /// Throws when the file is not an image stb can decode, or a gif that can be uploaded as it is.
    /// </summary>
    public static void ValidateThumbnailImage(string path)
    {
        if (IsGifFile(path))
        {
            var size = new FileInfo(path).Length;

            if (size >= MaxThumbnailSize)
            {
                throw new InvalidDataException($"Thumbnail gif '{path}' is {AddonContents.FormatSize(size)}, gifs are uploaded unchanged and the workshop takes thumbnails under 1 MB.");
            }

            ValidateGif(path, File.ReadAllBytes(path));
            return;
        }

        DecodeThumbnailImage(path);
    }

    private static bool IsGifFile(string path)
    {
        using var stream = File.OpenRead(path);

        Span<byte> header = stackalloc byte[4];
        return stream.ReadAtLeast(header, header.Length, throwOnEndOfStream: false) == header.Length && header.SequenceEqual("GIF8"u8);
    }

    /// <summary>
    /// Walks the blocks of a gif without decoding its pixels, since stb throws on valid gifs whose encoder keeps a full LZW dictionary
    /// instead of clearing it, which optimizers like ezgif do.
    /// </summary>
    private static void ValidateGif(string path, ReadOnlySpan<byte> file)
    {
        var damaged = () => new InvalidDataException($"Thumbnail gif '{path}' is damaged.");

        if (file.Length < 13 || BinaryPrimitives.ReadUInt16LittleEndian(file[6..]) == 0 || BinaryPrimitives.ReadUInt16LittleEndian(file[8..]) == 0)
        {
            throw damaged();
        }

        // header and logical screen descriptor, then the global color table when there is one
        var position = 13 + GifColorTableSize(file[10]);
        var images = 0;

        // some encoders leave out the trailer, which viewers accept, so running out of file after an image is fine
        while (position < file.Length && file[position] != 0x3B)
        {
            switch (file[position])
            {
                case 0x21: // extension: introducer, label, sub-blocks
                    position = SkipGifSubBlocks(file, position + 2) ?? throw damaged();
                    break;

                case 0x2C: // image: descriptor, local color table, LZW minimum code size, sub-blocks
                    if (position + 11 > file.Length)
                    {
                        throw damaged();
                    }

                    position += 10 + GifColorTableSize(file[position + 9]);
                    position = SkipGifSubBlocks(file, position + 1) ?? throw damaged();
                    images++;
                    break;

                default:
                    throw damaged();
            }
        }

        if (images == 0)
        {
            throw damaged();
        }
    }

    private static int GifColorTableSize(byte flags)
    {
        return (flags & 0x80) != 0 ? 3 << ((flags & 7) + 1) : 0;
    }

    /// <summary>Returns the position after the terminating sub-block, or null when the file ends first.</summary>
    private static int? SkipGifSubBlocks(ReadOnlySpan<byte> file, int position)
    {
        while (position < file.Length && file[position] != 0)
        {
            position += file[position] + 1;
        }

        return position < file.Length ? position + 1 : null;
    }

    private static ImageResult DecodeThumbnailImage(string path)
    {
        using var stream = File.OpenRead(path);

        try
        {
            return ImageResult.FromStream(stream, StbImageSharp.ColorComponents.RedGreenBlue);
        }
        catch (Exception exception) when (exception is not IOException)
        {
            // stb is a port of C, so a file it can not handle surfaces as whatever the port trips over, not just InvalidOperationException
            throw new InvalidDataException($"Thumbnail image '{path}' could not be decoded: {exception.Message.Trim()}", exception);
        }
    }

    /// <summary>
    /// Steam only accepts small thumbnail images (1 mb or less) so the thumbnail is transformed into a JPEG, except for gifs which are uploaded unchanged.
    /// </summary>
    private static string WriteThumbnail(string sourcePath, ulong publishedFileId, DateTimeOffset time)
    {
        var directory = Path.Combine(Path.GetTempPath(), $"workshopupload_{publishedFileId}");
        Directory.CreateDirectory(directory);

        if (IsGifFile(sourcePath))
        {
            var gifPath = Path.Combine(directory, $"thumbnail_{time.ToUnixTimeSeconds():x}.gif");
            File.Copy(sourcePath, gifPath, overwrite: true);
            return gifPath;
        }

        var image = DecodeThumbnailImage(sourcePath);

        var path = Path.Combine(directory, $"thumbnail_{time.ToUnixTimeSeconds():x}.jpg");

        using var stream = File.Create(path);
        new ImageWriter().WriteJpg(image.Data, image.Width, image.Height, StbImageWriteSharp.ColorComponents.RedGreenBlue, stream, ThumbnailJpegQuality);

        return path;
    }
}

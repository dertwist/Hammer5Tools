using System.Buffers.Binary;
using System.Runtime.InteropServices;

namespace Steamworks;

/// <summary>
/// The Steam Workshop calls the CS2 workshop manager makes, on ISteamUGC.
/// </summary>
public sealed class SteamUGC
{
    /// <summary>ISteamUGC version whose layout is used below, the client keeps serving old versions.</summary>
    public const string InterfaceVersion = "STEAMUGC_INTERFACE_VERSION020";

    /// <summary>kNumUGCResultsPerPage, the most results a query page can hold.</summary>
    public const uint ResultsPerPage = 50;

    /// <summary>k_UGCQueryHandleInvalid</summary>
    public const ulong InvalidQueryHandle = ulong.MaxValue;

    /// <summary>MAX_PATH, the folder buffer the workshop manager hands to GetItemInstallInfo.</summary>
    private const int InstallFolderBufferSize = 260;

    private const int PreviewUrlBufferSize = 1024;

    /// <summary>MAX_PATH again, for the file name a gallery entry was uploaded under.</summary>
    private const int PreviewFileNameBufferSize = 260;

    /// <summary>ISteamUGC vtable slots, in the order of isteamugc.h.</summary>
    private enum Slot
    {
        CreateQueryUserUGCRequest = 0,
        SendQueryUGCRequest = 4,
        GetQueryUGCResult = 5,
        GetQueryUGCPreviewURL = 9,
        GetQueryUGCStatistic = 12,
        GetQueryUGCNumAdditionalPreviews = 13,
        GetQueryUGCAdditionalPreview = 14,
        ReleaseQueryUGCRequest = 21,
        AddRequiredTag = 22,
        SetReturnLongDescription = 27,
        SetReturnAdditionalPreviews = 30,
        CreateItem = 44,
        StartItemUpdate = 45,
        SetItemTitle = 46,
        SetItemDescription = 47,
        SetItemVisibility = 50,
        SetItemTags = 51,
        SetItemContent = 52,
        SetItemPreview = 53,
        AddItemPreviewFile = 58,
        AddItemPreviewVideo = 59,
        UpdateItemPreviewFile = 60,
        UpdateItemPreviewVideo = 61,
        RemoveItemPreview = 62,
        SubmitItemUpdate = 66,
        GetItemUpdateProgress = 67,
        GetItemInstallInfo = 77,
        DeleteItem = 90,
    }

    private readonly nint instance;

    internal SteamUGC(nint instance)
    {
        this.instance = instance;
    }

    private unsafe void** VTable => SteamClient.VTable(instance);

    /// <returns>Query handle, <see cref="InvalidQueryHandle"/> when the request could not be created.</returns>
    public unsafe ulong CreateQueryUserUGCRequest(uint accountId, EUserUGCList list, EUGCMatchingUGCType matchingType, EUserUGCListSortOrder sortOrder, uint creatorAppId, uint consumerAppId, uint page)
    {
        return ((delegate* unmanaged<void*, uint, int, int, int, uint, uint, uint, ulong>)VTable[(int)Slot.CreateQueryUserUGCRequest])((void*)instance, accountId, (int)list, (int)matchingType, (int)sortOrder, creatorAppId, consumerAppId, page);
    }

    public bool AddRequiredTag(ulong query, string tag)
    {
        return CallWithString(Slot.AddRequiredTag, query, tag);
    }

    public unsafe bool SetReturnLongDescription(ulong query, bool returnLongDescription)
    {
        return ((delegate* unmanaged<void*, ulong, byte, byte>)VTable[(int)Slot.SetReturnLongDescription])((void*)instance, query, returnLongDescription ? (byte)1 : (byte)0) != 0;
    }

    /// <returns>Call handle for <see cref="SteamClient.WaitForCallResultAsync{T}"/> with <see cref="SteamUGCQueryCompleted"/>.</returns>
    public unsafe ulong SendQueryUGCRequest(ulong query)
    {
        return ((delegate* unmanaged<void*, ulong, ulong>)VTable[(int)Slot.SendQueryUGCRequest])((void*)instance, query);
    }

    /// <returns>The details of one result of a completed query, or null when there is no such result.</returns>
    public unsafe SteamUGCDetails? GetQueryUGCResult(ulong query, uint index)
    {
        var details = stackalloc byte[SteamUGCDetails.Size];

        var found = ((delegate* unmanaged<void*, ulong, uint, byte*, byte>)VTable[(int)Slot.GetQueryUGCResult])((void*)instance, query, index, details) != 0;

        return found ? SteamUGCDetails.Read(new ReadOnlySpan<byte>(details, SteamUGCDetails.Size)) : null;
    }

    /// <returns>The preview image url of one result of a completed query, or null when it has none.</returns>
    public unsafe Uri? GetQueryUGCPreviewURL(ulong query, uint index)
    {
        var url = stackalloc byte[PreviewUrlBufferSize];

        var found = ((delegate* unmanaged<void*, ulong, uint, byte*, uint, byte>)VTable[(int)Slot.GetQueryUGCPreviewURL])((void*)instance, query, index, url, PreviewUrlBufferSize) != 0;

        return found ? ToUri(Marshal.PtrToStringUTF8((nint)url)) : null;
    }

    /// <returns>One statistic of one result of a completed query, or null when the result does not carry it.</returns>
    public unsafe ulong? GetQueryUGCStatistic(ulong query, uint index, EItemStatistic statistic)
    {
        ulong value;

        var found = ((delegate* unmanaged<void*, ulong, uint, int, ulong*, byte>)VTable[(int)Slot.GetQueryUGCStatistic])((void*)instance, query, index, (int)statistic, &value) != 0;

        return found ? value : null;
    }

    public unsafe bool SetReturnAdditionalPreviews(ulong query, bool returnAdditionalPreviews)
    {
        return ((delegate* unmanaged<void*, ulong, byte, byte>)VTable[(int)Slot.SetReturnAdditionalPreviews])((void*)instance, query, returnAdditionalPreviews ? (byte)1 : (byte)0) != 0;
    }

    /// <returns>How many previews one result of a completed query has besides its main one, when the query asked for them.</returns>
    public unsafe uint GetQueryUGCNumAdditionalPreviews(ulong query, uint index)
    {
        return ((delegate* unmanaged<void*, ulong, uint, uint>)VTable[(int)Slot.GetQueryUGCNumAdditionalPreviews])((void*)instance, query, index);
    }

    /// <returns>One of the previews a result has besides its main one, or null when there is no such preview.</returns>
    public unsafe AdditionalPreview? GetQueryUGCAdditionalPreview(ulong query, uint index, uint previewIndex)
    {
        var url = stackalloc byte[PreviewUrlBufferSize];
        var fileName = stackalloc byte[PreviewFileNameBufferSize];
        int type;

        var found = ((delegate* unmanaged<void*, ulong, uint, uint, byte*, uint, byte*, uint, int*, byte>)VTable[(int)Slot.GetQueryUGCAdditionalPreview])((void*)instance, query, index, previewIndex, url, PreviewUrlBufferSize, fileName, PreviewFileNameBufferSize, &type) != 0;

        return found ? new AdditionalPreview((EItemPreviewType)type, Marshal.PtrToStringUTF8((nint)url) ?? string.Empty, Marshal.PtrToStringUTF8((nint)fileName) ?? string.Empty) : null;
    }

    internal static Uri? ToUri(string? url)
    {
        return string.IsNullOrEmpty(url) ? null : new Uri(url);
    }

    public unsafe bool ReleaseQueryUGCRequest(ulong query)
    {
        return ((delegate* unmanaged<void*, ulong, byte>)VTable[(int)Slot.ReleaseQueryUGCRequest])((void*)instance, query) != 0;
    }

    /// <returns>Call handle for <see cref="SteamClient.WaitForCallResultAsync{T}"/> with <see cref="CreateItemResult"/>.</returns>
    public unsafe ulong CreateItem(uint appId, EWorkshopFileType fileType)
    {
        return ((delegate* unmanaged<void*, uint, int, ulong>)VTable[(int)Slot.CreateItem])((void*)instance, appId, (int)fileType);
    }

    public unsafe ulong StartItemUpdate(uint appId, ulong publishedFileId)
    {
        return ((delegate* unmanaged<void*, uint, ulong, ulong>)VTable[(int)Slot.StartItemUpdate])((void*)instance, appId, publishedFileId);
    }

    public bool SetItemTitle(ulong handle, string title)
    {
        return CallWithString(Slot.SetItemTitle, handle, title);
    }

    public bool SetItemDescription(ulong handle, string description)
    {
        return CallWithString(Slot.SetItemDescription, handle, description);
    }

    public unsafe bool SetItemVisibility(ulong handle, ERemoteStoragePublishedFileVisibility visibility)
    {
        return ((delegate* unmanaged<void*, ulong, int, byte>)VTable[(int)Slot.SetItemVisibility])((void*)instance, handle, (int)visibility) != 0;
    }

    public unsafe bool SetItemTags(ulong handle, IReadOnlyList<string> tags, bool allowAdminTags = false)
    {
        var strings = new nint[tags.Count];

        try
        {
            for (var i = 0; i < strings.Length; i++)
            {
                strings[i] = Marshal.StringToCoTaskMemUTF8(tags[i]);
            }

            fixed (nint* pointers = strings)
            {
                var array = new StringArray
                {
                    Strings = (byte**)pointers,
                    Count = strings.Length,
                };

                return ((delegate* unmanaged<void*, ulong, StringArray*, byte, byte>)VTable[(int)Slot.SetItemTags])((void*)instance, handle, &array, allowAdminTags ? (byte)1 : (byte)0) != 0;
            }
        }
        finally
        {
            foreach (var value in strings)
            {
                Marshal.FreeCoTaskMem(value);
            }
        }
    }

    public bool SetItemContent(ulong handle, string contentFolder)
    {
        return CallWithString(Slot.SetItemContent, handle, contentFolder);
    }

    public bool SetItemPreview(ulong handle, string previewFile)
    {
        return CallWithString(Slot.SetItemPreview, handle, previewFile);
    }

    /// <summary>Adds a picture to the item's previews besides the main one, which Steam wants under 1 MB.</summary>
    public unsafe bool AddItemPreviewFile(ulong handle, string previewFile, EItemPreviewType type)
    {
        fixed (byte* text = SteamClient.NullTerminated(previewFile))
        {
            return ((delegate* unmanaged<void*, ulong, byte*, int, byte>)VTable[(int)Slot.AddItemPreviewFile])((void*)instance, handle, text, (int)type) != 0;
        }
    }

    /// <summary>Adds a YouTube video, by its id, to the item's previews besides the main one.</summary>
    public bool AddItemPreviewVideo(ulong handle, string videoId)
    {
        return CallWithString(Slot.AddItemPreviewVideo, handle, videoId);
    }

    /// <summary>Replaces one of the item's previews besides the main one, by its index among them, with a picture.</summary>
    public unsafe bool UpdateItemPreviewFile(ulong handle, uint index, string previewFile)
    {
        fixed (byte* text = SteamClient.NullTerminated(previewFile))
        {
            return ((delegate* unmanaged<void*, ulong, uint, byte*, byte>)VTable[(int)Slot.UpdateItemPreviewFile])((void*)instance, handle, index, text) != 0;
        }
    }

    /// <summary>Replaces one of the item's previews besides the main one, by its index among them, with a YouTube video by its id.</summary>
    public unsafe bool UpdateItemPreviewVideo(ulong handle, uint index, string videoId)
    {
        fixed (byte* text = SteamClient.NullTerminated(videoId))
        {
            return ((delegate* unmanaged<void*, ulong, uint, byte*, byte>)VTable[(int)Slot.UpdateItemPreviewVideo])((void*)instance, handle, index, text) != 0;
        }
    }

    /// <summary>Removes one of the item's previews besides the main one, by its index among them.</summary>
    public unsafe bool RemoveItemPreview(ulong handle, uint index)
    {
        return ((delegate* unmanaged<void*, ulong, uint, byte>)VTable[(int)Slot.RemoveItemPreview])((void*)instance, handle, index) != 0;
    }

    /// <returns>Call handle for <see cref="SteamClient.WaitForCallResultAsync{T}"/> with <see cref="SubmitItemUpdateResult"/>.</returns>
    public unsafe ulong SubmitItemUpdate(ulong handle, string? changeNote)
    {
        fixed (byte* text = changeNote != null ? SteamClient.NullTerminated(changeNote) : null)
        {
            return ((delegate* unmanaged<void*, ulong, byte*, ulong>)VTable[(int)Slot.SubmitItemUpdate])((void*)instance, handle, text);
        }
    }

    public unsafe ItemUpdateProgress GetItemUpdateProgress(ulong handle)
    {
        ulong bytesProcessed;
        ulong bytesTotal;

        var status = ((delegate* unmanaged<void*, ulong, ulong*, ulong*, int>)VTable[(int)Slot.GetItemUpdateProgress])((void*)instance, handle, &bytesProcessed, &bytesTotal);

        return new ItemUpdateProgress((EItemUpdateStatus)status, bytesProcessed, bytesTotal);
    }

    /// <returns>Call handle for <see cref="SteamClient.WaitForCallResultAsync{T}"/> with <see cref="DeleteItemResult"/>.</returns>
    public unsafe ulong DeleteItem(ulong publishedFileId)
    {
        return ((delegate* unmanaged<void*, ulong, ulong>)VTable[(int)Slot.DeleteItem])((void*)instance, publishedFileId);
    }

    /// <summary>
    /// The folder an item is installed to, GetItemInstallInfo, or null when it is not installed.
    /// </summary>
    public unsafe string? GetItemInstallFolder(ulong publishedFileId)
    {
        var folder = stackalloc byte[InstallFolderBufferSize];
        ulong sizeOnDisk;
        uint timestamp;

        var installed = ((delegate* unmanaged<void*, ulong, ulong*, byte*, uint, uint*, byte>)VTable[(int)Slot.GetItemInstallInfo])((void*)instance, publishedFileId, &sizeOnDisk, folder, InstallFolderBufferSize, &timestamp) != 0;

        return installed ? Marshal.PtrToStringUTF8((nint)folder) : null;
    }

    private unsafe bool CallWithString(Slot slot, ulong handle, string value)
    {
        fixed (byte* text = SteamClient.NullTerminated(value))
        {
            return ((delegate* unmanaged<void*, ulong, byte*, byte>)VTable[(int)slot])((void*)instance, handle, text) != 0;
        }
    }

    /// <summary>SteamParamStringArray_t</summary>
    [StructLayout(LayoutKind.Sequential)]
    private unsafe struct StringArray
    {
        public byte** Strings;
        public int Count;
    }
}

public readonly record struct ItemUpdateProgress(EItemUpdateStatus Status, ulong BytesProcessed, ulong BytesTotal);

/// <summary>One of an item's previews besides its main one: the url of a picture or the id of a YouTube video, and the name it was uploaded under.</summary>
public readonly record struct AdditionalPreview(EItemPreviewType Type, string Value, string FileName);

/// <summary>EItemPreviewType</summary>
public enum EItemPreviewType
{
    Image = 0,
    YouTubeVideo = 1,
    EnvironmentMapHorizontalCross = 3,
    EnvironmentMapLatLong = 4,
    Clip = 5,
}

/// <summary>SteamUGCQueryCompleted_t</summary>
public readonly record struct SteamUGCQueryCompleted(ulong Query, EResult Result, uint NumResultsReturned, uint TotalMatchingResults, bool CachedData) : ICallResult<SteamUGCQueryCompleted>
{
    public static SteamUGCQueryCompleted Read(ReadOnlySpan<byte> data)
    {
        // UGCQueryHandle_t m_handle; EResult m_eResult; uint32 m_unNumResultsReturned; uint32 m_unTotalMatchingResults; bool m_bCachedData; char m_rgchNextCursor[256];
        var reader = new NativeStructReader(data);

        return new SteamUGCQueryCompleted(
            reader.ReadUInt64(),
            (EResult)reader.ReadInt32(),
            reader.ReadUInt32(),
            reader.ReadUInt32(),
            reader.ReadBool());
    }
}

/// <summary>SteamUGCDetails_t</summary>
public sealed record SteamUGCDetails(
    ulong PublishedFileId,
    EResult Result,
    EWorkshopFileType FileType,
    uint CreatorAppId,
    uint ConsumerAppId,
    string Title,
    string Description,
    ulong SteamIdOwner,
    uint TimeCreated,
    uint TimeUpdated,
    uint TimeAddedToUserList,
    ERemoteStoragePublishedFileVisibility Visibility,
    bool Banned,
    bool AcceptedForUse,
    bool TagsTruncated,
    string Tags,
    ulong File,
    ulong PreviewFile,
    string FileName,
    int FileSize,
    int PreviewFileSize,
    Uri? Url,
    uint VotesUp,
    uint VotesDown,
    float Score,
    uint NumChildren,
    ulong TotalFilesSize)
{
    private const int TitleMax = 129; // k_cchPublishedDocumentTitleMax
    private const int DescriptionMax = 8000; // k_cchPublishedDocumentDescriptionMax
    private const int TagListMax = 1025; // k_cchTagListMax
    private const int FilenameMax = 260; // k_cchFilenameMax
    private const int UrlMax = 256; // k_cchPublishedFileURLMax

    /// <summary>Size of the native struct on this platform.</summary>
    public static readonly int Size = Measure();

    public static SteamUGCDetails Read(ReadOnlySpan<byte> data)
    {
        return Read(data, out _);
    }

    private static int Measure()
    {
        Read(new byte[16384], out var size);
        return size;
    }

    private static SteamUGCDetails Read(ReadOnlySpan<byte> data, out int size)
    {
        var reader = new NativeStructReader(data);

        var details = new SteamUGCDetails(
            reader.ReadUInt64(),
            (EResult)reader.ReadInt32(),
            (EWorkshopFileType)reader.ReadInt32(),
            reader.ReadUInt32(),
            reader.ReadUInt32(),
            reader.ReadString(TitleMax),
            reader.ReadString(DescriptionMax),
            reader.ReadUInt64(),
            reader.ReadUInt32(),
            reader.ReadUInt32(),
            reader.ReadUInt32(),
            (ERemoteStoragePublishedFileVisibility)reader.ReadInt32(),
            reader.ReadBool(),
            reader.ReadBool(),
            reader.ReadBool(),
            reader.ReadString(TagListMax),
            reader.ReadUInt64(),
            reader.ReadUInt64(),
            reader.ReadString(FilenameMax),
            reader.ReadInt32(),
            reader.ReadInt32(),
            SteamUGC.ToUri(reader.ReadString(UrlMax)),
            reader.ReadUInt32(),
            reader.ReadUInt32(),
            reader.ReadSingle(),
            reader.ReadUInt32(),
            reader.ReadUInt64());

        size = reader.Size;

        return details;
    }
}

/// <summary>CreateItemResult_t</summary>
public readonly record struct CreateItemResult(EResult Result, ulong PublishedFileId, bool UserNeedsToAcceptWorkshopLegalAgreement) : ICallResult<CreateItemResult>
{
    public static CreateItemResult Read(ReadOnlySpan<byte> data)
    {
        // EResult m_eResult; PublishedFileId_t m_nPublishedFileId; bool m_bUserNeedsToAcceptWorkshopLegalAgreement;
        var publishedFileIdOffset = SteamClient.StructPack;

        return new CreateItemResult(
            (EResult)BinaryPrimitives.ReadInt32LittleEndian(data),
            BinaryPrimitives.ReadUInt64LittleEndian(data[publishedFileIdOffset..]),
            data[publishedFileIdOffset + sizeof(ulong)] != 0);
    }
}

/// <summary>DeleteItemResult_t</summary>
public readonly record struct DeleteItemResult(EResult Result, ulong PublishedFileId) : ICallResult<DeleteItemResult>
{
    public static DeleteItemResult Read(ReadOnlySpan<byte> data)
    {
        // EResult m_eResult; PublishedFileId_t m_nPublishedFileId;
        return new DeleteItemResult(
            (EResult)BinaryPrimitives.ReadInt32LittleEndian(data),
            BinaryPrimitives.ReadUInt64LittleEndian(data[SteamClient.StructPack..]));
    }
}

/// <summary>SubmitItemUpdateResult_t</summary>
public readonly record struct SubmitItemUpdateResult(EResult Result, bool UserNeedsToAcceptWorkshopLegalAgreement, ulong PublishedFileId) : ICallResult<SubmitItemUpdateResult>
{
    public static SubmitItemUpdateResult Read(ReadOnlySpan<byte> data)
    {
        // EResult m_eResult; bool m_bUserNeedsToAcceptWorkshopLegalAgreement; PublishedFileId_t m_nPublishedFileId;
        return new SubmitItemUpdateResult(
            (EResult)BinaryPrimitives.ReadInt32LittleEndian(data),
            data[sizeof(int)] != 0,
            BinaryPrimitives.ReadUInt64LittleEndian(data[(2 * sizeof(int))..]));
    }
}

public enum EWorkshopFileType
{
    Community = 0,
    Microtransaction = 1,
    Collection = 2,
    Art = 3,
    Video = 4,
    Screenshot = 5,
    Game = 6,
    Software = 7,
    Concept = 8,
    WebGuide = 9,
    IntegratedGuide = 10,
    Merch = 11,
    ControllerBinding = 12,
    SteamworksAccessInvite = 13,
    SteamVideo = 14,
    GameManagedItem = 15,
    Clip = 16,
}

public enum ERemoteStoragePublishedFileVisibility
{
    k_ERemoteStoragePublishedFileVisibilityPublic = 0,
    k_ERemoteStoragePublishedFileVisibilityFriendsOnly = 1,
    k_ERemoteStoragePublishedFileVisibilityPrivate = 2,
    k_ERemoteStoragePublishedFileVisibilityUnlisted = 3,
}

public enum EItemUpdateStatus
{
    Invalid = 0,
    PreparingConfig = 1,
    PreparingContent = 2,
    UploadingContent = 3,
    UploadingPreviewFile = 4,
    CommittingChanges = 5,
}

/// <summary>EItemStatistic, the counts a query result carries.</summary>
public enum EItemStatistic
{
    NumSubscriptions = 0,
    NumFavorites = 1,
    NumFollowers = 2,
    NumUniqueSubscriptions = 3,
    NumUniqueFavorites = 4,
    NumUniqueFollowers = 5,
    NumUniqueWebsiteViews = 6,
    ReportScore = 7,
    NumSecondsPlayed = 8,
    NumPlaytimeSessions = 9,
    NumComments = 10,
    NumSecondsPlayedDuringTimePeriod = 11,
    NumPlaytimeSessionsDuringTimePeriod = 12,
}

public enum EUserUGCList
{
    Published = 0,
    VotedOn = 1,
    VotedUp = 2,
    VotedDown = 3,
    WillVoteLater = 4,
    Favorited = 5,
    Subscribed = 6,
    UsedOrPlayed = 7,
    Followed = 8,
}

public enum EUGCMatchingUGCType
{
    Items = 0,
    ItemsMtx = 1,
    ItemsReadyToUse = 2,
    Collections = 3,
    Artwork = 4,
    Videos = 5,
    Screenshots = 6,
    AllGuides = 7,
    WebGuides = 8,
    IntegratedGuides = 9,
    UsableInGame = 10,
    ControllerBindings = 11,
    GameManagedItems = 12,
    All = -1,
}

public enum EUserUGCListSortOrder
{
    CreationOrderDesc = 0,
    CreationOrderAsc = 1,
    TitleAsc = 2,
    LastUpdatedDesc = 3,
    SubscriptionDateDesc = 4,
    VoteScoreDesc = 5,
    ForModeration = 6,
}

using System.IO;
using ValveKeyValue;

namespace CS2WorkshopManager;

/// <summary>The look of the apps: the system's light or dark, or one of them whatever the system is.</summary>
public enum AppTheme
{
    System,
    Light,
    Dark,
}

/// <summary>
/// What the user has set for every game and addon alike, kept as settings.txt in the user's application data folder in the key values format of the game's own files.
/// The file records the version of the app that saved it, and whatever a newer version put in it is kept through a save by an older one.
/// </summary>
public sealed class AppSettings
{
    public const string FileName = "settings.txt";

    private const string VersionKey = "version";
    private const string ThemeKey = "theme";
    private const string AccentKey = "accent";
    private const string RulesKey = "publish_rules";

    /// <summary>Where the settings are kept, under the user's application data folder: %AppData% on Windows, ~/.config on Linux.</summary>
    public static string FilePath { get; } = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "CS2WorkshopManager", FileName);

    /// <summary>The version of this app, as three parts, which is what it writes into the file.</summary>
    public static Version AppVersion { get; } = ThreeParts(typeof(AppSettings).Assembly.GetName().Version ?? new Version(0, 0, 0));

    /// <summary>The version of the app that last saved the file, or null when nothing has been saved yet or the file does not say.</summary>
    public Version? SavedBy { get; private set; }

    /// <summary>Whether the file was saved by a newer app than this one, which may have put in it what this one does not know.</summary>
    public bool SavedByNewerApp => SavedBy != null && SavedBy > AppVersion;

    /// <summary>The look of the apps, following the system unless set.</summary>
    public AppTheme Theme { get; set; }

    /// <summary>The accent colour set over the theme's own, as #RRGGBB, or null for the theme's.</summary>
    public string? Accent { get; set; }

    /// <summary>The packing rules that apply to every addon, checked before the addon's own rules and gameinfo's.</summary>
    public AddonRules GlobalRules { get; } = new();

    /// <summary>Everything the file holds, so what this version does not know survives a save.</summary>
    private KVObject data = KVObject.Collection();

    /// <summary>The settings as saved, or none when nothing has been saved yet.</summary>
    public static AppSettings Load()
    {
        var settings = new AppSettings();

        if (!File.Exists(FilePath))
        {
            return settings;
        }

        using var stream = File.OpenRead(FilePath);
        settings.data = KVSerializer.Create(KVSerializationFormat.KeyValues1Text).Deserialize(stream, KVSerializerOptions.DefaultOptions).Root;

        if (settings.data.TryGetValue(VersionKey, out var version) && Version.TryParse((string)version, out var parsed))
        {
            settings.SavedBy = ThreeParts(parsed);
        }

        if (settings.data.TryGetValue(ThemeKey, out var theme) && Enum.TryParse((string)theme, ignoreCase: true, out AppTheme parsedTheme))
        {
            settings.Theme = parsedTheme;
        }

        if (settings.data.TryGetValue(AccentKey, out var accent) && (string)accent is { Length: > 0 } hex)
        {
            settings.Accent = hex;
        }

        if (settings.data.TryGetValue(RulesKey, out var rules))
        {
            settings.GlobalRules.Read(rules);
        }

        return settings;
    }

    public void Save()
    {
        // the version and the settings first, then whatever else was in the file as it was
        var saved = KVObject.Collection();
        saved.Add(VersionKey, AppVersion.ToString());
        saved.Add(ThemeKey, Theme.ToString().ToLowerInvariant());

        if (Accent != null)
        {
            saved.Add(AccentKey, Accent);
        }

        saved.Add(RulesKey, GlobalRules.Write());

        foreach (var child in data.Children)
        {
            if (child.Key is not (VersionKey or ThemeKey or AccentKey or RulesKey))
            {
                saved.Add(child.Key, child.Value);
            }
        }

        Directory.CreateDirectory(Path.GetDirectoryName(FilePath)!);

        using (var stream = File.Create(FilePath))
        {
            KVSerializer.Create(KVSerializationFormat.KeyValues1Text).Serialize(stream, saved, "settings");
        }

        data = saved;
        SavedBy = AppVersion;
    }

    /// <summary>The version as major, minor and patch, the way it is written and compared, whatever parts it came with.</summary>
    private static Version ThreeParts(Version version)
    {
        return new Version(version.Major, version.Minor, Math.Max(version.Build, 0));
    }
}

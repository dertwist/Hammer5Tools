using System.IO;
using ValveKeyValue;

namespace CS2WorkshopManager;

/// <summary>
/// Custom file packing rules, the same way VpkDirectories works, kept as publish_rules.txt in the addon's content folder and applied ahead of gameinfo's VpkDirectories.
/// A rule is a path prefix to include or exclude, matched the way gameinfo's entries are: the first rule that fits a path decides.
/// The file can also name a compiled map whose unused content is kept out, see <see cref="ExcludeUnused"/>. The rules that come from it are not stored, they are worked out whenever the addon is packed.
/// </summary>
public sealed class AddonRules
{
    public const string FileName = "publish_rules.txt";

    private const string ExcludeKey = "exclude";
    private const string IncludeKey = "include";
    private const string ExcludeUnusedKey = "exclude_unused";

    /// <summary>A path prefix to keep out of, or in, the upload.</summary>
    public readonly record struct Rule(bool Exclude, string Pattern);

    public List<Rule> Rules { get; } = [];

    /// <summary>
    /// The compiled map, relative to the addon, whose unused content is kept out of the upload, or null to take it all.
    /// See <see cref="WorkshopManager.BuildUnusedRules"/>.
    /// </summary>
    public string? ExcludeUnused { get; set; }

    public static string GetPath(string contentRoot, string addonName)
    {
        return Path.Combine(contentRoot, addonName, FileName);
    }

    public static AddonRules Load(string path)
    {
        var rules = new AddonRules();

        if (!File.Exists(path))
        {
            return rules;
        }

        using var stream = File.OpenRead(path);
        var data = KVSerializer.Create(KVSerializationFormat.KeyValues1Text).Deserialize(stream, KVSerializerOptions.DefaultOptions);

        rules.Read(data.Root);

        return rules;
    }

    public void Save(string path)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);

        using var stream = File.Create(path);
        KVSerializer.Create(KVSerializationFormat.KeyValues1Text).Serialize(stream, Write(), "publish_rules");
    }

    /// <summary>Adds the rules a key values block holds, its "exclude" and "include" entries in their order.</summary>
    internal void Read(KVObject block)
    {
        foreach (var child in block.Children)
        {
            if (child.Key.Equals(ExcludeUnusedKey, StringComparison.OrdinalIgnoreCase))
            {
                ExcludeUnused = Normalize((string)child.Value);
                continue;
            }

            var exclude = child.Key.Equals(ExcludeKey, StringComparison.OrdinalIgnoreCase);

            if (exclude || child.Key.Equals(IncludeKey, StringComparison.OrdinalIgnoreCase))
            {
                Rules.Add(new Rule(exclude, Normalize((string)child.Value)));
            }
        }
    }

    /// <summary>The rules as a key values block, an "exclude" or "include" entry each in their order.</summary>
    internal KVObject Write()
    {
        var data = KVObject.ListCollection();

        if (ExcludeUnused != null)
        {
            data.Add(ExcludeUnusedKey, ExcludeUnused);
        }

        foreach (var rule in Rules)
        {
            data.Add(rule.Exclude ? ExcludeKey : IncludeKey, rule.Pattern);
        }

        return data;
    }

    /// <summary>These rules followed by <paramref name="next"/>'s, as one set for packing by, leaving both as they are.</summary>
    public AddonRules Then(AddonRules next)
    {
        ArgumentNullException.ThrowIfNull(next);

        var rules = new AddonRules();

        rules.Rules.AddRange(Rules);
        rules.Rules.AddRange(next.Rules);

        return rules;
    }

    public void Add(Rule rule)
    {
        rule = rule with { Pattern = Normalize(rule.Pattern) };

        if (!Rules.Contains(rule))
        {
            Rules.Add(rule);
        }
    }

    public static string Normalize(string pattern)
    {
        return pattern.Trim().Replace('\\', '/');
    }
}

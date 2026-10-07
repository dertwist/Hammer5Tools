namespace Hammer5Tools.App.Features.SoundEvents;

using System.Text.Json;

internal sealed class SoundEventPresentation
{
    public List<SoundPropertyGroup> Groups { get; set; } = [];
    public List<SoundPropertySpec> Properties { get; set; } = [];

    public static SoundEventPresentation Legacy { get; } = Load();

    private static SoundEventPresentation Load()
    {
        using var stream = typeof(SoundEventPresentation).Assembly.GetManifestResourceStream(
            "Hammer5Tools.App.Features.SoundEvents.SoundEventPresentation.json")!;
        return JsonSerializer.Deserialize<SoundEventPresentation>(stream)!;
    }

    public SoundPropertySpec GetSpec(string key) => Properties.FirstOrDefault(item => item.Key == key)
        ?? (key.StartsWith("comment_", StringComparison.Ordinal) ? GetSpec("comment") : new SoundPropertySpec { Key = key, Title = key.Replace('_', ' '), Kind = "legacy", Group = "custom" });
}

internal sealed class SoundPropertyGroup
{
    public string Key { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
}

internal sealed class SoundPropertySpec
{
    public string Key { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public string Kind { get; set; } = string.Empty;
    public string Group { get; set; } = string.Empty;
    public string Tooltip { get; set; } = string.Empty;
    public string DefaultValue { get; set; } = "\"\"";
    public string? Toggle { get; set; }
    public Dictionary<string, JsonElement> Options { get; set; } = [];
}

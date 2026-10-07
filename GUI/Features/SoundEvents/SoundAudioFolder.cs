namespace Hammer5Tools.App.Features.SoundEvents;

internal sealed class SoundAudioFolder
{
    public string Name { get; init; } = string.Empty;
    public string? SoundPath { get; init; }
    public List<SoundAudioFolder> Children { get; } = [];

    public static List<SoundAudioFolder> Build(IEnumerable<string> paths, string? filter)
    {
        var roots = new List<SoundAudioFolder>();
        foreach (var path in paths.Where(path => path.Contains(filter ?? string.Empty, StringComparison.OrdinalIgnoreCase)))
        {
            var parts = path.Replace('\\', '/').Split('/', StringSplitOptions.RemoveEmptyEntries);
            var current = roots;
            for (var i = parts[0] == "sounds" ? 1 : 0; i < parts.Length; i++)
            {
                var leaf = i == parts.Length - 1;
                var name = leaf ? Path.GetFileNameWithoutExtension(parts[i]) : parts[i];
                var node = current.FirstOrDefault(item => item.Name == name);
                if (node is null)
                {
                    node = new SoundAudioFolder { Name = name, SoundPath = leaf ? path : null };
                    current.Add(node);
                }
                current = node.Children;
            }
        }
        return roots;
    }
}

internal sealed record SoundAudioRow(string Path, long Bytes)
{
    public string Name => System.IO.Path.GetFileNameWithoutExtension(Path);
    public string Size => Bytes >= 1024 * 1024 ? $"{Bytes / (1024.0 * 1024):F2} MiB" : $"{Bytes / 1024.0:F2} KiB";
}

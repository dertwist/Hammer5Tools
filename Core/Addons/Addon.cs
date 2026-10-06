namespace Hammer5Tools.Core.Addons;

using System.IO;

/// <summary>
/// Represents a CS2 addon workspace with content and compiled game directories.
/// </summary>
public class Addon
{
    public string Name { get; }

    public string ContentPath { get; }

    public string GamePath { get; }

    public bool HasContent => Directory.Exists(ContentPath);

    public bool HasGame => Directory.Exists(GamePath);

    public bool HasMaps
    {
        get
        {
            var mapsDir = Path.Combine(ContentPath, "maps");
            return Directory.Exists(mapsDir) && Directory.EnumerateFiles(mapsDir, "*.vmap").Any();
        }
    }

    public bool HasPrimaryMap
    {
        get
        {
            var primaryMapPath = Path.Combine(ContentPath, "maps", $"{Name}.vmap");
            return File.Exists(primaryMapPath);
        }
    }

    public Addon(string name, string contentPath, string gamePath)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(name);
        ArgumentException.ThrowIfNullOrWhiteSpace(contentPath);
        ArgumentException.ThrowIfNullOrWhiteSpace(gamePath);

        Name = name;
        ContentPath = contentPath;
        GamePath = gamePath;
    }

    public override string ToString() => Name;
}

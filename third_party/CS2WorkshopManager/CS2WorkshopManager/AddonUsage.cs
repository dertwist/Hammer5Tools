using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using ValveKeyValue;
using ValvePak;
using ValveResourceFormat;
using ValveResourceFormat.ResourceTypes;
using ValveResourceFormat.Serialization.KeyValues;
using ValveResourceFormat.Utils;

namespace CS2WorkshopManager;

/// <summary>
/// Which of an addon's files a compiled map actually reaches, so that what it does not can be kept out of an upload.
/// The map's vpk is read and every reference followed: what a resource names in its external reference list, what an entity holds in its
/// properties, and what any other key values data has as a string that lands on a file of the addon. What is never reached is unused.
/// </summary>
public static partial class AddonUsage
{
    /// <summary>
    /// Some references cannot be detected by following vpk references, but we assume the game uses them.
    /// Those folders and files are hardcoded as used, but a user rule still wins of this.
    /// </summary>
    private static readonly string[] AlwaysUsedPaths =
    [
        "panorama/",
        "resource/",
        "scripts/",
        "soundevents/",
        "cfg/",
        "addoninfo.txt",
    ];

    /// <summary>An entity naming another map to load, the 3d skybox among them, which is packed as a vpk of its own.</summary>
    private const string ChildMapKey = "targetmapname";

    /// <summary>How deep a key values tree is walked for strings, past which a file is malformed rather than deep.</summary>
    private const int MaxKeyValuesDepth = 64;

    /// <summary>What a crawl found, see <see cref="Detect"/>.</summary>
    /// <param name="Unused">The addon's files that nothing reaches, relative to the addon and in path order.</param>
    /// <param name="Maps">The maps that were read, the chosen one and the child maps it named, relative to the addon.</param>
    /// <param name="HasCompiledMap">Whether there was a map to read at all, without which nothing can be said about any file.</param>
    public sealed record Result(IReadOnlyList<string> Unused, IReadOnlyList<string> Maps, bool HasCompiledMap);

    /// <summary>
    /// The compiled maps of the addon, relative to it, in path order. A map named after the addon comes first, being the one it is usually about.
    /// </summary>
    public static List<string> FindMaps(string addonPath)
    {
        addonPath = Path.TrimEndingDirectorySeparator(Path.GetFullPath(addonPath));

        var mapsPath = Path.Combine(addonPath, "maps");

        if (!Directory.Exists(mapsPath))
        {
            return [];
        }

        var addonName = Path.GetFileName(addonPath);

        return [.. Directory.EnumerateFiles(mapsPath, "*.vpk", SearchOption.AllDirectories)
            .Select(path => AddonPackager.GetRelativePath(addonPath, path))
            .OrderByDescending(map => Path.GetFileNameWithoutExtension(map).Equals(addonName, StringComparison.OrdinalIgnoreCase))
            .ThenBy(map => map, StringComparer.OrdinalIgnoreCase)];
    }

    /// <summary>
    /// Crawls <paramref name="mapName"/>, or the first of <see cref="FindMaps"/> when that is null, and says which of the addon's files it never reaches.
    /// Nothing is unused when the addon has no compiled map, since there would be nothing to judge it by.
    /// </summary>
    /// <param name="addonPath">The addon folder under game/csgo_addons.</param>
    /// <param name="mapName">The map to start from, relative to the addon as <see cref="FindMaps"/> gives it, or null for the addon's own.</param>
    public static Result Detect(string addonPath, string? mapName = null)
    {
        addonPath = Path.TrimEndingDirectorySeparator(Path.GetFullPath(addonPath));

        var maps = FindMaps(addonPath);
        var start = mapName == null ? maps.FirstOrDefault() : maps.Find(map => map.Equals(AddonRules.Normalize(mapName), StringComparison.OrdinalIgnoreCase));

        if (start == null)
        {
            return new Result([], [], HasCompiledMap: false);
        }

        // every file a rule could pack, which is everything the crawl can be about
        var files = AddonPackager.ListFiles(addonPath)
            .ToDictionary(file => AddonPackager.GetRelativePath(addonPath, file.FullName), file => file.FullName, StringComparer.OrdinalIgnoreCase);

        var crawl = new Crawl(files);
        crawl.ReadMap(start);

        // a map names the child maps it loads as it is read, and those name their own
        for (var i = 0; i < crawl.Maps.Count; i++)
        {
            if (i > 0)
            {
                crawl.ReadMap(crawl.Maps[i]);
            }
        }

        crawl.Finish();

        var unused = files.Keys
            .Where(path => !crawl.Used.Contains(path))
            .OrderBy(path => path, StringComparer.OrdinalIgnoreCase)
            .ToList();

        return new Result(unused, crawl.Maps, HasCompiledMap: true);
    }

    /// <summary>
    /// One run over an addon: the files it has, the ones reached so far, and the maps to read.
    /// </summary>
    private sealed class Crawl(Dictionary<string, string> files)
    {
        private readonly Queue<string> pending = new();

        /// <summary>The addon's files that something reaches.</summary>
        public HashSet<string> Used { get; } = new(StringComparer.OrdinalIgnoreCase);

        /// <summary>The maps to read, the one started from and the child maps named while reading.</summary>
        public List<string> Maps { get; } = [];

        /// <summary>Reads every resource a map's vpk holds, then follows what they reached.</summary>
        public void ReadMap(string map)
        {
            if (!Maps.Contains(map, StringComparer.OrdinalIgnoreCase))
            {
                Maps.Add(map);
            }

            Used.Add(map);

            // a map's own text and navigation files sit beside its vpk under the same name
            var beside = Path.ChangeExtension(map, null);

            foreach (var path in files.Keys.Where(path => Path.ChangeExtension(path, null).Equals(beside, StringComparison.OrdinalIgnoreCase)))
            {
                Used.Add(path);
            }

            using var package = new Package();
            package.Read(files[map]);

            foreach (var entry in (package.Entries ?? []).SelectMany(pair => pair.Value))
            {
                var path = entry.GetFullPath();

                if (!path.EndsWith("_c", StringComparison.Ordinal))
                {
                    continue;
                }

                // a map's vmap_c carries no data of its own, only a list of everything the compile consumed, which includes the static
                // props and smartprops it baked into the world. Following that list would mark the sources of baked geometry as in use
                if (path.EndsWith(".vmap_c", StringComparison.Ordinal))
                {
                    continue;
                }

                package.ReadEntry(entry, out var data);

                using var stream = new MemoryStream(data);
                Read(stream, path);
            }

            Follow();
        }

        /// <summary>Marks what is left as used: the folders and files the game loads by name, whatever the crawl reached.</summary>
        public void Finish()
        {
            // these are files of the addon already, so they are marked directly: Want passes over a name without a slash, such as addoninfo.txt in the root
            foreach (var path in files.Keys.Where(path => AlwaysUsedPaths.Any(used => path.StartsWith(used, StringComparison.OrdinalIgnoreCase))))
            {
                if (Used.Add(path) && path.EndsWith("_c", StringComparison.Ordinal))
                {
                    pending.Enqueue(path);
                }
            }

            Follow();
        }

        /// <summary>Reads what has been reached but not yet looked into, and what that reaches in turn, until nothing is left.</summary>
        private void Follow()
        {
            while (pending.Count > 0)
            {
                var path = pending.Dequeue();

                using var stream = File.OpenRead(files[path]);
                Read(stream, path);
            }
        }

        /// <summary>
        /// Takes in what a resource references. A file that cannot be read is left as it is: it stays packed, and only what it alone reaches is missed.
        /// </summary>
        private void Read(Stream stream, string name)
        {
            try
            {
                using var resource = new Resource { FileName = name };
                resource.Read(stream, verifyFileSize: false, leaveOpen: true);

                foreach (var reference in resource.ExternalReferences?.ResourceRefInfoList ?? [])
                {
                    Want(reference.Name);
                }

                if (resource.DataBlock is EntityLump lump)
                {
                    ReadEntities(lump);
                    return;
                }

                if (resource.DataBlock is Panorama script)
                {
                    ReadScript(script);
                    return;
                }

                // models, materials, particles and the world hold their key values as a typed block, everything else as a plain one
                var data = resource.DataBlock switch
                {
                    KeyValuesOrNTRO typed => typed.Data,
                    BinaryKV3 or NTRO => resource.DataBlock.AsKeyValueCollection(),
                    _ => null,
                };

                if (data != null)
                {
                    ReadKeyValues(data, 0);
                }
            }
            catch (Exception exception) when (exception is IOException or InvalidDataException or UnexpectedMagicException or NotImplementedException or ArgumentException)
            {
            }
        }

        /// <summary>
        /// Takes in what a map's entities reference. An entity lump keeps its entities as its own blocks of key values rather than as part of
        /// the resource's data, so what a prop or a sound or a post processing volume names is only found by reading them out.
        /// </summary>
        private void ReadEntities(EntityLump lump)
        {
            foreach (var entity in lump.GetEntities())
            {
                foreach (var property in entity)
                {
                    if (property.Value is not KVObject value || value.ValueType != KVValueType.String)
                    {
                        continue;
                    }

                    if (property.Key.Equals(ChildMapKey, StringComparison.OrdinalIgnoreCase))
                    {
                        WantChildMap((string)value);
                        continue;
                    }

                    Want((string)value);
                }

                // an entity can also be handed an asset by another entity firing at it, SetModel on a prop among them, which is
                // kept as a connection rather than as one of its properties
                foreach (var connection in entity.Connections ?? [])
                {
                    Want(connection.OverrideParam);
                }
            }
        }

        /// <summary>
        /// Takes in what a script names. A compiled script keeps the source as it was written rather than a list of what it uses, so the only
        /// way to see an asset it loads is to read the paths out of the text. A path the script puts together as it runs cannot be seen at all.
        /// </summary>
        private void ReadScript(Panorama script)
        {
            // a panorama layout lists the images it draws apart from its text
            foreach (var image in script.Images)
            {
                Want(image.Name);
            }

            var source = Encoding.UTF8.GetString(script.Data);

            foreach (var match in PathLike().EnumerateMatches(source))
            {
                Want(source.AsSpan(match.Index, match.Length).ToString());
            }
        }

        /// <summary>Takes in every string of a key values tree, since what a resource names is not always in its reference list.</summary>
        private void ReadKeyValues(KVObject node, int depth)
        {
            if (depth > MaxKeyValuesDepth)
            {
                return;
            }

            if (node.ValueType == KVValueType.String)
            {
                Want((string)node);
                return;
            }

            if (!node.IsCollection && !node.IsArray)
            {
                return;
            }

            foreach (var child in node.Children)
            {
                ReadKeyValues(child.Value, depth + 1);
            }
        }

        /// <summary>The map an entity names is a content path, which is packed as a vpk of the same name under the addon.</summary>
        private void WantChildMap(string name)
        {
            var map = Path.ChangeExtension(AddonRules.Normalize(name), ".vpk");

            if (files.ContainsKey(map) && !Maps.Contains(map, StringComparer.OrdinalIgnoreCase))
            {
                Maps.Add(map);
            }
        }

        /// <summary>
        /// Marks the addon file <paramref name="name"/> lands on as used, and queues it to be read. A reference names an asset as the content
        /// has it, "models/x.vmdl", where the addon holds what it compiled to, "models/x.vmdl_c". Anything that is not a path of the addon is passed over.
        /// </summary>
        private void Want(string? name)
        {
            if (string.IsNullOrEmpty(name) || !name.Contains('/', StringComparison.Ordinal))
            {
                return;
            }

            var path = AddonRules.Normalize(name).TrimStart('/');

            if (!files.ContainsKey(path + "_c") && !files.ContainsKey(path))
            {
                return;
            }

            path = files.ContainsKey(path + "_c") ? path + "_c" : path;

            if (Used.Add(path) && path.EndsWith("_c", StringComparison.Ordinal))
            {
                pending.Enqueue(path);
            }
        }
    }

    /// <summary>Anything shaped like a path, two or more parts with a slash between them, whatever else it turns out to be.</summary>
    [GeneratedRegex(@"[\w\-.]+(?:[/\\][\w\-.]+)+")]
    private static partial Regex PathLike();
}

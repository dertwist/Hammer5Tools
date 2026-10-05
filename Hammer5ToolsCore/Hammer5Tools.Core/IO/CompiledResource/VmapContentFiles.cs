using System.Text.Json.Nodes;
using Hammer5Tools.Core.Format.SmartProps;
using ValveResourceFormat;
using ValveResourceFormat.IO;
using ValveResourceFormat.ResourceTypes;

namespace Hammer5Tools.Core.IO.CompiledResource;

/// <summary>Resolves uncompiled map dependencies against an explicit content root or the map's ancestors.</summary>
internal sealed class VmapContentFiles(string mapPath, string? contentRoot, string gameDirectory = "", string activeAddon = "") : IDisposable
{
    private readonly Dictionary<string, JsonObject> documents = new(StringComparer.OrdinalIgnoreCase);
    private GameFileLoader? loader;
    public HashSet<string> Dependencies { get; } = new(StringComparer.OrdinalIgnoreCase);
    public List<string> Diagnostics { get; } = [];

    public void Dispose() => loader?.Dispose();

    public string? Resolve(string resource, string? referringMap = null)
    {
        if (Path.IsPathFullyQualified(resource) && File.Exists(resource))
        {
            return Path.GetFullPath(resource);
        }
        var relative = resource.Replace('\\', '/').TrimStart('/');
        if (!string.IsNullOrWhiteSpace(contentRoot))
        {
            var candidate = Path.Combine(contentRoot, relative);
            if (File.Exists(candidate))
            {
                return Path.GetFullPath(candidate);
            }
        }
        return ContentPathResolver.Resolve(referringMap ?? mapPath, relative);
    }

    public JsonObject ReadSmartProp(string resource, out JsonObject nested)
    {
        var root = Load(resource);
        nested = ReadSmartPropDependencies(root, resource);
        return root;
    }

    public JsonObject ReadSmartPropDependencies(JsonObject root, string? rootResource = null)
    {
        JsonObject nested = [];
        var pending = new Queue<(JsonNode Document, int Depth)>();
        var visited = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        if (rootResource is not null)
        {
            visited.Add(rootResource);
        }
        pending.Enqueue((root, 0));
        while (pending.TryDequeue(out var item))
        {
            foreach (var reference in References(item.Document))
            {
                if (!visited.Add(reference))
                {
                    continue;
                }
                if (item.Depth >= 31)
                {
                    throw new InvalidDataException("SmartProp dependency nesting exceeds 32 levels.");
                }
                JsonObject child;
                try
                {
                    child = Load(reference);
                }
                catch (Exception error) when (error is IOException or System.Text.Json.JsonException or InvalidDataException or KeyNotFoundException)
                {
                    Diagnostics.Add($"{reference}: {error.Message}");
                    continue;
                }
                nested[reference.Replace('\\', '/')] = child;
                pending.Enqueue((child, item.Depth + 1));
            }
        }
        return nested;
    }

    private JsonObject Load(string resource)
    {
        if (documents.TryGetValue(resource, out var cached))
            return (JsonObject)cached.DeepClone();
        var path = Resolve(resource);
        string json;
        if (path is not null && !path.EndsWith("_c", StringComparison.OrdinalIgnoreCase))
        {
            Dependencies.Add(path);
            json = SmartPropDocumentSerializer.DeserializeText(File.ReadAllText(path));
        }
        else
        {
            using var compiled = ReadCompiled(path ?? resource);
            if (compiled?.DataBlock is not SmartProp smartProp)
                throw new FileNotFoundException($"SmartProp source or compiled resource not found: {resource}");
            json = SmartPropDocumentSerializer.DeserializeRoot(smartProp.Data.Root);
        }
        var document = JsonNode.Parse(json) as JsonObject
            ?? throw new InvalidDataException($"SmartProp source is not an object: {resource}");
        documents[resource] = document;
        return (JsonObject)document.DeepClone();
    }

    private Resource? ReadCompiled(string resource)
    {
        var compiledPath = resource.EndsWith("_c", StringComparison.OrdinalIgnoreCase) ? resource : resource + "_c";
        var path = Resolve(compiledPath);
        if (path is not null)
        {
            Dependencies.Add(path);
            var result = new Resource();
            try
            {
                result.Read(path);
                return result;
            }
            catch
            {
                result.Dispose();
                throw;
            }
        }
        if (string.IsNullOrWhiteSpace(gameDirectory))
            return null;
        if (loader is null)
        {
            // VRF skips the current file's VPK, expecting CurrentPackage to already own it.
            loader = new GameFileLoader(null, Path.Combine(gameDirectory, "csgo", "gameinfo.gi"));
            var addon = Path.Combine(gameDirectory, "csgo_addons", activeAddon);
            if (Directory.Exists(addon))
                loader.AddDiskPathToSearch(addon);
        }
        return loader.LoadFileCompiled(resource.Replace('\\', '/'));
    }

    private static IEnumerable<string> References(JsonNode node)
    {
        if (node is JsonObject obj)
        {
            foreach (var (key, value) in obj)
            {
                if (key == "m_sSmartProp" && value is JsonValue text && text.TryGetValue<string>(out var path)
                    && !string.IsNullOrWhiteSpace(path))
                {
                    yield return path;
                }
                else if (value is not null)
                {
                    foreach (var reference in References(value))
                    {
                        yield return reference;
                    }
                }
            }
        }
        else if (node is JsonArray array)
        {
            foreach (var value in array)
            {
                if (value is null)
                {
                    continue;
                }
                foreach (var reference in References(value))
                {
                    yield return reference;
                }
            }
        }
    }
}

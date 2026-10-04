using System.Text.Json.Nodes;
using Hammer5Tools.Core.Format.SmartProps;
using Hammer5Tools.Core.Format.Vmap;

namespace Hammer5Tools.Core.IO.CompiledResource;

/// <summary>Resolves uncompiled map dependencies against an explicit content root or the map's ancestors.</summary>
internal sealed class VmapContentFiles(string mapPath, string? contentRoot)
{
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
        return ValveMapSceneReader.ResolveContentRelative(referringMap ?? mapPath, relative);
    }

    public JsonObject ReadSmartProp(string resource, out JsonObject nested)
    {
        nested = [];
        var root = Load(resource);
        var pending = new Queue<(JsonNode Document, int Depth)>();
        var visited = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { resource };
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
                var child = Load(reference);
                nested[reference.Replace('\\', '/')] = child;
                pending.Enqueue((child, item.Depth + 1));
            }
        }
        return root;
    }

    private JsonObject Load(string resource)
    {
        var path = Resolve(resource) ?? throw new FileNotFoundException($"SmartProp source not found: {resource}");
        return JsonNode.Parse(SmartPropDocumentSerializer.DeserializeText(File.ReadAllText(path))) as JsonObject
            ?? throw new InvalidDataException($"SmartProp source is not an object: {resource}");
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

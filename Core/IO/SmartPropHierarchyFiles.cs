using System.Text.Json.Nodes;
using Hammer5Tools.Core.Format.SmartProps;

namespace Hammer5Tools.Core.IO;

internal static class SmartPropHierarchyFiles
{
    public static string Import(string json, string[] target, string[] paths, string gameDirectory)
    {
        var children = new JsonArray();
        foreach (var path in paths)
        {
            var extension = Path.GetExtension(path).ToLowerInvariant();
            if (extension is not ".vmdl" and not ".vsmart")
            {
                continue;
            }
            var normalized = Path.GetFullPath(path).Replace('\\', '/');
            var roots = new List<string>();
            if (!string.IsNullOrWhiteSpace(gameDirectory))
            {
                var game = Path.GetFullPath(gameDirectory);
                roots.Add(Path.Combine(game, "csgo"));
                var content = Path.Combine(Directory.GetParent(game)?.FullName ?? game, "content");
                roots.Add(Path.Combine(content, "csgo"));
                var addons = Path.Combine(content, "csgo_addons");
                if (Directory.Exists(addons))
                {
                    roots.AddRange(Directory.EnumerateDirectories(addons));
                }
            }
            var root = roots.Select(value => value.Replace('\\', '/').TrimEnd('/') + '/').FirstOrDefault(value => normalized.StartsWith(value, StringComparison.OrdinalIgnoreCase));
            if (root is null)
            {
                throw new InvalidDataException($"The asset is outside the CS2 content folders: {path}");
            }
            children.Add(new JsonObject
            {
                ["_class"] = extension == ".vmdl" ? "CSmartPropElement_Model" : "CSmartPropElement_SmartProp",
                ["m_sLabel"] = Path.GetFileNameWithoutExtension(path),
                [extension == ".vmdl" ? "m_sModelName" : "m_sSmartProp"] = normalized[root.Length..],
                ["m_Modifiers"] = new JsonArray(),
                ["m_SelectionCriteria"] = new JsonArray(),
                ["m_bEnabled"] = true
            });
        }
        if (children.Count == 0)
        {
            throw new InvalidDataException("Drop .vmdl or .vsmart source assets.");
        }
        var fragment = JsonNode.Parse(SmartPropEditorDocument.Create())!.AsObject();
        fragment["m_Children"] = children;
        var request = new JsonObject
        {
            ["action"] = "paste",
            ["target"] = new JsonArray(target.Select(segment => (JsonNode?)JsonValue.Create(segment)).ToArray()),
            ["text"] = SmartPropDocumentSerializer.SerializeJson(fragment.ToJsonString())
        };
        return SmartPropEditorDocument.Edit(json, [], "hierarchy", request.ToJsonString());
    }
}

using System.Globalization;
using System.Text.Json.Nodes;

namespace Hammer5Tools.Core.Format.SmartProps;

internal static class SmartPropHierarchyDocument
{
    public static string Copy(string json, string[][] paths)
    {
        var root = JsonNode.Parse(SmartPropEditorDocument.Validate(json))!.AsObject();
        var nodes = Selected(root, paths);
        var clipboard = JsonNode.Parse(SmartPropEditorDocument.Create())!.AsObject();
        clipboard["m_Children"] = new JsonArray(nodes.Select(node => node.DeepClone()).ToArray());
        return SmartPropDocumentSerializer.SerializeJson(clipboard.ToJsonString());
    }

    public static string Edit(JsonObject root, string requestJson)
    {
        var request = JsonNode.Parse(requestJson)?.AsObject() ?? throw new InvalidDataException("Missing hierarchy request.");
        var action = request["action"]?.GetValue<string>();
        var paths = request["paths"]?.AsArray().Select(item => item!.AsArray().Select(segment => segment!.GetValue<string>()).ToArray()).ToArray() ?? [];
        var selected = Selected(root, paths);
        var targetPath = request["target"]?.AsArray().Select(segment => segment!.GetValue<string>()).ToArray() ?? [];
        var target = Resolve(root, targetPath);
        var nextId = All(root).Select(node => node["m_nElementID"]?.GetValue<int>() ?? -1).DefaultIfEmpty(-1).Max();
        nextId = checked(nextId + 1);
        switch (action)
        {
            case "remove":
                foreach (var node in selected)
                {
                    node.AsArrayParent().Remove(node);
                }
                break;
            case "duplicate":
                foreach (var node in selected)
                {
                    var copy = node.DeepClone();
                    AssignIds(copy, ref nextId);
                    var siblings = node.AsArrayParent();
                    siblings.Insert(siblings.IndexOf(node) + 1, copy);
                }
                break;
            case "up":
            case "down":
                foreach (var node in action == "down" ? selected.AsEnumerable().Reverse() : selected)
                {
                    var siblings = node.AsArrayParent();
                    var index = siblings.IndexOf(node);
                    var destination = index + (action == "up" ? -1 : 1);
                    if (destination >= 0 && destination < siblings.Count && !selected.Contains(siblings[destination]))
                    {
                        siblings.RemoveAt(index);
                        siblings.Insert(destination, node);
                    }
                }
                break;
            case "group":
                if (selected.Count == 0)
                {
                    break;
                }
                var group = new JsonObject
                {
                    ["_class"] = "CSmartPropElement_Group",
                    ["m_sLabel"] = "Group",
                    ["m_nElementID"] = nextId,
                    ["m_bEnabled"] = true,
                    ["m_Modifiers"] = new JsonArray(),
                    ["m_SelectionCriteria"] = new JsonArray(),
                    ["m_Children"] = new JsonArray()
                };
                foreach (var node in selected)
                {
                    node.AsArrayParent().Remove(node);
                    group["m_Children"]!.AsArray().Add(node);
                }
                Children(root).Add(group);
                break;
            case "rename":
                target["m_sLabel"] = request["label"]?.GetValue<string>() ?? "";
                break;
            case "move":
                var position = request["position"]?.GetValue<string>() ?? "inside";
                var owner = position == "inside" ? target : target.AsArrayParent().Parent!.AsObject();
                if (IsLeaf(owner))
                {
                    throw new InvalidDataException("Model and SmartProp elements cannot contain children.");
                }
                if (selected.Any(node => ReferenceEquals(node, target) || All(node).Any(descendant => ReferenceEquals(descendant, owner))))
                {
                    throw new InvalidDataException("Cannot move an element onto itself or into its descendants.");
                }
                var destinationChildren = Children(owner);
                var insertion = position == "inside" ? destinationChildren.Count : destinationChildren.IndexOf(target) + (position == "after" ? 1 : 0);
                var copies = request["copy"]?.GetValue<bool>() == true;
                foreach (var node in selected)
                {
                    JsonNode moved = node;
                    if (copies)
                    {
                        moved = node.DeepClone();
                        AssignIds(moved, ref nextId);
                    }
                    else
                    {
                        var oldParent = node.AsArrayParent();
                        if (ReferenceEquals(oldParent, destinationChildren) && oldParent.IndexOf(node) < insertion)
                        {
                            insertion--;
                        }
                        oldParent.Remove(node);
                    }
                    destinationChildren.Insert(insertion++, moved);
                }
                break;
            case "paste":
                var clipboard = JsonNode.Parse(SmartPropDocumentSerializer.DeserializeText(request["text"]!.GetValue<string>()))!.AsObject();
                clipboard["generic_data_type"] ??= "CSmartPropRoot";
                SmartPropEditorDocument.Validate(clipboard.ToJsonString());
                var pasted = clipboard["m_Children"] as JsonArray ?? throw new InvalidDataException("The clipboard contains no hierarchy elements.");
                var pasteOwner = SafeOwner(root, target);
                foreach (var node in pasted.OfType<JsonObject>())
                {
                    var copy = node.DeepClone();
                    AssignIds(copy, ref nextId);
                    Children(pasteOwner).Add(copy);
                }
                break;
            case "add":
                var className = request["class"]!.GetValue<string>();
                if (!className.StartsWith("CSmartPropElement_", StringComparison.Ordinal))
                {
                    throw new InvalidDataException("Choose an element class.");
                }
                var ownerPath = PathOf(SafeOwner(root, target));
                return SmartPropEditorDocument.Edit(root.ToJsonString(), ownerPath, "add-component", JsonValue.Create(className)!.ToJsonString());
            default:
                throw new InvalidDataException($"Unknown hierarchy action: {action}");
        }
        return SmartPropEditorDocument.Validate(root.ToJsonString());
    }

    private static void AssignIds(JsonNode node, ref int next)
    {
        foreach (var element in All(node))
        {
            if (element["_class"]?.ToString().StartsWith("CSmartProp", StringComparison.Ordinal) == true)
            {
                element["m_nElementID"] = next;
                next = checked(next + 1);
            }
        }
    }

    private static List<JsonObject> Selected(JsonObject root, string[][] paths)
    {
        var requested = paths.Where(path => path.Length > 0).Select(path => Resolve(root, path)).Distinct().ToHashSet();
        return Hierarchy(root).Where(node => requested.Contains(node) && !Parents(node).Any(requested.Contains)).ToList();
    }

    private static IEnumerable<JsonObject> Hierarchy(JsonObject node)
    {
        if (node["m_Children"] is JsonArray children)
        {
            foreach (var child in children.OfType<JsonObject>())
            {
                yield return child;
                foreach (var descendant in Hierarchy(child))
                {
                    yield return descendant;
                }
            }
        }
    }

    private static IEnumerable<JsonObject> Parents(JsonObject node)
    {
        for (var parent = node.Parent; parent is not null; parent = parent.Parent)
        {
            if (parent is JsonObject obj)
            {
                yield return obj;
            }
        }
    }

    private static IEnumerable<JsonObject> All(JsonNode node)
    {
        if (node is JsonObject obj)
        {
            yield return obj;
        }
        var values = node is JsonObject dict ? dict.Select(pair => pair.Value) : node is JsonArray array ? array : [];
        foreach (var value in values.OfType<JsonNode>())
        {
            foreach (var child in All(value))
            {
                yield return child;
            }
        }
    }

    private static JsonObject Resolve(JsonObject root, string[] path)
    {
        JsonObject node = root;
        if (path.Length % 2 != 0)
        {
            throw new InvalidDataException("Invalid hierarchy path.");
        }
        for (var index = 0; index < path.Length; index += 2)
        {
            if (path[index] != "m_Children" || !int.TryParse(path[index + 1], NumberStyles.None, CultureInfo.InvariantCulture, out var childIndex)
                || node["m_Children"] is not JsonArray children || childIndex >= children.Count || children[childIndex] is not JsonObject child)
            {
                throw new InvalidDataException("The hierarchy element no longer exists.");
            }
            node = child;
        }
        return node;
    }

    private static string[] PathOf(JsonObject node)
    {
        List<string> path = [];
        for (var current = node; current.Parent is JsonArray array; current = array.Parent!.AsObject())
        {
            path.InsertRange(0, ["m_Children", array.IndexOf(current).ToString(CultureInfo.InvariantCulture)]);
        }
        return path.ToArray();
    }

    private static bool IsLeaf(JsonObject node) => node["_class"]?.ToString() is "CSmartPropElement_Model" or "CSmartPropElement_SmartProp";
    private static JsonObject SafeOwner(JsonObject root, JsonObject target) => IsLeaf(target) ? target.Parent?.Parent?.AsObject() ?? root : target;
    private static JsonArray Children(JsonObject node)
    {
        node["m_Children"] ??= new JsonArray();
        return node["m_Children"]!.AsArray();
    }

    private static JsonArray AsArrayParent(this JsonObject node) => node.Parent as JsonArray ?? throw new InvalidDataException("Select a hierarchy element.");
}

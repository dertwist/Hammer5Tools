using System.Text.Json;
using System.Text.Json.Nodes;

namespace Hammer5Tools.Core.Format.SmartProps;

internal static class SmartPropEditorDocument
{
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };

    public static string Create() => """
        {
          "generic_data_type": "CSmartPropRoot",
          "m_Children": [],
          "m_Variables": [],
          "m_Choices": []
        }
        """;

    public static string Validate(string json)
    {
        var root = JsonNode.Parse(json) as JsonObject
            ?? throw new InvalidDataException("A SmartProp document must be an object.");
        if ((root["generic_data_type"] ?? root["_class"])?.GetValue<string>() != "CSmartPropRoot")
        {
            throw new InvalidDataException("Expected a CSmartPropRoot document.");
        }
        foreach (var key in new[] { "m_Children", "m_Variables", "m_Choices" })
        {
            if (root[key] is not null and not JsonArray)
            {
                throw new InvalidDataException($"{key} must be an array.");
            }
        }
        ValidateChildren(root["m_Children"] as JsonArray);
        return root.ToJsonString(JsonOptions);
    }

    public static string Edit(string json, string[] path, string operation, string valueJson)
    {
        var root = JsonNode.Parse(Validate(json))!;
        if (operation == "hierarchy")
        {
            return SmartPropHierarchyDocument.Edit(root.AsObject(), valueJson);
        }
        if (operation == "replace" && path.Length == 0)
        {
            return Validate(valueJson);
        }
        var target = Resolve(root, path);
        switch (operation)
        {
            case "add-component":
            case "paste-component":
                var componentOwner = target as JsonObject ?? throw new InvalidDataException("Select an element to add a component.");
                var payload = JsonNode.Parse(valueJson);
                var className = operation == "paste-component" ? payload?["_class"]?.GetValue<string>() : payload?.GetValue<string>();
                if (className is null)
                {
                    throw new InvalidDataException("Choose a component class.");
                }
                using (var stream = typeof(SmartPropEditorDocument).Assembly.GetManifestResourceStream("SmartPropEditorTemplates")!)
                using (var reader = new StreamReader(stream))
                {
                    var templates = JsonNode.Parse(reader.ReadToEnd())!.AsObject();
                    var template = templates[className]?.DeepClone().AsObject() ?? throw new InvalidDataException($"Unknown SmartProp component: {className}");
                    if (operation == "paste-component")
                    {
                        template = payload!.DeepClone().AsObject();
                    }
                    var componentKey = className.StartsWith("CSmartPropElement_", StringComparison.Ordinal) ? "m_Children"
                        : className.StartsWith("CSmartPropSelectionCriteria_", StringComparison.Ordinal) ? "m_SelectionCriteria" : "m_Modifiers";
                    var nextComponentId = NextId(root);
                    ReassignIds(template, ref nextComponentId);
                    template["m_nElementID"] ??= nextComponentId;
                    template["m_bEnabled"] ??= true;
                    var components = componentOwner[componentKey] as JsonArray ?? new JsonArray();
                    componentOwner[componentKey] = components;
                    components.Add(template);
                }
                break;
            case "replace":
                var parent = target?.Parent ?? throw new InvalidDataException("Cannot replace a missing value.");
                var value = JsonNode.Parse(valueJson);
                if (parent is JsonArray array)
                {
                    array[array.IndexOf(target)] = value;
                }
                else
                {
                    parent[path[^1]] = value;
                }
                break;
            case "add-group":
            case "add-model":
                var owner = target as JsonObject ?? throw new InvalidDataException("Select an element or the document.");
                var children = owner["m_Children"] as JsonArray;
                if (children is null)
                {
                    children = [];
                    owner["m_Children"] = children;
                }
                var model = operation == "add-model";
                var element = new JsonObject
                {
                    ["_class"] = model ? "CSmartPropElement_Model" : "CSmartPropElement_Group",
                    ["m_sLabel"] = model ? "Model" : "Group",
                    ["m_nElementID"] = NextId(root),
                    ["m_bEnabled"] = true,
                    ["m_Modifiers"] = new JsonArray(),
                    ["m_SelectionCriteria"] = new JsonArray()
                };
                if (model)
                {
                    element["m_sModelName"] = "";
                }
                children.Add(element);
                break;
            case "duplicate":
            case "remove":
            case "up":
            case "down":
                var siblings = target?.Parent as JsonArray
                    ?? throw new InvalidDataException("Select an element in the hierarchy.");
                var index = siblings.IndexOf(target);
                if (operation == "remove")
                {
                    siblings.RemoveAt(index);
                }
                else if (operation == "duplicate")
                {
                    var clone = target!.DeepClone();
                    var next = NextId(root);
                    ReassignIds(clone, ref next);
                    siblings.Insert(index + 1, clone);
                }
                else
                {
                    var destination = index + (operation == "up" ? -1 : 1);
                    if (destination >= 0 && destination < siblings.Count)
                    {
                        siblings.RemoveAt(index);
                        siblings.Insert(destination, target);
                    }
                }
                break;
            default:
                throw new ArgumentException($"Unknown editor operation: {operation}", nameof(operation));
        }
        return Validate(root.ToJsonString(JsonOptions));
    }

    private static JsonNode? Resolve(JsonNode root, IEnumerable<string> path)
    {
        JsonNode? node = root;
        foreach (var segment in path)
        {
            node = node is JsonArray array
                ? array[int.Parse(segment, System.Globalization.CultureInfo.InvariantCulture)]
                : node?[segment];
        }
        return node;
    }

    private static void ValidateChildren(JsonArray? children)
    {
        if (children is null)
        {
            return;
        }
        foreach (var child in children)
        {
            if (child is not JsonObject element || element["_class"] is not JsonValue classValue || !classValue.TryGetValue<string>(out _))
            {
                throw new InvalidDataException("Every hierarchy element must be an object with a _class.");
            }
            if (element["m_nElementID"] is not null && (element["m_nElementID"] is not JsonValue id || !id.TryGetValue<int>(out _)))
            {
                throw new InvalidDataException("Element IDs must be integers.");
            }
            if (element["m_Children"] is not null and not JsonArray)
            {
                throw new InvalidDataException("Element m_Children must be an array.");
            }
            ValidateChildren(element["m_Children"] as JsonArray);
        }
    }

    private static int NextId(JsonNode root)
    {
        var maximum = -1;
        Visit(root, node =>
        {
            if (node["m_nElementID"] is JsonValue value && value.TryGetValue<int>(out var id))
            {
                maximum = Math.Max(maximum, id);
            }
        });
        return checked(maximum + 1);
    }

    private static void ReassignIds(JsonNode node, ref int next)
    {
        // Duplicate ordinary elements only; reference IDs keep their original targets.
        var current = next;
        Visit(node, value =>
        {
            if (value.ContainsKey("m_nElementID"))
            {
                value["m_nElementID"] = current;
                current = checked(current + 1);
            }
        });
        next = current;
    }

    private static void Visit(JsonNode? node, Action<JsonObject> action)
    {
        if (node is JsonObject obj)
        {
            action(obj);
            foreach (var child in obj.ToArray())
            {
                Visit(child.Value, action);
            }
        }
        else if (node is JsonArray array)
        {
            foreach (var child in array)
            {
                Visit(child, action);
            }
        }
    }
}

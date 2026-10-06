using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Hammer5Tools.Core.IO.Automation;
using Hammer5Tools.Core.IO.Vpk;
using ValveKeyValue;
using ValveResourceFormat.Serialization.KeyValues;

namespace Hammer5Tools.Core.Format.Authoring;

internal static class SourceAssetAuthoring
{
    private sealed record Prepared(string Path, string Content, bool Changed, JsonArray Fields, int FieldCount);

    internal static JsonObject Batch(JsonElement request, string format, Func<string, string, string?>? replace = null)
    {
        lock (SafeAssetWrites.Sync)
        {
            var addonRoot = CompilerService.Text(request, "addon_root");
            var hasItems = request.TryGetProperty("items", out var items);
            var hasManifest = request.TryGetProperty("manifest", out var manifest);
            if (hasItems == hasManifest) throw new ArgumentException("Specify exactly one of items or manifest.");
            using var manifestDocument = hasManifest ? JsonDocument.Parse(File.ReadAllText(AssetPathResolver.Resolve(manifest.GetString()!, addonRoot))) : null;
            var rows = (manifestDocument?.RootElement ?? items).EnumerateArray().ToArray();
            if (rows.Length == 0) throw new ArgumentException("items must not be empty.");
            var prepared = rows.Select(item => Prepare(item, format, addonRoot, CompilerService.Flag(request, "overwrite"))).ToArray();
            if (prepared.Select(item => item.Path).Distinct(StringComparer.OrdinalIgnoreCase).Count() != prepared.Length)
                throw new ArgumentException("Duplicate destination paths.");
            var destinations = prepared.Select(item => item.Path).ToHashSet(StringComparer.OrdinalIgnoreCase);
            using var resources = OpenResources(CompilerService.Text(request, "cs2_path"));
            foreach (var item in rows) ValidateReferences(item, format, addonRoot, destinations, resources);
            var dryRun = CompilerService.Flag(request, "dry_run");
            var staged = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            var results = new JsonArray();
            var changed = 0;
            var skipped = 0;
            var failed = 0;
            try
            {
                if (!dryRun)
                {
                    foreach (var item in prepared.Where(item => item.Changed))
                        staged[item.Path] = SafeAssetWrites.Stage(item.Path, path => File.WriteAllText(path, item.Content, new UTF8Encoding(false)), path => _ = Read(path, format));
                }
                foreach (var item in prepared)
                {
                    var row = new JsonObject
                    {
                        ["path"] = item.Path.Replace('\\', '/'),
                        ["fields"] = item.Fields.DeepClone(),
                        ["field_count"] = item.FieldCount,
                        ["fields_truncated"] = item.FieldCount > item.Fields.Count
                    };
                    if (!item.Changed)
                    {
                        skipped++;
                        row["status"] = "skipped";
                    }
                    else if (dryRun)
                    {
                        changed++;
                        row["status"] = "would_change";
                    }
                    else
                    {
                        try
                        {
                            row["backup"] = (replace ?? SafeAssetWrites.Replace)(staged[item.Path], item.Path);
                            changed++;
                            row["status"] = "changed";
                        }
                        catch (Exception exception)
                        {
                            failed++;
                            row["status"] = "failed";
                            row["error"] = exception.Message;
                        }
                    }
                    if (results.Count < 50) results.Add(row);
                }
                return new JsonObject
                {
                    ["dry_run"] = dryRun,
                    ["changed"] = changed,
                    ["skipped"] = skipped,
                    ["failed"] = failed,
                    ["total"] = prepared.Length,
                    ["results"] = results,
                    ["truncated"] = prepared.Length > 50,
                    ["atomicity"] = "per-file replacement; batch has no rollback"
                };
            }
            finally
            {
                foreach (var path in staged.Values) File.Delete(path);
            }
        }
    }

    internal static JsonObject Single(JsonElement request, string format)
    {
        var item = JsonNode.Parse(request.GetRawText())!.AsObject();
        var action = item["action"]?.GetValue<string>() ?? "create";
        item["action"] = action;
        // Single-item calls retain their existing permissive resource-reference contract.
        lock (SafeAssetWrites.Sync)
        {
            using var itemDocument = JsonDocument.Parse(item.ToJsonString(AutomationJsonContext.Default.Options));
            var prepared = Prepare(itemDocument.RootElement, format, CompilerService.Text(request, "addon_root"), true);
            var dryRun = CompilerService.Flag(request, "dry_run");
            string? backup = null;
            if (!dryRun && prepared.Changed)
            {
                var staged = SafeAssetWrites.Stage(prepared.Path, path => File.WriteAllText(path, prepared.Content, new UTF8Encoding(false)), path => _ = Read(path, format));
                try
                {
                    backup = SafeAssetWrites.Replace(staged, prepared.Path);
                }
                finally
                {
                    File.Delete(staged);
                }
            }
            var result = new JsonObject
            {
                ["path"] = prepared.Path.Replace('\\', '/'),
                ["dry_run"] = dryRun,
                ["action"] = (action == "update" ? "edit_" : "write_") + format,
                ["modified_keys"] = prepared.Fields.DeepClone(),
                ["modified_fields"] = prepared.Fields.DeepClone(),
                ["modified_count"] = prepared.FieldCount,
                ["fields_truncated"] = prepared.FieldCount > prepared.Fields.Count,
                ["content_length"] = prepared.Content.Length,
                ["content_utf8_bytes"] = Encoding.UTF8.GetByteCount(prepared.Content),
                ["changed"] = prepared.Changed,
                ["backup"] = backup
            };
            if (format == "vmat")
            {
                using var contentStream = new MemoryStream(Encoding.UTF8.GetBytes(prepared.Content));
                result["shader"] = KVSerializer.Create(KVSerializationFormat.KeyValues1Text).Deserialize(contentStream).Root["shader"].ToString(null);
                result["slots_count"] = Count(request, "slots");
                result["parameters_count"] = Count(request, "parameters");
                result["flags_count"] = Count(request, "flags");
            }
            else if (action == "create")
            {
                result["mesh"] = request.GetProperty("mesh_rel_path").GetString()!.Replace('\\', '/');
                result["import_scale"] = Scale(request);
                result["material_remaps_count"] = Count(request, "material_remaps");
            }
            return result;
        }
    }

    private static int Count(JsonElement request, string key) => request.TryGetProperty(key, out var value)
        ? value.ValueKind == JsonValueKind.Array ? value.GetArrayLength()
        : value.ValueKind == JsonValueKind.Object ? value.EnumerateObject().Count() : 0 : 0;

    private static Prepared Prepare(JsonElement item, string format, string? root, bool overwrite)
    {
        var action = CompilerService.Text(item, "action") ?? "create";
        if (action is not ("create" or "update")) throw new ArgumentException("action must be create or update.");
        var path = AssetPathResolver.Resolve(item.GetProperty("path").GetString()!, root, action == "update");
        if (!path.EndsWith("." + format, StringComparison.OrdinalIgnoreCase)) throw new ArgumentException($"Destination must be .{format}");
        if (action == "create" && File.Exists(path) && !overwrite) throw new IOException($"Destination exists; set overwrite: '{path}'.");
        var document = action == "update" ? Read(path, format) : KVObject.Collection();
        var before = action == "update" ? Serialize(document, format) : null;
        var fields = new JsonArray();
        if (format == "vmat") ApplyMaterial(document, item, action, fields);
        else ApplyModel(document, item, action, fields);
        var content = Serialize(document, format);
        var distinctFields = fields.Select(field => field!.GetValue<string>()).Distinct(StringComparer.Ordinal).ToArray();
        return new Prepared(path, content, before != content, CompilerService.Strings(distinctFields.Take(50)), distinctFields.Length);
    }

    private static KVObject Read(string path, string format)
    {
        using var stream = File.OpenRead(path);
        return format == "vmat" ? KVSerializer.Create(KVSerializationFormat.KeyValues1Text).Deserialize(stream).Root
            : KVDocumentExtensions.ParseKV3(stream).Root;
    }

    private static string Serialize(KVObject document, string format)
    {
        if (format == "vmdl")
        {
            var text = document.ToKV3String();
            var body = text.IndexOf('\n');
            return "<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc41:version{12fc9d44-453a-4ae4-b4d9-7e2ac0bbd4e0} -->" + text[body..];
        }
        using var output = new MemoryStream();
        KVSerializer.Create(KVSerializationFormat.KeyValues1Text).Serialize(output, document, "Layer0");
        return Encoding.UTF8.GetString(output.ToArray());
    }

    private static void ApplyMaterial(KVObject document, JsonElement item, string action, JsonArray fields)
    {
        if (action == "create")
        {
            document["shader"] = CompilerService.Text(item, "shader") ?? "csgo_environment.vfx";
            fields.Add(JsonValue.Create("shader"));
        }
        else if (item.TryGetProperty("shader", out var shader) && shader.ValueKind != JsonValueKind.Null)
        {
            document["shader"] = shader.GetString()!;
            fields.Add(JsonValue.Create("shader"));
        }
        foreach (var key in action == "create" ? new List<string> { "slots", "parameters", "flags", "system_attributes", "attributes" } : ["set_slots", "set_parameters", "set_flags"])
        {
            if (!item.TryGetProperty(key, out var properties) || properties.ValueKind == JsonValueKind.Null) continue;
            var target = document;
            if (key is "system_attributes" or "attributes")
            {
                var name = key == "system_attributes" ? "SystemAttributes" : "Attributes";
                document[name] = target = KVObject.Collection();
            }
            foreach (var property in properties.EnumerateObject())
            {
                var value = property.Value.ValueKind == JsonValueKind.String ? property.Value.GetString()! : property.Value.GetRawText();
                if (key.Contains("slots", StringComparison.Ordinal)) value = value.Replace('\\', '/');
                target[property.Name] = value;
                fields.Add(JsonValue.Create(property.Name));
            }
        }
        if (item.TryGetProperty("remove_keys", out var remove) && remove.ValueKind != JsonValueKind.Null)
            foreach (var key in remove.EnumerateArray())
            {
                if (document.Remove(key.GetString()!)) fields.Add(JsonValue.Create(key.GetString()!));
            }
    }

    private static void ApplyModel(KVObject document, JsonElement item, string action, JsonArray fields)
    {
        KVObject children;
        if (action == "create")
        {
            var node = KVObject.Collection();
            node["_class"] = "RootNode";
            node["children"] = children = KVObject.Array();
            node["model_archetype"] = ""; node["primary_associated_entity"] = ""; node["anim_graph_name"] = "";
            document["rootNode"] = node;
            foreach (var kind in CompilerService.Flag(item, "physics") || !item.TryGetProperty("physics", out _) ? new List<string> { "RenderMeshList", "PhysicsShapeList" } : ["RenderMeshList"])
            {
                var mesh = KVObject.Collection();
                mesh["_class"] = kind == "RenderMeshList" ? "RenderMeshFile" : "PhysicsHullFile";
                mesh["name"] = kind == "RenderMeshList" ? "mesh0" : Path.GetFileNameWithoutExtension(item.GetProperty("mesh_rel_path").GetString())!;
                mesh["filename"] = item.GetProperty("mesh_rel_path").GetString()!.Replace('\\', '/');
                mesh["import_scale"] = Scale(item);
                mesh["import_filter"] = KVObject.Collection(); mesh["import_filter"]["exclude_by_default"] = false;
                mesh["import_filter"]["exception_list"] = KVObject.Array();
                if (kind == "PhysicsShapeList")
                {
                    mesh["surface_prop"] = "default";
                    mesh["collision_prop"] = "default";
                }
                var group = KVObject.Collection(); group["_class"] = kind; group["children"] = KVObject.Array([mesh]); children.Add(group);
            }
        }
        else children = document["rootNode"]["children"];
        var updates = item.TryGetProperty("updates", out var changes) ? changes : item;
        if (action == "update")
            foreach (var group in children.AsArraySpan())
                if (group["_class"].ToString(null) is "RenderMeshList" or "PhysicsShapeList")
                    foreach (var mesh in group["children"].AsArraySpan())
                    {
                        if (updates.TryGetProperty("import_scale", out _)) mesh["import_scale"] = Scale(updates);
                        if (updates.TryGetProperty("mesh_rel_path", out var filename)) mesh["filename"] = filename.GetString()!.Replace('\\', '/');
                    }
        if (updates.TryGetProperty("material_remaps", out var remaps) && remaps.ValueKind != JsonValueKind.Null || action == "create")
        {
            KVObject? material = null;
            foreach (var group in children.AsArraySpan())
                if (group["_class"].ToString(null) == "MaterialGroupList")
                    foreach (var child in group["children"].AsArraySpan())
                        if (child["_class"].ToString(null) == "DefaultMaterialGroup") material = child;
            if (material is null)
            {
                material = KVObject.Collection(); material["_class"] = "DefaultMaterialGroup";
                material["use_global_default"] = false; material["global_default_material"] = "";
                var group = KVObject.Collection(); group["_class"] = "MaterialGroupList"; group["children"] = KVObject.Array([material]); children.Add(group);
            }
            material["remaps"] = remaps.ValueKind == JsonValueKind.Array ? SmartProps.SmartPropJsonConverter.Convert(remaps.GetRawText()) : KVObject.Array();
        }
        foreach (var property in updates.EnumerateObject()) fields.Add(JsonValue.Create(property.Name));
    }

    private static float Scale(JsonElement item)
    {
        var scale = item.TryGetProperty("import_scale", out var value) ? value.GetSingle() : 1f;
        if (!float.IsFinite(scale) || scale == 0) throw new ArgumentException("import_scale must be finite and nonzero.");
        return scale;
    }

    private static VpkIndex OpenResources(string? cs2Path)
    {
        var index = new VpkIndex();
        if (cs2Path is null) return index;
        foreach (var name in new List<string> { "csgo", "csgo_core", "csgo_imported", "csgo_lv", "core" })
            index.MountVpk(Path.Combine(cs2Path, "game", name, "pak01_dir.vpk"));
        index.AddLooseRoot(Path.Combine(cs2Path, "content", "csgo"));
        index.AddLooseRoot(Path.Combine(cs2Path, "content", "core"));
        return index;
    }

    private static void ValidateReferences(JsonElement item, string format, string? root, HashSet<string> destinations, VpkIndex resources)
    {
        var updates = item.TryGetProperty("updates", out var value) ? value : item;
        var references = new List<string>();
        if (format == "vmat")
        {
            foreach (var key in new List<string> { "slots", "set_slots" })
                if (updates.TryGetProperty(key, out var slots)) references.AddRange(slots.EnumerateObject().Select(slot => slot.Value.GetString()!));
        }
        else
        {
            if (updates.TryGetProperty("mesh_rel_path", out var mesh)) references.Add(mesh.GetString()!);
            if (updates.TryGetProperty("material_remaps", out var remaps))
                references.AddRange(remaps.EnumerateArray().Select(remap => remap.GetProperty("to").GetString()!));
        }
        foreach (var reference in references)
        {
            string? path = null;
            if (Path.IsPathFullyQualified(reference) || root is not null)
                path = AssetPathResolver.Resolve(reference, root, false);
            else if (Path.IsPathRooted(reference) || reference.Contains(':') || reference.Replace('\\', '/').Split('/').Contains(".."))
                throw new ArgumentException("Resource reference must be absolute or remain addon-relative.");
            if (path is not null && (File.Exists(path) || destinations.Contains(path))) continue;
            var resource = reference.Replace('\\', '/');
            if (!Path.IsPathRooted(resource) && (resources.Exists(resource) || resources.Exists(resource + "_c"))) continue;
            throw new FileNotFoundException("Referenced source or compiled game asset not found", path ?? reference);
        }
    }
}

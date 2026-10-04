using System.Numerics;
using System.Text.Json;
using System.Text.Json.Nodes;
using Datamodel;
using Hammer5Tools.Core.IO.Automation;

namespace Hammer5Tools.Core.Format.Vmap;

internal static class MapAuthoring
{
    internal const string DefaultBoxModel = "models/editor/placeholder_box.vmdl";
    private sealed record Node(Element Element, Element? Parent, Matrix4x4 World);

    internal static JsonObject Execute(JsonElement request, string operation)
    {
        lock (SafeAssetWrites.Sync)
        {
            var root = CompilerService.Text(request, "addon_root");
            var path = AssetPathResolver.Resolve(request.GetProperty("path").GetString()!, root, operation is not ("insert" or "zoo"));
            var source = CompilerService.Text(request, "skeleton") ?? (File.Exists(path) ? path : null);
            if (source is null && operation is "insert" or "zoo")
            {
                var cs2 = CompilerService.Text(request, "cs2_path") ?? throw new ArgumentException("A skeleton or cs2_path is required.");
                source = Path.Combine(cs2, "content", "csgo_addons", "addon_template", "maps", "xxx_mapname_xxx.vmap");
            }
            source = AssetPathResolver.Resolve(source ?? path, root);
            var document = VmapDocument.LoadInMemory(source);
            var nodes = Index(document);
            if (operation == "nodes")
            {
                var offset = request.TryGetProperty("offset", out var off) ? off.GetInt32() : 0;
                var limit = request.TryGetProperty("limit", out var max) ? max.GetInt32() : 50;
                if (offset < 0 || limit is < 1 or > 500)
                {
                    throw new ArgumentException("Invalid pagination.");
                }

                var entries = nodes.Values.OrderBy(node => node.Element.ID).Skip(offset).Take(limit).Select(node => (JsonNode)new JsonObject
                {
                    ["id"] = node.Element.ID.ToString(),
                    ["name"] = node.Element.Name,
                    ["class"] = node.Element.ClassName,
                    ["parent_id"] = node.Parent?.ID.ToString(),
                    ["world_origin"] = Vector(node.World.Translation),
                }).ToArray();
                return new JsonObject
                {
                    ["nodes"] = new JsonArray(entries),
                    ["total"] = nodes.Count,
                    ["offset"] = offset,
                    ["returned"] = entries.Length,
                    ["truncated"] = offset + entries.Length < nodes.Count
                };
            }
            var changedIds = new List<string>();
            if (operation is "insert" or "zoo")
            {
                Insert(document, request, operation, nodes, changedIds);
            }
            else if (operation == "transform")
            {
                var node = Find(nodes, request.GetProperty("id").GetString()!);
                if (node.Parent is null)
                {
                    throw new ArgumentException("Cannot transform the world root.");
                }

                if (request.TryGetProperty("position", out _))
                {
                    node.Element["origin"] = Numbers(request, "position", Vector3.Zero);
                }

                if (request.TryGetProperty("angles", out _))
                {
                    var angles = Numbers(request, "angles", Vector3.Zero);
                    node.Element["angles"] = new QAngle(angles.X, angles.Y, angles.Z);
                }
                if (request.TryGetProperty("scale", out _))
                {
                    node.Element["scales"] = Numbers(request, "scale", Vector3.One, true);
                }

                changedIds.Add(node.Element.ID.ToString());
            }
            else if (operation == "group")
            {
                Group(document, request, nodes, changedIds);
            }
            else
            {
                throw new ArgumentException("Unknown map authoring operation.");
            }

            var dry = CompilerService.Flag(request, "dry_run");
            var changedNodes = Index(document);
            string? backup = null;
            if (!dry)
            {
                var staged = SafeAssetWrites.Stage(path, document.Save, stagedPath => _ = VmapDocument.LoadInMemory(stagedPath));
                try
                {
                    backup = SafeAssetWrites.Replace(staged, path);
                }
                finally
                {
                    File.Delete(staged);
                }
            }
            return new JsonObject
            {
                ["path"] = path.Replace('\\', '/'),
                ["dry_run"] = dry,
                ["action"] = operation == "insert" ? "vmap_write_blockout" : "vmap_" + operation,
                ["box_count"] = operation is "insert" or "zoo" ? changedIds.Count : 0,
                ["changed_count"] = changedIds.Count,
                ["ids"] = CompilerService.Strings(changedIds.Take(50)),
                ["models"] = operation is "insert" or "zoo" ? CompilerService.Strings(changedIds.Select(id => ((Element)changedNodes[Guid.Parse(id)].Element["entity_properties"]!)["model"]!.ToString()!).Distinct(StringComparer.OrdinalIgnoreCase).Take(50)) : null,
                ["bytes_written"] = dry ? 0 : new FileInfo(path).Length,
                ["truncated"] = changedIds.Count > 50,
                ["backup"] = backup,
                ["skeleton"] = source
            };
        }
    }

    private static Dictionary<Guid, Node> Index(VmapDocument document)
    {
        var result = new Dictionary<Guid, Node>();
        void Visit(Element element, Element? parent, Matrix4x4 transform)
        {
            if (result.ContainsKey(element.ID))
            {
                throw new InvalidDataException("Map contains a cycle or multiply parented node.");
            }

            var world = ValveMapSceneReader.LocalTransform(element) * transform;
            result.Add(element.ID, new Node(element, parent, world));
            if (element.TryGetValue("children", out var children) && children is ElementArray array)
            {
                foreach (var child in array)
                {
                    Visit(child, element, world);
                }
            }
        }
        Visit(document.World, null, Matrix4x4.Identity);
        return result;
    }

    private static Node Find(Dictionary<Guid, Node> nodes, string identifier)
    {
        if (Guid.TryParse(identifier, out var id) && nodes.TryGetValue(id, out var node))
        {
            return node;
        }

        var matches = nodes.Values.Where(node => node.Element.Name == identifier).ToArray();
        return matches.Length == 1 ? matches[0] : throw new ArgumentException("Node identifier is missing or ambiguous; use its GUID.");
    }

    private static void Insert(VmapDocument document, JsonElement request, string operation, Dictionary<Guid, Node> nodes, List<string> changed)
    {
        var parent = CompilerService.Text(request, "group_id") is { } group ? Find(nodes, group) : nodes[document.World.ID];
        if (parent.Element.ClassName is not ("CMapGroup" or "CMapWorld"))
        {
            throw new ArgumentException("group_id must name a group.");
        }

        var placements = new List<UnrealMapPlacement>();
        if (operation == "zoo")
        {
            var hasModels = request.TryGetProperty("models", out var models);
            var hasPattern = request.TryGetProperty("pattern", out var pattern);
            if (hasModels == hasPattern)
            {
                throw new ArgumentException("Specify models or pattern.");
            }

            var root = CompilerService.Text(request, "addon_root");
            using var patternRequest = JsonDocument.Parse(new JsonObject { ["pattern"] = hasPattern ? pattern.GetString() : null, ["addon_root"] = root }.ToJsonString(AutomationJsonContext.Default.Options));
            var resources = hasModels ? models.EnumerateArray().Select(item => item.GetString()!).ToArray()
                : CompilerService.ResolveInputs(patternRequest.RootElement).Select(path => Path.GetRelativePath(root!, path)).ToArray();
            var columns = request.TryGetProperty("columns", out var value) ? value.GetInt32() : 10;
            if (columns < 1 || resources.Length == 0)
            {
                throw new ArgumentException("columns and model count must be positive.");
            }

            var origin = Numbers(request, "position", Vector3.Zero);
            var spacing = Numbers(request, "spacing", new Vector3(128, 128, 0));
            if (spacing.X <= 0 || spacing.Y <= 0)
            {
                throw new ArgumentException("Grid spacing must be positive on X and Y.");
            }

            var scale = Numbers(request, "scale", Vector3.One, true);
            var groundAlign = CompilerService.Flag(request, "ground_align");
            var groundOffsets = new Dictionary<string, float>(StringComparer.OrdinalIgnoreCase);
            for (var index = 0; index < resources.Length; index++)
            {
                var groundOffset = 0f;
                if (groundAlign && !groundOffsets.TryGetValue(resources[index], out groundOffset))
                {
                    var gameDirectory = CompilerService.Text(request, "game_dir") ?? CompilerService.Text(request, "cs2_path")
                        ?? throw new ArgumentException("ground_align requires game_dir or cs2_path for compiled geometry.");
                    using var boundsRequest = JsonDocument.Parse(new JsonObject
                    {
                        ["path"] = resources[index],
                        ["game_dir"] = gameDirectory,
                        ["addon"] = CompilerService.Text(request, "addon"),
                        ["scale"] = Vector(scale)
                    }.ToJsonString(AutomationJsonContext.Default.Options));
                    var bounds = Resources.ModelInspection.Inspect(boundsRequest.RootElement);
                    if (!bounds["supported"]!.GetValue<bool>())
                    {
                        throw new ArgumentException("ground_align requires available compiled render geometry; no source bounds were inferred.");
                    }

                    groundOffsets[resources[index]] = groundOffset = bounds["pivot_to_ground_offset"]!.GetValue<float>();
                }
                placements.Add(Placement(resources[index], origin + new Vector3(index % columns * spacing.X, index / columns * spacing.Y, groundOffset), Vector3.Zero, scale, "default"));
            }
        }
        else
        {
            var inline = request.TryGetProperty("boxes", out var boxes);
            var fileBacked = request.TryGetProperty("items_file", out var file);
            if (inline == fileBacked)
            {
                throw new ArgumentException("Specify exactly one of boxes or items_file.");
            }

            using var manifest = fileBacked ? JsonDocument.Parse(File.ReadAllText(AssetPathResolver.Resolve(file.GetString()!, CompilerService.Text(request, "addon_root")))) : null;
            foreach (var item in (manifest?.RootElement ?? boxes).EnumerateArray())
            {
                if (item.TryGetProperty("size", out _) && item.TryGetProperty("scale", out _))
                {
                    throw new ArgumentException("Specify size or scale, never both.");
                }

                var scales = item.TryGetProperty("size", out _) ? Numbers(item, "size", Vector3.One) / 10 : Numbers(item, "scale", Vector3.One, true);
                if (item.TryGetProperty("size", out _) && (scales.X <= 0 || scales.Y <= 0 || scales.Z <= 0))
                {
                    throw new ArgumentException("size must be positive.");
                }

                placements.Add(Placement(CompilerService.Text(item, "model") ?? DefaultBoxModel,
                    Numbers(item, "position", Vector3.Zero), Numbers(item, "angles", Vector3.Zero), scales, CompilerService.Text(item, "skin") ?? "default"));
            }
            if (placements.Count == 0)
            {
                throw new ArgumentException("boxes must contain at least one box.");
            }
        }
        var nodeId = nodes.Values.Max(node => node.Element.TryGetValue("nodeID", out var value) && value is int id ? id : 0);
        foreach (var placement in placements)
        {
            var entity = UnrealMapWriter.CreateEntity(document.Model, placement, checked(++nodeId));
            if (parent.Element != document.World)
            {
                SetTransform(entity, ValveMapSceneReader.LocalTransform(entity), parent.World);
            }

            Children(parent.Element).Add(entity);
            changed.Add(entity.ID.ToString());
        }
        var references = document.Model.PrefixAttributes.TryGetValue("map_asset_references", out var existing) && existing is StringArray array ? array : new StringArray();
        foreach (var resource in placements.Select(item => item.Properties!["model"]).Distinct(StringComparer.OrdinalIgnoreCase))
        {
            if (!references.Contains(resource))
            {
                references.Add(resource);
            }
        }

        document.Model.PrefixAttributes["map_asset_references"] = references;
    }

    private static UnrealMapPlacement Placement(string model, Vector3 origin, Vector3 angles, Vector3 scales, string skin)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(model);
        return new UnrealMapPlacement(UnrealMapPlacementKind.Entity, Path.GetFileNameWithoutExtension(model),
            [origin.X, origin.Y, origin.Z], [angles.X, angles.Y, angles.Z], [scales.X, scales.Y, scales.Z],
            new Dictionary<string, string>
            {
                ["classname"] = "prop_static",
                ["model"] = model.Replace('\\', '/'),
                ["skin"] = skin,
                ["solid"] = "6",
                ["bakelighting"] = "-1",
                ["disableshadows"] = "0",
                ["lightmapscalebias"] = "0",
                ["lightingorigin"] = "",
                ["bakelightdoublesided"] = "0",
                ["visoccluder"] = "0",
                ["materialoverride"] = "",
                ["lodlevel"] = "-1",
                ["baketoworld"] = "0",
                ["disablemerging"] = "0",
                ["rendertocubemaps"] = "1"
            }, null);
    }

    private static void Group(VmapDocument document, JsonElement request, Dictionary<Guid, Node> nodes, List<string> changed)
    {
        var action = request.GetProperty("action").GetString();
        if (action == "create")
        {
            var parent = CompilerService.Text(request, "parent_id") is { } parentId ? Find(nodes, parentId) : nodes[document.World.ID];
            if (parent.Element.ClassName is not ("CMapWorld" or "CMapGroup"))
            {
                throw new ArgumentException("Parent must be a group or world.");
            }

            var max = nodes.Values.Max(node => node.Element.TryGetValue("nodeID", out var value) && value is int id ? id : 0);
            var group = UnrealMapWriter.NodeDefaults(new Element(document.Model, request.GetProperty("name").GetString()!, null, "CMapGroup"), checked(max + 1));
            Children(parent.Element).Add(group);
            changed.Add(group.ID.ToString());
            return;
        }
        var target = Find(nodes, request.GetProperty("id").GetString()!);
        if (target.Parent is null)
        {
            throw new ArgumentException("Cannot modify the world root.");
        }

        if (action == "rename")
        {
            if (target.Element.ClassName != "CMapGroup")
            {
                throw new ArgumentException("Target is not a group.");
            }

            target.Element.Name = request.GetProperty("name").GetString()!;
        }
        else if (action == "reparent")
        {
            var parent = CompilerService.Text(request, "parent_id") is { } parentId ? Find(nodes, parentId) : nodes[document.World.ID];
            if (parent.Element.ClassName is not ("CMapWorld" or "CMapGroup"))
            {
                throw new ArgumentException("Parent must be a group or world.");
            }

            for (var ancestor = parent; ; ancestor = nodes[ancestor.Parent.ID])
            {
                if (ancestor.Element == target.Element)
                {
                    throw new ArgumentException("Reparent would create a cycle.");
                }

                if (ancestor.Parent is null)
                {
                    break;
                }
            }
            SetTransform(target.Element, target.World, parent.World);
            Children(target.Parent).Remove(target.Element);
            Children(parent.Element).Add(target.Element);
        }
        else if (action == "remove")
        {
            if (target.Element.ClassName != "CMapGroup")
            {
                throw new ArgumentException("Only group wrappers may be removed.");
            }

            foreach (var child in Children(target.Element).ToArray())
            {
                SetTransform(child, nodes[child.ID].World, nodes[target.Parent.ID].World);
                Children(target.Parent).Add(child);
            }
            Children(target.Parent).Remove(target.Element);
        }
        else
        {
            throw new ArgumentException("Group action must be create, rename, reparent, or remove.");
        }

        changed.Add(target.Element.ID.ToString());
    }

    private static ElementArray Children(Element node) => node["children"] is ElementArray array ? array : throw new InvalidDataException("Node lacks children array.");

    private static void SetTransform(Element element, Matrix4x4 world, Matrix4x4 parent)
    {
        if (!Matrix4x4.Invert(parent, out var inverse) || !Matrix4x4.Decompose(world * inverse, out var scale, out var rotation, out var translation))
        {
            throw new ArgumentException("Parent transform is singular or cannot preserve this world transform.");
        }

        var matrix = Matrix4x4.CreateFromQuaternion(rotation);
        var pitch = MathF.Asin(Math.Clamp(-matrix.M13, -1, 1));
        var roll = MathF.Atan2(matrix.M23, matrix.M33);
        var yaw = MathF.Atan2(matrix.M12, matrix.M11);
        if (MathF.Abs(MathF.Cos(pitch)) < 0.00001f)
        {
            roll = 0;
            yaw = MathF.Atan2(-matrix.M21, matrix.M22);
        }
        element["origin"] = translation; element["scales"] = scale;
        element["angles"] = new QAngle(float.RadiansToDegrees(pitch), float.RadiansToDegrees(yaw), float.RadiansToDegrees(roll));
        var expected = world * inverse;
        var actual = ValveMapSceneReader.LocalTransform(element);
        var error = new[] { actual.M11 - expected.M11, actual.M12 - expected.M12, actual.M13 - expected.M13,
            actual.M21 - expected.M21, actual.M22 - expected.M22, actual.M23 - expected.M23,
            actual.M31 - expected.M31, actual.M32 - expected.M32, actual.M33 - expected.M33 }.Max(MathF.Abs);
        if (error > 0.001f)
        {
            throw new ArgumentException("Regrouping requires shear, which VMAP position/angles/scales cannot represent; no file was written.");
        }
    }

    private static Vector3 Numbers(JsonElement item, string key, Vector3 fallback, bool scalar = false)
    {
        if (!item.TryGetProperty(key, out var value))
        {
            return fallback;
        }

        if (scalar && value.ValueKind == JsonValueKind.Number)
        {
            var number = value.GetSingle();
            if (!float.IsFinite(number) || number == 0)
            {
                throw new ArgumentException($"{key} must be finite and nonzero.");
            }

            return new Vector3(number);
        }
        var parts = value.EnumerateArray().Select(component => component.GetSingle()).ToArray();
        if (parts.Length != 3 || parts.Any(component => !float.IsFinite(component)))
        {
            throw new ArgumentException($"{key} must contain three finite numbers.");
        }

        if (scalar && parts.Any(component => component == 0))
        {
            throw new ArgumentException("scale must be nonzero.");
        }

        return new Vector3(parts[0], parts[1], parts[2]);
    }

    private static JsonArray Vector(Vector3 value) => new(value.X, value.Y, value.Z);
}

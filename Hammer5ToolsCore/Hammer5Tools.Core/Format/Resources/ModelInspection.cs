using System.Numerics;
using System.Text.Json;
using System.Text.Json.Nodes;
using Hammer5Tools.Core.IO.Automation;

namespace Hammer5Tools.Core.Format.Resources;

internal static class ModelInspection
{
    private static readonly object ConsoleSync = new();

    internal static JsonObject Inspect(JsonElement request)
    {
        // VRF writes mount diagnostics to Console.Out; stdout belongs to MCP JSON-RPC.
        lock (ConsoleSync)
        {
            var output = Console.Out;
            try
            {
                Console.SetOut(Console.Error);
                return InspectResource(request);
            }
            finally
            {
                Console.SetOut(output);
            }
        }
    }

    private static JsonObject InspectResource(JsonElement request)
    {
        var path = request.GetProperty("path").GetString()!;
        if (path.EndsWith(".fbx", StringComparison.OrdinalIgnoreCase))
        {
            return new JsonObject { ["supported"] = false, ["source_kind"] = "source-fbx", ["diagnostic"] = "No source-FBX bounds importer is available; compile the VMDL and inspect compiled render geometry." };
        }

        if (!path.EndsWith(".vmdl", StringComparison.OrdinalIgnoreCase) && !path.EndsWith(".vmdl_c", StringComparison.OrdinalIgnoreCase))
        {
            throw new ArgumentException("Model inspection accepts VMDL or compiled VMDL_C resources.");
        }

        var gameDirectory = request.GetProperty("game_dir").GetString()!;
        if (Directory.Exists(Path.Combine(gameDirectory, "game")))
        {
            gameDirectory = Path.Combine(gameDirectory, "game");
        }

        using var reader = new CompiledModelReader(gameDirectory, CompilerService.Text(request, "addon") ?? "");
        var result = reader.Read(path, maximumTextureDimension: 1, baseColorOnly: true);
        if (!result.IsSuccess)
        {
            return new JsonObject { ["supported"] = false, ["source_kind"] = "compiled-render", ["diagnostic"] = "Compiled LoD0 geometry unavailable; source-FBX bounds are not inferred." };
        }

        var model = result.Value!;
        return Summarize(model, request, path);
    }

    internal static JsonObject Summarize(CompiledModel model, JsonElement request, string path)
    {
        var scale = Numbers(request, "scale", Vector3.One);
        var origin = Numbers(request, "position", Vector3.Zero);
        var angles = Numbers(request, "angles", Vector3.Zero);
        var transform = Matrix4x4.CreateScale(scale) * Matrix4x4.CreateRotationX(float.DegreesToRadians(angles.Z))
            * Matrix4x4.CreateRotationY(float.DegreesToRadians(angles.X)) * Matrix4x4.CreateRotationZ(float.DegreesToRadians(angles.Y)) * Matrix4x4.CreateTranslation(origin);
        var minimum = new Vector3(float.PositiveInfinity);
        var maximum = new Vector3(float.NegativeInfinity);
        for (var index = 0; index < model.Vertices.Length; index += 3)
        {
            var vertex = Vector3.Transform(new Vector3(model.Vertices[index], model.Vertices[index + 1], model.Vertices[index + 2]), transform);
            minimum = Vector3.Min(minimum, vertex); maximum = Vector3.Max(maximum, vertex);
        }
        var diagnostics = new JsonArray("Physics geometry is not exposed by this reader; render bounds are not physics bounds.");
        if (request.TryGetProperty("triangle_warning_threshold", out var threshold))
        {
            if (threshold.GetInt32() <= 0)
            {
                throw new ArgumentException("triangle_warning_threshold must be positive.");
            }

            if (model.Indices.Length / 3 > threshold.GetInt32())
            {
                diagnostics.Add(JsonValue.Create("Render triangle count exceeds the caller's advisory threshold; collision hull complexity has not been measured."));
            }
        }
        return new JsonObject
        {
            ["supported"] = true,
            ["source_kind"] = "compiled-render",
            ["path"] = path,
            ["minimum"] = Vector(minimum),
            ["maximum"] = Vector(maximum),
            ["dimensions"] = Vector(maximum - minimum),
            ["center"] = Vector((minimum + maximum) / 2),
            ["pivot_to_ground_offset"] = -minimum.Z,
            ["vertex_count"] = model.Vertices.Length / 3,
            ["triangle_count"] = model.Indices.Length / 3,
            ["mesh_count"] = model.SubMeshes.Length,
            ["mesh_count_kind"] = "render submeshes",
            ["physics_bounds"] = null,
            ["coordinate_space"] = "compiled model coordinates after requested scale/angles/position",
            ["units"] = "native Source 2 world units; no unit conversion",
            ["lod_policy"] = "compiled LoD0",
            ["source_import_transforms"] = "baked into compiled geometry; no exact source-FBX claim",
            ["diagnostics"] = diagnostics
        };
    }

    private static Vector3 Numbers(JsonElement request, string key, Vector3 fallback)
    {
        if (!request.TryGetProperty(key, out var value))
        {
            return fallback;
        }

        if (key == "scale" && value.ValueKind == JsonValueKind.Number)
        {
            var scalar = value.GetSingle();
            if (!float.IsFinite(scalar) || scalar == 0)
            {
                throw new ArgumentException("scale must be finite and nonzero.");
            }

            return new Vector3(scalar);
        }
        var values = value.EnumerateArray().Select(item => item.GetSingle()).ToArray();
        if (values.Length != 3 || values.Any(component => !float.IsFinite(component)))
        {
            throw new ArgumentException($"{key} requires three finite numbers.");
        }

        if (key == "scale" && values.Any(component => component == 0))
        {
            throw new ArgumentException("scale must be nonzero.");
        }

        return new Vector3(values[0], values[1], values[2]);
    }

    private static JsonArray Vector(Vector3 value) => new(value.X, value.Y, value.Z);
}

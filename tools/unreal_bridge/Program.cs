using System.Text;
using CUE4Parse.FileProvider;
using CUE4Parse.UE4.Assets.Exports.Actor;
using CUE4Parse.UE4.Assets.Exports.Component.Landscape;
using CUE4Parse.UE4.Assets.Objects;
using CUE4Parse.UE4.Objects.Core.Math;
using CUE4Parse.UE4.Objects.UObject;
using CUE4Parse.UE4.Versions;
using CUE4Parse_Conversion;
using CUE4Parse_Conversion.Landscape;
using CUE4Parse_Conversion.Meshes;
using CUE4Parse_Conversion.Textures;
using Newtonsoft.Json;

// H5T Unreal Bridge — thin CLI over CUE4Parse for the Unreal Converter.
// Commands:
//   info <projectContentDir>
//   list <projectContentDir> <substring>
//   dump <projectContentDir> <objectPath>        (raw JSON of all exports)
//   dump-scene <projectContentDir> <mapPath>      (normalized actor list)

static class Program
{
    static int Main(string[] args)
    {
        Console.OutputEncoding = Encoding.UTF8;
        if (args.Length < 2)
        {
            Console.Error.WriteLine("usage: <info|list|dump> <contentDir> [arg]");
            return 2;
        }

        var cmd = args[0].ToLowerInvariant();
        var dir = args[1];

        DefaultFileProvider provider;
        try
        {
            provider = new DefaultFileProvider(
                dir, SearchOption.AllDirectories, true,
                new VersionContainer(EGame.GAME_UE5_7));
            provider.Initialize();
        }
        catch (Exception e)
        {
            Console.Error.WriteLine("MOUNT_ERROR: " + e);
            return 1;
        }

        try
        {
            switch (cmd)
            {
                case "info": return Info(provider, dir);
                case "list": return List(provider, args.Length > 2 ? args[2] : "");
                case "dump": return Dump(provider, args[2]);
                case "dump-scene": return DumpScene(provider, args[2]);
                case "dump-blueprint": return DumpBlueprint(provider, args[2]);
                case "dump-material": return DumpMaterial(provider, args[2]);
                case "export-landscape": return ExportLandscape(provider, args[2], args[3], args.Length > 4 ? args[4] : "all");
                default:
                    Console.Error.WriteLine("unknown command: " + cmd);
                    return 2;
            }
        }
        catch (Exception e)
        {
            Console.Error.WriteLine("ERROR: " + e);
            return 1;
        }
    }

    static int Info(DefaultFileProvider provider, string dir)
    {
        var files = provider.Files.Keys.ToList();
        int external = files.Count(f => f.Contains("__ExternalActors__", StringComparison.OrdinalIgnoreCase));
        int umaps = files.Count(f => f.EndsWith(".umap", StringComparison.OrdinalIgnoreCase));
        int uassets = files.Count(f => f.EndsWith(".uasset", StringComparison.OrdinalIgnoreCase));

        var info = new
        {
            contentDir = dir,
            game = provider.Versions.Game.ToString(),
            totalFiles = files.Count,
            uassets,
            umaps,
            externalActorFiles = external,
            sampleFiles = files.Take(15).ToList(),
        };
        Console.WriteLine(JsonConvert.SerializeObject(info, Formatting.Indented));
        return 0;
    }

    static int List(DefaultFileProvider provider, string substring)
    {
        var matches = provider.Files.Keys
            .Where(f => f.Contains(substring, StringComparison.OrdinalIgnoreCase))
            .OrderBy(f => f)
            .Take(200)
            .ToList();
        Console.WriteLine(JsonConvert.SerializeObject(matches, Formatting.Indented));
        return 0;
    }

    static int Dump(DefaultFileProvider provider, string objectPath)
    {
        var pkg = provider.LoadPackage(objectPath);
        var exports = pkg.GetExports();
        var json = JsonConvert.SerializeObject(exports, Formatting.Indented);
        Console.WriteLine(json);
        return 0;
    }

    // Matrix math helpers to accumulate parent-child transforms into world space.
    private static double[,] IdentityMatrix()
    {
        return new double[4, 4] {
            { 1, 0, 0, 0 },
            { 0, 1, 0, 0 },
            { 0, 0, 1, 0 },
            { 0, 0, 0, 1 }
        };
    }

    private static double[,] MakeMatrix(double x, double y, double z, double pitch, double yaw, double roll, double sx, double sy, double sz)
    {
        double p = pitch * Math.PI / 180.0;
        double yRad = yaw * Math.PI / 180.0;
        double r = roll * Math.PI / 180.0;

        double sp = Math.Sin(p), cp = Math.Cos(p);
        double syVal = Math.Sin(yRad), cyVal = Math.Cos(yRad);
        double sr = Math.Sin(r), cr = Math.Cos(r);

        double fwdX = cp * cyVal * sx;
        double fwdY = cp * syVal * sx;
        double fwdZ = sp * sx;

        double rgtX = (sr * sp * cyVal - cr * syVal) * sy;
        double rgtY = (sr * sp * syVal + cr * cyVal) * sy;
        double rgtZ = (-sr * cp) * sy;

        double upX = (-(cr * sp * cyVal + sr * syVal)) * sz;
        double upY = (cyVal * sr - cr * sp * syVal) * sz;
        double upZ = (cr * cp) * sz;

        return new double[4, 4] {
            { fwdX, rgtX, upX, x },
            { fwdY, rgtY, upY, y },
            { fwdZ, rgtZ, upZ, z },
            { 0,    0,    0,   1 }
        };
    }

    private static double[,] MultiplyMatrix(double[,] A, double[,] B)
    {
        double[,] C = new double[4, 4];
        for (int i = 0; i < 4; i++)
        {
            for (int j = 0; j < 4; j++)
            {
                double sum = 0.0;
                for (int k = 0; k < 4; k++)
                {
                    sum += A[i, k] * B[k, j];
                }
                C[i, j] = sum;
            }
        }
        return C;
    }

    private static (FVector loc, FRotator rot, FVector scale) DecomposeMatrix(double[,] M)
    {
        float x = (float)M[0, 3];
        float y = (float)M[1, 3];
        float z = (float)M[2, 3];

        double sx = Math.Sqrt(M[0, 0] * M[0, 0] + M[1, 0] * M[1, 0] + M[2, 0] * M[2, 0]);
        double sy = Math.Sqrt(M[0, 1] * M[0, 1] + M[1, 1] * M[1, 1] + M[2, 1] * M[2, 1]);
        double sz = Math.Sqrt(M[0, 2] * M[0, 2] + M[1, 2] * M[1, 2] + M[2, 2] * M[2, 2]);

        double fwdX = sx > 1e-6 ? M[0, 0] / sx : 1.0;
        double fwdY = sx > 1e-6 ? M[1, 0] / sx : 0.0;
        double fwdZ = sx > 1e-6 ? M[2, 0] / sx : 0.0;

        double rgtZ = sy > 1e-6 ? M[2, 1] / sy : 0.0;
        double upZ  = sz > 1e-6 ? M[2, 2] / sz : 1.0;
        double rgtX = sy > 1e-6 ? M[0, 1] / sy : 0.0;
        double rgtY = sy > 1e-6 ? M[1, 1] / sy : 1.0;

        double xyDist = Math.Sqrt(fwdX * fwdX + fwdY * fwdY);
        float pitch, yaw, roll;

        if (xyDist > 1e-4)
        {
            yaw = (float)(Math.Atan2(fwdY, fwdX) * 180.0 / Math.PI);
            pitch = (float)(Math.Atan2(fwdZ, xyDist) * 180.0 / Math.PI);
            roll = (float)(Math.Atan2(-rgtZ, upZ) * 180.0 / Math.PI);
        }
        else
        {
            yaw = (float)(Math.Atan2(-rgtX, rgtY) * 180.0 / Math.PI);
            pitch = (float)(Math.Atan2(fwdZ, xyDist) * 180.0 / Math.PI);
            roll = 0f;
        }

        return (new FVector(x, y, z), new FRotator(pitch, yaw, roll), new FVector((float)sx, (float)sy, (float)sz));
    }

    private static (FVector loc, FRotator rot, FVector scale) GetWorldTransform(CUE4Parse.UE4.Assets.Exports.UObject comp)
    {
        var chain = new List<CUE4Parse.UE4.Assets.Exports.UObject>();
        var curr = comp;
        var visited = new HashSet<CUE4Parse.UE4.Assets.Exports.UObject>();

        while (curr != null && visited.Add(curr))
        {
            chain.Add(curr);

            CUE4Parse.UE4.Assets.Exports.UObject? parent = null;
            var attachParentRef = curr.GetOrDefault<FPackageIndex?>("AttachParent", null);
            if (attachParentRef?.ResolvedObject?.Load() is CUE4Parse.UE4.Assets.Exports.UObject parentObj)
            {
                parent = parentObj;
            }
            else if (curr.Outer?.Load() is CUE4Parse.UE4.Assets.Exports.UObject outer && outer != curr)
            {
                var rootCompRef = outer.GetOrDefault<FPackageIndex?>("RootComponent", null);
                if (rootCompRef?.ResolvedObject?.Load() is CUE4Parse.UE4.Assets.Exports.UObject rootComp && rootComp != curr && !visited.Contains(rootComp))
                {
                    parent = rootComp;
                }
            }
            curr = parent;
        }

        chain.Reverse();
        double[,] worldMat = IdentityMatrix();

        foreach (var item in chain)
        {
            var loc = item.GetOrDefault("RelativeLocation", FVector.ZeroVector);
            var rot = item.GetOrDefault("RelativeRotation", FRotator.ZeroRotator);
            var scale = item.GetOrDefault("RelativeScale3D", FVector.OneVector);

            double[,] localMat = MakeMatrix(loc.X, loc.Y, loc.Z, rot.Pitch, rot.Yaw, rot.Roll, scale.X, scale.Y, scale.Z);
            worldMat = MultiplyMatrix(worldMat, localMat);
        }

        return DecomposeMatrix(worldMat);
    }

    // Normalized scene extraction: every static-mesh-bearing component with its
    // mesh reference and UE transform. Coordinate conversion to Source 2 is done
    // on the Python side via the shared transform module. Instanced/foliage/spline
    // components are tagged by componentType so the caller can special-case them.
    static int DumpScene(DefaultFileProvider provider, string mapPath)
    {
        var pkg = provider.LoadPackage(mapPath);
        var actors = new List<object>();
        var processedBpActors = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        ALandscapeProxy? landscapeActor = null;

        foreach (var export in pkg.GetExports())
        {
            var cls = export.ExportType;
            if (cls == null) continue;

            // Landscapes have no static-mesh asset — they're heightmap-driven
            // terrain baked by ExportLandscape into an OBJ. Only the first
            // components-bearing landscape actor in the map is reported (matches
            // ExportLandscape's own selection); the Python side calls
            // export-landscape to get the actual mesh and treats it like any
            // other placed prop_static using this actor's world transform.
            if (export is ALandscapeProxy lp && lp.LandscapeComponents.Length > 0)
            {
                if (landscapeActor == null)
                {
                    landscapeActor = lp;
                    var (lLoc, lRot, lScale) = GetWorldTransform(export);
                    actors.Add(new
                    {
                        actor = export.Name,
                        componentType = "Landscape",
                        blueprint = (string?)null,
                        mesh = (string?)null,
                        landscapeActor = export.Name,
                        location = new { x = lLoc.X, y = lLoc.Y, z = lLoc.Z },
                        rotation = new { pitch = lRot.Pitch, yaw = lRot.Yaw, roll = lRot.Roll },
                        scale = new { x = lScale.X, y = lScale.Y, z = lScale.Z },
                    });
                }
                continue;
            }

            string? outerName = export.Outer?.Name.Text;
            string? outerClass = export.Outer?.Class?.Name.Text;

            if (!string.IsNullOrEmpty(outerName) && !string.IsNullOrEmpty(outerClass) &&
                outerClass.EndsWith("_C", StringComparison.OrdinalIgnoreCase) &&
                !outerClass.Equals("Level", StringComparison.OrdinalIgnoreCase) &&
                !outerClass.Equals("World", StringComparison.OrdinalIgnoreCase))
            {
                if (processedBpActors.Add(outerName))
                {
                    string bpName = outerClass.Substring(0, outerClass.Length - 2);
                    var actorObj = export.Outer?.Load();
                    var rootCompRef = actorObj?.GetOrDefault<FPackageIndex?>("RootComponent", null);
                    var rootComp = rootCompRef?.ResolvedObject?.Load();
                    var (bpLoc, bpRot, bpScale) = GetWorldTransform(rootComp ?? actorObj ?? export);
                    actors.Add(new
                    {
                        actor = outerName,
                        componentType = "BlueprintActor",
                        blueprint = bpName,
                        mesh = (string?)null,
                        location = new { x = bpLoc.X, y = bpLoc.Y, z = bpLoc.Z },
                        rotation = new { pitch = bpRot.Pitch, yaw = bpRot.Yaw, roll = bpRot.Roll },
                        scale = new { x = bpScale.X, y = bpScale.Y, z = bpScale.Z },
                    });
                }
                continue;
            }

            if (cls.Contains("DecalComponent", StringComparison.Ordinal))
            {
                var decalMatRef = export.GetOrDefault<FPackageIndex?>("DecalMaterial", null);
                string? decalMat = decalMatRef?.ResolvedObject?.GetPathName();
                if (decalMat == null)
                    continue;

                var (dLoc, dRot, dScale) = GetWorldTransform(export);
                actors.Add(new
                {
                    actor = outerName,
                    componentType = "DecalComponent",
                    blueprint = (string?)null,
                    mesh = (string?)null,
                    material = decalMat,
                    location = new { x = dLoc.X, y = dLoc.Y, z = dLoc.Z },
                    rotation = new { pitch = dRot.Pitch, yaw = dRot.Yaw, roll = dRot.Roll },
                    scale = new { x = dScale.X, y = dScale.Y, z = dScale.Z },
                });
                continue;
            }

            if (!cls.Contains("StaticMeshComponent", StringComparison.Ordinal))
                continue;

            var meshRef = export.GetOrDefault<FPackageIndex?>("StaticMesh", null);
            string? mesh = meshRef?.ResolvedObject?.GetPathName();
            if (mesh == null)
                continue;

            var (loc, rot, scale) = GetWorldTransform(export);

            actors.Add(new
            {
                actor = outerName,
                componentType = cls,
                blueprint = (string?)null,
                mesh,
                location = new { x = loc.X, y = loc.Y, z = loc.Z },
                rotation = new { pitch = rot.Pitch, yaw = rot.Yaw, roll = rot.Roll },
                scale = new { x = scale.X, y = scale.Y, z = scale.Z },
            });
        }

        var result = new { map = mapPath, count = actors.Count, actors };
        Console.WriteLine(JsonConvert.SerializeObject(result, Formatting.Indented));
        return 0;
    }

    static int DumpBlueprint(DefaultFileProvider provider, string bpPath)
    {
        var pkg = provider.LoadPackage(bpPath);
        var one = new FVector(1f, 1f, 1f);
        var components = new List<object>();

        var nodeParentMap = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var export in pkg.GetExports())
        {
            if (export.ExportType != null && export.ExportType.Contains("SCS_Node", StringComparison.Ordinal))
            {
                var templateRef = export.GetOrDefault<FPackageIndex?>("ComponentTemplate", null);
                string? templateName = templateRef?.ResolvedObject?.Name.Text;
                var parentName = export.GetOrDefault<FName?>("AttachVariableName", null)?.Text
                    ?? export.GetOrDefault<FName?>("ParentComponentOrVariableName", null)?.Text;

                if (!string.IsNullOrEmpty(templateName) && !string.IsNullOrEmpty(parentName) && parentName != "None")
                {
                    nodeParentMap[templateName] = parentName;
                }
            }
        }

        foreach (var export in pkg.GetExports())
        {
            var cls = export.ExportType;
            if (cls == null) continue;

            bool isStaticMesh = cls.Contains("StaticMeshComponent", StringComparison.Ordinal);
            bool isScene = cls.Contains("SceneComponent", StringComparison.Ordinal);

            if (!isStaticMesh && !isScene)
                continue;

            var meshRef = export.GetOrDefault<FPackageIndex?>("StaticMesh", null);
            string? mesh = meshRef?.ResolvedObject?.GetPathName();

            if (isStaticMesh && mesh == null)
                continue;

            var loc = export.GetOrDefault("RelativeLocation", new FVector(0f, 0f, 0f));
            var rot = export.GetOrDefault("RelativeRotation", new FRotator(0f, 0f, 0f));
            var scale = export.GetOrDefault("RelativeScale3D", one);

            var attachParentRef = export.GetOrDefault<FPackageIndex?>("AttachParent", null);
            string? parent = attachParentRef?.ResolvedObject?.Name.Text;

            string name = export.Name;
            if (string.IsNullOrEmpty(parent) && nodeParentMap.TryGetValue(name, out var scsParent))
            {
                parent = scsParent;
            }

            components.Add(new
            {
                name,
                componentType = cls,
                mesh,
                parent,
                location = new { x = loc.X, y = loc.Y, z = loc.Z },
                rotation = new { pitch = rot.Pitch, yaw = rot.Yaw, roll = rot.Roll },
                scale = new { x = scale.X, y = scale.Y, z = scale.Z },
            });
        }

        var result = new { blueprint = bpPath, count = components.Count, components };
        Console.WriteLine(JsonConvert.SerializeObject(result, Formatting.Indented));
        return 0;
    }

    // Walk a material's Parent chain to the base UMaterial and read the render
    // flags that decide the Source shader (domain/blend/shading/two-sided), then
    // apply any MI BasePropertyOverrides on top.
    static string? EnumText(CUE4Parse.UE4.Assets.Exports.UObject o, string key)
    {
        // Byte/enum properties can surface as FName or as a plain string.
        var fn = o.GetOrDefault<FName?>(key, null);
        if (fn != null && !string.IsNullOrEmpty(fn.Value.Text)) return fn.Value.Text;
        var s = o.GetOrDefault<string?>(key, null);
        return string.IsNullOrEmpty(s) ? null : s;
    }

    static string? ParentPackagePath(CUE4Parse.UE4.Assets.Exports.UObject o)
    {
        var pref = o.GetOrDefault<FPackageIndex?>("Parent", null);
        var name = pref?.ResolvedObject?.GetPathName();
        if (string.IsNullOrEmpty(name)) return null;
        name = name.Replace("/Game/", "");
        int dot = name.LastIndexOf('.');
        if (dot > 0) name = name.Substring(0, dot);   // drop ".ObjectName"
        return name.TrimStart('/');
    }

    static object ResolveMaterialFlags(DefaultFileProvider provider, CUE4Parse.UE4.Assets.Exports.UObject miExport)
    {
        var baseMat = miExport;
        var seen = new HashSet<string>();
        for (int i = 0; i < 16; i++)
        {
            if (EnumText(baseMat, "MaterialDomain") != null) break;
            var ppath = ParentPackagePath(baseMat);
            if (ppath == null || !seen.Add(ppath)) break;
            CUE4Parse.UE4.Assets.Exports.UObject? next = null;
            try
            {
                var ppkg = provider.LoadPackage(ppath);
                foreach (var ex in ppkg.GetExports())
                {
                    if (EnumText(ex, "MaterialDomain") != null || ex.GetOrDefault<FPackageIndex?>("Parent", null) != null)
                    { next = ex; break; }
                }
                next ??= ppkg.GetExports().FirstOrDefault();
            }
            catch { }
            if (next == null) break;
            baseMat = next;
        }

        string? domain = EnumText(baseMat, "MaterialDomain");
        string? blend = EnumText(baseMat, "BlendMode");
        string? shading = EnumText(baseMat, "ShadingModel");
        string? decalBlend = EnumText(baseMat, "DecalBlendMode");
        bool twoSided = baseMat.GetOrDefault<bool>("TwoSided", false);

        var bpo = miExport.GetOrDefault<FStructFallback?>("BasePropertyOverrides", null);
        if (bpo != null)
        {
            if (bpo.GetOrDefault<bool>("bOverride_BlendMode", false))
                blend = bpo.GetOrDefault<FName?>("BlendMode", null)?.Text ?? blend;
            if (bpo.GetOrDefault<bool>("bOverride_TwoSided", false))
                twoSided = bpo.GetOrDefault<bool>("TwoSided", twoSided);
            if (bpo.GetOrDefault<bool>("bOverride_ShadingModel", false))
                shading = bpo.GetOrDefault<FName?>("ShadingModel", null)?.Text ?? shading;
        }

        return new { domain, blendMode = blend, shadingModel = shading, twoSided, decalBlendMode = decalBlend };
    }

    // Extract a UE Material's OWN instance-level overrides (TextureParameterValues
    // / ScalarParameterValues / VectorParameterValues) from a single export — used
    // at every level while walking a MaterialInstance parent chain.
    static void CollectInstanceParams(
        CUE4Parse.UE4.Assets.Exports.UObject export,
        Dictionary<string, string> textures, Dictionary<string, float> scalars, Dictionary<string, object> vectors)
    {
        var texParams = export.GetOrDefault<FStructFallback[]?>("TextureParameterValues", null);
        if (texParams != null)
            foreach (var tp in texParams)
            {
                var name = tp.GetOrDefault<FStructFallback?>("ParameterInfo", null)?.GetOrDefault<FName?>("Name", null)?.Text;
                var texPath = tp.GetOrDefault<FPackageIndex?>("ParameterValue", null)?.ResolvedObject?.GetPathName();
                if (!string.IsNullOrEmpty(name) && !string.IsNullOrEmpty(texPath) && !textures.ContainsKey(name))
                    textures[name] = texPath;
            }

        var scalarParams = export.GetOrDefault<FStructFallback[]?>("ScalarParameterValues", null);
        if (scalarParams != null)
            foreach (var sp in scalarParams)
            {
                var name = sp.GetOrDefault<FStructFallback?>("ParameterInfo", null)?.GetOrDefault<FName?>("Name", null)?.Text;
                if (!string.IsNullOrEmpty(name) && !scalars.ContainsKey(name))
                    scalars[name] = sp.GetOrDefault<float>("ParameterValue", 0f);
            }

        var vectorParams = export.GetOrDefault<FStructFallback[]?>("VectorParameterValues", null);
        if (vectorParams != null)
            foreach (var vp in vectorParams)
            {
                var name = vp.GetOrDefault<FStructFallback?>("ParameterInfo", null)?.GetOrDefault<FName?>("Name", null)?.Text;
                var val = vp.GetOrDefault<FLinearColor?>("ParameterValue", null);
                if (!string.IsNullOrEmpty(name) && val != null && !vectors.ContainsKey(name))
                    vectors[name] = new { r = val.Value.R, g = val.Value.G, b = val.Value.B, a = val.Value.A };
            }
    }

    // A base UMaterial has no instance param arrays — its "default" values for
    // each named parameter live on the individual MaterialExpression*Parameter
    // nodes in its expression graph. This is what a child MaterialInstance falls
    // back to for any parameter it doesn't itself override, so it has to be
    // walked once the parent chain bottoms out at a real Material.
    static void CollectExpressionDefaults(
        CUE4Parse.UE4.Assets.IPackage pkg,
        Dictionary<string, string> textures, Dictionary<string, float> scalars, Dictionary<string, object> vectors)
    {
        foreach (var ex in pkg.GetExports())
        {
            switch (ex.ExportType)
            {
                case "MaterialExpressionTextureSampleParameter2D":
                case "MaterialExpressionTextureSampleParameter":
                case "MaterialExpressionTextureSampleParameterCube":
                    {
                        var name = EnumText(ex, "ParameterName");
                        var tex = ex.GetOrDefault<FPackageIndex?>("Texture", null)?.ResolvedObject?.GetPathName();
                        if (!string.IsNullOrEmpty(name) && !string.IsNullOrEmpty(tex) && !textures.ContainsKey(name))
                            textures[name] = tex;
                        break;
                    }
                case "MaterialExpressionScalarParameter":
                    {
                        var name = EnumText(ex, "ParameterName");
                        if (!string.IsNullOrEmpty(name) && !scalars.ContainsKey(name))
                            scalars[name] = ex.GetOrDefault<float>("DefaultValue", 0f);
                        break;
                    }
                case "MaterialExpressionVectorParameter":
                    {
                        var name = EnumText(ex, "ParameterName");
                        var val = ex.GetOrDefault<FLinearColor?>("DefaultValue", null);
                        if (!string.IsNullOrEmpty(name) && val != null && !vectors.ContainsKey(name))
                            vectors[name] = new { r = val.Value.R, g = val.Value.G, b = val.Value.B, a = val.Value.A };
                        break;
                    }
            }
        }
    }

    // Find the export in a loaded package that represents "the material" at this
    // level: a MaterialInstance (has Parent or instance param arrays) or the base
    // Material itself. NOTE: MaterialDomain is UE's default-valued Surface enum
    // and is simply not serialized when left at its default, so its presence
    // cannot be used to detect "this is a base Material" — the export TYPE name
    // ("Material") is the reliable signal instead.
    static CUE4Parse.UE4.Assets.Exports.UObject? FindMaterialExport(CUE4Parse.UE4.Assets.IPackage pkg)
    {
        foreach (var ex in pkg.GetExports())
        {
            if (ex.ExportType == "Material" ||
                ex.GetOrDefault<FPackageIndex?>("Parent", null) != null ||
                ex.GetOrDefault<FStructFallback[]?>("TextureParameterValues", null) != null)
                return ex;
        }
        return null;
    }

    static int DumpMaterial(DefaultFileProvider provider, string matPath)
    {
        var textures = new Dictionary<string, string>();
        var scalars = new Dictionary<string, float>();
        var vectors = new Dictionary<string, object>();
        string? parent = null;
        object? flags = null;

        // Walk the MaterialInstance parent chain top -> bottom, merging each
        // level's own overrides (highest priority = the requested material,
        // decreasing per parent hop). Once the chain bottoms out at a base
        // Material, the expression-graph node defaults fill anything still
        // unset — this is what makes MIs whose own TextureParameterValues array
        // is empty (they only override a scalar/vector) still resolve textures.
        string? currentPath = matPath;
        var seen = new HashSet<string>();
        for (int level = 0; level < 16 && currentPath != null; level++)
        {
            if (!seen.Add(currentPath)) break;

            CUE4Parse.UE4.Assets.IPackage pkg;
            try { pkg = provider.LoadPackage(currentPath); }
            catch { break; }

            var matExport = FindMaterialExport(pkg);
            if (matExport == null) break;

            if (level == 0)
            {
                var pref = matExport.GetOrDefault<FPackageIndex?>("Parent", null);
                parent = pref?.ResolvedObject?.GetPathName();
            }

            CollectInstanceParams(matExport, textures, scalars, vectors);

            if (flags == null)
            {
                try { flags = ResolveMaterialFlags(provider, matExport); } catch { }
            }

            if (matExport.ExportType == "Material")
            {
                // Reached the base Material — pull its expression-node defaults
                // as the lowest-priority fallback layer, then stop.
                CollectExpressionDefaults(pkg, textures, scalars, vectors);
                break;
            }

            currentPath = ParentPackagePath(matExport);
        }

        var result = new { material = matPath, parent, flags, textures, scalars, vectors };
        Console.WriteLine(JsonConvert.SerializeObject(result, Formatting.Indented));
        return 0;
    }

    // Convert a UE Landscape into a mesh (OBJ) and, optionally, heightmap/weightmap
    // PNGs. flagsArg selects what to export: "mesh" (just the OBJ — used by the
    // Unreal Converter's Scenes/Models pipeline to place the landscape as a
    // prop_static), "heightmap", "weightmap", or "all" (default; used by the
    // standalone research workflow).
    static int ExportLandscape(DefaultFileProvider provider, string mapPath, string outDir, string flagsArg = "all")
    {
        var pkg = provider.LoadPackage(mapPath);
        ALandscapeProxy? landscape = null;
        foreach (var e in pkg.GetExports())
            if (e is ALandscapeProxy lp && lp.LandscapeComponents.Length > 0) { landscape = lp; break; }
        if (landscape == null)
        {
            Console.Error.WriteLine("NO_LANDSCAPE: no ALandscapeProxy with components in this map.");
            return 1;
        }

        var comps = landscape.LandscapeComponents
            .Select(pi => pi.Load<ULandscapeComponent>())
            .Where(c => c != null).Cast<ULandscapeComponent>().ToArray();

        var options = new ExporterOptions
        {
            MeshFormat = EMeshFormat.OBJ,
            LodFormat = ELodFormat.FirstLod,
            TextureFormat = ETextureFormat.Png,
            Platform = provider.Versions.Platform,
            ExportMaterials = false,
        };

        ELandscapeExportFlags flags = flagsArg.ToLowerInvariant() switch
        {
            "mesh" => ELandscapeExportFlags.Mesh,
            "heightmap" => ELandscapeExportFlags.Heightmap,
            "weightmap" => ELandscapeExportFlags.Weightmap,
            _ => ELandscapeExportFlags.All,
        };
        var exporter = new LandscapeExporter(landscape, comps, options, flags);
        Directory.CreateDirectory(outDir);
        if (exporter.TryWriteToDir(new DirectoryInfo(outDir), out var label, out var saved))
        {
            Console.WriteLine(JsonConvert.SerializeObject(
                new { ok = true, components = comps.Length, label, saved }, Formatting.Indented));
            return 0;
        }
        Console.Error.WriteLine("EXPORT_FAILED");
        return 1;
    }
}

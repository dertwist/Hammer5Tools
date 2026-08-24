using System.Text;
using CUE4Parse.FileProvider;
using CUE4Parse.UE4.Assets.Exports.Actor;
using CUE4Parse.UE4.Assets.Exports.Component.Landscape;
using CUE4Parse.UE4.Assets.Objects;
using CUE4Parse.UE4.Assets.Objects.Properties;
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
//   iter-refs <projectContentDir> <objectPath>   (flat list of referenced object paths)
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
                case "iter-refs": return IterRefs(provider, args[2]);
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

    // No cap. This is the converter's whole view of a project: the port scope,
    // the material scan and reference expansion are all built from it, so a
    // truncated list does not shrink the port, it silently drops every asset
    // past the cut (a 563-asset project ported 52 meshes). A few thousand paths
    // of JSON over stdout costs nothing next to that.
    static int List(DefaultFileProvider provider, string substring)
    {
        var matches = provider.Files.Keys
            .Where(f => f.Contains(substring, StringComparison.OrdinalIgnoreCase))
            .OrderBy(f => f)
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

    // Collect every asset reference in a package as a flat list of object paths,
    // WITHOUT serialising the whole export tree. `dump` greps the rendered JSON
    // for reference fields, which for a StaticMesh means buffering hundreds of
    // megabytes of RenderData (and the material slots serialise as null when
    // their FPackageIndex import doesn't resolve). This walks the live objects
    // and resolves each ref the same way dump-scene/dump-blueprint do.
    static int IterRefs(DefaultFileProvider provider, string objectPath)
    {
        var pkg = provider.LoadPackage(objectPath);
        var refs = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        foreach (var export in pkg.GetExports())
        {
            CollectExportRefs(export, refs);
        }

        Console.WriteLine(JsonConvert.SerializeObject(refs.OrderBy(r => r).ToList(), Formatting.Indented));
        return 0;
    }

    // Walk one export for references. Mesh material arrays are pulled explicitly
    // (StaticMaterials/SkeletalMaterials hold the slots every other path reads
    // one at a time); the generic property walk then catches Parent (materials),
    // StaticMesh (components), textures on material expression nodes, etc.
    private static void CollectExportRefs(CUE4Parse.UE4.Assets.Exports.UObject export, HashSet<string> refs)
    {
        // StaticMesh.StaticMaterials[].MaterialInterface (+ OverlayMaterialInterface)
        if (export is CUE4Parse.UE4.Assets.Exports.StaticMesh.UStaticMesh sm && sm.StaticMaterials != null)
        {
            foreach (var slot in sm.StaticMaterials)
            {
                AddRef(refs, slot.MaterialInterface?.GetPathName());
                AddRef(refs, PkgIndexPath(slot.OverlayMaterialInterface));
            }
        }
        // SkeletalMesh.SkeletalMaterials[].Material (+ OverlayMaterialInterface)
        if (export is CUE4Parse.UE4.Assets.Exports.SkeletalMesh.USkeletalMesh skm && skm.SkeletalMaterials != null)
        {
            foreach (var slot in skm.SkeletalMaterials)
            {
                AddRef(refs, slot.Material?.GetPathName());
                AddRef(refs, PkgIndexPath(slot.OverlayMaterialInterface));
            }
        }

        // Generic walk over the export's tagged properties.
        WalkProperties(export.Properties, refs, 0);
    }

    // Resolve every FPackageIndex inside a list of FPropertyTag, recursing into
    // structs and arrays. Mirrors the property access dump-scene does inline.
    private static void WalkProperties(List<FPropertyTag> properties, HashSet<string> refs, int depth)
    {
        if (properties == null || depth > 8) return; // defence against pathological nesting
        foreach (var tag in properties)
        {
            switch (tag.Tag)
            {
                case ObjectProperty obj:                 // FPropertyTagType<FPackageIndex>
                    AddRef(refs, PkgIndexPath(obj.Value));
                    break;
                case StructProperty st when st.Value?.StructType is FStructFallback fb:
                    WalkProperties(fb.Properties, refs, depth + 1);
                    break;
                case ArrayProperty arr:                  // FPropertyTagType<UScriptArray>
                    if (arr.Value != null)
                    {
                        foreach (var item in arr.Value.Properties)
                        {
                            switch (item)
                            {
                                case ObjectProperty o:
                                    AddRef(refs, PkgIndexPath(o.Value));
                                    break;
                                case StructProperty s when s.Value?.StructType is FStructFallback inner:
                                    WalkProperties(inner.Properties, refs, depth + 1);
                                    break;
                            }
                        }
                    }
                    break;
            }
        }
    }

    private static string? PkgIndexPath(FPackageIndex? pi)
    {
        // Matches dump-scene/dump-blueprint: resolve through the package.
        if (pi == null || pi.IsNull) return null;
        return pi.ResolvedObject?.GetPathName();
    }

    private static void AddRef(HashSet<string> refs, string? path)
    {
        if (!string.IsNullOrEmpty(path)) refs.Add(path);
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

        // Column magnitudes are always positive, so a mirrored actor would come
        // out as an ordinary one with a bogus (improper) rotation. A negative
        // determinant is the only evidence the scale flipped handedness; which
        // axis it was is not recoverable and does not matter, because every
        // single-axis flip differs from the others only by a rotation this
        // decomposition then absorbs. Putting it on X keeps that choice in one
        // place and leaves the basis below proper.
        double det = M[0, 0] * (M[1, 1] * M[2, 2] - M[1, 2] * M[2, 1])
                   - M[0, 1] * (M[1, 0] * M[2, 2] - M[1, 2] * M[2, 0])
                   + M[0, 2] * (M[1, 0] * M[2, 1] - M[1, 1] * M[2, 0]);
        if (det < 0.0) sx = -sx;

        // Magnitude, not value: sx is signed now, and "> 1e-6" would treat a
        // mirrored axis as a degenerate one and throw the basis away.
        double axLen = Math.Abs(sx);
        double fwdX = axLen > 1e-6 ? M[0, 0] / sx : 1.0;
        double fwdY = axLen > 1e-6 ? M[1, 0] / sx : 0.0;
        double fwdZ = axLen > 1e-6 ? M[2, 0] / sx : 0.0;

        double rgtZ = sy > 1e-6 ? M[2, 1] / sy : 0.0;
        double upZ = sz > 1e-6 ? M[2, 2] / sz : 1.0;
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

    // Find the Blueprint actor a component belongs to, if any. The direct Outer
    // covers a Blueprint's own components; the AttachParent hop covers the child
    // actors a Blueprint spawns, which the editor saves into the level as
    // top-level "..._CAT_<n>" actors owned by nothing. Without that hop every
    // child actor is placed a second time as a loose prop_static alongside the
    // smartprop that already contains it.
    private static (string? actorName, string? className, CUE4Parse.UE4.Assets.Exports.UObject? actor)
        OwningBlueprintActor(CUE4Parse.UE4.Assets.Exports.UObject comp)
    {
        var curr = comp;
        for (int i = 0; i < 16 && curr != null; i++)
        {
            var outer = curr.Outer;
            var outerName = outer?.Name.Text;
            var outerClass = outer?.Class?.Name.Text;
            if (outer != null && !string.IsNullOrEmpty(outerName) && !string.IsNullOrEmpty(outerClass) &&
                outerClass.EndsWith("_C", StringComparison.OrdinalIgnoreCase) &&
                !outerClass.Equals("Level", StringComparison.OrdinalIgnoreCase) &&
                !outerClass.Equals("World", StringComparison.OrdinalIgnoreCase))
            {
                return (outerName, outerClass, outer.Load());
            }
            curr = curr.GetOrDefault<FPackageIndex?>("AttachParent", null)?.ResolvedObject?.Load();
        }
        return (null, null, null);
    }

    // Light / sky / reflection components the vmap writer knows how to place.
    // Spot and rect components derive from the point light component but export
    // under their own type name, so a plain name match is enough — order is kept
    // most-specific-first anyway so a renamed subclass cannot fall through to
    // the wrong CS2 entity.
    private static string? LightComponentKind(string cls)
    {
        if (cls.Contains("SpotLightComponent", StringComparison.Ordinal)) return "SpotLight";
        if (cls.Contains("RectLightComponent", StringComparison.Ordinal)) return "RectLight";
        if (cls.Contains("PointLightComponent", StringComparison.Ordinal)) return "PointLight";
        if (cls.Contains("DirectionalLightComponent", StringComparison.Ordinal)) return "DirectionalLight";
        if (cls.Contains("SkyLightComponent", StringComparison.Ordinal) ||
            cls.Contains("SkyAtmosphereComponent", StringComparison.Ordinal)) return "SkyLight";
        if (cls.Contains("ReflectionCaptureComponent", StringComparison.Ordinal)) return "ReflectionCapture";
        return null;
    }

    // Raw Unreal light properties, straight off the component. No conversion
    // happens here: the photometric and unit mapping lives in Python
    // (light_entities.py) next to the CS2 key names it has to satisfy, so both
    // halves of that mapping can be read — and tested — in one place.
    private static object LightPayload(CUE4Parse.UE4.Assets.Exports.UObject comp, string kind, FVector worldScale)
    {
        var color = comp.GetOrDefault("LightColor", new FColor(255, 255, 255, 255));
        object? boxExtent = null;
        if (kind == "ReflectionCapture" &&
            comp.ExportType?.Contains("BoxReflectionCapture", StringComparison.Ordinal) == true)
        {
            // A box capture has no radius: its volume is a 100uu cube scaled by
            // the component transform, so the extent has to come from there.
            boxExtent = new { x = worldScale.X * 100f, y = worldScale.Y * 100f, z = worldScale.Z * 100f };
        }

        return new
        {
            intensity = comp.GetOrDefault("Intensity", 0f),
            // Nullable read, matching DumpBlueprint: an unset enum property must
            // come back as null rather than dereferencing a default FName.
            intensityUnits = comp.GetOrDefault<FName?>("IntensityUnits", null)?.Text,
            color = new { r = color.R, g = color.G, b = color.B },
            useTemperature = comp.GetOrDefault("bUseTemperature", false),
            temperature = comp.GetOrDefault("Temperature", 6500f),
            attenuationRadius = comp.GetOrDefault("AttenuationRadius", 0f),
            innerConeAngle = comp.GetOrDefault("InnerConeAngle", 0f),
            outerConeAngle = comp.GetOrDefault("OuterConeAngle", 44f),
            sourceRadius = comp.GetOrDefault("SourceRadius", 0f),
            sourceWidth = comp.GetOrDefault("SourceWidth", 64f),
            sourceHeight = comp.GetOrDefault("SourceHeight", 64f),
            castShadows = comp.GetOrDefault("CastShadows", true),
            sourceAngle = comp.GetOrDefault("LightSourceAngle", 0f),
            cubemap = comp.GetOrDefault<FPackageIndex?>("Cubemap", null)?.ResolvedObject?.GetPathName(),
            influenceRadius = comp.GetOrDefault("InfluenceRadius", 0f),
            boxExtent,
            brightness = comp.GetOrDefault("Brightness", 1f),
        };
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

            var (bpActorName, bpClass, bpActorObj) = OwningBlueprintActor(export);
            if (bpActorName != null && bpClass != null)
            {
                if (processedBpActors.Add(bpActorName))
                {
                    string bpName = bpClass.Substring(0, bpClass.Length - 2);
                    var actorObj = bpActorObj;
                    var rootCompRef = actorObj?.GetOrDefault<FPackageIndex?>("RootComponent", null);
                    var rootComp = rootCompRef?.ResolvedObject?.Load();
                    var (bpLoc, bpRot, bpScale) = GetWorldTransform(rootComp ?? actorObj ?? export);
                    actors.Add(new
                    {
                        actor = bpActorName,
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

            var lightKind = LightComponentKind(cls);
            if (lightKind != null)
            {
                var (lLoc2, lRot2, lScale2) = GetWorldTransform(export);
                actors.Add(new
                {
                    actor = outerName,
                    componentType = lightKind,
                    blueprint = (string?)null,
                    mesh = (string?)null,
                    light = LightPayload(export, lightKind, lScale2),
                    location = new { x = lLoc2.X, y = lLoc2.Y, z = lLoc2.Z },
                    rotation = new { pitch = lRot2.Pitch, yaw = lRot2.Yaw, roll = lRot2.Roll },
                    scale = new { x = lScale2.X, y = lScale2.Y, z = lScale2.Z },
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

    // SCS component templates are exported as "<VariableName>_GEN_VARIABLE".
    // Native/inherited subobjects use the bare variable name, so normalizing to
    // the variable name gives one namespace both sides can be keyed by.
    private const string GenVariableSuffix = "_GEN_VARIABLE";

    private static string ScsVariableName(string exportName) =>
        exportName.EndsWith(GenVariableSuffix, StringComparison.Ordinal)
            ? exportName.Substring(0, exportName.Length - GenVariableSuffix.Length)
            : exportName;

    // A ChildActorComponent carries no mesh of its own — it spawns a template
    // actor that holds one. Unreal's "convert selected actors to Blueprint ->
    // child actors" builds whole props this way (a fence is 11 StaticMeshActor
    // child actors), so without this every one of them converts as an empty node.
    private static CUE4Parse.UE4.Assets.Exports.UObject? ChildActorTemplate(CUE4Parse.UE4.Assets.Exports.UObject comp) =>
        comp.GetOrDefault<FPackageIndex?>("ChildActorTemplate", null)?.ResolvedObject?.Load();

    private static string? ChildActorMesh(CUE4Parse.UE4.Assets.Exports.UObject comp)
    {
        var template = ChildActorTemplate(comp);
        if (template == null) return null;
        // AStaticMeshActor's mesh component is also its root; check both names.
        var rootRef = template.GetOrDefault<FPackageIndex?>("StaticMeshComponent", null)
                   ?? template.GetOrDefault<FPackageIndex?>("RootComponent", null);
        if (rootRef?.ResolvedObject?.Load() is not CUE4Parse.UE4.Assets.Exports.UObject rootComp)
            return null;
        // The template's own relative transform is discarded by Unreal — the
        // child actor is spawned at the component's transform — so only the
        // mesh reference is taken from here.
        return rootComp.GetOrDefault<FPackageIndex?>("StaticMesh", null)?.ResolvedObject?.GetPathName();
    }

    static int DumpBlueprint(DefaultFileProvider provider, string bpPath)
    {
        var pkg = provider.LoadPackage(bpPath);
        var one = new FVector(1f, 1f, 1f);
        var components = new List<object>();

        // A Blueprint's component hierarchy lives in the SimpleConstructionScript,
        // NOT on the component templates: SCS templates are never AttachParent-ed
        // to each other, so reading AttachParent alone flattens every nested
        // component to the root and its parent's offset/rotation is lost. Walk
        // USCS_Node.ChildNodes to recover the real tree.
        var templateToVar = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        var parentByVar = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        var scsNodes = pkg.GetExports()
            .Where(e => e.ExportType != null && e.ExportType.Contains("SCS_Node", StringComparison.Ordinal))
            .ToList();

        static string? TemplateName(CUE4Parse.UE4.Assets.Exports.UObject node) =>
            node.GetOrDefault<FPackageIndex?>("ComponentTemplate", null)?.ResolvedObject?.Name.Text;

        foreach (var node in scsNodes)
        {
            var templateName = TemplateName(node);
            if (string.IsNullOrEmpty(templateName)) continue;
            var varName = node.GetOrDefault<FName?>("InternalVariableName", null)?.Text;
            templateToVar[templateName] = string.IsNullOrEmpty(varName) || varName == "None"
                ? ScsVariableName(templateName)
                : varName;
        }

        // Must agree with the emitted component names below, so route through
        // the same template -> variable map (a renamed variable keeps its old
        // "_GEN_VARIABLE" template name).
        string? TemplateVar(CUE4Parse.UE4.Assets.Exports.UObject node)
        {
            var templateName = TemplateName(node);
            if (string.IsNullOrEmpty(templateName)) return null;
            return templateToVar.TryGetValue(templateName, out var v) ? v : ScsVariableName(templateName);
        }

        foreach (var node in scsNodes)
        {
            var myVar = TemplateVar(node);
            if (myVar == null) continue;

            foreach (var childRef in node.GetOrDefault<FPackageIndex[]?>("ChildNodes", null) ?? Array.Empty<FPackageIndex>())
            {
                if (childRef?.ResolvedObject?.Load() is not CUE4Parse.UE4.Assets.Exports.UObject childNode) continue;
                var childVar = TemplateVar(childNode);
                if (childVar != null && !childVar.Equals(myVar, StringComparison.OrdinalIgnoreCase))
                    parentByVar[childVar] = myVar;
            }
        }

        // Root SCS nodes record their parent (a native or inherited component,
        // e.g. DefaultSceneRoot) by name instead of appearing in any ChildNodes.
        foreach (var node in scsNodes)
        {
            var myVar = TemplateVar(node);
            if (myVar == null || parentByVar.ContainsKey(myVar)) continue;
            var parentName = node.GetOrDefault<FName?>("ParentComponentOrVariableName", null)?.Text;
            if (!string.IsNullOrEmpty(parentName) && parentName != "None" &&
                !parentName.Equals(myVar, StringComparison.OrdinalIgnoreCase))
                parentByVar[myVar] = parentName;
        }

        // Emitted names must be unique — the package can hold both an SCS template
        // and an inherited subobject that normalize to the same variable name; the
        // SCS template carries the authored transform, so it wins.
        var byName = new Dictionary<string, object>(StringComparer.OrdinalIgnoreCase);
        var fromScs = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        // Components living inside a ChildActorTemplate belong to the spawned
        // actor, not to this Blueprint — the ChildActorComponent already stands
        // in for them, so emitting them too would duplicate every mesh under a
        // second, transform-less name.
        var childActorTemplateNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var export in pkg.GetExports())
        {
            if (export.ExportType?.Contains("ChildActorComponent", StringComparison.Ordinal) != true) continue;
            var template = ChildActorTemplate(export);
            if (template != null) childActorTemplateNames.Add(template.Name);
        }

        foreach (var export in pkg.GetExports())
        {
            var cls = export.ExportType;
            if (cls == null) continue;

            // Anything that can hold a transform is kept, even without a mesh:
            // dropping an empty scene/spline/arrow node orphans its children and
            // loses the offset it was carrying for them.
            bool isScsTemplate = templateToVar.ContainsKey(export.Name);
            if (!isScsTemplate && !cls.EndsWith("Component", StringComparison.Ordinal))
                continue;

            var ownerName = export.Outer?.Name.Text;
            if (!string.IsNullOrEmpty(ownerName) && childActorTemplateNames.Contains(ownerName))
                continue;

            string name = templateToVar.TryGetValue(export.Name, out var mappedVar)
                ? mappedVar
                : ScsVariableName(export.Name);

            if (byName.ContainsKey(name) && (fromScs.Contains(name) || !isScsTemplate))
                continue;
            if (isScsTemplate) fromScs.Add(name);

            var meshRef = export.GetOrDefault<FPackageIndex?>("StaticMesh", null) ?? export.GetOrDefault<FPackageIndex?>("SkeletalMesh", null);
            string? mesh = meshRef?.ResolvedObject?.GetPathName() ?? ChildActorMesh(export);

            var loc = export.GetOrDefault("RelativeLocation", new FVector(0f, 0f, 0f));
            var rot = export.GetOrDefault("RelativeRotation", new FRotator(0f, 0f, 0f));
            var scale = export.GetOrDefault("RelativeScale3D", one);

            if (!parentByVar.TryGetValue(name, out string? parent))
            {
                var attachParentName = export.GetOrDefault<FPackageIndex?>("AttachParent", null)?.ResolvedObject?.Name.Text;
                parent = string.IsNullOrEmpty(attachParentName) ? null : ScsVariableName(attachParentName);
            }

            byName[name] = new
            {
                name,
                componentType = cls,
                mesh,
                parent,
                location = new { x = loc.X, y = loc.Y, z = loc.Z },
                rotation = new { pitch = rot.Pitch, yaw = rot.Yaw, roll = rot.Roll },
                scale = new { x = scale.X, y = scale.Y, z = scale.Z },
            };
        }

        components.AddRange(byName.Values);
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
    // UE 4.19+ nests a parameter's name inside FMaterialParameterInfo
    // ("ParameterInfo": { "Name": ... }); assets saved by 4.18 and earlier carry
    // a flat FName "ParameterName" instead. Reading only the modern shape makes
    // every override on old content resolve to null, so the instance contributes
    // nothing and DumpMaterial falls through to the base Material's expression
    // defaults — which is why whole marketplace packs converted to one flat
    // placeholder colour.
    static string? ParamName(FStructFallback p) =>
        p.GetOrDefault<FStructFallback?>("ParameterInfo", null)?.GetOrDefault<FName?>("Name", null)?.Text
        ?? p.GetOrDefault<FName?>("ParameterName", null)?.Text;

    static void CollectInstanceParams(
        CUE4Parse.UE4.Assets.Exports.UObject export,
        Dictionary<string, string> textures, Dictionary<string, float> scalars, Dictionary<string, object> vectors,
        Dictionary<string, bool> switches)
    {
        var texParams = export.GetOrDefault<FStructFallback[]?>("TextureParameterValues", null);
        if (texParams != null)
            foreach (var tp in texParams)
            {
                var name = ParamName(tp);
                var texPath = tp.GetOrDefault<FPackageIndex?>("ParameterValue", null)?.ResolvedObject?.GetPathName();
                if (!string.IsNullOrEmpty(name) && !string.IsNullOrEmpty(texPath) && !textures.ContainsKey(name))
                    textures[name] = texPath;
            }

        var scalarParams = export.GetOrDefault<FStructFallback[]?>("ScalarParameterValues", null);
        if (scalarParams != null)
            foreach (var sp in scalarParams)
            {
                var name = ParamName(sp);
                if (!string.IsNullOrEmpty(name) && !scalars.ContainsKey(name))
                    scalars[name] = sp.GetOrDefault<float>("ParameterValue", 0f);
            }

        var vectorParams = export.GetOrDefault<FStructFallback[]?>("VectorParameterValues", null);
        if (vectorParams != null)
            foreach (var vp in vectorParams)
            {
                var name = ParamName(vp);
                var val = vp.GetOrDefault<FLinearColor?>("ParameterValue", null);
                if (!string.IsNullOrEmpty(name) && val != null && !vectors.ContainsKey(name))
                    vectors[name] = new { r = val.Value.R, g = val.Value.G, b = val.Value.B, a = val.Value.A };
            }

        // Static switches ("Static Switch Parameter" nodes, e.g. "Use Normal Map")
        // live under the editor-only StaticParameters struct, not as a flat array
        // like the value params above — only present on uncooked assets, which is
        // exactly what this bridge reads.
        var switchParams = export.GetOrDefault<FStructFallback?>("StaticParameters", null)
            ?.GetOrDefault<FStructFallback[]?>("StaticSwitchParameters", null);
        if (switchParams != null)
            foreach (var swp in switchParams)
            {
                var name = ParamName(swp);
                if (!string.IsNullOrEmpty(name) && !switches.ContainsKey(name))
                    switches[name] = swp.GetOrDefault<bool>("Value", false);
            }
    }

    // A base UMaterial has no instance param arrays — its "default" values for
    // each named parameter live on the individual MaterialExpression*Parameter
    // nodes in its expression graph. This is what a child MaterialInstance falls
    // back to for any parameter it doesn't itself override, so it has to be
    // walked once the parent chain bottoms out at a real Material.
    static void CollectExpressionDefaults(
        CUE4Parse.UE4.Assets.IPackage pkg,
        Dictionary<string, string> textures, Dictionary<string, float> scalars, Dictionary<string, object> vectors,
        Dictionary<string, bool> switches)
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
                case "MaterialExpressionStaticBoolParameter":
                    {
                        var name = EnumText(ex, "ParameterName");
                        if (!string.IsNullOrEmpty(name) && !switches.ContainsKey(name))
                            switches[name] = ex.GetOrDefault<bool>("DefaultValue", false);
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
        var switches = new Dictionary<string, bool>();
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

            CollectInstanceParams(matExport, textures, scalars, vectors, switches);

            if (flags == null)
            {
                try { flags = ResolveMaterialFlags(provider, matExport); } catch { }
            }

            if (matExport.ExportType == "Material")
            {
                // Reached the base Material — pull its expression-node defaults
                // as the lowest-priority fallback layer, then stop.
                CollectExpressionDefaults(pkg, textures, scalars, vectors, switches);
                break;
            }

            currentPath = ParentPackagePath(matExport);
        }

        var result = new { material = matPath, parent, flags, textures, scalars, vectors, switches };
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

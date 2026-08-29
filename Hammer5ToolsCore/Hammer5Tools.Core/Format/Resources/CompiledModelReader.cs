using System.Collections.Concurrent;
using System.Collections.Immutable;
using System.Diagnostics.CodeAnalysis;
using System.Text.RegularExpressions;

using SkiaSharp;
using ValveResourceFormat;
using ValveResourceFormat.Blocks;
using ValveResourceFormat.IO;
using ValveResourceFormat.ResourceTypes;
using ValveResourceFormat.Serialization.KeyValues;

namespace Hammer5Tools.Core.Format.Resources;

/// <summary>Reads compiled Source 2 viewport resources through ValveResourceFormat.</summary>
[SuppressMessage("Design", "CA1031:Do not catch general exception types", Justification = "Public resource operations return structured diagnostics for parser and filesystem failures.")]
public sealed partial class CompiledModelReader(string gameDirectory, string activeAddon) : ICompiledModelReader, IDisposable
{
    private static readonly string[] BaseTextures = [
        "g_tColor", "g_tColor1", "g_tColor2", "g_tColor3", "g_tColor0", "g_tColorA", "g_tColorB", "g_tColorC",
        "g_tBaseColor", "g_tAlbedo", "g_tBaseTexture", "g_tGlassTintColor", "g_tGlassMaskColor", "g_tTintColor"
    ];
    private static readonly string[] NormalTextures = [
        "g_tNormal", "g_tNormal1", "g_tNormal2", "g_tNormal3", "g_tNormal0", "g_tNormalA",
        "g_tNormalRoughness", "g_tNormalMap", "g_tBumpMap"
    ];
    private static readonly string[] MetalTextures = [
        "g_tMetalness", "g_tMetalness1", "g_tMetalness2", "g_tMetalness3", "g_tMetalness0",
        "g_tMetallic", "g_tMetal"
    ];
    private static readonly string[] RoughnessTextures = [
        "g_tRoughness", "g_tRoughness1", "g_tRoughness2", "g_tRoughness3", "g_tRoughness0",
        "g_tGlassRoughness"
    ];
    private static readonly string[] AmbientOcclusionTextures = [
        "g_tAmbientOcclusion", "g_tAmbientOcclusion1", "g_tAmbientOcclusion2", "g_tAO"
    ];
    private static readonly string[] EmissiveTextures = [
        "g_tSelfIllumMask", "g_tEmissiveMask", "g_tSelfIllum", "g_tEmissive", "g_tSelfIllumMask1"
    ];
    private static readonly string[] TranslucencyTextures = [
        "g_tTranslucency", "g_tTranslucency1", "g_tTranslucency2", "g_tTranslucency3", "g_tTranslucencyA",
        "g_tOpacity", "g_tOpacity1", "g_tOpacity2",
        "g_tOpacityMask", "g_tOpacityMask1", "g_tOpacityMask2",
        "g_tGlassMaskTranslucency", "g_tGlassMaskTransmission", "g_tGlassMask", "g_tAlpha", "g_tAlphaMask"
    ];
    private static readonly CompiledMaterial DefaultMaterial = new(
        "", null, null, null, null, null, Vector4.One, 1, 1, Vector3.Zero,
        "OPAQUE", 0.5f, false, 0, 0, 0, Vector2.One, Vector2.Zero,
        new Vector2(0.5f), 0);
    /// <summary>Concurrent loads permitted per mount before callers wait for a free loader.</summary>
    private static readonly int MaximumLoadersPerKey = Math.Clamp(Environment.ProcessorCount, 2, 8);

    // A plain monitor rather than System.Threading.Lock: leases block on Monitor.Wait
    // for a free loader, and Monitor.Wait/Pulse are not available on Lock.
    private readonly object loaderLock = new();
    private readonly Dictionary<LoaderKey, LoaderPool> loaders = [];
    private readonly ConcurrentDictionary<string, CompiledMaterial> sharedMaterialCache = new(StringComparer.Ordinal);
    private readonly ConcurrentDictionary<string, CompiledTexture> sharedTextureCache = new(StringComparer.Ordinal);
    private bool disposed;

    /// <summary>Distinct mounts this reader has opened a loader for.</summary>
    internal int LoaderCount
    {
        get
        {
            lock (loaderLock)
                return loaders.Count;
        }
    }

    /// <summary>Every <see cref="GameFileLoader"/> created for one mount, and the idle subset.</summary>
    private sealed class LoaderPool
    {
        public readonly List<GameFileLoader> All = [];
        public readonly Stack<GameFileLoader> Idle = new();
    }

    /// <summary>Exclusive use of one loader for the duration of a read.</summary>
    private readonly struct LoaderLease(CompiledModelReader reader, LoaderPool pool, GameFileLoader loader)
        : IDisposable
    {
        public GameFileLoader Loader { get; } = loader;

        public void Dispose()
        {
            lock (reader.loaderLock)
            {
                pool.Idle.Push(Loader);
                Monitor.Pulse(reader.loaderLock);
            }
        }
    }

    /// <inheritdoc/>
    public CoreResult<CompiledModel> Read(
        string resourcePath,
        string? contextAddon = null,
        int maximumTextureDimension = 1024,
        bool baseColorOnly = false,
        int skin = 0)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(resourcePath);
        try
        {
            var (addon, relativePath) = Resolve(resourcePath, contextAddon);
            // The lease is held for the whole read, so the nested material/texture/mesh
            // loads below need no further locking — they all run on this loader alone.
            using var lease = RentLoader(addon, relativePath);
            var loader = lease.Loader;
            using (var resource = loader.LoadFileCompiled(relativePath))
            {
                if (resource?.DataBlock is not Model model)
                    return CoreResult.Failure<CompiledModel>("compiled_model_missing", $"Could not read '{relativePath}'.");

                var skinMap = ReadSkinMap(model, skin);
                var vertices = new List<float>();
                var normals = new List<float>();
                var uvs = new List<float>();
                var indices = new List<uint>();
                var subMeshes = new List<CompiledSubMesh>();
                var materialCache = new Dictionary<string, CompiledMaterial>(StringComparer.Ordinal);
                foreach (var mesh in ReadMeshes(loader, model))
                    AppendMesh(loader, mesh, skinMap, vertices, normals, uvs, indices, subMeshes,
                        materialCache, maximumTextureDimension, baseColorOnly);

                if (vertices.Count == 0 || indices.Count == 0)
                    return CoreResult.Failure<CompiledModel>("compiled_model_empty", $"'{relativePath}' has no LoD0 geometry.");

                var (minimum, maximum) = Bounds(vertices);
                return CoreResult.Success(new CompiledModel(
                    [.. vertices], [.. normals], [.. uvs], [.. indices], minimum, maximum,
                    [.. subMeshes], []));
            }
        }
        catch (Exception exception)
        {
            return CoreResult.Failure<CompiledModel>(
                "compiled_model_read_failed", $"Could not read '{resourcePath}': {exception.Message}");
        }
    }

    /// <inheritdoc/>
    public CoreResult<IReadOnlyList<string>> ReadMaterialGroups(string resourcePath, string? contextAddon = null)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(resourcePath);
        try
        {
            var (addon, relativePath) = Resolve(resourcePath, contextAddon);
            using var lease = RentLoader(addon, relativePath);
            using (var resource = lease.Loader.LoadFileCompiled(relativePath))
            {
                if (resource?.DataBlock is not Model model)
                    return CoreResult.Failure<IReadOnlyList<string>>(
                        "compiled_model_missing", $"Could not read '{relativePath}'.");
                return CoreResult.Success<IReadOnlyList<string>>(
                    model.GetMaterialGroups().Select(group => group.Item1).ToArray());
            }
        }
        catch (Exception exception)
        {
            return CoreResult.Failure<IReadOnlyList<string>>(
                "compiled_model_groups_failed", $"Could not read '{resourcePath}': {exception.Message}");
        }
    }

    /// <summary>Reads one material on its own, for previews that have no model to hang it on.</summary>
    public CoreResult<CompiledMaterial> ReadStandaloneMaterial(
        string resourcePath, string? contextAddon = null, int maximumTextureDimension = 1024,
        bool baseColorOnly = false)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(resourcePath);
        try
        {
            var (addon, relativePath) = Resolve(resourcePath, contextAddon, ".vmat");
            using var lease = RentLoader(addon, relativePath);
            return CoreResult.Success(
                ReadMaterial(lease.Loader, relativePath, maximumTextureDimension, baseColorOnly));
        }
        catch (Exception exception)
        {
            return CoreResult.Failure<CompiledMaterial>(
                "compiled_material_read_failed", $"Could not read '{resourcePath}': {exception.Message}");
        }
    }

    /// <summary>Reads one texture on its own, for previews that have no material to hang it on.</summary>
    public CoreResult<CompiledTexture> ReadStandaloneTexture(
        string resourcePath, string? contextAddon = null, int maximumTextureDimension = 1024)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(resourcePath);
        try
        {
            var (addon, relativePath) = Resolve(resourcePath, contextAddon, ".vtex");
            using var lease = RentLoader(addon, relativePath);
            var texture = ReadTexture(lease.Loader, relativePath, maximumTextureDimension);
            return texture is null
                ? CoreResult.Failure<CompiledTexture>(
                    "compiled_texture_read_failed", $"'{resourcePath}' holds no decodable texture data.")
                : CoreResult.Success(texture);
        }
        catch (Exception exception)
        {
            return CoreResult.Failure<CompiledTexture>(
                "compiled_texture_read_failed", $"Could not read '{resourcePath}': {exception.Message}");
        }
    }

    /// <summary>
    /// Takes exclusive use of a loader for the caller's whole read. VRF's
    /// <see cref="GameFileLoader"/> keeps mutable current-file state, so one loader serves
    /// one read at a time — but several loaders may serve the same mount concurrently,
    /// which is what lets parallel thumbnail workers overlap instead of queueing behind a
    /// single global lock. Blocks once <see cref="MaximumLoadersPerKey"/> are in flight.
    /// </summary>
    private LoaderLease RentLoader(string addon, string relativePath)
    {
        var addonFolder = Path.Combine(gameDirectory, "csgo_addons", addon);
        var addonFile = Path.Combine(addonFolder, relativePath.Replace('/', Path.DirectorySeparatorChar) + "_c");
        var coreFile = Path.Combine(gameDirectory, "csgo", relativePath.Replace('/', Path.DirectorySeparatorChar) + "_c");
        var useAddonFile = File.Exists(addonFile);
        var key = new LoaderKey(addon.ToUpperInvariant(), useAddonFile);

        lock (loaderLock)
        {
            while (true)
            {
                ObjectDisposedException.ThrowIf(disposed, this);
                if (!loaders.TryGetValue(key, out var pool))
                {
                    pool = new LoaderPool();
                    loaders.Add(key, pool);
                }

                if (pool.Idle.Count > 0)
                    return new LoaderLease(this, pool, pool.Idle.Pop());

                if (pool.All.Count < MaximumLoadersPerKey)
                {
                    var created = CreateLoader(addonFolder, useAddonFile ? addonFile : coreFile);
                    pool.All.Add(created);
                    return new LoaderLease(this, pool, created);
                }

                Monitor.Wait(loaderLock);
            }
        }
    }

    private GameFileLoader CreateLoader(string addonFolder, string packageFile)
    {
        var loader = new GameFileLoader(null!, packageFile);
        if (Directory.Exists(addonFolder))
            loader.AddDiskPathToSearch(addonFolder);
        var activeFolder = Path.Combine(gameDirectory, "csgo_addons", activeAddon);
        if (!string.Equals(activeFolder, addonFolder, StringComparison.OrdinalIgnoreCase)
            && Directory.Exists(activeFolder))
            loader.AddDiskPathToSearch(activeFolder);
        return loader;
    }

    /// <inheritdoc/>
    public void Dispose()
    {
        lock (loaderLock)
        {
            if (disposed)
                return;
            foreach (var pool in loaders.Values)
                foreach (var loader in pool.All)
                    loader.Dispose();
            loaders.Clear();
            sharedMaterialCache.Clear();
            sharedTextureCache.Clear();
            disposed = true;
        }
    }

    private void AppendMesh(
        GameFileLoader loader,
        Mesh mesh,
        Dictionary<string, string> skinMap,
        List<float> vertices,
        List<float> normals,
        List<float> uvs,
        List<uint> indices,
        List<CompiledSubMesh> subMeshes,
        Dictionary<string, CompiledMaterial> materialCache,
        int maximumTextureDimension,
        bool baseColorOnly)
    {
        var vbib = mesh.VBIB;
        var positions = new Dictionary<int, Vector3[]>();
        var normalData = new Dictionary<int, Vector3[]>();
        var uvData = new Dictionary<int, Vector2[]>();
        for (var bufferIndex = 0; bufferIndex < vbib.VertexBuffers.Count; bufferIndex++)
        {
            var buffer = vbib.VertexBuffers[bufferIndex];
            var positionField = FindField(buffer, "POSITION", 0);
            if (positionField is null)
                continue;
            var positionValues = VBIB.GetVector3AttributeArray(buffer, positionField.Value);
            positions[bufferIndex] = positionValues;
            var normalField = FindField(buffer, "NORMAL", 0);
            normalData[bufferIndex] = normalField is null
                ? new Vector3[positionValues.Length]
                : VBIB.GetNormalTangentArray(buffer, normalField.Value).Item1;
            var uvField = FindField(buffer, "TEXCOORD", 0);
            uvData[bufferIndex] = uvField is null
                ? new Vector2[positionValues.Length]
                : VBIB.GetVector2AttributeArray(buffer, uvField.Value);
        }

        var indexBuffers = mesh.VBIB.IndexBuffers.Select(ReadIndices).ToArray();
        foreach (var sceneObject in mesh.Data.GetArray("m_sceneObjects"))
            foreach (var drawCall in sceneObject.GetArray("m_drawCalls"))
            {
                var start = drawCall.GetInt32Property("m_nStartIndex", 0);
                var count = drawCall.GetInt32Property("m_nIndexCount", 0);
                var baseVertex = drawCall.GetInt32Property("m_nBaseVertex", 0);
                if (count <= 0)
                    continue;
                var boundBuffers = drawCall.GetArray("m_vertexBuffers");
                var bufferIndex = boundBuffers.Count == 0 ? 0 : boundBuffers[0].GetInt32Property("m_hBuffer", 0);
                if (!positions.TryGetValue(bufferIndex, out var positionValues))
                    continue;
                var indexBuffer = drawCall.GetSubCollection("m_indexBuffer");
                var indexHandle = indexBuffer?.GetInt32Property("m_hBuffer", 0) ?? 0;
                if (indexHandle < 0 || indexHandle >= indexBuffers.Length)
                    continue;

                var materialPath = drawCall.GetStringProperty("m_material", "");
                if (skinMap.TryGetValue(materialPath, out var replacement))
                    materialPath = replacement;
                if (!materialCache.TryGetValue(materialPath, out var material))
                {
                    material = ReadMaterial(loader, materialPath, maximumTextureDimension, baseColorOnly);
                    materialCache[materialPath] = material;
                }

                var indexOffset = indices.Count;
                var sourceIndices = indexBuffers[indexHandle];
                var appended = 0;
                for (var offset = start; offset < start + count && offset < sourceIndices.Length; offset++)
                {
                    var sourceIndex = (long)sourceIndices[offset] + baseVertex;
                    if (sourceIndex < 0 || sourceIndex >= positionValues.Length)
                        continue;
                    var index = (int)sourceIndex;
                    Append(vertices, positionValues[index]);
                    Append(normals, Normalize(normalData[bufferIndex][index]));
                    Append(uvs, uvData[bufferIndex][index]);
                    indices.Add((uint)(indices.Count));
                    appended++;
                }
                if (appended > 0)
                    subMeshes.Add(new CompiledSubMesh(indexOffset, appended, material));
            }
    }

    private CompiledMaterial ReadMaterial(
        GameFileLoader loader, string materialPath, int maximumTextureDimension, bool baseColorOnly)
    {
        var cacheKey = $"{materialPath}:{maximumTextureDimension}:{(baseColorOnly ? 1 : 0)}";
        if (sharedMaterialCache.TryGetValue(cacheKey, out var cached))
            return cached;

        try
        {
            using (var resource = loader.LoadFileCompiled(materialPath))
            {
                if (resource?.DataBlock is not Material material)
                    return DefaultMaterial with { Name = materialPath };

                var shaderName = material.ShaderName ?? "";
                var isGlassShader = shaderName.Contains("glass", StringComparison.OrdinalIgnoreCase);
                var isWaterShader = shaderName.Contains("water", StringComparison.OrdinalIgnoreCase);
                var isTranslucentShader = isGlassShader || isWaterShader || shaderName.Contains("translucent", StringComparison.OrdinalIgnoreCase) || shaderName.Contains("refract", StringComparison.OrdinalIgnoreCase) || shaderName.Contains("particle", StringComparison.OrdinalIgnoreCase);

                // F_BLEND_MODE is an enum, not a bool: 1 = Translucent, 2 = Alpha Test
                // (csgo_static_overlay).  Treating any non-zero value as translucent
                // blended alpha-tested decals instead of cutting them out.
                var blendMode = IntParameter(material, "F_BLEND_MODE");

                var alphaTest = IntParameter(material, "F_ALPHA_TEST") != 0
                    || IntParameter(material, "F_OPACITY_MASK") != 0
                    || IntParameter(material, "F_CUTOUT") != 0
                    || blendMode == 2;

                var translucent = isTranslucentShader
                    || IntParameter(material, "F_TRANSLUCENT") != 0
                    || IntParameter(material, "F_TRANSLUCENCY") != 0
                    || IntParameter(material, "F_TRANSLUCENT_DECAL") != 0
                    || blendMode == 1
                    || IntParameter(material, "F_OVERLAY") != 0
                    || IntParameter(material, "F_ADDITIVE_BLEND") != 0;

                var alphaCutoff = FloatParameter(material, "g_flAlphaTestReference",
                    FloatParameter(material, "g_flAlphaCutoff",
                    FloatParameter(material, "g_flOpacityMaskAlphaReference",
                    FloatParameter(material, "g_flAlphaTestRef", 0.5f))));

                var doubleSided = IntParameter(material, "F_RENDER_BACKFACES") != 0
                    || IntParameter(material, "F_DO_NOT_CULL_BACKFACES") != 0
                    || isGlassShader;

                var textures = material.TextureParams.ToDictionary(entry => entry.Key, entry => entry.Value);
                var baseName = BaseTextures.FirstOrDefault(textures.ContainsKey);
                var baseColor = ReadTexture(loader, TexturePath(textures, BaseTextures), maximumTextureDimension);
                var translucency = ReadTexture(loader, TexturePath(textures, TranslucencyTextures), maximumTextureDimension);

                var colorTint = VectorParameter(material, "g_vColorTint",
                    VectorParameter(material, "GlassMaskColor",
                    VectorParameter(material, "g_vGlassTintColor",
                    VectorParameter(material, "g_vColorTint1",
                    VectorParameter(material, "g_vColorTint0", Vector4.One)))));

                // g_vColorTint's alpha is a tint slot, not surface opacity -- csgo_environment
                // and friends write 0 there to mean "no tint", which is most shipped
                // materials.  Taking it as opacity made every alpha-tested material discard
                // wholesale and every translucent one vanish.  Scalar opacity lives in
                // g_flOpacityScale; glass keeps a see-through default when it authors none.
                var opacity = FloatParameter(material, "g_flOpacityScale",
                    FloatParameter(material, "g_flOpacity", isGlassShader ? 0.35f : 1.0f));
                colorTint = new Vector4(colorTint.X, colorTint.Y, colorTint.Z, Math.Clamp(opacity, 0.0f, 1.0f));

                if (translucency is not null)
                {
                    if (baseColor is not null)
                        baseColor = CombineBaseColorWithTranslucency(baseColor, translucency);
                    else if (translucent || alphaTest || isTranslucentShader)
                        baseColor = CreateBaseColorFromTranslucency(translucency, colorTint);
                }

                var normal = baseColorOnly ? null : ReadTexture(loader, TexturePath(textures, NormalTextures), maximumTextureDimension);
                var metal = baseColorOnly ? null : ReadTexture(loader, TexturePath(textures, MetalTextures), maximumTextureDimension);
                var roughness = baseColorOnly ? null : ReadTexture(loader, TexturePath(textures, RoughnessTextures), maximumTextureDimension);
                var roughnessFallback = isGlassShader
                    ? FloatParameter(material, "g_flRoughness", FloatParameter(material, "g_flGlassRoughness", 0.15f))
                    : FloatParameter(material, "g_flRoughness", 1);
                var metallicRoughness = baseColorOnly ? null : CombineMetallicRoughness(normal, metal, roughness,
                    FloatParameter(material, "g_flMetalness", 0), roughnessFallback);

                var alphaMode = translucent ? "BLEND" : alphaTest ? "MASK" : "OPAQUE";
                if (alphaMode == "OPAQUE" && translucency is not null)
                    alphaMode = alphaCutoff > 0 ? "MASK" : "BLEND";

                var suffix = baseName is not null && "123".Contains(baseName[^1], StringComparison.Ordinal) ? baseName[^1].ToString() : "";
                var compiled = new CompiledMaterial(
                    materialPath, baseColor, normal, metallicRoughness,
                    baseColorOnly ? null : ReadTexture(loader, TexturePath(textures, AmbientOcclusionTextures), maximumTextureDimension),
                    baseColorOnly ? null : ReadTexture(loader, TexturePath(textures, EmissiveTextures), maximumTextureDimension),
                    colorTint, metallicRoughness is null ? FloatParameter(material, "g_flMetalness", 0) : 1,
                    roughnessFallback, Vector3.Zero, alphaMode,
                    alphaCutoff, doubleSided,
                    IntParameter(material, "g_nTextureAddressModeU"), IntParameter(material, "g_nTextureAddressModeV"), 0,
                    Vector2Parameter(material, $"g_vTexCoordScale{suffix}", Vector2Parameter(material, "g_vTexCoordScale", Vector2.One)),
                    Vector2Parameter(material, $"g_vTexCoordOffset{suffix}", Vector2Parameter(material, "g_vTexCoordOffset", Vector2.Zero)),
                    Vector2Parameter(material, $"g_vTexCoordCenter{suffix}", Vector2Parameter(material, "g_vTexCoordCenter", new Vector2(0.5f))),
                    FloatParameter(material, $"g_flTexCoordRotation{suffix}", FloatParameter(material, "g_flTexCoordRotation", 0)));

                sharedMaterialCache.TryAdd(cacheKey, compiled);
                return compiled;
            }
        }
        catch
        {
            return DefaultMaterial with { Name = materialPath };
        }
    }

    private CompiledTexture? ReadTexture(GameFileLoader loader, string? texturePath, int maximumDimension)
    {
        if (string.IsNullOrWhiteSpace(texturePath))
            return null;
        var cacheKey = $"{texturePath}:{maximumDimension}";
        if (sharedTextureCache.TryGetValue(cacheKey, out var cached))
            return cached;

        var resource = loader.LoadFileCompiled(texturePath);
        if (resource is null)
            return null;
        using (resource)
        {
            if (resource.DataBlock is not Texture texture)
                return null;
            uint mip = 0;
            var width = (int)texture.ActualWidth;
            var height = (int)texture.ActualHeight;
            while (mip + 1 < texture.NumMipLevels && maximumDimension > 0 && Math.Max(width, height) > maximumDimension)
            {
                mip++;
                width = Math.Max(1, width / 2);
                height = Math.Max(1, height / 2);
            }
            using var bitmap = texture.GenerateBitmap(0, Texture.CubemapFace.PositiveX, mip, texture.RetrieveCodecFromResourceEditInfo());
            var rgba = new byte[bitmap.Width * bitmap.Height * 4];
            var source = bitmap.Bytes;
            for (var index = 0; index < rgba.Length; index += 4)
            {
                rgba[index] = source[index + 2];
                rgba[index + 1] = source[index + 1];
                rgba[index + 2] = source[index];
                rgba[index + 3] = source[index + 3];
            }
            var result = new CompiledTexture(bitmap.Width, bitmap.Height, System.Runtime.InteropServices.ImmutableCollectionsMarshal.AsImmutableArray(rgba));
            sharedTextureCache.TryAdd(cacheKey, result);
            return result;
        }
    }

    private static CompiledTexture? CombineMetallicRoughness(
        CompiledTexture? normal, CompiledTexture? metal, CompiledTexture? roughness, float metallicFactor, float roughnessFactor)
    {
        var reference = normal ?? roughness ?? metal;
        if (reference is null)
            return null;
        var data = new byte[reference.Width * reference.Height * 4];
        for (var pixel = 0; pixel < reference.Width * reference.Height; pixel++)
        {
            var offset = pixel * 4;
            data[offset + 1] = roughness is not null ? Sample(roughness, pixel, reference, 0)
                : normal is not null ? (byte)(255 - Sample(normal, pixel, reference, 3)) : ToByte(roughnessFactor);
            data[offset + 2] = metal is not null ? Sample(metal, pixel, reference, 0) : ToByte(metallicFactor);
            data[offset + 3] = 255;
        }
        return new CompiledTexture(reference.Width, reference.Height, [.. data]);
    }

    private static CompiledTexture CombineBaseColorWithTranslucency(CompiledTexture baseColor, CompiledTexture translucency)
    {
        var width = baseColor.Width;
        var height = baseColor.Height;
        var data = new byte[width * height * 4];
        for (var pixel = 0; pixel < width * height; pixel++)
        {
            var offset = pixel * 4;
            data[offset] = baseColor.Rgba[offset];
            data[offset + 1] = baseColor.Rgba[offset + 1];
            data[offset + 2] = baseColor.Rgba[offset + 2];
            data[offset + 3] = SampleTranslucency(translucency, pixel, baseColor);
        }
        return new CompiledTexture(width, height, [.. data]);
    }

    private static CompiledTexture CreateBaseColorFromTranslucency(CompiledTexture trans, Vector4 tint)
    {
        var width = trans.Width;
        var height = trans.Height;
        var data = new byte[width * height * 4];
        var r = ToByte(tint.X);
        var g = ToByte(tint.Y);
        var b = ToByte(tint.Z);
        for (var pixel = 0; pixel < width * height; pixel++)
        {
            var offset = pixel * 4;
            data[offset] = r;
            data[offset + 1] = g;
            data[offset + 2] = b;
            data[offset + 3] = SampleTranslucency(trans, pixel, trans);
        }
        return new CompiledTexture(width, height, [.. data]);
    }

    private static byte SampleTranslucency(CompiledTexture trans, int pixel, CompiledTexture target)
    {
        var x = pixel % target.Width * trans.Width / target.Width;
        var y = pixel / target.Width * trans.Height / target.Height;
        var offset = (y * trans.Width + x) * 4;
        var r = trans.Rgba[offset];
        var a = trans.Rgba[offset + 3];
        return a < 255 ? a : r;
    }

    private static byte Sample(CompiledTexture texture, int pixel, CompiledTexture target, int channel)
    {
        var x = pixel % target.Width * texture.Width / target.Width;
        var y = pixel / target.Width * texture.Height / target.Height;
        return texture.Rgba[(y * texture.Width + x) * 4 + channel];
    }

    private static byte ToByte(float value) => (byte)Math.Clamp((int)MathF.Round(value * 255), 0, 255);
    private static string? TexturePath(Dictionary<string, string> textures, IEnumerable<string> names) =>
        names.Select(name => textures.GetValueOrDefault(name)).FirstOrDefault(value => value is not null);
    private static int IntParameter(Material material, string name, int fallback = 0)
    {
        foreach (var entry in material.IntParams)
            if (entry.Key == name)
                return checked((int)entry.Value);
        return fallback;
    }

    private static float FloatParameter(Material material, string name, float fallback)
    {
        foreach (var entry in material.FloatParams)
            if (entry.Key == name)
                return entry.Value;
        return fallback;
    }

    private static Vector4 VectorParameter(Material material, string name, Vector4 fallback)
    {
        foreach (var entry in material.VectorParams)
            if (entry.Key == name)
                return entry.Value;
        return fallback;
    }
    private static Vector2 Vector2Parameter(Material material, string name, Vector2 fallback)
    {
        var value = VectorParameter(material, name, new Vector4(fallback, 0, 0));
        return new Vector2(value.X, value.Y);
    }

    private IEnumerable<Mesh> ReadMeshes(GameFileLoader loader, Model model)
    {
        foreach (var entry in model.GetEmbeddedMeshesAndLoD())
            if ((entry.Item4 & 1) != 0)
                yield return entry.Item1;
        foreach (var entry in model.GetReferenceMeshNamesAndLoD())
        {
            if (entry.Item3 != 0 && (entry.Item3 & 1) == 0)
                continue;
            using (var resource = loader.LoadFileCompiled(entry.Item2))
            {
                if (resource?.DataBlock is Mesh mesh)
                    yield return mesh;
            }
        }
    }

    private static Dictionary<string, string> ReadSkinMap(Model model, int skin)
    {
        var result = new Dictionary<string, string>(StringComparer.Ordinal);
        if (skin <= 0)
            return result;
        var groups = model.GetMaterialGroups().ToArray();
        if (skin >= groups.Length)
            return result;
        foreach (var pair in groups[0].Item2.Zip(groups[skin].Item2))
            result[pair.First] = pair.Second;
        return result;
    }

    private static VBIB.RenderInputLayoutField? FindField(
        VBIB.OnDiskBufferData buffer, string semantic, int semanticIndex) =>
        buffer.InputLayoutFields.FirstOrDefault(field =>
            string.Equals(field.SemanticName, semantic, StringComparison.Ordinal)
            && field.SemanticIndex == semanticIndex);

    private static uint[] ReadIndices(VBIB.OnDiskBufferData buffer)
    {
        if (buffer.ElementSizeInBytes == 2)
        {
            var result = new uint[buffer.ElementCount];
            for (var index = 0; index < result.Length; index++)
                result[index] = BitConverter.ToUInt16(buffer.Data, index * 2);
            return result;
        }
        var wide = new uint[buffer.ElementCount];
        Buffer.BlockCopy(buffer.Data, 0, wide, 0, buffer.Data.Length);
        return wide;
    }

    private static void Append(List<float> values, Vector3 vector)
    {
        values.Add(vector.X);
        values.Add(vector.Y);
        values.Add(vector.Z);
    }

    private static void Append(List<float> values, Vector2 vector)
    {
        values.Add(vector.X);
        values.Add(vector.Y);
    }

    private static Vector3 Normalize(Vector3 value) =>
        value.LengthSquared() < 1e-16f ? Vector3.Zero : Vector3.Normalize(value);

    private static (Vector3 Minimum, Vector3 Maximum) Bounds(List<float> vertices)
    {
        var minimum = new Vector3(float.PositiveInfinity);
        var maximum = new Vector3(float.NegativeInfinity);
        for (var index = 0; index < vertices.Count; index += 3)
        {
            var value = new Vector3(vertices[index], vertices[index + 1], vertices[index + 2]);
            minimum = Vector3.Min(minimum, value);
            maximum = Vector3.Max(maximum, value);
        }
        return (minimum, maximum);
    }

    private (string Addon, string RelativePath) Resolve(string resourcePath, string? contextAddon,
        string extension = ".vmdl")
    {
        var path = resourcePath.Replace('\\', '/').Trim('/');
        var addon = string.IsNullOrWhiteSpace(contextAddon) ? activeAddon : contextAddon;
        var addonMatch = AddonPathRegex().Match('/' + path);
        var coreMatch = CorePathRegex().Match('/' + path);
        if (addonMatch.Success)
        {
            addon = addonMatch.Groups[1].Value;
            path = addonMatch.Groups[2].Value;
        }
        else if (coreMatch.Success)
        {
            path = coreMatch.Groups[1].Value;
        }
        path = path.EndsWith(extension + "_c", StringComparison.OrdinalIgnoreCase)
            ? path[..^2]
            : path.EndsWith(extension, StringComparison.OrdinalIgnoreCase) ? path : path + extension;
        return (addon ?? activeAddon, path);
    }

    [GeneratedRegex(@"/csgo_addons/([^/]+)/(.*)$", RegexOptions.IgnoreCase)]
    private static partial Regex AddonPathRegex();

    [GeneratedRegex(@"/csgo/(.*)$", RegexOptions.IgnoreCase)]
    private static partial Regex CorePathRegex();

    private readonly record struct LoaderKey(string Addon, bool UsesAddonFile);
}

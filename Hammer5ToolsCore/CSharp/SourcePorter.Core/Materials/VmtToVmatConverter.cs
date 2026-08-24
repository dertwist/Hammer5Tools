namespace SourcePorter.Core.Materials;

/// <summary>
/// Converts a parsed Source 1 <see cref="VmtFile"/> into a Source 2 <see cref="VmatDocument"/>.
///
/// This is a C# port of the parameter-mapping core of kristiker/source1import's
/// <c>materials_import.py</c> (<c>vmt_to_vmat_pre()</c> tables + <c>convertVmtToVmat()</c> loop),
/// resolved to SourcePorter's CS2 target (see <see cref="ShaderMapping"/>). It gives SourcePorter a
/// <b>non-binary</b> VMT→VMAT path — useful for the missing-asset repair flow and as the basis for
/// fixing custom brush-material scale without relying on Valve's <c>source1import.exe</c>.
///
/// Faithfully ported: the <c>features</c>, <c>textures</c>, <c>transform</c> (the
/// scale/offset that drives correct UV scaling), <c>settings</c>, and <c>SystemAttributes</c>
/// groups, plus the value transforms in <see cref="MaterialValues"/>.
///
/// <para><b>Known limitation (documented in ARCHITECTURE §5).</b> The <c>channeled_masks</c> group —
/// which in the Python tool extracts a single channel from one texture into a new image (e.g.
/// roughness from base-color alpha) — needs per-pixel image work and is <b>not</b> ported here; those
/// entries are skipped rather than emitting a wrong whole-texture reference. Texture-group masks that
/// point at an already-separate mask texture (<c>$envmapmask</c>, <c>$ao</c>, <c>$phongmask</c>, …)
/// <i>are</i> emitted, referencing the converted source texture directly.</para>
/// </summary>
public sealed class VmtToVmatConverter
{
    /// <summary>How a <c>.vmt</c> texture path is rewritten to a <c>.vmat</c> texture reference.
    /// Defaults to <c>materials/&lt;path&gt;.tga</c>; override to point at real on-disk content.</summary>
    public Func<string, string> TexturePathResolver { get; init; } = FixVmtTextureDir;

    /// <summary>Whether to flag normal maps with <c>legacy_source1_inverted_normal</c> instead of
    /// flipping the green channel (mirrors materials_import.py's <c>NORMALMAP_G_VTEX_INVERT</c>).</summary>
    public bool LegacyInvertedNormals { get; init; } = true;

    /// <summary>Converts a VMT to a VMAT document.</summary>
    public VmatDocument Convert(VmtFile vmt)
    {
        var vmat = new VmatDocument { Shader = ShaderMapping.Choose(vmt) + ".vfx" };

        foreach (var (rawKey, rawVal) in vmt.Parameters)
        {
            var key = rawKey.ToLowerInvariant();
            var val = rawVal.Trim().Trim('"', '\'').Trim();

            // A key may appear in more than one group (e.g. $translucent in features), so don't break.
            ApplyFeature(vmat, vmt, key, val);
            ApplyTexture(vmat, key, val);
            ApplyTransform(vmat, key, val);
            ApplySetting(vmat, key, val);
            ApplySystemAttribute(vmat, key, val);
        }

        // Per-shader post-processing: unconditional combo flags gated on the Source 1 shader
        // (e.g. F_LAYERS "1" for worldvertextransition — without it the layer-2 samplers are dead
        // code) and combo flags gated on the presence of a Source 1 key (e.g. F_TEXTURETRANSFORMS
        // only when a layer-2 transform is actually supplied). See docs/blend_material_porting.md §3.
        if (ShaderOverrides.TryGetValue(vmat.Shader, out var ov))
        {
            if (ov.EmitOnSourceShader.TryGetValue(vmt.Shader, out var emit))
                vmat.Set(emit.Key, emit.Value);
            foreach (var (srcKey, flagKey, flagVal) in ov.EmitFlagOnKeys)
                if (vmt.Parameters.ContainsKey(srcKey))
                    vmat.Set(flagKey, flagVal);
        }

        if (vmt.IsToolMaterial)
            ApplyToolAttributes(vmat, vmt);

        return vmat;
    }

    // ---- features -------------------------------------------------------------------------------

    private void ApplyFeature(VmatDocument vmat, VmtFile vmt, string key, string val)
    {
        var f = FeatureFor(vmat.Shader, key);
        if (f is null)
            return;

        var outVal = string.IsNullOrEmpty(val) ? f.Default : val;

        if (f.Transform is not null)
        {
            var rv = f.Transform(val, vmt, vmat);
            if (rv is not null)
                outVal = rv;
        }

        // $translucent becomes a blend-mode selector on decal/overlay shaders.
        if (key == "$translucent" && vmat.Shader is "csgo_projected_decals.vfx" or "csgo_static_overlay.vfx")
        {
            vmat.Set("F_BLEND_MODE", vmat.Shader == "csgo_projected_decals.vfx" ? "0" : "1");
            return;
        }

        foreach (var (ek, ev) in f.Extra)
            vmat.Set(ek, ev);
        vmat.Set(f.Key, outVal);
    }

    // ---- textures -------------------------------------------------------------------------------

    private void ApplyTexture(VmatDocument vmat, string key, string val)
    {
        var t = TextureFor(vmat.Shader, key);
        if (t is null)
            return;

        var outVal = string.IsNullOrEmpty(val) ? Default(t.Suffix) : TexturePathResolver(val);

        // Normal maps: flag the legacy inverted-green convention rather than re-encoding pixels.
        if (key is "$normalmap" or "$bumpmap2" or "$normalmap2"
            && LegacyInvertedNormals
            && outVal != Default("_normal"))
        {
            vmat.Set("legacy_source1_inverted_normal", "1");
        }

        foreach (var (ek, ev) in t.Extra)
            vmat.Set(ek, ev);
        vmat.Set(t.Key, outVal);
    }

    // ---- transform (scale / offset — the UV-scale fix) ------------------------------------------

    private static void ApplyTransform(VmatDocument vmat, string key, string val)
    {
        if (!Transforms.TryGetValue(key, out var vmatKey) || string.IsNullOrEmpty(val))
            return;

        var transform = MaterialValues.TexTransform.Parse(val);

        if (transform.Scale != (1f, 1f)
            && MaterialValues.FixVector(FormattableString.Invariant($"{transform.Scale.X} {transform.Scale.Y}"), addAlpha: false) is { } scale)
            vmat.Set(vmatKey + "Scale", scale);

        if (transform.Translate != (0f, 0f)
            && MaterialValues.FixVector(FormattableString.Invariant($"{transform.Translate.X} {transform.Translate.Y}"), addAlpha: false) is { } offset)
            vmat.Set(vmatKey + "Offset", offset);
    }

    // ---- settings -------------------------------------------------------------------------------

    private static void ApplySetting(VmatDocument vmat, string key, string val)
    {
        var s = SettingFor(vmat.Shader, key);
        if (s is null)
            return;

        var outVal = string.IsNullOrEmpty(val) ? s.Default : val;

        var rv = s.Transform(val);
        if (rv is not null)
            outVal = rv;

        foreach (var (ek, ev) in s.Extra)
            vmat.Set(ek, ev);
        vmat.Set(s.Key, outVal);
    }

    // ---- SystemAttributes -----------------------------------------------------------------------

    private static void ApplySystemAttribute(VmatDocument vmat, string key, string val)
    {
        if (!SystemAttributes.TryGetValue(key, out var attrKey))
            return;
        vmat.SetSystemAttribute(attrKey, string.IsNullOrEmpty(val) ? "default" : val);
    }

    // ---- tool materials -------------------------------------------------------------------------

    private static void ApplyToolAttributes(VmatDocument vmat, VmtFile vmt)
    {
        vmat.SetAttribute("tools.toolsmaterial", "1");
        vmat.SetAttribute("mapbuilder.nodraw", "1");
        vmat.SetAttribute("mapbuilder.nonsolid", "1");

        foreach (var (rawKey, val) in vmt.Parameters)
        {
            if (!rawKey.StartsWith('%'))
                continue;
            var k = rawKey.TrimStart('%');
            if (k.StartsWith("compile", StringComparison.OrdinalIgnoreCase))
                k = k["compile".Length..];
            if (k.Equals("keywords", StringComparison.OrdinalIgnoreCase))
                continue;
            vmat.SetAttribute($"mapbuilder.{k}", val);
        }
    }

    // =============================================================================================
    // Mapping tables (resolved to CS2 / CSGO_EXPORT_TOUCHSTONE), ported from vmt_to_vmat_pre().
    // =============================================================================================

    private sealed record Feature(string Key, string Default, Func<string, VmtFile, VmatDocument, string?>? Transform = null, (string, string)[]? Extra = null)
    {
        public (string, string)[] Extra { get; } = Extra ?? [];
    }

    private sealed record Texture(string Key, string Suffix, (string, string)[]? Extra = null)
    {
        public (string, string)[] Extra { get; } = Extra ?? [];
    }

    private sealed record Setting(string Key, string Default, Func<string, string?> Transform, (string, string)[]? Extra = null)
    {
        public (string, string)[] Extra { get; } = Extra ?? [];
    }

    private static readonly Dictionary<string, string> DetailBlend = new() { ["0"] = "1", ["1"] = "2", ["7"] = "1", ["12"] = "0" };
    private static readonly Dictionary<string, string> DecalBlend = new() { ["0"] = "1", ["1"] = "2", ["12"] = "0" };
    private static readonly Dictionary<string, string> SeqBlend = new() { ["0"] = "1", ["1"] = "2", ["2"] = "3" };

    private static readonly Dictionary<string, Feature> Features = new(StringComparer.OrdinalIgnoreCase)
    {
        ["$translucent"] = new("F_TRANSLUCENT", "1"),
        ["$alphatest"] = new("F_ALPHA_TEST", "1"),
        ["$notint"] = new("F_NOTINT", "1"),
        ["$phong"] = new("F_SPECULAR_DIRECT", "1"),
        ["$envmap"] = new("F_SPECULAR_INDIRECT", "1", FixEnvmap),
        ["$envmapanisotropy"] = new("F_SPECULAR_CUBE_MAP_ANISOTROPIC_WARP", "1"),
        ["$selfillum"] = new("F_SELF_ILLUM", "1"),
        ["$additive"] = new("F_ADDITIVE_BLEND", "1"),
        ["$ignorez"] = new("F_DISABLE_Z_BUFFERING", "1"),
        ["$nocull"] = new("F_RENDER_BACKFACES", "1"),
        ["$decal"] = new("F_OVERLAY", "1"),
        ["$detailblendmode"] = new("F_DETAILTEXTURE", "1", (v, _, _) => MaterialValues.MappedVal(v, DetailBlend)),
        ["$decalblendmode"] = new("F_DETAILTEXTURE", "1", (v, _, _) => MaterialValues.MappedVal(v, DecalBlend)),
        ["$sequence_blend_mode"] = new("F_FAST_SEQUENCE_BLEND_MODE", "1", (v, _, _) => MaterialValues.MappedVal(v, SeqBlend)),
        ["$gradientmodulation"] = new("F_GRADIENTMODULATION", "1"),
        ["$selfillum_envmapmask_alpha"] = new("F_SELF_ILLUM", "1"),
        ["$forceenvmap"] = new("F_REFLECTION_TYPE", "1"),
        ["$addbumpmaps"] = new("F_ADDBUMPMAPS", "1"),
        ["$newlayerblending"] = new("F_FANCY_BLENDING", "1"),
        ["$vertexcolor"] = new("F_VERTEX_COLOR", "1"),
    };

    private static readonly Dictionary<string, Texture> Textures = new(StringComparer.OrdinalIgnoreCase)
    {
        ["$hdrcompressedtexture"] = new("TextureColor", "_color"),
        ["$hdrbasetexture"] = new("TextureColor", "_color"),
        ["$basetexture"] = new("TextureColor", "_color"),
        ["$painttexture"] = new("TextureColor", "_color"),
        ["$material"] = new("TextureColor", "_color"),
        ["$modelmaterial"] = new("TextureColor", "_color"),
        ["$compress"] = new("TextureSquishColor", "_color", [("F_MORPH_SUPPORTED", "1"), ("F_WRINKLE", "1")]),
        ["$stretch"] = new("TextureStretchColor", "_color", [("F_MORPH_SUPPORTED", "1"), ("F_WRINKLE", "1")]),
        ["$normalmap"] = new("TextureNormal", "_normal"),
        ["$bumpcompress"] = new("TextureSquishNormal", "_normal", [("F_MORPH_SUPPORTED", "1"), ("F_WRINKLE", "1")]),
        ["$bumpstretch"] = new("TextureStretchNormal", "_normal", [("F_MORPH_SUPPORTED", "1"), ("F_WRINKLE", "1")]),
        ["$basetexture2"] = new("TextureColorB", "_color"),
        ["$texture2"] = new("TextureColorB", "_color"),
        ["$bumpmap2"] = new("TextureNormalB", "_normal"),
        ["$basetexture3"] = new("TextureLayer2Color", "_color"),
        ["$basetexture4"] = new("TextureLayer3Color", "_color"),
        ["$normalmap2"] = new("TextureNormal2", "_normal", [("F_SECONDARY_NORMAL", "1")]),
        ["$flowmap"] = new("TextureFlow", "", [("F_FLOW_NORMALS", "1"), ("F_FLOW_DEBUG", "1")]),
        ["$flow_noise_texture"] = new("TextureNoise", "_noise", [("F_FLOW_NORMALS", "1"), ("F_FLOW_DEBUG", "2")]),
        ["$detail"] = new("TextureDetail", "_detail", [("F_DETAILTEXTURE", "1")]),
        ["$decaltexture"] = new("TextureDetail", "_detail", [("F_DETAILTEXTURE", "1"), ("F_SECONDARY_UV", "1"), ("g_bUseSecondaryUvForDetailTexture", "1")]),
        ["$detail2"] = new("TextureDetail2", "_detail"),
        ["$selfillummask"] = new("TextureSelfIllumMask", "_selfillummask"),
        ["$tintmasktexture"] = new("TextureTintMask", "_mask", [("F_TINT_MASK", "1")]),
        ["$_vmat_metalmask"] = new("TextureMetalness", "_metal", [("F_METALNESS_TEXTURE", "1")]),
        ["$_vmat_transmask"] = new("TextureTranslucency", "_trans"),
        ["$_vmat_rimmask"] = new("TextureRimMask", "_rimmask"),
        ["$ao"] = new("TextureAmbientOcclusion", "_ao", [("F_AMBIENT_OCCLUSION_TEXTURE", "1")]),
        ["$aotexture"] = new("TextureAmbientOcclusion", "_ao", [("F_AMBIENT_OCCLUSION_TEXTURE", "1")]),
        ["$phongexponenttexture"] = new("TextureSpecularExponent", "_specexp"),
        ["$lightwarptexture"] = new("TextureDiffuseWarp", "_diffusewarp", [("F_DIFFUSE_WARP", "1")]),
        ["$phongwarptexture"] = new("TextureSpecularWarp", "_specwarp", [("F_SPECULAR_WARP", "1")]),
        ["$envmapmask"] = new("TextureRoughness", "_rough"),
        ["$phongmask"] = new("TextureRoughness", "_rough"),
    };

    private static readonly Dictionary<string, string> Transforms = new(StringComparer.OrdinalIgnoreCase)
    {
        ["$basetexturetransform"] = "g_vTexCoord",
        ["$detailtexturetransform"] = "g_vDetailTexCoord",
        ["$bumptransform"] = "g_vNormalTexCoord",
        ["$blendmodulatetransform"] = "g_vBlendModulateTexCoord",
        ["$bumptransform2"] = "g_vLayer2NormalTexCoord",
        ["$basetexturetransform2"] = "g_vLayer2TexCoord",
        ["$texture2transform"] = "g_vTexCoord2",
    };

    private static readonly Dictionary<string, Setting> Settings = new(StringComparer.OrdinalIgnoreCase)
    {
        ["$detailblendfactor"] = new("g_flDetailBlendFactor", "1.000", MaterialValues.FloatVal),
        ["$detailscale"] = new("g_vDetailTexCoordScale", "[1.000 1.000]", v => MaterialValues.FixVector(v, false)),
        ["$detailscale2"] = new("g_vLayer2DetailScale", "[1.000 1.000]", v => MaterialValues.FixVector(v, false)),
        ["$color"] = new("g_vColorTint", "[1.000 1.000 1.000 0.000]", v => MaterialValues.FixVector(v, true)),
        ["$color2"] = new("g_vColorTint", "[1.000 1.000 1.000 0.000]", v => MaterialValues.FixVector(v, true)),
        ["$selfillumtint"] = new("g_vSelfIllumTint", "[1.000 1.000 1.000 0.000]", v => MaterialValues.FixVector(v, true)),
        ["$envmaptint"] = new("g_vEnvironmentMapTint", "[1.000 1.000 1.000 0.000]", v => MaterialValues.FixVector(v, true)),
        ["$emissiveblendtint"] = new("g_vEmissiveTint", "[1.000 1.000 1.000 0.000]", v => MaterialValues.FixVector(v, true)),
        ["$layertint1"] = new("g_vLayer1Tint", "[1.000 1.000 1.000 0.000]", v => MaterialValues.FixVector(v, true)),
        ["$layertint2"] = new("g_vLayer2Tint", "[1.000 1.000 1.000 0.000]", v => MaterialValues.FixVector(v, true)),
        ["$reflecttint"] = new("g_vReflectionTint", "[1.000 1.000 1.000 0.000]", v => MaterialValues.FixVector(v, true)),
        ["$refracttint"] = new("g_vRefractionTint", "[1.000 1.000 1.000 0.000]", v => MaterialValues.FixVector(v, true)),
        ["$fogcolor"] = new("g_vWaterFogColor", "[1.000 1.000 1.000 0.000]", v => MaterialValues.FixVector(v, true)),
        ["$gradientcolorstop0"] = new("g_vGradientColorStop0", "[1.000 1.000 1.000 0.000]", v => MaterialValues.FixVector(v, true)),
        ["$gradientcolorstop1"] = new("g_vGradientColorStop1", "[1.000 1.000 1.000 0.000]", v => MaterialValues.FixVector(v, true)),
        ["$gradientcolorstop2"] = new("g_vGradientColorStop2", "[1.000 1.000 1.000 0.000]", v => MaterialValues.FixVector(v, true)),
        ["$scale2"] = new("g_vTexCoordScale2", "[1.000 1.000]", MaterialValues.UniformVec2),
        ["$scale3"] = new("g_vTexCoordScale3", "[1.000 1.000]", MaterialValues.UniformVec2),
        ["$scale4"] = new("g_vTexCoordScale4", "[1.000 1.000]", MaterialValues.UniformVec2),
        ["$phongtint"] = new("g_vSpecularColor", "[1.000 1.000 1.000 0.000]", v => MaterialValues.FixVector(v, true)),
        ["$frame"] = new("g_flAnimationFrame", "0.000", MaterialValues.FloatVal, [("F_TEXTURE_ANIMATION", "1")]),
        ["$alpha"] = new("g_flOpacityScale", "1.000", MaterialValues.FloatVal),
        ["$alphatestreference"] = new("g_flAlphaTestReference", "0.500", MaterialValues.FloatVal, [("g_flAntiAliasedEdgeStrength", "1.0")]),
        ["$blendtintcoloroverbase"] = new("g_flModelTintAmount", "1.000", MaterialValues.FloatVal),
        ["$selfillumscale"] = new("g_flSelfIllumScale", "1.000", MaterialValues.FloatVal),
        ["$phongexponent"] = new("g_flSpecularExponent", "32.000", MaterialValues.FloatVal),
        ["$phongboost"] = new("g_flPhongBoost", "1.000", MaterialValues.FloatVal),
        ["$metalness"] = new("g_flMetalness", "0.000", MaterialValues.FloatVal),
        ["$_metalness2"] = new("g_flMetalnessB", "0.000", MaterialValues.FloatVal),
        ["$flow_worlduvscale"] = new("g_flWorldUvScale", "1.000", MaterialValues.FloatVal),
        ["$flow_noise_scale"] = new("g_flNoiseUvScale", "0.010", MaterialValues.FloatVal),
        ["$nofog"] = new("g_bFogEnabled", "0", v => MaterialValues.BoolVal(v, invert: true)),
        ["$notint"] = new("g_flModelTintAmount", "1.000", v => MaterialValues.BoolVal(v, invert: true)),
        ["$allowdiffusemodulation"] = new("g_flModelTintAmount", "1.000", v => MaterialValues.BoolVal(v, invert: false)),
        ["$rimlightscale"] = new("g_flRimLightScale", "1.000", MaterialValues.FloatVal),
        ["$rimlightcolor"] = new("g_vRimLightColor", "[1.000000 1.000000 1.000000 0.000000]", v => MaterialValues.FixVector(v, true)),
        ["$blendsoftness"] = new("g_flLayer1BlendSoftness", "0.500", MaterialValues.FloatVal),
        ["$layerborderstrenth"] = new("g_flLayer1BorderStrength", "0.500", MaterialValues.FloatVal),
        ["$layerborderoffset"] = new("g_flLayer1BorderOffset", "0.000", MaterialValues.FloatVal),
        ["$layerbordersoftness"] = new("g_flLayer1BorderSoftness", "0.500", MaterialValues.FloatVal),
        ["$layerbordertint"] = new("g_vLayer1BorderColor", "[1.000000 1.000000 1.000000 0.000000]", v => MaterialValues.FixVector(v, true)),
    };

    private static readonly Dictionary<string, string> SystemAttributes = new(StringComparer.OrdinalIgnoreCase)
    {
        ["$surfaceprop"] = "PhysicsSurfaceProperties",
        ["$surfaceprop2"] = "PhysicsSurfaceProperties2",
        ["$surfaceprop3"] = "PhysicsSurfaceProperties3",
        ["$surfaceprop4"] = "PhysicsSurfaceProperties4",
    };

    // =============================================================================================
    // Per-shader overrides.
    //
    // The flat tables above are applied to *every* target shader, but the correct Source 2 parameter
    // names are per-shader: TextureColorB is right for csgo_simple_2way_blend.vfx and wrong for
    // csgo_lightmappedgeneric.vfx (which wants TextureLayer2Color). Changing the shared tables in
    // place would silently break the majority csgo_complex path. This override layer keeps the flat
    // tables as the default and substitutes per-key for the shaders listed here. See
    // docs/blend_material_porting.md (measured from 750 decompiled shipped CS2 materials, not inferred).
    // =============================================================================================

    /// <summary>Per-shader substitutions layered on top of the shared flat tables. Only the S2 shader
    /// names that need correction are listed; any key absent from the override falls through to the
    /// flat table. Minimal by design — extend only when a shader's real parameter names are known.</summary>
    private sealed record ShaderOverride
    {
        public Dictionary<string, Texture> Textures { get; init; } = new(StringComparer.OrdinalIgnoreCase);
        public Dictionary<string, Setting> Settings { get; init; } = new(StringComparer.OrdinalIgnoreCase);
        public Dictionary<string, Feature> Features { get; init; } = new(StringComparer.OrdinalIgnoreCase);

        /// <summary>Layer0 keys force-emitted after the parameter loop, gated on the Source 1 shader.
        /// Used for combo flags that are unconditional for a given S1 shader — chiefly
        /// <c>F_LAYERS "1"</c> for <c>worldvertextransition</c>, the combo that makes layer-2
        /// samplers non-dead-code (research doc fact #1).</summary>
        public Dictionary<string, (string Key, string Value)> EmitOnSourceShader { get; init; } = new(StringComparer.OrdinalIgnoreCase);

        /// <summary>Combo flags emitted only when the named Source 1 key is actually present — e.g.
        /// <c>F_TEXTURETRANSFORMS "1"</c> is emitted only if one of the layer-2 transform keys is
        /// supplied, matching how Valve ships the feature.</summary>
        public (string SourceKey, string FlagKey, string FlagValue)[] EmitFlagOnKeys { get; init; } = [];
    }

    /// <summary>Override for <c>csgo_lightmappedgeneric.vfx</c>, populated from
    /// <c>docs/blend_material_porting.md §3</c> (the WorldVertexTransition → csgo_lightmappedgeneric
    /// table). Layer 1 is asymmetric: albedo is TextureColor, but normal/AO/detail are Layer1-prefixed;
    /// layer 2 is fully prefixed. Note $bumpmap is folded into $normalmap by VmtFile, so the layer-1
    /// normal override keys off $normalmap; $bumpmap2 is not folded.</summary>
    private static readonly ShaderOverride LightmappedGenericOverride = new()
    {
        Textures =
        {
            // Layer 1 normal: TextureNormal → TextureLayer1NormalRoughness ($bumpmap folded to $normalmap).
            ["$normalmap"] = new("TextureLayer1NormalRoughness", "_normal"),
            // Layer 2 (fully prefixed, replacing the flat TextureColorB/TextureNormalB).
            ["$basetexture2"] = new("TextureLayer2Color", "_color"),
            ["$texture2"] = new("TextureLayer2Color", "_color"),
            ["$bumpmap2"] = new("TextureLayer2NormalRoughness", "_normal"),
            // $detail: TextureDetail → TextureLayer1Detail; flag spelling is F_DETAILTEXTURE (no underscore).
            ["$detail"] = new("TextureLayer1Detail", "_detail", [("F_DETAILTEXTURE", "1")]),
            // $blendmodulatetexture was dropped entirely — it has no flat-table entry at all.
            ["$blendmodulatetexture"] = new("TextureBlendModulation", "", [("F_FANCY_BLENDING", "1")]),
        },
        Settings =
        {
            // g_vLayer1DetailScale is a vec4 [s s 0 0]; $detailscale is scalar/vec2 (flat table emits vec2).
            ["$detailscale"] = new("g_vLayer1DetailScale", "[1.000000 1.000000 0.000000 0.000000]", Layer1DetailScale),
            // g_vLayer1DetailTintAndBlend is [1 1 1 <factor>]; $detailblendfactor is the w component.
            ["$detailblendfactor"] = new("g_vLayer1DetailTintAndBlend", "[1.000000 1.000000 1.000000 1.000000]", Layer1DetailTintAndBlend),
            // $color/$color2 both collapse to g_vColorTint in the flat table; here they split per layer.
            ["$color"] = new("g_vLayer1Tint", "[1.000000 1.000000 1.000000 0.000000]", v => MaterialValues.FixVector(v, true)),
            ["$color2"] = new("g_vLayer2Tint", "[1.000000 1.000000 1.000000 0.000000]", v => MaterialValues.FixVector(v, true)),
            // Border/softness settings drop the "1" suffix (0 uses of the Layer1-prefixed spellings shipped).
            ["$blendsoftness"] = new("g_flBlendSoftness", "0.500", MaterialValues.FloatVal),
            ["$layerborderstrenth"] = new("g_flLayerBorderStrength", "0.500", MaterialValues.FloatVal),
            ["$layerborderoffset"] = new("g_flLayerBorderOffset", "0.000", MaterialValues.FloatVal),
            ["$layerbordersoftness"] = new("g_flLayerBorderSoftness", "0.500", MaterialValues.FloatVal),
            ["$layerbordertint"] = new("g_vLayerBorderTint", "[1.000000 1.000000 1.000000 0.000000]", v => MaterialValues.FixVector(v, true)),
        },
        Features =
        {
            // $detailblendmode: F_DETAIL_TEXTURE → F_DETAILBLENDMODE (existing DetailBlend map reused).
            ["$detailblendmode"] = new("F_DETAILBLENDMODE", "0", (v, _, _) => MaterialValues.MappedVal(v, DetailBlend)),
        },
        // F_LAYERS "1" is what enables blending (research doc fact #1). Emitted for worldvertextransition
        // only — NOT for plain lightmappedgeneric (single-layer materials must stay single-layer), and
        // deliberately not for multiblend either (out of scope; csgo_lightmappedgeneric only ships 2 layers).
        EmitOnSourceShader =
        {
            ["worldvertextransition"] = ("F_LAYERS", "1"),
        },
        // F_TEXTURETRANSFORMS gates the g_v*TexCoord transform block. The transform key mappings live in
        // the flat Transforms table (already correct); only the combo flag was missing.
        EmitFlagOnKeys =
        [
            ("$basetexturetransform2", "F_TEXTURETRANSFORMS", "1"),
            ("$bumptransform2", "F_TEXTURETRANSFORMS", "1"),
            ("$blendmodulatetransform", "F_TEXTURETRANSFORMS", "1"),
        ],
    };

    private static readonly Dictionary<string, ShaderOverride> ShaderOverrides = new(StringComparer.Ordinal)
    {
        ["csgo_lightmappedgeneric.vfx"] = LightmappedGenericOverride,
    };

    // Per-shader-aware table lookups: prefer an override entry for the resolved shader, else fall
    // through to the flat table. Returning null means "no mapping for this key" (Apply* then returns).
    private static Texture? TextureFor(string shader, string key)
        => ShaderOverrides.TryGetValue(shader, out var ov) && ov.Textures.TryGetValue(key, out var t)
            ? t : Textures.TryGetValue(key, out var fb) ? fb : null;

    private static Feature? FeatureFor(string shader, string key)
        => ShaderOverrides.TryGetValue(shader, out var ov) && ov.Features.TryGetValue(key, out var f)
            ? f : Features.TryGetValue(key, out var fb) ? fb : null;

    private static Setting? SettingFor(string shader, string key)
        => ShaderOverrides.TryGetValue(shader, out var ov) && ov.Settings.TryGetValue(key, out var s)
            ? s : Settings.TryGetValue(key, out var fb) ? fb : null;

    // ---- helpers (ported) -----------------------------------------------------------------------

    /// <summary>Ported from <c>fix_envmap</c>: drive metalness/cube-map flags from the env-map value.</summary>
    private static string? FixEnvmap(string val, VmtFile vmt, VmatDocument vmat)
    {
        if (val.Contains("environment maps/metal", StringComparison.OrdinalIgnoreCase))
            vmat.Set("g_flMetalness", val.Equals("environment maps/metal_generic_003", StringComparison.OrdinalIgnoreCase) ? "0.550000" : "0.888000");
        else if (val.Equals("env_cubemap", StringComparison.OrdinalIgnoreCase))
            vmat.Set("F_SPECULAR_CUBE_MAP", "1");
        else
        {
            vmat.Set("F_SPECULAR_CUBE_MAP", "2");
            vmat.Set("TextureCubeMap", Default("_cube", ".pfm"));
        }
        return "1";
    }

    /// <summary>Ported from <c>default()</c>: the placeholder texture path for a suffix.</summary>
    private static string Default(string suffix, string extension = ".tga")
        => "materials/default/default" + suffix + extension;

    /// <summary>Ported from <c>fixVmtTextureDir</c>: <c>foo\bar.vtf</c> -> <c>materials/foo/bar.tga</c>.</summary>
    private static string FixVmtTextureDir(string localPath)
    {
        if (string.IsNullOrWhiteSpace(localPath))
            return string.Empty;

        var p = localPath.Replace('\\', '/').TrimStart('/');
        var dot = p.LastIndexOf('.');
        var slash = p.LastIndexOf('/');
        if (dot > slash)
            p = p[..dot];
        return "materials/" + p + ".tga";
    }

    // ---- blend-material transforms (csgo_lightmappedgeneric.vfx, research doc §3) --------------

    /// <summary><c>g_vLayer1DetailScale</c> is a vec4 <c>[s s 0 0]</c>; the Source 1
    /// <c>$detailscale</c> is a scalar or vec2. Reuse FixVector for the xy, then pad z/w with zero.
    /// (E.g. <c>12</c> → <c>[12.000000 12.000000 0.000000 0.000000]</c>.)</summary>
    private static string? Layer1DetailScale(string v)
        => MaterialValues.FixVector(v, addAlpha: false) is { } xy
            ? xy.TrimEnd(']') + " 0.000000 0.000000]"
            : null;

    /// <summary><c>g_vLayer1DetailTintAndBlend</c> is <c>[1 1 1 &lt;factor&gt;]</c>; the Source 1
    /// <c>$detailblendfactor</c> supplies the w component, RGB tint is fixed at white.
    /// (E.g. <c>0.25</c> → <c>[1.000000 1.000000 1.000000 0.250000]</c>.)</summary>
    private static string? Layer1DetailTintAndBlend(string v)
        => MaterialValues.FloatVal(v) is { } f
            ? $"[1.000000 1.000000 1.000000 {f}]"
            : null;
}

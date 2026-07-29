namespace SourcePorter.Core.Materials;

/// <summary>
/// Resolves a Source 1 <c>.vmt</c> shader to its Source 2 equivalent. Ported from
/// <c>shaderDict</c> + <c>chooseShader()</c> in materials_import.py, with every build-branch
/// conditional collapsed to SourcePorter's target: <b>CS2 with CSGO_EXPORT_TOUCHSTONE</b> — i.e.
/// the Source-1-ported <c>csgo_*</c> shaders (<c>csgo_lightmappedgeneric</c>, <c>csgo_vertexlitgeneric</c>,
/// …) that match what Valve's own <c>source1import</c> emits for ported maps, rather than the newer
/// stock <c>csgo_*</c> core shaders.
/// </summary>
internal static class ShaderMapping
{
    // shaderDict resolved for CS2/touchstone (only the values reachable without an earlier touchstone match).
    private static readonly Dictionary<string, string> Resolved = new(StringComparer.OrdinalIgnoreCase)
    {
        ["black"] = "black",
        ["sky"] = "sky",
        ["unlitgeneric"] = "csgo_complex",
        ["vertexlitgeneric"] = "csgo_complex",
        ["decalmodulate"] = "csgo_projected_decals",
        ["lightmappedgeneric"] = "csgo_complex",
        ["lightmappedreflective"] = "csgo_complex",
        ["character"] = "csgo_complex",
        ["customcharacter"] = "csgo_complex",
        ["teeth"] = "csgo_complex",
        ["water"] = "csgo_water",
        ["refract"] = "csgo_refract",
        ["worldvertextransition"] = "csgo_lightmappedgeneric",
        ["lightmapped_4wayblend"] = "csgo_lightmappedgeneric",
        ["multiblend"] = "csgo_lightmappedgeneric",
        ["lightmappedtwotexture"] = "csgo_complex",
        ["unlittwotexture"] = "csgo_complex",
        ["cable"] = "cables",
        ["splinerope"] = "cables",
        ["shatteredglass"] = "csgo_glass",
        ["wireframe"] = "tools_wireframe",
        ["wireframe_dx9"] = "error",
        ["weapondecal"] = "csgo_weapon_sticker",
        ["patch"] = "csgo_complex",
        ["customweapon"] = "csgo_weapon",
    };

    /// <summary>The Source 2 shader name (without the <c>.vfx</c> extension) for a parsed material.</summary>
    public static string Choose(VmtFile vmt)
    {
        if (!Resolved.ContainsKey(vmt.Shader))
            return "csgo_black_unlit";

        if (vmt.IsToolMaterial)
            return "generic";

        // CSGO_EXPORT_TOUCHSTONE overrides for the Source-1-ported shaders.
        switch (vmt.Shader)
        {
            case "lightmappedgeneric":
            case "worldvertextransition":
                return "csgo_lightmappedgeneric";
            case "lightmapped_4wayblend":
                return "csgo_lightmapped_4wayblend";
            case "vertexlitgeneric":
                return "csgo_vertexlitgeneric";
            case "unlitgeneric":
                if (vmt["$moondome"] == "1") return "csgo_moondome";
                if (vmt["$beachfoam"] == "1") return "csgo_beachfoam";
                return "csgo_unlitgeneric";
            case "character":
            case "customcharacter":
                return "csgo_character";
            case "decal_modulate":
                return "csgo_decal_modulate";
        }

        if (vmt.Shader == "decalmodulate")
            return "csgo_projected_decals";

        // $decal -> static_decal_solution() -> main_ubershader() on CS2.
        if (vmt["$decal"] == "1")
            return "csgo_complex";

        return Resolved[vmt.Shader];
    }
}

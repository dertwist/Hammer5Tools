using SourcePorter.Core.Toolchain;

namespace SourcePorter.Core.Tests;

public class ToolMaterialFallbackTests : IDisposable
{
    private readonly string _root = Path.Combine(Path.GetTempPath(), "sptool_" + Guid.NewGuid().ToString("N"));
    private string Csgo => Path.Combine(_root, "csgo");

    public ToolMaterialFallbackTests() => Directory.CreateDirectory(Csgo);

    private void Write(string relForward, string content)
    {
        var full = Path.Combine(Csgo, relForward.Replace('/', Path.DirectorySeparatorChar));
        Directory.CreateDirectory(Path.GetDirectoryName(full)!);
        File.WriteAllText(full, content);
    }

    [Fact]
    public void Extracts_materials_under_tools_path()
    {
        var materials = new List<string> { "materials/tools/toolsclip_tile.vmt", "materials/wood/plain.vmt" };
        var tools = MissingAssetImporter.ExtractToolMaterials(materials);

        Assert.Equal(new[] { "materials/tools/toolsclip_tile.vmt" }, tools);
        Assert.Equal(new[] { "materials/wood/plain.vmt" }, materials); // non-tool stays for the toolchain
    }

    [Fact]
    public void Material_with_compile_keys_outside_tools_path_is_not_a_tool_material()
    {
        // Faithful to upstream is_tool_material: only materials/tools/tools* are tool materials —
        // %compile* keys alone (e.g. water's %compilewater) do NOT make a tool material.
        var materials = new List<string> { "materials/custom/clip_special.vmt" };
        var tools = MissingAssetImporter.ExtractToolMaterials(materials);

        Assert.Empty(tools);
        Assert.Single(materials);
    }

    [Fact]
    public void Leaves_normal_material_for_the_toolchain()
    {
        var materials = new List<string> { "materials/wood/floor.vmt" };
        var tools = MissingAssetImporter.ExtractToolMaterials(materials);

        Assert.Empty(tools);
        Assert.Single(materials);
    }

    public void Dispose()
    {
        if (Directory.Exists(_root))
            Directory.Delete(_root, recursive: true);
    }
}

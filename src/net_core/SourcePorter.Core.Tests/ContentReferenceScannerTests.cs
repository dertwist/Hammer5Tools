using System.Text;
using SourcePorter.Core.Validation;

namespace SourcePorter.Core.Tests;

public class ContentReferenceScannerTests
{
    [Fact]
    public void Extracts_prefab_maps_materials_models_and_mesh_sources()
    {
        // A text vmap-ish blob with each kind of reference.
        var text =
            "\"map_asset_references\" \"string_array\" [ \"maps/prefabs/lvl/lvl_gameplay.vmap\" ]\n" +
            "material \"materials/concrete/floor_a.vmat\"\n" +
            "model \"models/props/crate.vmdl\"\n" +
            "filename \"models/props/crate.dmx\"\n";

        var refs = ContentReferenceScanner.Extract(text);

        Assert.Contains(refs, r => r.Path == "maps/prefabs/lvl/lvl_gameplay.vmap" && r.Kind == ContentReferenceScanner.ReferenceKind.PrefabMap);
        Assert.Contains(refs, r => r.Path == "materials/concrete/floor_a.vmat" && r.Kind == ContentReferenceScanner.ReferenceKind.Material);
        Assert.Contains(refs, r => r.Path == "models/props/crate.vmdl" && r.Kind == ContentReferenceScanner.ReferenceKind.Model);
        Assert.Contains(refs, r => r.Path == "models/props/crate.dmx" && r.Kind == ContentReferenceScanner.ReferenceKind.MeshSource);
    }

    [Fact]
    public void Extracts_texture_references_from_all_source_extensions()
    {
        var text =
            "TextureColor \"materials/de_coastal/sand.tga\"\n" +
            "TextureNormal \"materials/de_coastal/sand_normal.png\"\n" +
            "TextureRoughness \"materials/de_coastal/sand_rough.psd\"\n";

        var refs = ContentReferenceScanner.Extract(text);

        Assert.Contains(refs, r => r.Path == "materials/de_coastal/sand.tga" && r.Kind == ContentReferenceScanner.ReferenceKind.Texture);
        Assert.Contains(refs, r => r.Path == "materials/de_coastal/sand_normal.png" && r.Kind == ContentReferenceScanner.ReferenceKind.Texture);
        Assert.Contains(refs, r => r.Path == "materials/de_coastal/sand_rough.psd" && r.Kind == ContentReferenceScanner.ReferenceKind.Texture);
    }

    [Fact]
    public void Finds_paths_embedded_in_binary_data()
    {
        // Simulate binary DMX: paths surrounded by null bytes / non-path noise.
        var bytes = new List<byte>();
        bytes.AddRange(Encoding.Latin1.GetBytes("\0\0\x05CGStringTable"));
        bytes.Add(0);
        bytes.AddRange(Encoding.Latin1.GetBytes("models/props/coop_apc/coop_apc.vmdl"));
        bytes.Add(0);
        bytes.AddRange(Encoding.Latin1.GetBytes("materials/metal/metalwall047a.vmat"));
        bytes.Add(0);

        var refs = ContentReferenceScanner.Extract(Encoding.Latin1.GetString(bytes.ToArray()));

        Assert.Contains(refs, r => r.Path == "models/props/coop_apc/coop_apc.vmdl" && r.Kind == ContentReferenceScanner.ReferenceKind.Model);
        Assert.Contains(refs, r => r.Path == "materials/metal/metalwall047a.vmat" && r.Kind == ContentReferenceScanner.ReferenceKind.Material);
    }

    [Fact]
    public void Dedupes_repeated_references()
    {
        var text = "models/a.vmdl models/a.vmdl models\\a.vmdl";

        var refs = ContentReferenceScanner.Extract(text);

        Assert.Single(refs);
        Assert.Equal("models/a.vmdl", refs[0].Path);
    }

    [Fact]
    public void Ignores_unrelated_text()
    {
        Assert.Empty(ContentReferenceScanner.Extract("the quick brown fox / jumped.over"));
    }
}

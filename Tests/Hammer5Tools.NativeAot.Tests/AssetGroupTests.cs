namespace Hammer5Tools.Core.Tests;

public sealed class AssetGroupTests
{
    [Test]
    [Arguments("prop_01_c", ".fbx", "prop_01_c")]
    [Arguments("prop_01_d", ".obj", "prop_01_d")]
    [Arguments("prop_01_n", ".dmx", "prop_01_n")]
    [Arguments("phys_prop_01_c", ".fbx", "prop_01_c")]
    [Arguments("prop_01_c_lod1", ".fbx", "prop_01_c")]
    [Arguments("prop_01_c", ".png", "prop_01")]
    [Arguments("prop_01_d", ".tga", "prop_01")]
    [Arguments("prop_01_c_normal", ".png", "prop_01_c")]
    [Arguments("mesh_prop_01_c", ".png", "prop_01")]
    [Arguments("prop_01_high", ".png", "prop_01")]
    [Arguments("phys_crate", "", "crate")]
    public async Task GroupsAffixesBySourceType(string name, string extension, string expected)
    {
        await Assert.That(CoreApi.NormalizeAssetGroupName(name, extension)).IsEqualTo(expected);
    }

    [Test]
    public async Task PreservesExplicitLegacyAlgorithm()
    {
        await Assert.That(CoreApi.NormalizeAssetGroupName("prop_01_c", ".fbx", 1)).IsEqualTo("prop_01");
    }

    [Test]
    public async Task KeepsUnassignedReferenceMaterialsAtTheirOriginalPaths()
    {
        var result = CoreApi.RenderAssetGroupTemplate("""
            {"content":"#$FOLDER_PATH$#/#$MESH$# | #$FOLDER_PATH$#/#$MATERIAL$# | #$MATERIAL_1_PATH$#",
             "name":"prop_01_c","folder":"models/test23","slots":{"mesh":"prop_01_c.fbx"},
             "materialSources":{"material":"dev/panorama_world_panel_hint_ui.vmat","material_1":"materials/rocks/rock.vmat"}}
            """);
        await Assert.That(result).IsEqualTo(
            "models/test23/prop_01_c.fbx | dev/panorama_world_panel_hint_ui.vmat | materials/rocks/rock.vmat");
    }

    [Test]
    public async Task AssignedMaterialOverridesReferenceFallback()
    {
        var result = CoreApi.RenderAssetGroupTemplate("""
            {"content":"#$FOLDER_PATH$#/#$MATERIAL$#","folder":"models/test23",
             "slots":{"material":"prop_01_c.vmat"},"materialSources":{"material":"dev/old.vmat"}}
            """);
        await Assert.That(result).IsEqualTo("models/test23/prop_01_c.vmat");
    }

    [Test]
    public async Task ExpandsReplacementsAndRemovesUnavailableConditionalBlocks()
    {
        var result = CoreApi.RenderAssetGroupTemplate("""
            {"content":"old #$ASSET_NAME$# #$MESH_NAME$#<!-- IF MESH --> mesh<!-- ENDIF --><!-- IF COLLISION --> collision<!-- ENDIF -->",
             "name":"crate_c","slots":{"mesh":"models/crate_c.fbx","collision":"models/crate_c_phys.fbx"},
             "skippedSlots":["collision"],"replacements":[{"from":"old","to":"new"}]}
            """);
        await Assert.That(result).IsEqualTo("new crate_c crate_c mesh");
    }
}

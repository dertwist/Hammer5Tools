using Datamodel;
using DM = Datamodel.Datamodel;
using SourcePorter.Core.Domain;
using SourcePorter.Core.Validation;

namespace SourcePorter.Core.Tests;

/// <summary>
/// End-to-end validator tests with a synthetic content tree (no CS2 install needed):
/// <see cref="GameInfo.ReadSearchDirs"/> falls back to defaults when gameinfo.gi is
/// absent, and <see cref="VpkIndex"/> / the validator's SafeEnumerate tolerate missing
/// directories, so the content-reference pass — including the vmdl→dmx graph follow —
/// can be exercised in isolation. Model <c>.dmx</c> meshes are built with the real
/// <c>KeyValues2</c> serializer so the structural material walker runs on true DMX.
/// </summary>
public class AssetValidatorTests
{
    // A material referenced only inside a model's .dmx mesh must surface as a missing
    // import: the validator follows the vmdl→dmx reference and parses the mesh structurally.
    [Fact]
    public void Dmx_material_referenced_only_inside_mesh_is_flagged()
    {
        var root = NewTempDir();
        try
        {
            const string addon = "dmx_addon";
            var cs2 = new Cs2Install(root);
            var content = cs2.ContentAddonDir(addon);

            // The .vmdl references its mesh source but NOT the material directly.
            Write(content, "models/props/crate.vmdl", "mesh \"models/props/crate.dmx\"\n");
            // The material reference lives only inside the .dmx (a real DMX model mesh).
            WriteModelDmx(content, "models/props/crate.dmx", ["materials/hidden/skin.vmat"]);

            var report = new AssetValidator(cs2, addon).Validate();

            var issue = Assert.Single(report.Issues,
                i => i.Kind == AssetIssueKind.MissingImport && i.ReferencePath == "materials/hidden/skin.vmat");
            Assert.Contains("material not imported", issue.Detail);
        }
        finally { Directory.Delete(root, recursive: true); }
    }

    // The same dmx-buried material, but present in the addon content tree, is not flagged.
    [Fact]
    public void Dmx_material_that_exists_is_not_flagged()
    {
        var root = NewTempDir();
        try
        {
            const string addon = "dmx_addon";
            var cs2 = new Cs2Install(root);
            var content = cs2.ContentAddonDir(addon);

            Write(content, "models/props/crate.vmdl", "mesh \"models/props/crate.dmx\"\n");
            WriteModelDmx(content, "models/props/crate.dmx", ["materials/hidden/skin.vmat"]);
            Write(content, "materials/hidden/skin.vmat", "present\n");

            var report = new AssetValidator(cs2, addon).Validate();

            Assert.DoesNotContain(report.Issues,
                i => i.ReferencePath == "materials/hidden/skin.vmat");
        }
        finally { Directory.Delete(root, recursive: true); }
    }

    // Two .vmdl files referencing the same .dmx: the mesh is scanned once, so the buried
    // material is checked and (here) reported exactly once.
    [Fact]
    public void Dmx_scanned_once_even_if_referenced_twice()
    {
        var root = NewTempDir();
        try
        {
            const string addon = "dmx_addon";
            var cs2 = new Cs2Install(root);
            var content = cs2.ContentAddonDir(addon);

            Write(content, "models/a.vmdl", "mesh \"models/shared/m.dmx\"\n");
            Write(content, "models/b.vmdl", "mesh \"models/shared/m.dmx\"\n");
            WriteModelDmx(content, "models/shared/m.dmx", ["materials/hidden/skin.vmat"]);

            var report = new AssetValidator(cs2, addon).Validate();

            Assert.Single(report.Issues,
                i => i.Kind == AssetIssueKind.MissingImport && i.ReferencePath == "materials/hidden/skin.vmat");
        }
        finally { Directory.Delete(root, recursive: true); }
    }

    // A texture a .vmat references but that wasn't imported into the addon is flagged as a
    // missing import (source-only: a .tga/.png/.psd under materials/ must exist in the addon).
    [Fact]
    public void Vmat_texture_not_in_addon_is_flagged()
    {
        var root = NewTempDir();
        try
        {
            const string addon = "tex_addon";
            var cs2 = new Cs2Install(root);
            var content = cs2.ContentAddonDir(addon);

            Write(content, "materials/de_coastal/sand.vmat",
                "TextureColor \"materials/de_coastal/sand.tga\"\n");
            // No texture file on disk.

            var report = new AssetValidator(cs2, addon).Validate();

            Assert.Single(report.Issues,
                i => i.Kind == AssetIssueKind.MissingImport && i.ReferencePath == "materials/de_coastal/sand.tga");
        }
        finally { Directory.Delete(root, recursive: true); }
    }

    // The referenced texture is present in the addon → not flagged.
    [Fact]
    public void Vmat_texture_present_is_not_flagged()
    {
        var root = NewTempDir();
        try
        {
            const string addon = "tex_addon";
            var cs2 = new Cs2Install(root);
            var content = cs2.ContentAddonDir(addon);

            Write(content, "materials/de_coastal/sand.vmat",
                "TextureColor \"materials/de_coastal/sand.tga\"\n");
            Write(content, "materials/de_coastal/sand.tga", "pixels");

            var report = new AssetValidator(cs2, addon).Validate();

            Assert.DoesNotContain(report.Issues,
                i => i.ReferencePath == "materials/de_coastal/sand.tga");
        }
        finally { Directory.Delete(root, recursive: true); }
    }

    // The reference says .tga but the importer actually wrote .png → accepted (alt extension),
    // and a materials/default/ placeholder is never reported even with no file on disk.
    [Fact]
    public void Vmat_texture_alt_extension_and_default_placeholder_resolve()
    {
        var root = NewTempDir();
        try
        {
            const string addon = "tex_addon";
            var cs2 = new Cs2Install(root);
            var content = cs2.ContentAddonDir(addon);

            // Reference points at .tga; only the .png source exists — still resolves.
            Write(content, "materials/de_coastal/sand.vmat",
                "TextureColor \"materials/de_coastal/sand.tga\"\n" +
                "TextureNormal \"materials/default/default_normal.tga\"\n");
            Write(content, "materials/de_coastal/sand.png", "pixels");
            // default_normal.tga intentionally absent — ships in base CS2, never flagged.

            var report = new AssetValidator(cs2, addon).Validate();

            Assert.DoesNotContain(report.Issues, i => i.ReferencePath == "materials/de_coastal/sand.tga");
            Assert.DoesNotContain(report.Issues, i => i.ReferencePath == "materials/default/default_normal.tga");
        }
        finally { Directory.Delete(root, recursive: true); }
    }

    private static string NewTempDir()
    {
        var root = Path.Combine(Path.GetTempPath(), "avtest_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        return root;
    }

    // File.WriteAllText throws if the parent dir is missing, so create it first. Paths are
    // passed content-relative with forward slashes (the asset-root convention the scanner uses).
    private static void Write(string contentRoot, string relPath, string contents)
    {
        var full = Path.Combine(contentRoot, relPath.Replace('/', Path.DirectorySeparatorChar));
        Directory.CreateDirectory(Path.GetDirectoryName(full)!);
        File.WriteAllText(full, contents);
    }

    // Builds a real Source 2 model .dmx (DmeModel → DmeDag → DmeMesh → DmeFaceSet →
    // DmeMaterial[mtlName]) with one face set per material path, serialized as text KeyValues2.
    private static void WriteModelDmx(string contentRoot, string relPath, string[] materialPaths)
    {
        var full = Path.Combine(contentRoot, relPath.Replace('/', Path.DirectorySeparatorChar));
        Directory.CreateDirectory(Path.GetDirectoryName(full)!);

        var dm = new DM("model", 22);
        var root = new Element(dm, "root", null, "DmElement");
        dm.Root = root;
        var dmeModel = new Element(dm, "model", null, "DmeModel");
        root["model"] = dmeModel;
        var children = new ElementArray();
        dmeModel["children"] = children;

        var mesh = new Element(dm, "mesh", null, "DmeMesh");
        var faceSets = new ElementArray();
        foreach (var mtl in materialPaths)
        {
            var faceSet = new Element(dm, "faceset", null, "DmeFaceSet");
            var material = new Element(dm, "material", null, "DmeMaterial");
            material["mtlName"] = mtl;
            faceSet["material"] = material;
            faceSets.Add(faceSet);
        }
        mesh["faceSets"] = faceSets;
        var dag = new Element(dm, "dag", null, "DmeDag");
        dag["shape"] = mesh;
        children.Add(dag);

        dm.Save(full, "keyvalues2", 4);
    }
}

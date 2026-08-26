using Datamodel;
using DM = Datamodel.Datamodel;

namespace SourcePorter.Core.Tests;

/// <summary>
/// Tests the structural DMX walker that pulls material references out of a Source 2 model
/// mesh. Fixtures are built with the real <c>KeyValues2</c> serializer (no real model files),
/// mirroring the <c>DmeModel → DmeDag → DmeMesh → DmeFaceSet → DmeMaterial(mtlName)</c>
/// graph ValveResourceFormat's exporter writes.
/// </summary>
public class DmxMaterialScannerTests
{
    [Fact]
    public void Reads_material_mtlName_from_each_face_set()
    {
        var root = NewTempDir();
        try
        {
            var path = Path.Combine(root, "crate.dmx");
            WriteModelDmx(path, dm =>
            {
                var mesh = MeshWithFaceSets(dm,
                    FaceSet(dm, "materials/models/props/crate.vmat"),
                    FaceSet(dm, "materials/models/props/crate_lod.vmat"));
                return new[] { mesh };
            });

            var materials = Hammer5Tools.Core.Format.Validation.DmxMaterialScanner.Scan(path);

            Assert.Contains("materials/models/props/crate.vmat", materials, StringComparer.OrdinalIgnoreCase);
            Assert.Contains("materials/models/props/crate_lod.vmat", materials, StringComparer.OrdinalIgnoreCase);
        }
        finally { Directory.Delete(root, recursive: true); }
    }

    [Fact]
    public void Skips_non_vmat_physics_face_sets()
    {
        var root = NewTempDir();
        try
        {
            var path = Path.Combine(root, "phys.dmx");
            WriteModelDmx(path, dm =>
            {
                var mesh = MeshWithFaceSets(dm,
                    FaceSet(dm, "materials/models/props/crate.vmat"),   // render mesh
                    FaceSet(dm, "solid$default"));                      // physics hull — not a vmat
                return new[] { mesh };
            });

            var materials = Hammer5Tools.Core.Format.Validation.DmxMaterialScanner.Scan(path);

            Assert.Single(materials);
            Assert.Contains("materials/models/props/crate.vmat", materials, StringComparer.OrdinalIgnoreCase);
        }
        finally { Directory.Delete(root, recursive: true); }
    }

    [Fact]
    public void Dedupes_the_same_material_across_face_sets()
    {
        var root = NewTempDir();
        try
        {
            var path = Path.Combine(root, "dup.dmx");
            WriteModelDmx(path, dm =>
            {
                // Two face sets referencing the same material, in two separate meshes.
                var m1 = MeshWithFaceSets(dm, FaceSet(dm, "materials/a.vmat"), FaceSet(dm, "materials/a.vmat"));
                var m2 = MeshWithFaceSets(dm, FaceSet(dm, "materials/A.VMAT"));
                return new[] { m1, m2 };
            });

            var materials = Hammer5Tools.Core.Format.Validation.DmxMaterialScanner.Scan(path);

            Assert.Single(materials);
        }
        finally { Directory.Delete(root, recursive: true); }
    }

    [Fact]
    public void Reads_vmt_material_and_normalizes_to_vmat()
    {
        var root = NewTempDir();
        try
        {
            var path = Path.Combine(root, "crate_vmt.dmx");
            WriteModelDmx(path, dm =>
            {
                var mesh = MeshWithFaceSets(dm,
                    FaceSet(dm, "materials/models/props/crate.vmt"));
                return new[] { mesh };
            });

            var materials = Hammer5Tools.Core.Format.Validation.DmxMaterialScanner.Scan(path);

            Assert.Contains("materials/models/props/crate.vmat", materials, StringComparer.OrdinalIgnoreCase);
        }
        finally { Directory.Delete(root, recursive: true); }
    }

    [Fact]
    public void Non_dmx_file_returns_empty_without_throwing()
    {
        var root = NewTempDir();
        try
        {
            var path = Path.Combine(root, "not-a-dmx.dmx");
            File.WriteAllBytes(path, [0x00, 0x01, 0x02, 0x03]); // garbage, not a DMX header

            var materials = Hammer5Tools.Core.Format.Validation.DmxMaterialScanner.Scan(path);

            Assert.Empty(materials);
        }
        finally { Directory.Delete(root, recursive: true); }
    }

    // ---- fixture builders (mirrors VRF's DmeModel graph) ----

    private static void WriteModelDmx(string path, Func<DM, Element[]> buildMeshes)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        var dm = new DM("model", 22);
        var root = new Element(dm, "root", null, "DmElement");
        dm.Root = root;

        var dmeModel = new Element(dm, "model", null, "DmeModel");
        root["model"] = dmeModel;

        var children = new ElementArray();
        dmeModel["children"] = children;
        foreach (var mesh in buildMeshes(dm))
        {
            var dag = new Element(dm, "dag", null, "DmeDag");
            dag["shape"] = mesh;
            children.Add(dag);
        }

        dm.Save(path, "keyvalues2", 4);
    }

    private static Element MeshWithFaceSets(DM dm, params Element[] faceSets)
    {
        var mesh = new Element(dm, "mesh", null, "DmeMesh");
        var faceSetArray = new ElementArray();
        foreach (var fs in faceSets)
            faceSetArray.Add(fs);
        mesh["faceSets"] = faceSetArray;
        return mesh;
    }

    private static Element FaceSet(DM dm, string materialPath)
    {
        var faceSet = new Element(dm, "faceset", null, "DmeFaceSet");
        var material = new Element(dm, "material", null, "DmeMaterial");
        material["mtlName"] = materialPath;
        faceSet["material"] = material;
        return faceSet;
    }

    private static string NewTempDir()
    {
        var dir = Path.Combine(Path.GetTempPath(), "sp_dmx_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        return dir;
    }
}

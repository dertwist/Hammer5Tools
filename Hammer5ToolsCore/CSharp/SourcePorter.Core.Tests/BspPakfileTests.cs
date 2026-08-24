using System.Buffers.Binary;
using System.IO.Compression;
using System.Text;
using SourcePorter.Core.Toolchain;

namespace SourcePorter.Core.Tests;

public class BspPakfileTests : IDisposable
{
    private readonly string _root = Path.Combine(Path.GetTempPath(), "spbsp_" + Guid.NewGuid().ToString("N"));

    public BspPakfileTests() => Directory.CreateDirectory(_root);

    /// <summary>Builds a minimal valid VBSP file whose pakfile lump (40) is a zip with the given entries.</summary>
    private string WriteSyntheticBsp(string name, Dictionary<string, string> entries)
    {
        // Build the embedded zip.
        byte[] zipBytes;
        using (var zms = new MemoryStream())
        {
            using (var zip = new ZipArchive(zms, ZipArchiveMode.Create, leaveOpen: true))
                foreach (var (entryPath, content) in entries)
                {
                    var e = zip.CreateEntry(entryPath);
                    using var es = e.Open();
                    es.Write(Encoding.UTF8.GetBytes(content));
                }
            zipBytes = zms.ToArray();
        }

        const int headerSize = 8 + 64 * 16 + 4; // ident+version + 64 lumps + revision
        var bsp = new byte[headerSize + zipBytes.Length];
        "VBSP"u8.CopyTo(bsp);
        BinaryPrimitives.WriteInt32LittleEndian(bsp.AsSpan(4), 21); // version

        var lump40 = 8 + 40 * 16;
        BinaryPrimitives.WriteInt32LittleEndian(bsp.AsSpan(lump40), headerSize);        // fileofs
        BinaryPrimitives.WriteInt32LittleEndian(bsp.AsSpan(lump40 + 4), zipBytes.Length); // filelen
        zipBytes.CopyTo(bsp.AsSpan(headerSize));

        var path = Path.Combine(_root, name);
        File.WriteAllBytes(path, bsp);
        return path;
    }

    [Fact]
    public void Reads_embedded_pakfile_entries()
    {
        var bsp = WriteSyntheticBsp("m.bsp", new()
        {
            ["materials/custom/wall.vmt"] = "\"LightmappedGeneric\"\n{\n}\n",
            ["models/custom/prop.mdl"] = "binary",
        });

        using var pak = BspPakfile.Open(bsp);

        Assert.Equal(2, pak.EntryCount);
        Assert.True(pak.Exists("materials/custom/wall.vmt"));
        Assert.True(pak.Exists("materials\\custom\\wall.vmt")); // backslash normalised
        Assert.Equal("\"LightmappedGeneric\"\n{\n}\n", Encoding.UTF8.GetString(pak.TryReadBytes("materials/custom/wall.vmt")!));
        Assert.Null(pak.TryReadBytes("materials/nope.vmt"));
    }

    [Fact]
    public void ExtractAll_writes_every_entry_preserving_paths()
    {
        var bsp = WriteSyntheticBsp("x.bsp", new()
        {
            ["materials/custom/wall.vmt"] = "vmt",
            ["materials/maps/m/wall_wvt_patch.vmt"] = "patch",
            ["models/custom/prop.mdl"] = "mdl",
        });
        var dest = Path.Combine(_root, "out");

        using var pak = BspPakfile.Open(bsp);
        var written = pak.ExtractAll(dest);

        Assert.Equal(3, written);
        Assert.Equal("patch", File.ReadAllText(Path.Combine(dest, "materials", "maps", "m", "wall_wvt_patch.vmt")));
        Assert.True(File.Exists(Path.Combine(dest, "materials", "custom", "wall.vmt")));
        Assert.True(File.Exists(Path.Combine(dest, "models", "custom", "prop.mdl")));
    }

    [Fact]
    public void Non_bsp_file_yields_empty_pakfile()
    {
        var notBsp = Path.Combine(_root, "not.bsp");
        File.WriteAllText(notBsp, "this is not a bsp");
        using var pak = BspPakfile.Open(notBsp);
        Assert.Equal(0, pak.EntryCount);
    }

    [Fact]
    public void Missing_file_yields_empty_pakfile()
    {
        using var pak = BspPakfile.Open(Path.Combine(_root, "absent.bsp"));
        Assert.Equal(0, pak.EntryCount);
    }

    [Fact]
    public void Locator_finds_bsp_embedded_file_as_custom_content()
    {
        var bsp = WriteSyntheticBsp("e.bsp", new()
        {
            ["materials/de_gracia/floor.vmt"] = "\"LightmappedGeneric\"\n{\n}\n",
        });
        var csgo = Path.Combine(_root, "csgo");
        Directory.CreateDirectory(csgo);

        using var locator = new S1SourceLocator(csgo, null, extraContentRoots: null, bspPath: bsp);

        Assert.Equal(1, locator.BspEmbeddedCount);
        Assert.Equal(S1Source.CustomContent, locator.Locate("materials/de_gracia/floor.vmt"));
        Assert.True(locator.IsOnlyInBspPak("materials/de_gracia/floor.vmt"));
        Assert.NotNull(locator.TryReadText("materials/de_gracia/floor.vmt"));
    }

    [Fact]
    public void EnsureUnarchivedBsp_extracts_bsp_from_zip_archive()
    {
        var zipPath = Path.Combine(_root, "test_map.bsp");
        using (var zms = File.Create(zipPath))
        using (var zip = new ZipArchive(zms, ZipArchiveMode.Create))
        {
            var entry = zip.CreateEntry("inner_map.bsp");
            using var writer = new StreamWriter(entry.Open());
            writer.Write("VBSP test map content");
        }

        var result = BspDecompiler.EnsureUnarchivedBsp(zipPath);

        Assert.NotEqual(zipPath, result);
        Assert.EndsWith("inner_map.bsp", result);
        Assert.True(File.Exists(result));
        Assert.Equal("VBSP test map content", File.ReadAllText(result));
    }

    public void Dispose()
    {
        if (Directory.Exists(_root))
            Directory.Delete(_root, recursive: true);
    }
}

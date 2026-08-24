using System.Text;
using SourcePorter.Core.Validation;

namespace SourcePorter.Core.Tests;

public class Source2ResourceTests
{
    [Fact]
    public void Reads_external_references_from_a_resource_with_a_RERL_block()
    {
        string[] names =
        [
            "materials/dev/reflectivity_30.vmat",
            "models/props/cs_office/computer.vmesh",
        ];

        using var stream = new MemoryStream(BuildResourceWithRerl(names));
        var refs = Source2Resource.ReadExternalReferences(stream);

        Assert.Equal(names, refs);
    }

    [Fact]
    public void Returns_empty_when_there_are_no_external_references()
    {
        using var stream = new MemoryStream(BuildResourceWithRerl([]));
        Assert.Empty(Source2Resource.ReadExternalReferences(stream));
    }

    [Fact]
    public void Throws_on_a_non_resource_stream()
    {
        using var stream = new MemoryStream([0, 0, 0, 0, 0, 0, 0, 0]);
        Assert.Throws<InvalidDataException>(() => Source2Resource.ReadExternalReferences(stream));
    }

    // Builds a minimal Source 2 resource (header + one RERL block) using the exact
    // byte layout of ValveResourceFormat's Resource header + ResourceExtRefList.Serialize.
    private static byte[] BuildResourceWithRerl(string[] names)
    {
        var body = BuildRerlBody(names);

        using var ms = new MemoryStream();
        using var bw = new BinaryWriter(ms);

        bw.Write(0u);            // FileSize (not verified by the reader)
        bw.Write((ushort)12);    // HeaderVersion (KnownHeaderVersion)
        bw.Write((ushort)0);     // Version
        bw.Write(8u);            // blockOffset → block directory immediately follows the header
        bw.Write(1u);            // blockCount

        // Block directory entry (pos 16): 4-char type + relative offset + size.
        bw.Write(Encoding.ASCII.GetBytes("RERL"));     // pos 16..20
        bw.Write(8u);                                  // offset field (pos 20) → body at pos 28
        bw.Write((uint)body.Length);                   // size

        bw.Write(body);                                // RERL body at pos 28
        bw.Flush();
        return ms.ToArray();
    }

    private static byte[] BuildRerlBody(string[] names)
    {
        using var ms = new MemoryStream();
        using var bw = new BinaryWriter(ms);

        if (names.Length == 0)
        {
            bw.Write(0u);
            bw.Write(0u);
            bw.Flush();
            return ms.ToArray();
        }

        bw.Write(8u);                 // offset to entries (relative)
        bw.Write(names.Length);       // count

        const int entrySize = sizeof(ulong) + sizeof(long);
        var stringsStart = names.Length * entrySize;
        var currentString = 0;

        for (var i = 0; i < names.Length; i++)
        {
            bw.Write((ulong)(i + 1));                       // id
            var posAfterId = sizeof(ulong) + i * entrySize;
            long relative = (stringsStart + currentString) - posAfterId;
            bw.Write(relative);
            currentString += Encoding.UTF8.GetByteCount(names[i]) + 1;
        }

        foreach (var name in names)
        {
            bw.Write(Encoding.UTF8.GetBytes(name));
            bw.Write((byte)0);
        }

        bw.Flush();
        return ms.ToArray();
    }
}

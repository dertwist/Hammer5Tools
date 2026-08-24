using System.Buffers.Binary;
using SourcePorter.Core.Materials;

namespace SourcePorter.Core.Tests;

public class VtfHeaderTests
{
    private static byte[] SynthHeader(int width, int height, uint flags = 0x2000, int major = 7, int minor = 4)
    {
        var buf = new byte[64];
        "VTF\0"u8.CopyTo(buf);
        BinaryPrimitives.WriteUInt32LittleEndian(buf.AsSpan(4), (uint)major);
        BinaryPrimitives.WriteUInt32LittleEndian(buf.AsSpan(8), (uint)minor);
        BinaryPrimitives.WriteUInt32LittleEndian(buf.AsSpan(12), 64); // headerSize
        BinaryPrimitives.WriteUInt16LittleEndian(buf.AsSpan(16), (ushort)width);
        BinaryPrimitives.WriteUInt16LittleEndian(buf.AsSpan(18), (ushort)height);
        BinaryPrimitives.WriteUInt32LittleEndian(buf.AsSpan(20), flags);
        return buf;
    }

    [Fact]
    public void Parses_dimensions_version_and_flags()
    {
        var header = VtfHeader.Parse(SynthHeader(1024, 512, 0x2000));

        Assert.NotNull(header);
        Assert.Equal(1024, header!.Value.Width);
        Assert.Equal(512, header.Value.Height);
        Assert.Equal(0x2000u, header.Value.Flags);
        Assert.Equal(7, header.Value.VersionMajor);
        Assert.Equal(4, header.Value.VersionMinor);
    }

    [Fact]
    public void Rejects_buffer_with_wrong_signature()
    {
        var buf = SynthHeader(256, 256);
        buf[0] = (byte)'X';
        Assert.Null(VtfHeader.Parse(buf));
    }

    [Fact]
    public void Reads_dimensions_from_a_file_on_disk()
    {
        var path = Path.Combine(Path.GetTempPath(), "spvtf_" + Guid.NewGuid().ToString("N") + ".vtf");
        File.WriteAllBytes(path, SynthHeader(2048, 64));
        try
        {
            var dims = VtfHeader.TryReadDimensions(path);
            Assert.Equal((2048, 64), dims);
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact]
    public void Missing_file_returns_null()
    {
        Assert.Null(VtfHeader.TryReadDimensions(Path.Combine(Path.GetTempPath(), "does_not_exist_" + Guid.NewGuid().ToString("N") + ".vtf")));
    }
}

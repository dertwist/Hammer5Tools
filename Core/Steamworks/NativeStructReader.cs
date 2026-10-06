using System.Buffers.Binary;
using System.Text;

namespace Steamworks;

/// <summary>
/// Reads the fields of a native Steam struct in order, placing each one the way the C++ compiler does under <see cref="SteamClient.StructPack"/>.
/// </summary>
internal ref struct NativeStructReader(ReadOnlySpan<byte> data)
{
    private readonly ReadOnlySpan<byte> data = data;
    private int offset;

    /// <summary>The struct size so far, padded to the struct's alignment like sizeof does.</summary>
    public int Size
    {
        get
        {
            var alignment = Math.Min(sizeof(ulong), SteamClient.StructPack);
            return (offset + alignment - 1) / alignment * alignment;
        }
    }

    public int ReadInt32()
    {
        Align(sizeof(int));
        var value = BinaryPrimitives.ReadInt32LittleEndian(data[offset..]);
        offset += sizeof(int);
        return value;
    }

    public uint ReadUInt32()
    {
        Align(sizeof(uint));
        var value = BinaryPrimitives.ReadUInt32LittleEndian(data[offset..]);
        offset += sizeof(uint);
        return value;
    }

    public ulong ReadUInt64()
    {
        Align(sizeof(ulong));
        var value = BinaryPrimitives.ReadUInt64LittleEndian(data[offset..]);
        offset += sizeof(ulong);
        return value;
    }

    public float ReadSingle()
    {
        Align(sizeof(float));
        var value = BinaryPrimitives.ReadSingleLittleEndian(data[offset..]);
        offset += sizeof(float);
        return value;
    }

    public bool ReadBool()
    {
        return data[offset++] != 0;
    }

    /// <summary>A fixed size char array, read up to its first zero byte.</summary>
    public string ReadString(int length)
    {
        var bytes = data.Slice(offset, length);
        offset += length;

        var end = bytes.IndexOf((byte)0);

        return Encoding.UTF8.GetString(end >= 0 ? bytes[..end] : bytes);
    }

    private void Align(int size)
    {
        var alignment = Math.Min(size, SteamClient.StructPack);
        offset = (offset + alignment - 1) / alignment * alignment;
    }
}

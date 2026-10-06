using System.Buffers.Binary;
using System.Runtime.InteropServices;
using System.Text;

namespace Hammer5Tools.Core;

/// <summary>Message kinds carried by the compact NativeAOT binary ABI.</summary>
internal enum NativeBinaryMessage : ushort
{
    Error,
    VmapSceneRequest,
    VmapSceneResult,
    VmapRewriteRequest,
    VmapRewriteResult,
    NavMeshRadarRequest,
    NavMeshRadarResult,
    SnapshotTextRequest,
    SnapshotDocument,
    SnapshotGenerateRequest,
    TextResult,
}

/// <summary>Writes versioned, little-endian ABI payloads without JSON or base64 expansion.</summary>
internal sealed class NativeBinaryWriter : IDisposable
{
    private readonly MemoryStream buffer = new();

    public int Length => checked((int)buffer.Length);

    public void WriteByte(byte value)
    {
        buffer.WriteByte(value);
    }

    public void WriteBoolean(bool value) => WriteByte(value ? (byte)1 : (byte)0);

    public void WriteInt32(int value)
    {
        Span<byte> destination = stackalloc byte[sizeof(int)];
        BinaryPrimitives.WriteInt32LittleEndian(destination, value);
        buffer.Write(destination);
    }

    public void WriteUInt16(ushort value)
    {
        Span<byte> destination = stackalloc byte[sizeof(ushort)];
        BinaryPrimitives.WriteUInt16LittleEndian(destination, value);
        buffer.Write(destination);
    }

    public void WriteUInt32(uint value)
    {
        Span<byte> destination = stackalloc byte[sizeof(uint)];
        BinaryPrimitives.WriteUInt32LittleEndian(destination, value);
        buffer.Write(destination);
    }

    public void WriteSingle(float value)
    {
        Span<byte> destination = stackalloc byte[sizeof(float)];
        BinaryPrimitives.WriteInt32LittleEndian(destination, BitConverter.SingleToInt32Bits(value));
        buffer.Write(destination);
    }

    public void WriteString(string value)
    {
        ArgumentNullException.ThrowIfNull(value);
        var byteCount = Encoding.UTF8.GetByteCount(value);
        WriteInt32(byteCount);
        if (byteCount == 0)
        {
            return;
        }

        buffer.Write(Encoding.UTF8.GetBytes(value));
    }

    public void WriteNullableString(string? value)
    {
        if (value is null)
        {
            WriteInt32(-1);
            return;
        }

        WriteString(value);
    }

    public void WriteSingles(ReadOnlySpan<float> values)
    {
        WriteInt32(values.Length);
        Align(sizeof(float));
        if (BitConverter.IsLittleEndian)
        {
            WriteRaw(MemoryMarshal.AsBytes(values));
            return;
        }

        foreach (var value in values)
        {
            WriteSingle(value);
        }
    }

    public void WriteUInt32s(ReadOnlySpan<uint> values)
    {
        WriteInt32(values.Length);
        Align(sizeof(uint));
        if (BitConverter.IsLittleEndian)
        {
            WriteRaw(MemoryMarshal.AsBytes(values));
            return;
        }

        foreach (var value in values)
        {
            WriteUInt32(value);
        }
    }

    public void WriteRaw(ReadOnlySpan<byte> values)
    {
        if (values.IsEmpty)
        {
            return;
        }

        buffer.Write(values);
    }

    public void PatchUInt32(int offset, uint value)
    {
        if (offset < 0 || offset > buffer.Length - sizeof(uint))
        {
            throw new ArgumentOutOfRangeException(nameof(offset));
        }

        var position = buffer.Position;
        buffer.Position = offset;
        WriteUInt32(value);
        buffer.Position = position;
    }

    public void Align(int alignment)
    {
        var padding = (-Length) & (alignment - 1);
        if (padding == 0)
        {
            return;
        }

        for (var index = 0; index < padding; index++)
        {
            buffer.WriteByte(0);
        }
    }

    public byte[] ToArray() => buffer.ToArray();

    public void Dispose() => buffer.Dispose();
}

/// <summary>Reads versioned, little-endian ABI payloads with strict bounds checks.</summary>
internal ref struct NativeBinaryReader
{
    private ReadOnlySpan<byte> buffer;
    private int offset;

    private NativeBinaryReader(ReadOnlySpan<byte> buffer)
    {
        this.buffer = buffer;
        offset = 0;
    }

    public static NativeBinaryReader Open(ReadOnlySpan<byte> source, NativeBinaryMessage expectedMessage)
    {
        var reader = new NativeBinaryReader(source);
        if (!reader.ReadRaw(4).SequenceEqual("H5TB"u8))
        {
            throw new InvalidDataException("The Native Core binary payload has an invalid signature.");
        }

        var version = reader.ReadUInt16();
        if (version != NativeBinary.Version)
        {
            throw new InvalidDataException($"Unsupported Native Core binary payload version {version}.");
        }

        var message = (NativeBinaryMessage)reader.ReadUInt16();
        if (message != expectedMessage)
        {
            throw new InvalidDataException($"Expected Native Core binary message '{expectedMessage}', found '{message}'.");
        }

        var payloadLength = reader.ReadUInt32();
        if (payloadLength != reader.Remaining)
        {
            throw new InvalidDataException("The Native Core binary payload length is invalid.");
        }

        return reader;
    }

    public int Remaining => buffer.Length - offset;

    public byte ReadByte()
    {
        Ensure(sizeof(byte));
        return buffer[offset++];
    }

    public bool ReadBoolean()
    {
        var value = ReadByte();
        return value switch
        {
            0 => false,
            1 => true,
            _ => throw new InvalidDataException("A binary boolean must be zero or one."),
        };
    }

    public int ReadInt32()
    {
        var value = BinaryPrimitives.ReadInt32LittleEndian(ReadRaw(sizeof(int)));
        return value;
    }

    public ushort ReadUInt16() => BinaryPrimitives.ReadUInt16LittleEndian(ReadRaw(sizeof(ushort)));

    public uint ReadUInt32() => BinaryPrimitives.ReadUInt32LittleEndian(ReadRaw(sizeof(uint)));

    public float ReadSingle() => BitConverter.Int32BitsToSingle(
        BinaryPrimitives.ReadInt32LittleEndian(ReadRaw(sizeof(float))));

    public string ReadString()
    {
        var length = ReadLength();
        return Encoding.UTF8.GetString(ReadRaw(length));
    }

    public string? ReadNullableString()
    {
        var length = ReadInt32();
        if (length == -1)
        {
            return null;
        }
        if (length < 0)
        {
            throw new InvalidDataException("A binary string length must not be negative.");
        }

        return Encoding.UTF8.GetString(ReadRaw(length));
    }

    public float[] ReadSingles()
    {
        var count = ReadLength();
        Align(sizeof(float));
        var bytes = ReadRaw(checked(count * sizeof(float)));
        var result = new float[count];
        if (BitConverter.IsLittleEndian)
        {
            bytes.CopyTo(MemoryMarshal.AsBytes(result.AsSpan()));
            return result;
        }

        for (var index = 0; index < count; index++)
        {
            result[index] = BitConverter.Int32BitsToSingle(
                BinaryPrimitives.ReadInt32LittleEndian(bytes[(index * sizeof(float))..]));
        }
        return result;
    }

    public uint[] ReadUInt32s()
    {
        var count = ReadLength();
        Align(sizeof(uint));
        var bytes = ReadRaw(checked(count * sizeof(uint)));
        var result = new uint[count];
        if (BitConverter.IsLittleEndian)
        {
            bytes.CopyTo(MemoryMarshal.AsBytes(result.AsSpan()));
            return result;
        }

        for (var index = 0; index < count; index++)
        {
            result[index] = BinaryPrimitives.ReadUInt32LittleEndian(bytes[(index * sizeof(uint))..]);
        }
        return result;
    }

    public ReadOnlySpan<byte> ReadRaw(int length)
    {
        if (length < 0)
        {
            throw new InvalidDataException("A binary payload length must not be negative.");
        }

        Ensure(length);
        var value = buffer.Slice(offset, length);
        offset += length;
        return value;
    }

    public void Align(int alignment)
    {
        var padding = (-offset) & (alignment - 1);
        if (padding == 0)
        {
            return;
        }

        if (ReadRaw(padding).IndexOfAnyExcept((byte)0) >= 0)
        {
            throw new InvalidDataException("A binary payload contains non-zero alignment padding.");
        }
    }

    public void EnsureFinished()
    {
        if (Remaining != 0)
        {
            throw new InvalidDataException("The Native Core binary payload has trailing bytes.");
        }
    }

    private int ReadLength()
    {
        var length = ReadInt32();
        if (length < 0 || length > Remaining)
        {
            throw new InvalidDataException("A binary payload length is invalid.");
        }
        return length;
    }

    private void Ensure(int count)
    {
        if (count > Remaining)
        {
            throw new InvalidDataException("The Native Core binary payload is truncated.");
        }
    }
}

/// <summary>Common envelope and error handling for compact NativeAOT binary payloads.</summary>
internal static unsafe class NativeBinary
{
    public const ushort Version = 1;

    public static byte[] Create(NativeBinaryMessage message, Action<NativeBinaryWriter> writePayload)
    {
        using var writer = new NativeBinaryWriter();
        writer.WriteRaw("H5TB"u8);
        writer.WriteUInt16(Version);
        writer.WriteUInt16((ushort)message);
        var lengthOffset = writer.Length;
        writer.WriteUInt32(0);
        var payloadStart = writer.Length;
        writePayload(writer);
        writer.PatchUInt32(lengthOffset, checked((uint)(writer.Length - payloadStart)));
        return writer.ToArray();
    }

    public static NativeBinaryReader Read(byte* input, int length, NativeBinaryMessage expectedMessage)
    {
        if (input is null || length < 0)
        {
            throw new ArgumentException("A valid Native Core binary input buffer is required.");
        }

        return NativeBinaryReader.Open(new ReadOnlySpan<byte>(input, length), expectedMessage);
    }

    public static byte[] CreateError(string message) => Create(NativeBinaryMessage.Error, writer => writer.WriteString(message));

    public static string ReadError(ReadOnlySpan<byte> payload)
    {
        var reader = NativeBinaryReader.Open(payload, NativeBinaryMessage.Error);
        var message = reader.ReadString();
        reader.EnsureFinished();
        return message;
    }
}

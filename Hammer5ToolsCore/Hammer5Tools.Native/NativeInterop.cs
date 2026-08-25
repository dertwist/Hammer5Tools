using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;

namespace Hammer5Tools.Native;

/// <summary>Shared buffer marshaling helpers for the versioned Hammer5Tools Native ABI.</summary>
internal static unsafe class NativeInterop
{
    public static string ReadUtf8(byte* input, int length)
    {
        if (input is null || length < 0)
            throw new ArgumentException("A valid UTF-8 input buffer is required.");

        return Encoding.UTF8.GetString(new ReadOnlySpan<byte>(input, length));
    }

    public static void WriteOutput(byte[] bytes, byte** output, int* outputLength)
    {
        var buffer = (byte*)NativeMemory.Alloc((nuint)bytes.Length + 1);
        bytes.CopyTo(new Span<byte>(buffer, bytes.Length));
        buffer[bytes.Length] = 0;
        *output = buffer;
        *outputLength = bytes.Length;
    }

    public static byte[] WriteNativeError(string message)
    {
        var buffer = new System.Buffers.ArrayBufferWriter<byte>();
        using var writer = new System.Text.Json.Utf8JsonWriter(buffer);
        writer.WriteStartObject();
        writer.WriteString("error", message);
        writer.WriteEndObject();
        writer.Flush();
        return buffer.WrittenSpan.ToArray();
    }

    /// <summary>Runs <paramref name="operation"/>, writing its result or a JSON error to the output buffer.</summary>
    public static int Invoke(byte** output, int* outputLength, Func<byte[]> operation)
    {
        if (output is null || outputLength is null)
            return -1;

        *output = null;
        *outputLength = 0;
        try
        {
            WriteOutput(operation(), output, outputLength);
            return 0;
        }
        catch (Exception exception)
        {
            WriteOutput(WriteNativeError(DescribeException(exception)), output, outputLength);
            return -2;
        }
    }

    /// <summary>Unwraps wrapper exceptions (type initializers, target invocations) to the root cause message.</summary>
    private static string DescribeException(Exception exception)
    {
        var current = exception;
        while (current.InnerException is not null &&
               current is TypeInitializationException or TargetInvocationException)
            current = current.InnerException;
        if (current is TypeInitializationException typeInit && typeInit.InnerException is null)
            return $"TypeInitializationException: {typeInit.TypeName} (no inner exception captured)";
        return $"{current.GetType().Name}: {current.Message}";
    }
}

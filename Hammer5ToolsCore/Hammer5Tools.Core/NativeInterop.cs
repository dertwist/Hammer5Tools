using System.Collections.Concurrent;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Text;

namespace Hammer5Tools.Core;

/// <summary>Shared buffer marshaling helpers for the versioned Hammer5Tools Native ABI.</summary>
internal static unsafe class NativeInterop
{
    // Shared across every API surface (SmartProp, SourcePorter, ...) behind
    // h5t_core_create_cancellation/h5t_core_cancel/h5t_core_release_cancellation —
    // one registry, one set of handles, regardless of which command created them.
    private static readonly ConcurrentDictionary<long, CancellationTokenSource> Cancellations = new();
    private static long NextCancellationId;

    [UnmanagedCallersOnly(EntryPoint = "h5t_core_create_cancellation", CallConvs = [typeof(CallConvCdecl)])]
    public static long CreateCancellation()
    {
        var id = Interlocked.Increment(ref NextCancellationId);
        Cancellations[id] = new CancellationTokenSource();
        return id;
    }

    [UnmanagedCallersOnly(EntryPoint = "h5t_core_cancel", CallConvs = [typeof(CallConvCdecl)])]
    public static int Cancel(long cancellationId)
    {
        if (!Cancellations.TryGetValue(cancellationId, out var cancellation))
            return -1;

        cancellation.Cancel();
        return 0;
    }

    [UnmanagedCallersOnly(EntryPoint = "h5t_core_release_cancellation", CallConvs = [typeof(CallConvCdecl)])]
    public static void ReleaseCancellation(long cancellationId)
    {
        if (Cancellations.TryRemove(cancellationId, out var cancellation))
            cancellation.Dispose();
    }

    public static CancellationToken GetCancellationToken(long cancellationId)
    {
        if (cancellationId == 0)
            return default;
        if (!Cancellations.TryGetValue(cancellationId, out var cancellation))
            throw new ArgumentException("The cancellation handle is invalid.");
        return cancellation.Token;
    }

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
    public static string DescribeException(Exception exception)
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

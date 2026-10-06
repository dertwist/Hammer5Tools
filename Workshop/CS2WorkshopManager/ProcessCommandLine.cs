using System.Buffers.Binary;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Text;

namespace CS2WorkshopManager;

/// <summary>
/// Reads the command line another process was started with, used to pull the -addon flag out of a running CS2 process, in order
/// to prefill the addon field when uploading a new addon while the tools are running.
/// </summary>
internal static partial class ProcessCommandLine
{
    /// <summary>The least access that lets the kernel answer, without any right to read the process's memory.</summary>
    private const int ProcessQueryLimitedInformation = 0x1000;

    /// <summary>ProcessCommandLineInformation: the kernel hands out the command line itself, as a UNICODE_STRING followed by its characters.</summary>
    private const int ProcessCommandLineInformationClass = 60;

    private const int StatusInfoLengthMismatch = unchecked((int)0xC0000004);
    private const int UnicodeStringSize = 16;

    /// <returns>The command line, or null when the process is gone, can not be asked or the platform is not supported.</returns>
    public static string? Read(Process process)
    {
        if (OperatingSystem.IsWindows())
        {
            return ReadWindows(process.Id);
        }

        if (OperatingSystem.IsLinux())
        {
            return ReadLinux(process.Id);
        }

        return null;
    }

    private static string? ReadLinux(int processId)
    {
        try
        {
            // the arguments are separated by nul characters
            return File.ReadAllText($"/proc/{processId}/cmdline").Replace('\0', ' ');
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return null;
        }
    }

    [SupportedOSPlatform("windows")]
    private static string? ReadWindows(int processId)
    {
        var handle = OpenProcess(ProcessQueryLimitedInformation, false, processId);

        if (handle == IntPtr.Zero)
        {
            return null;
        }

        try
        {
            // the first call only says how much room the answer needs
            var status = NtQueryInformationProcess(handle, ProcessCommandLineInformationClass, [], 0, out var length);

            if (status != StatusInfoLengthMismatch || length <= UnicodeStringSize)
            {
                return null;
            }

            var information = new byte[length];

            if (NtQueryInformationProcess(handle, ProcessCommandLineInformationClass, information, information.Length, out _) != 0)
            {
                return null;
            }

            // the UNICODE_STRING's length in bytes, its characters come right after the header
            var characters = BinaryPrimitives.ReadUInt16LittleEndian(information);

            return Encoding.Unicode.GetString(information, UnicodeStringSize, Math.Min(characters, information.Length - UnicodeStringSize));
        }
        finally
        {
            CloseHandle(handle);
        }
    }

    [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
    [LibraryImport("kernel32.dll", SetLastError = true)]
    private static partial IntPtr OpenProcess(int desiredAccess, [MarshalAs(UnmanagedType.Bool)] bool inheritHandle, int processId);

    [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
    [LibraryImport("kernel32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static partial bool CloseHandle(IntPtr handle);

    [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
    [LibraryImport("ntdll.dll")]
    private static partial int NtQueryInformationProcess(IntPtr process, int informationClass, Span<byte> information, int length, out int returnLength);
}

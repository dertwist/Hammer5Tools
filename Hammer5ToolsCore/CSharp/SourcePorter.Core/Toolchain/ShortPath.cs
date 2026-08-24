using System.Runtime.InteropServices;
using System.Text;

namespace SourcePorter.Core.Toolchain;

/// <summary>
/// Win32 8.3 short-path helper (<c>kernel32!GetShortPathName</c>). Used to feed
/// <c>source1import</c> a space-free content dir when <c>-usebsp</c> is on: the tool
/// passes that path to <c>vbsp.exe</c> <b>unquoted</b>, so a space in the install path
/// (e.g. <i>"Counter-Strike Global Offensive"</i>) splits the argument, vbsp never runs,
/// and the map falls back to broken vmf-only geometry (see ARCHITECTURE.md §4).
/// </summary>
internal static class ShortPath
{
    /// <summary>
    /// Returns the 8.3 short path for <paramref name="path"/> (which never contains
    /// spaces), or <c>null</c> if it can't be resolved — the path doesn't exist, or
    /// 8.3 name generation is disabled on the volume (<c>fsutil 8dot3name</c>).
    /// </summary>
    public static string? TryGet(string path)
    {
        if (string.IsNullOrEmpty(path))
            return null;

        var needed = GetShortPathNameW(path, null, 0);
        if (needed == 0)
            return null;

        var buffer = new StringBuilder((int)needed);
        var written = GetShortPathNameW(path, buffer, (uint)buffer.Capacity);
        return written == 0 ? null : buffer.ToString();
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern uint GetShortPathNameW(string lpszLongPath, StringBuilder? lpszShortPath, uint cchBuffer);
}

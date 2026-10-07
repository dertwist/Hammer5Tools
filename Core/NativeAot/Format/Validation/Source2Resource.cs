using System.Linq;
using ValveResourceFormat;
using ValveResourceFormat.Exceptions;

namespace Hammer5Tools.Core.Format.Validation;

/// <summary>
/// Reads external references from Source 2 compiled resources via ValveResourceFormat.
/// </summary>
public static class Source2Resource
{
    /// <summary>
    /// Returns the external resource references (RERL) of a compiled resource.
    /// Names use the uncompiled extension (e.g. <c>materials/foo.vmat</c>,
    /// <c>models/bar.vmesh</c>) — append <c>_c</c> to find them on disk.
    /// </summary>
    /// <exception cref="InvalidDataException">The stream is not a Source 2 resource.</exception>
    public static IReadOnlyList<string> ReadExternalReferences(Stream stream)
    {
        ArgumentNullException.ThrowIfNull(stream);
        try
        {
            using var resource = new Resource();
            resource.Read(stream, verifyFileSize: false);
            return resource.ExternalReferences?.ResourceRefInfoList.Select(r => r.Name).ToArray() ?? [];
        }
        catch (UnexpectedMagicException ex)
        {
            throw new InvalidDataException(ex.Message, ex);
        }
    }
}


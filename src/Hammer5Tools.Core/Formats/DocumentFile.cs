namespace Hammer5Tools.Core.Formats;

using System.Text;
using ValveKeyValue;

/// <summary>
/// Validates source KV3 before atomic replacement, retaining the previous file.
/// </summary>
public static class DocumentFile
{
    public static void Write(string path, string text)
    {
        WriteValidated(path, text, KVSerializationFormat.KeyValues3Text);
    }

    /// <summary>Validates and atomically replaces a KeyValues1 source file with a backup.</summary>
    public static void WriteKeyValues1(string path, string text)
    {
        WriteValidated(path, text, KVSerializationFormat.KeyValues1Text);
    }

    private static void WriteValidated(string path, string text, KVSerializationFormat format)
    {
        using var input = new MemoryStream(Encoding.UTF8.GetBytes(text));
        KVSerializer.Create(format).Deserialize(input);
        path = Path.GetFullPath(path);
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        var staged = $"{path}.{Guid.NewGuid():N}.tmp";
        try
        {
            File.WriteAllText(staged, text, new UTF8Encoding(false));
            if (File.Exists(path))
            {
                File.Copy(path, $"{path}.bak", overwrite: true);
            }

            File.Move(staged, path, overwrite: true);
        }
        finally
        {
            if (File.Exists(staged))
            {
                File.Delete(staged);
            }
        }
    }
}

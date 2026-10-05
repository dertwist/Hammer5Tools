using Hammer5Tools.Core.Format.SmartProps;
using Hammer5Tools.Core.IO.Automation;

namespace Hammer5Tools.Core.IO;

internal static class SmartPropDocumentFile
{
    public static string? Save(string path, string json)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);
        var destination = Path.GetFullPath(path);
        var text = SmartPropDocumentSerializer.SerializeJson(SmartPropEditorDocument.Validate(json));
        lock (SafeAssetWrites.Sync)
        {
            var staged = SafeAssetWrites.Stage(destination,
                temporary => File.WriteAllText(temporary, text),
                temporary => SmartPropEditorDocument.Validate(SmartPropDocumentSerializer.DeserializeText(File.ReadAllText(temporary))));
            try
            {
                return SafeAssetWrites.Replace(staged, destination);
            }
            finally
            {
                File.Delete(staged);
            }
        }
    }
}

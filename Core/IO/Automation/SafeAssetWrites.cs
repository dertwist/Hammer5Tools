namespace Hammer5Tools.Core.IO.Automation;

internal static class SafeAssetWrites
{
    // ponytail: serialize all authoring; per-destination locks only if throughput warrants it.
    internal static readonly object Sync = new();

    internal static string? Replace(string stagedPath, string destination)
    {
        if (File.Exists(destination))
        {
            var backup = destination + ".h5t-" + Guid.NewGuid().ToString("N") + ".bak";
            File.Replace(stagedPath, destination, backup);
            return backup;
        }
        File.Move(stagedPath, destination);
        return null;
    }

    internal static string Stage(string destination, Action<string> write, Action<string> validate)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(destination)!);
        var staged = destination + ".h5t-" + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            write(staged);
            validate(staged);
            return staged;
        }
        catch
        {
            File.Delete(staged);
            throw;
        }
    }
}

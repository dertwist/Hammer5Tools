namespace SourcePorter.Core.Vmap;

/// <summary>
/// Copies a <c>.vmap</c> to a timestamped <c>.bak</c> beside it before the post-import
/// tools overwrite it (project safety rule §11 "back up before overwrite"). The user's
/// own source files are never touched — only the imported addon-content <c>.vmap</c>.
/// </summary>
public static class VmapBackup
{
    /// <summary>Backs up <paramref name="path"/> and returns the backup file path.</summary>
    public static string Backup(string path, Action<string>? log = null)
    {
        var stamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
        var backup = $"{path}.{stamp}.bak";
        var n = 1;
        while (File.Exists(backup))
            backup = $"{path}.{stamp}_{n++}.bak";

        File.Copy(path, backup, overwrite: false);
        log?.Invoke($"  Backed up {System.IO.Path.GetFileName(path)} → {System.IO.Path.GetFileName(backup)}");
        return backup;
    }
}

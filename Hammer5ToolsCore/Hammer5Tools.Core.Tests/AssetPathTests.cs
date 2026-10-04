namespace Hammer5Tools.Core.Tests;

public sealed class AssetPathTests
{
    [Test]
    public async Task ResolvesSeparatorsAndRejectsEscape()
    {
        var root = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(Path.Combine(root, "models"));
        try
        {
            var file = Path.Combine(root, "models", "模型 file.vmdl");
            File.WriteAllText(file, "fixture");
            await Assert.That(CoreApi.ResolveAssetPath("models/模型 file.vmdl", root)).IsEqualTo(file);
            await Assert.That(CoreApi.ResolveAssetPath("models\\模型 file.vmdl", root)).IsEqualTo(file);
            await Assert.That(CoreApi.ResolveAssetPath("new.vmdl", root, false)).IsEqualTo(Path.Combine(root, "new.vmdl"));
            await Assert.That(() => CoreApi.ResolveAssetPath("../outside.vmdl", root, false)).Throws<ArgumentException>();
            await Assert.That(() => CoreApi.ResolveAssetPath("missing.vmdl", root)).Throws<FileNotFoundException>();
            await Assert.That(() => CoreApi.ResolveAssetPath("missing.vmdl")).Throws<ArgumentException>();
            await Assert.That(() => CoreApi.ResolveAssetPath("C:missing.vmdl", root)).Throws<ArgumentException>();
        }
        finally
        {
            Directory.Delete(root, true);
        }
    }

    [Test]
    public async Task RejectsDirectoryLinkEscapeIncludingNewOutput()
    {
        var root = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        var link = Path.Combine(root, "outside");
        try
        {
            if (OperatingSystem.IsWindows())
            {
                using var process = System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
                {
                    FileName = "cmd.exe",
                    Arguments = $"/c mklink /J \"{link}\" \"{Path.GetTempPath()}\"",
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                })!;
                process.WaitForExit();
                if (process.ExitCode != 0)
                {
                    throw new IOException(process.StandardError.ReadToEnd());
                }
            }
            else
            {
                Directory.CreateSymbolicLink(link, Path.GetTempPath());
            }
            await Assert.That(() => CoreApi.ResolveAssetPath("outside/new.vmdl", root, false)).Throws<ArgumentException>();
        }
        finally
        {
            if (Directory.Exists(link))
            {
                Directory.Delete(link);
            }
            Directory.Delete(root);
        }
    }
}

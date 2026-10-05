namespace Hammer5Tools.IntegrationTests.Compiler;

using System.IO;
using Hammer5Tools.Core.IO.Addons;
using Hammer5Tools.Core.IO.Compiler;
using Hammer5Tools.Core.IO.Cs2;
using Hammer5Tools.Core.IO.Settings;

public class ResourceCompilerTests
{
    [Test]
    public async Task BuildArgumentsIncludesAddonAndFlags()
    {
        var tempDir = Path.Combine(Path.GetTempPath(), "H5T_RcTest_" + Guid.NewGuid().ToString("N"));
        var settingsFile = Path.Combine(tempDir, "settings.json");

        try
        {
            var settings = new JsonSettingsService(settingsFile);
            var locator = new Cs2Locator(settings, customSteamPath: tempDir);
            using var addonService = new AddonService(locator, settings);
            var compiler = new ResourceCompiler(locator, addonService);

            var argsNoAddon = compiler.BuildArguments("-i \"file.vmat\"");
            await Assert.That(argsNoAddon).IsEqualTo("-i \"file.vmat\"");

            var argsWithAddon = compiler.BuildArguments("-i \"file.vmat\"", "de_inferno");
            await Assert.That(argsWithAddon).IsEqualTo("-addon de_inferno -i \"file.vmat\"");
        }
        finally
        {
            if (Directory.Exists(tempDir))
            {
                Directory.Delete(tempDir, recursive: true);
            }
        }
    }

    [Test]
    public async Task CompileAssetFailsGracefullyWhenCompilerBinaryMissing()
    {
        var tempDir = Path.Combine(Path.GetTempPath(), "H5T_RcTest_" + Guid.NewGuid().ToString("N"));
        var settingsFile = Path.Combine(tempDir, "settings.json");

        try
        {
            var settings = new JsonSettingsService(settingsFile);
            var locator = new Cs2Locator(settings, customSteamPath: tempDir);
            using var addonService = new AddonService(locator, settings);
            var compiler = new ResourceCompiler(locator, addonService);

            await Assert.That(compiler.IsAvailable).IsFalse();
            var result = await compiler.CompileAssetAsync("fake.vmat");

            await Assert.That(result.Success).IsFalse();
            await Assert.That(result.ExitCode).IsEqualTo(-1);
        }
        finally
        {
            if (Directory.Exists(tempDir))
            {
                Directory.Delete(tempDir, recursive: true);
            }
        }
    }

    [Test]
    public async Task MapCompilerPassesBuildFlagsAndCancellationTerminatesItsProcess()
    {
        if (OperatingSystem.IsWindows())
        {
            return;
        }

        var root = Path.Combine(Path.GetTempPath(), $"h5t-compiler-{Guid.NewGuid():N}");
        try
        {
            Directory.CreateDirectory(Path.Combine(root, "content"));
            Directory.CreateDirectory(Path.Combine(root, "game", "csgo"));
            File.WriteAllText(Path.Combine(root, "game", "csgo", "gameinfo.gi"), "\"GameInfo\" {} ");
            var binary = Path.Combine(root, "game", "bin", "win64", "resourcecompiler.exe");
            Directory.CreateDirectory(Path.GetDirectoryName(binary)!);
            File.WriteAllText(binary, "#!/bin/sh\nprintf '%s\\n' \"$@\"\n");
            File.SetUnixFileMode(binary, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
            var settings = new JsonSettingsService(Path.Combine(root, "settings.json"));
            settings.Update(value => value.Cs2PathOverride = root);
            var locator = new Cs2Locator(settings);
            using var addons = new AddonService(locator, settings);
            var compiler = new ResourceCompiler(locator, addons);
            var result = await compiler.CompileAssetAsync(Path.Combine(root, "a map.vmap"), "test", additionalArguments: "-threads 0 -vrad -fast");
            await Assert.That(result.Success).IsTrue();
            await Assert.That(result.StandardOutput).Contains("a map.vmap");
            await Assert.That(result.StandardOutput).Contains("-fast");

            File.WriteAllText(binary, "#!/bin/sh\necho $$ > compiler.pid\nsleep 30\n");
            using var cancellation = new CancellationTokenSource();
            var pending = compiler.CompileAssetAsync("test.vmap", ct: cancellation.Token);
            var actualPidPath = Path.Combine(Path.GetDirectoryName(binary)!, "compiler.pid");
            for (var attempt = 0; attempt < 100 && !File.Exists(actualPidPath); attempt++)
            {
                await Task.Delay(10);
            }

            var pid = int.Parse(await File.ReadAllTextAsync(actualPidPath), System.Globalization.CultureInfo.InvariantCulture);
            cancellation.Cancel();
            try
            {
                await pending;
                throw new InvalidOperationException("Compilation did not report cancellation.");
            }
            catch (OperationCanceledException)
            {
            }

            await Assert.That(System.Diagnostics.Process.GetProcesses().Any(process => process.Id == pid)).IsFalse();
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    [Test]
    public async Task QuickCreateVmdlGeneratesValidKv3File()
    {
        var tempDir = Path.Combine(Path.GetTempPath(), "H5T_RcTest_" + Guid.NewGuid().ToString("N"));
        var settingsFile = Path.Combine(tempDir, "settings.json");
        var meshFile = Path.Combine(tempDir, "crate.fbx");
        var expectedVmdl = Path.Combine(tempDir, "crate.vmdl");

        try
        {
            Directory.CreateDirectory(tempDir);
            await File.WriteAllTextAsync(meshFile, "mock fbx content");

            var settings = new JsonSettingsService(settingsFile);
            var locator = new Cs2Locator(settings, customSteamPath: tempDir);
            using var addonService = new AddonService(locator, settings);
            var compiler = new ResourceCompiler(locator, addonService);

            // Execute (will fail compile step since RC is not installed in tempDir, but file generation occurs)
            var result = await compiler.QuickCreateVmdlAsync(meshFile);

            await Assert.That(File.Exists(expectedVmdl)).IsTrue();
            var content = await File.ReadAllTextAsync(expectedVmdl);
            await Assert.That(content).Contains("RenderMeshFile");
            await Assert.That(content).Contains("crate.fbx");
            await Assert.That(result.Success).IsFalse(); // Missing exe in mock dir
        }
        finally
        {
            if (Directory.Exists(tempDir))
            {
                Directory.Delete(tempDir, recursive: true);
            }
        }
    }
}

namespace Hammer5Tools.IntegrationTests.Compiler;

using System.IO;
using Hammer5Tools.Infrastructure.Addons;
using Hammer5Tools.Infrastructure.Compiler;
using Hammer5Tools.Infrastructure.Cs2;
using Hammer5Tools.Infrastructure.Settings;

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
            var locator = new Cs2Locator(settings);
            var addonService = new AddonService(locator, settings);
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
            var locator = new Cs2Locator(settings);
            var addonService = new AddonService(locator, settings);
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
            var locator = new Cs2Locator(settings);
            var addonService = new AddonService(locator, settings);
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

namespace Hammer5Tools.Core.Tests;

using System.IO.Compression;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.IO.Addons;
using Hammer5Tools.Core.IO.Settings;

public sealed class AddonWorkflowTests
{
    [Test]
    public async Task PresetCreationCopiesBothTreesRenamesTokensAndRefusesOverwrite()
    {
        var root = Path.Combine(Path.GetTempPath(), $"h5t-preset-{Guid.NewGuid():N}");
        Directory.CreateDirectory(root);
        try
        {
            var preset = Path.Combine(root, "presets", "example");
            Write(preset, "content/maps/xxx_mapname_xxx.vmap", "map bytes");
            Write(preset, "game/maps/xxx_mapname_xxx.vpk", "compiled bytes");
            var install = Path.Combine(root, "install");
            Directory.CreateDirectory(install);
            AddonPresetFiles.Create(install, "de_example", preset);
            await Assert.That(File.ReadAllText(Path.Combine(install, "content/csgo_addons/de_example/maps/de_example.vmap"))).IsEqualTo("map bytes");
            await Assert.That(File.ReadAllText(Path.Combine(install, "game/csgo_addons/de_example/maps/de_example.vpk"))).IsEqualTo("compiled bytes");
            await Assert.That(() => AddonPresetFiles.Create(install, "de_example", preset)).Throws<IOException>();
            await Assert.That(() => AddonPresetFiles.Create(install, "../escape", preset)).Throws<ArgumentException>();
            await Assert.That(File.ReadAllText(Path.Combine(preset, "content/maps/xxx_mapname_xxx.vmap"))).IsEqualTo("map bytes");
            var presets = AddonPresetFiles.Discover([Path.Combine(root, "presets"), Path.Combine(root, "presets")]);
            await Assert.That(presets.Count).IsEqualTo(1);
        }
        finally { Directory.Delete(root, recursive: true); }
    }

    [Test]
    public async Task ExportFiltersAndSelectionKeepLegacyArchivePaths()
    {
        var root = Path.Combine(Path.GetTempPath(), $"h5t-export-{Guid.NewGuid():N}");
        Directory.CreateDirectory(root);
        try
        {
            var content = Path.Combine(root, "content");
            var game = Path.Combine(root, "game");
            Write(content, "maps/test.vmap", "map");
            Write(content, "maps/test.vmap.bak", "backup");
            Write(content, ".git/config", "git");
            Write(content, "custom/source.txt", "custom");
            Write(game, "maps/test.vpk", "compiled map");
            Write(game, "models/test.vmdl_c", "model");
            var addon = new Addon("test", content, game);
            var options = new AddonExportOptions { SkipNonDefaultContentFolders = true, IncludeCompiledModels = false };
            var files = AddonArchive.ListFiles(addon, options);
            string[] expected = ["content/csgo_addons/test/maps/test.vmap", "game/csgo_addons/test/maps/test.vpk"];
            await Assert.That(files.Select(file => file.ArchivePath).ToArray()).IsEquivalentTo(expected);
            options.SelectedFiles = new HashSet<string> { files[0].ArchivePath };
            var destination = Path.Combine(root, "test.zip");
            AddonArchive.Export(addon, destination, options);
            using var zip = ZipFile.OpenRead(destination);
            await Assert.That(zip.Entries.Count).IsEqualTo(1);
            await Assert.That(zip.Entries[0].FullName).IsEqualTo(files[0].ArchivePath);
        }
        finally { Directory.Delete(root, recursive: true); }
    }

    [Test]
    public async Task CancelledExportRetainsPreviousArchiveAndRemovesStagingFile()
    {
        var root = Path.Combine(Path.GetTempPath(), $"h5t-export-{Guid.NewGuid():N}");
        Directory.CreateDirectory(root);
        try
        {
            Write(root, "content/maps/test.vmap", "map");
            var destination = Path.Combine(root, "test.zip");
            File.WriteAllText(destination, "previous archive");
            using var cancellation = new CancellationTokenSource();
            cancellation.Cancel();
            await Assert.That(() => AddonArchive.Export(new("test", Path.Combine(root, "content"), Path.Combine(root, "game")), destination, new(), cancellationToken: cancellation.Token)).Throws<OperationCanceledException>();
            await Assert.That(File.ReadAllText(destination)).IsEqualTo("previous archive");
            await Assert.That(Directory.GetFiles(root, "*.tmp").Length).IsEqualTo(0);
        }
        finally { Directory.Delete(root, recursive: true); }
    }

    [Test]
    public async Task LaunchSwitchesPreserveQuotedValuesAndSubstituteAddonTokens()
    {
        var options = new LaunchOptions { OpenMap = true, Steam = true, Retail = true, GpuRayTracing = true, NoCustomerMachine = true };
        var args = options.BuildArguments("de_test", "+exec \"config with spaces.cfg\" +first 1 +second 1 +map addon_name");
        await Assert.That(args).Contains("-tool hammer -asset maps/de_test.vmap");
        await Assert.That(args).Contains("-steam -retail -gpuraytracing -insecure -nocustomermachine");
        await Assert.That(args).Contains("+exec \"config with spaces.cfg\" +first 1 +second 1 +map de_test");
        options.OpenTools = options.Insecure = false;
        var disabled = options.BuildArguments("de_test", "");
        await Assert.That(disabled.Contains("-tools", StringComparison.Ordinal)).IsFalse();
        await Assert.That(disabled.Contains("-insecure", StringComparison.Ordinal)).IsFalse();
    }

    [Test]
    public async Task LegacyLaunchCommandsMigrateToCheckboxesAndPreserveUnknownArguments()
    {
        var root = Path.Combine(Path.GetTempPath(), $"h5t-launch-{Guid.NewGuid():N}");
        Directory.CreateDirectory(root);
        try
        {
            File.WriteAllText(Path.Combine(root, "settings.ini"), "[LAUNCH]\ncommands= -addon addon_name -tool hammer -asset maps/addon_name.vmap -tools -steam -retail -gpuraytracing -noinsecru +exec \"custom file.cfg\"\nncm_mode=true\n");
            var settings = new JsonSettingsService(Path.Combine(root, "settings.json")).Settings;
            await Assert.That(settings.Editor.LaunchOptions.OpenMap).IsTrue();
            await Assert.That(settings.Editor.LaunchOptions.GpuRayTracing).IsTrue();
            await Assert.That(settings.Editor.LaunchOptions.Insecure).IsTrue();
            await Assert.That(settings.Editor.LaunchNcmMode).IsTrue();
            await Assert.That(settings.Editor.CustomLaunchArgs).IsEqualTo("+exec \"custom file.cfg\"");
            var restored = new JsonSettingsService(Path.Combine(root, "settings.json")).Settings;
            await Assert.That(restored.Editor.LaunchOptions.OpenMap).IsTrue();
        }
        finally { Directory.Delete(root, recursive: true); }
    }

    private static void Write(string root, string relative, string contents)
    {
        var path = Path.Combine(root, relative);
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.WriteAllText(path, contents);
    }

    [Test]
    public async Task PreviousManagedLaunchArgumentsMigrateWithoutLeavingHiddenSwitches()
    {
        var root = Path.Combine(Path.GetTempPath(), $"h5t-launch-{Guid.NewGuid():N}");
        Directory.CreateDirectory(root);
        try
        {
            var path = Path.Combine(root, "settings.json");
            File.WriteAllText(path, "{\"editor\":{\"customLaunchArgs\":\"-tools -steam +exec autoexec.cfg\"}}");
            var settings = new JsonSettingsService(path).Settings;
            await Assert.That(settings.Editor.LaunchOptions.OpenTools).IsTrue();
            await Assert.That(settings.Editor.LaunchOptions.Steam).IsTrue();
            await Assert.That(settings.Editor.LaunchOptions.OpenMap).IsFalse();
            await Assert.That(settings.Editor.LaunchOptions.Retail).IsFalse();
            await Assert.That(settings.Editor.LaunchOptions.GpuRayTracing).IsFalse();
            await Assert.That(settings.Editor.CustomLaunchArgs).IsEqualTo("+exec autoexec.cfg");
            settings.Editor.LaunchOptions.OpenTools = false;
            await Assert.That(settings.Editor.LaunchOptions.BuildArguments("test", settings.Editor.CustomLaunchArgs).Contains("-tools", StringComparison.Ordinal)).IsFalse();
        }
        finally { Directory.Delete(root, recursive: true); }
    }

    [Test]
    public async Task NcmPreparationCopiesMissingFilesAndPreservesExistingConfiguration()
    {
        var root = Path.Combine(Path.GetTempPath(), $"h5t-ncm-{Guid.NewGuid():N}");
        Directory.CreateDirectory(root);
        try
        {
            Write(root, "game/bin/assettypes_common.txt", "asset types");
            Write(root, "game/bin/sdkenginetools.txt", "tools");
            Write(root, "game/bin/enginetools.txt", "user configuration");
            IO.Cs2.Cs2Launcher.PrepareNcmFiles(root);
            await Assert.That(File.ReadAllText(Path.Combine(root, "game/bin/assettypes_internal.txt"))).IsEqualTo("asset types");
            await Assert.That(File.ReadAllText(Path.Combine(root, "game/bin/enginetools.txt"))).IsEqualTo("user configuration");
        }
        finally { Directory.Delete(root, recursive: true); }
    }
}

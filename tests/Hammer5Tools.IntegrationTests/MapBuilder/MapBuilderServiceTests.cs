namespace Hammer5Tools.IntegrationTests.MapBuilder;

using Hammer5Tools.Core.MapBuilder;
using Hammer5Tools.Infrastructure;
using Hammer5Tools.Infrastructure.Settings;
using Microsoft.Extensions.DependencyInjection;

public class MapBuilderServiceTests
{
    [Test]
    public async Task QueueStreamsOutputSnapshotsOptionsAndCancelsPendingMaps()
    {
        if (OperatingSystem.IsWindows()) return;
        var root = Path.Combine(Path.GetTempPath(), $"h5t-build-{Guid.NewGuid():N}");
        try
        {
            var binaryDirectory = Path.Combine(root, "game", "bin", "win64");
            var mapsDirectory = Path.Combine(root, "content", "csgo_addons", "test", "maps");
            Directory.CreateDirectory(binaryDirectory);
            Directory.CreateDirectory(mapsDirectory);
            Directory.CreateDirectory(Path.Combine(root, "game", "csgo"));
            File.WriteAllText(Path.Combine(root, "game", "csgo", "gameinfo.gi"), "\"GameInfo\" {}");
            File.WriteAllText(Path.Combine(mapsDirectory, "one.vmap"), "fixture");
            File.WriteAllText(Path.Combine(mapsDirectory, "two.vmap"), "fixture");
            var binary = Path.Combine(binaryDirectory, "resourcecompiler.exe");
            File.WriteAllText(binary, "#!/bin/sh\necho 'phase started'\nprintf '%s\\n' \"$@\"\nwhile [ ! -e proceed ]; do sleep 0.02; done\necho 'phase finished'\n");
            File.SetUnixFileMode(binary, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
            var settings = new JsonSettingsService(Path.Combine(root, "settings.json"));
            settings.Update(value => value.Cs2PathOverride = root);
            var registrations = new ServiceCollection();
            registrations.AddLogging();
            registrations.AddInfrastructure();
            registrations.AddSingleton<Core.Settings.ISettingsService>(settings);
            using var services = registrations.BuildServiceProvider();
            var builder = services.GetRequiredService<IMapBuilderService>();
            var started = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            builder.JobUpdated += (_, job) =>
            {
                if (job.OutputLogs.Contains("phase started")) started.TrySetResult();
            };
            var options = new MapBuildOptions { Threads = 3, SaveBuildLogs = true, LaunchAfterBuild = false };
            var first = await builder.EnqueueBuildAsync("test", "one", options);
            var second = await builder.EnqueueBuildAsync("test", "two", options);
            options.BakeLighting = true;
            await started.Task.WaitAsync(TimeSpan.FromSeconds(10));
            await Assert.That(first.Status).IsEqualTo("Building");
            await Assert.That(second.Status).IsEqualTo("Queued");
            builder.CancelJob(second.Id);
            File.WriteAllText(Path.Combine(binaryDirectory, "proceed"), "");
            var log = Path.Combine(root, "content", "csgo_addons", "test", ".hammer5tools", "build_logs", $"{first.Id}.log");
            using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
            while (!File.Exists(log) || second.FinishedAt is null)
            {
                await Task.Delay(10, timeout.Token);
            }
            await Assert.That(first.Success).IsTrue();
            await Assert.That(second.Status).IsEqualTo("Cancelled");
            await Assert.That(string.Join('\n', first.OutputLogs)).Contains("-nolightmaps");
            await Assert.That(string.Join('\n', first.OutputLogs).Contains("-bakelighting")).IsFalse();
            await Assert.That(await File.ReadAllTextAsync(log)).Contains("phase finished");
            var outside = await builder.EnqueueBuildAsync("test", "../outside", new() { LaunchAfterBuild = false });
            while (outside.FinishedAt is null) await Task.Delay(10, timeout.Token);
            await Assert.That(outside.Status).IsEqualTo("Error");
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }
}

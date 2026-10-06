namespace Hammer5Tools.IntegrationTests.Commands;

using System.IO;
using Hammer5Tools.Core.IO.Commands;
using Hammer5Tools.Core.IO.Cs2;
using Hammer5Tools.Core.IO.Settings;

public class CommandServiceTests
{
    [Test]
    public async Task CommandServiceListensInTheGameDirectory()
    {
        var root = Path.Combine(Path.GetTempPath(), $"h5t-console-{Guid.NewGuid():N}");
        Directory.CreateDirectory(Path.Combine(root, "game", "csgo"));
        try
        {
            await File.WriteAllTextAsync(Path.Combine(root, "game", "csgo", "gameinfo.gi"), "GameInfo {}");
            var settings = new JsonSettingsService(Path.Combine(root, "settings.json"));
            settings.Update(value => value.Cs2PathOverride = root);
            using var service = new CommandService(new Cs2Locator(settings));
            var received = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
            service.OutputLineReceived += (_, line) => received.TrySetResult(line);
            service.Start();
            await File.WriteAllTextAsync(Path.Combine(root, "game", "csgo", Cs2Launcher.LogFileName), "Live output\n");
            await Assert.That(await received.Task.WaitAsync(TimeSpan.FromSeconds(5))).IsEqualTo("Live output");
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    [Test]
    public async Task ConsoleLogListenerTailsAppendedLines()
    {
        var tempFile = Path.Combine(Path.GetTempPath(), "H5T_LogTest_" + Guid.NewGuid().ToString("N") + ".log");

        try
        {
            await File.WriteAllTextAsync(tempFile, "Initial line 1\n");

            using var listener = new ConsoleLogListener(tempFile);
            var receivedLines = new List<string>();
            listener.LineReceived += (_, line) => receivedLines.Add(line);

            listener.Start();

            await File.AppendAllTextAsync(tempFile, "Appended line 2\nAppended line 3\n");
            await Task.Delay(300);

            await Assert.That(receivedLines).Contains("Appended line 2");
            await Assert.That(receivedLines).Contains("Appended line 3");
        }
        finally
        {
            if (File.Exists(tempFile))
            {
                File.Delete(tempFile);
            }
        }
    }

    [Test]
    public async Task CommandServiceGracefullyHandlesDisconnectedPipe()
    {
        var tempDir = Path.Combine(Path.GetTempPath(), "H5T_CmdTest_" + Guid.NewGuid().ToString("N"));
        var settingsFile = Path.Combine(tempDir, "settings.json");

        try
        {
            var settings = new JsonSettingsService(settingsFile);
            var locator = new Cs2Locator(settings);
            using var cmdService = new CommandService(locator);

            await Assert.That(cmdService.IsConnected).IsFalse();
            var success = await cmdService.SendCommandAsync("status");
            await Assert.That(success).IsFalse();
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

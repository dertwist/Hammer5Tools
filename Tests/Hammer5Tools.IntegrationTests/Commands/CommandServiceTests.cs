namespace Hammer5Tools.IntegrationTests.Commands;

using System.IO;
using System.IO.Pipes;
using Hammer5Tools.Core.Commands;
using Hammer5Tools.Core.IO.Commands;
using Hammer5Tools.Core.IO.Cs2;
using Hammer5Tools.Core.IO.Settings;

public class CommandServiceTests
{
    [Test]
    public async Task CommandServiceSurvivesApplicationRestartWithTheGameStillConnected()
    {
        var root = Path.Combine(Path.GetTempPath(), $"h5t-console-{Guid.NewGuid():N}");
        Directory.CreateDirectory(Path.Combine(root, "game", "csgo"));
        var commandName = $"h5t-test-command-{Guid.NewGuid():N}";
        var outputName = $"h5t-test-output-{Guid.NewGuid():N}";
        var controlName = $"h5t-test-control-{Guid.NewGuid():N}";
        using var hostCancellation = new CancellationTokenSource();
        var host = new CommandPipeHost(new Cs2CommandPipe(commandName: commandName, outputName: outputName), controlName);
        var hostTask = host.RunAsync(hostCancellation.Token);
        try
        {
            await File.WriteAllTextAsync(Path.Combine(root, "game", "csgo", "gameinfo.gi"), "GameInfo {}");
            var helperDirectory = Path.Combine(root, "game", "core", "tools", "convarhelper", "workshop");
            Directory.CreateDirectory(helperDirectory);
            await File.WriteAllTextAsync(Path.Combine(helperDirectory, "test.ini"), "[General]\nButton-00-00-Label=Heading\nButton-00-01-AltButtonText=Test preset\nButton-00-01-Command=\"sv_cheats 1; bot_kick\"\nButton-00-01-Description=First\\nSecond\n");
            var settings = new JsonSettingsService(Path.Combine(root, "settings.json"));
            settings.Update(value => value.Cs2PathOverride = root);
            using var service = new CommandService(new Cs2Locator(settings), pipe: new CommandPipeClient(controlName: controlName, launchHost: false));
            var received = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
            service.OutputLineReceived += (_, line) => received.TrySetResult(line);
            service.Start();
            var preset = service.HelperCommands.Single(command => command.Label == "Test preset");
            await Assert.That(preset.Command).IsEqualTo("sv_cheats 1; bot_kick");
            await Assert.That(preset.Description).IsEqualTo("First\nSecond");
            await Assert.That(preset.Row).IsEqualTo(1);
            await Assert.That(preset.Column).IsEqualTo(0);
            await Assert.That(service.HelperCommands.Any(command => command.Source == "test" && command.IsHeading && command.Label == "Heading")).IsTrue();
            ((ICommandService)service).SetVConsoleEnabled(true);
            await Assert.That(((ICommandService)service).Convars.Count).IsEqualTo(0);
            await File.WriteAllTextAsync(Path.Combine(root, "game", "csgo", Cs2Launcher.LogFileName), "Live output\n");
            await Assert.That(await received.Task.WaitAsync(TimeSpan.FromSeconds(5))).IsEqualTo("Live output");
            using var commandPipe = new NamedPipeClientStream(".", commandName, PipeDirection.InOut, PipeOptions.Asynchronous);
            using var outputPipe = new NamedPipeClientStream(".", outputName, PipeDirection.InOut, PipeOptions.Asynchronous);
            await Task.WhenAll(commandPipe.ConnectAsync(5000), outputPipe.ConnectAsync(5000));
            await Assert.That(await service.PrepareLaunchAsync()).IsTrue();
            using var reader = new StreamReader(commandPipe);
            var commandReceived = reader.ReadLineAsync();
            await Assert.That(await service.SendCommandAsync(preset.Command).WaitAsync(TimeSpan.FromSeconds(5))).IsTrue();
            await Assert.That(await commandReceived.WaitAsync(TimeSpan.FromSeconds(5))).IsEqualTo(preset.Command);
            service.Dispose();
            using var restartedService = new CommandService(new Cs2Locator(settings), pipe: new CommandPipeClient(controlName: controlName, launchHost: false));
            await Assert.That(await restartedService.PrepareLaunchAsync()).IsTrue();
            commandReceived = reader.ReadLineAsync();
            await Assert.That(await restartedService.SendCommandAsync("status").WaitAsync(TimeSpan.FromSeconds(5))).IsTrue();
            await Assert.That(await commandReceived.WaitAsync(TimeSpan.FromSeconds(5))).IsEqualTo("status");
            var newOutput = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
            restartedService.OutputLineReceived += (_, line) =>
            {
                if (line == "Output after application restart") newOutput.TrySetResult(line);
            };
            await File.AppendAllTextAsync(Path.Combine(root, "game", "csgo", Cs2Launcher.LogFileName), "Output after application restart\n");
            await Assert.That(await newOutput.Task.WaitAsync(TimeSpan.FromSeconds(5))).IsEqualTo("Output after application restart");
            // Stop/start the same service must also create a fresh application-side connection.
            restartedService.Stop();
            await Assert.That(await restartedService.PrepareLaunchAsync()).IsTrue();
            commandReceived = reader.ReadLineAsync();
            await Assert.That(await restartedService.SendCommandAsync("sv_cheats 1").WaitAsync(TimeSpan.FromSeconds(5))).IsTrue();
            await Assert.That(await commandReceived.WaitAsync(TimeSpan.FromSeconds(5))).IsEqualTo("sv_cheats 1");
            using var anotherClient = new CommandPipeClient(controlName: controlName, launchHost: false);
            await Assert.That(await anotherClient.WaitUntilReadyAsync()).IsTrue();
            commandReceived = reader.ReadLineAsync();
            await Assert.That(await anotherClient.SendCommandAsync("echo another client").WaitAsync(TimeSpan.FromSeconds(5))).IsTrue();
            await Assert.That(await commandReceived.WaitAsync(TimeSpan.FromSeconds(5))).IsEqualTo("echo another client");
        }
        finally
        {
            hostCancellation.Cancel();
            try
            {
                await hostTask;
            }
            catch (OperationCanceledException)
            {
                // End the isolated persistent host after the simulated game exits.
            }
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
            using var cmdService = new CommandService(locator, pipe: new CommandPipeClient(launchHost: false));

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

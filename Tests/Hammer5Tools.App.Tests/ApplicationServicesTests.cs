namespace Hammer5Tools.App.Tests;

using System.Collections.Concurrent;
using System.IO.Pipes;
using Hammer5Tools.App.Services.Lifecycle;
using Hammer5Tools.App.Services.Updates;
using Hammer5Tools.Core.IO.Settings;

[NotInParallel]
public class ApplicationServicesTests
{
    [Test]
    public async Task SingleInstanceGuardRejectsSecondInstanceAndReleasesOwnership()
    {
        var instanceName = $"h5t-instance-test-{Guid.NewGuid():N}";
        bool firstAccepted;
        bool secondAccepted;
        using (var first = new SingleInstanceGuard(instanceName))
        {
            firstAccepted = first.IsFirstInstance;
            using var second = new SingleInstanceGuard(instanceName);
            secondAccepted = second.IsFirstInstance;
        }

        bool nextAccepted;
        using (var next = new SingleInstanceGuard(instanceName))
        {
            nextAccepted = next.IsFirstInstance;
        }

        await Assert.That(firstAccepted).IsTrue();
        await Assert.That(secondAccepted).IsFalse();
        await Assert.That(nextAccepted).IsTrue();
    }

    [Test]
    public async Task LaunchRequestsAreForwardedAndInvalidClientsDoNotStopTheListener()
    {
        var instanceName = $"h5t-forward-test-{Guid.NewGuid():N}";
        var received = new ConcurrentQueue<StartupTool>();
        using (var owner = new SingleInstanceGuard(instanceName))
        {
            owner.StartListening(received.Enqueue);
            using (var invalidClient = new NamedPipeClientStream(".", instanceName, PipeDirection.InOut, PipeOptions.Asynchronous))
            {
                invalidClient.Connect(2000);
                invalidClient.WriteByte(255);
                using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(2));
                invalidClient.ReadAsync(new byte[1], timeout.Token).AsTask().GetAwaiter().GetResult();
            }

            using var client = new SingleInstanceGuard(instanceName);
            foreach (var tool in Enum.GetValues<StartupTool>())
            {
                client.ForwardAsync(tool).GetAwaiter().GetResult();
            }
        }

        await Assert.That(received.ToArray().SequenceEqual(Enum.GetValues<StartupTool>())).IsTrue();
    }

    [Test]
    public async Task StartupArgumentsSelectToolsAndRejectUnknownModes()
    {
        await Assert.That(StartupArguments.Parse([])).IsEqualTo(StartupTool.Main);
        await Assert.That(StartupArguments.Parse(["--tool", "soundevents"])).IsEqualTo(StartupTool.SoundEvents);
        await Assert.That(StartupArguments.Parse(["--tool", "mapbuilder"])).IsEqualTo(StartupTool.MapBuilder);
        await Assert.That(StartupArguments.Parse(["--tool", "workshop"])).IsEqualTo(StartupTool.Workshop);
        await Assert.That(StartupArguments.Parse(["--tool", "smartprops"])).IsEqualTo(StartupTool.SmartProps);
        foreach (var (executable, tool) in new[]
        {
            ("Hammer5Tools.exe", StartupTool.Main),
            ("SoundEventEditor.exe", StartupTool.SoundEvents),
            ("MapBuilder.exe", StartupTool.MapBuilder),
            ("SmartPropEditor.exe", StartupTool.SmartProps),
            ("WorkshopManager.exe", StartupTool.Workshop),
        })
        {
            await Assert.That(StartupArguments.Parse([], Path.Combine(Path.GetTempPath(), executable))).IsEqualTo(tool);
        }
        await Assert.That(StartupArguments.Parse(["--tool", "mapbuilder"], "SmartPropEditor.exe")).IsEqualTo(StartupTool.MapBuilder);
        foreach (var args in new[] { new[] { "--tool" }, new[] { "--tool", "unknown" }, new[] { "--unknown", "soundevents" } })
        {
            var rejected = false;
            try
            {
                StartupArguments.Parse(args);
            }
            catch (ArgumentException)
            {
                rejected = true;
            }

            await Assert.That(rejected).IsTrue();
        }
    }

    [Test]
    public async Task CancelledUpdateCheckClearsCheckingState()
    {
        var settingsPath = Path.Combine(Path.GetTempPath(), $"h5t-update-{Guid.NewGuid():N}", "settings.json");
        var service = new VelopackUpdateService(new JsonSettingsService(settingsPath));
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        var cancelled = false;
        try
        {
            await service.CheckForUpdatesAsync(ct: cancellation.Token);
        }
        catch (OperationCanceledException)
        {
            cancelled = true;
        }

        await Assert.That(cancelled).IsTrue();
        await Assert.That(service.IsChecking).IsFalse();
        await Assert.That(await service.CheckForUpdatesAsync()).IsFalse();
        await Assert.That(service.Status.Contains("not a Velopack installation", StringComparison.Ordinal)).IsTrue();
        await Assert.That(service.IsChecking).IsFalse();
    }
}

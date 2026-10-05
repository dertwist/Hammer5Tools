namespace Hammer5Tools.App.Tests;

using Hammer5Tools.App.Services.Lifecycle;
using Hammer5Tools.App.Services.Updates;
using Hammer5Tools.Core.IO.Settings;

[NotInParallel]
public class ApplicationServicesTests
{
    [Test]
    public async Task SingleInstanceGuardRejectsSecondInstanceAndReleasesOwnership()
    {
        bool instanceAvailable;
        using (var probe = new Mutex(false, "Local\\Hammer5Tools_SingleInstance_Mutex", out var createdNew))
        {
            instanceAvailable = createdNew;
        }

        bool firstAccepted;
        bool secondAccepted;
        using (var first = new SingleInstanceGuard())
        {
            firstAccepted = first.IsFirstInstance;
            using var second = new SingleInstanceGuard();
            secondAccepted = second.IsFirstInstance;
        }

        bool nextAccepted;
        using (var next = new SingleInstanceGuard())
        {
            nextAccepted = next.IsFirstInstance;
        }

        await Assert.That(firstAccepted).IsEqualTo(instanceAvailable);
        await Assert.That(secondAccepted).IsFalse();
        await Assert.That(nextAccepted).IsEqualTo(instanceAvailable);
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
        await Assert.That(service.IsChecking).IsFalse();
    }
}

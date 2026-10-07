namespace Hammer5Tools.App.Tests;

using Avalonia.Controls;
using Avalonia.Headless;
using Avalonia.Interactivity;
using Avalonia.Threading;
using Avalonia.VisualTree;
using Hammer5Tools.App.Features.Shell;
using Hammer5Tools.App.Services;
using Hammer5Tools.App.Services.Updates;
using Hammer5Tools.Core;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.IO.Cs2;
using Hammer5Tools.Core.IO.Settings;
using Hammer5Tools.Core.Settings;
using Microsoft.Extensions.DependencyInjection;
using Velopack;
using Velopack.Locators;

[NotInParallel]
public class StartupRecoveryTests
{
    [Test]
    public async Task NormalLaunchAutomaticallyOpensUpdatesWhenAnEditorCannotStart()
    {
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            var window = Program.OpenToolOrRecovery(() => throw new InvalidOperationException("Editor startup failed after an update."));
            try
            {
                window.UpdateLayout();
                await Assert.That(window is UpdateWindow).IsTrue();
                await Assert.That(window.IsVisible).IsTrue();
                await Assert.That(window.GetVisualDescendants().OfType<Button>()
                    .Any(button => Equals(button.Content, "Check for updates") && button.IsEnabled)).IsTrue();
                await Assert.That(window.GetVisualDescendants().OfType<TextBox>()
                    .Any(text => text.Text == "Editor startup failed after an update.")).IsTrue();
            }
            finally
            {
                window.Close();
            }
            return true;
        }, CancellationToken.None);
    }

    [Test]
    public async Task ShellStartsWithoutSteamOrCs2AndOffersUpdates()
    {
        var root = Path.Combine(Path.GetTempPath(), $"h5t-no-cs2-{Guid.NewGuid():N}");
        var settings = new JsonSettingsService(Path.Combine(root, "settings.json"));
        var services = new ServiceCollection().AddHammer5ToolsCore();
        services.AddLogging();
        services.AddSingleton<ISettingsService>(settings);
        services.AddSingleton<ICs2Locator>(new Cs2Locator(settings, customSteamPath: root));
        services.AddSingleton<DialogService>();
        services.AddSingleton<IDialogService>(provider => provider.GetRequiredService<DialogService>());
        services.AddSingleton<ToolWindowService>();
        services.AddTransient<ShellViewModel>();
        services.AddTransient<MainWindow>();
        using var provider = services.BuildServiceProvider();
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            var tools = provider.GetRequiredService<ToolWindowService>();
            var window = tools.Open(Services.Lifecycle.StartupTool.Main);
            try
            {
                await Assert.That(provider.GetRequiredService<ICs2Locator>().ResolvedCs2Path).IsNull();
                await Assert.That(window.IsVisible).IsTrue();
                var shell = (ShellViewModel)window.DataContext!;
                await Assert.That(shell.Addons.Count).IsEqualTo(0);
                await Assert.That(shell.HelpMenu.Items.Any(item => item.Header == "Check for updates...")).IsTrue();
            }
            finally
            {
                window.Close();
                Dispatcher.UIThread.RunJobs();
            }
            return true;
        }, CancellationToken.None);
    }

    [Test]
    public async Task ReleaseNotesRenderInsideUpdateWindow()
    {
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            using var window = new UpdateWindow(new FakeUpdates(), () => Task.FromResult(true));
            window.Show();
            try
            {
                window.UpdateLayout();
                await Assert.That(window.GetVisualDescendants().OfType<TextBlock>()
                    .Any(text => text.Text == "Version: 2.0.0")).IsTrue();
                await Assert.That(window.Width).IsEqualTo(600);
                await Assert.That(window.Height).IsEqualTo(700);
                var buttons = window.GetVisualDescendants().OfType<Button>().ToArray();
                await Assert.That(buttons.Any(button => Equals(button.Content, "Update"))).IsTrue();
                await Assert.That(buttons.Any(button => Equals(button.Content, "ReleaseNotes"))).IsTrue();
                await Assert.That(buttons.Any(button => Equals(button.Content, "OK"))).IsTrue();
                await Assert.That(window.GetVisualDescendants().OfType<SelectableTextBlock>()
                    .Any(text => text.Inlines?.Text?.Contains("Preserves dirty documents") == true)).IsTrue();
                using var frame = window.CaptureRenderedFrame();
                await Assert.That(frame).IsNotNull();
                var output = Path.Combine(AppContext.BaseDirectory, "snapshots", "update-notes.png");
                Directory.CreateDirectory(Path.GetDirectoryName(output)!);
                frame!.Save(output, Avalonia.Media.Imaging.PngBitmapEncoderOptions.Default);
            }
            finally
            {
                window.Close();
            }
            return true;
        }, CancellationToken.None);
    }

    [Test]
    public async Task RecoveryRendersAndCancelledRestartDoesNotApplyTheUpdate()
    {
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            var updates = new FakeUpdates();
            using var window = new UpdateWindow(updates, () => Task.FromResult(false), "A startup service failed.");
            window.Show();
            try
            {
                window.UpdateLayout();
                using var frame = window.CaptureRenderedFrame();
                await Assert.That(frame).IsNotNull();
                var output = Path.Combine(AppContext.BaseDirectory, "snapshots", "startup-recovery.png");
                Directory.CreateDirectory(Path.GetDirectoryName(output)!);
                frame!.Save(output, Avalonia.Media.Imaging.PngBitmapEncoderOptions.Default);
                var buttons = window.GetVisualDescendants().OfType<Button>().ToArray();
                var check = buttons.Single(button => Equals(button.Content, "Check for updates"));
                var download = buttons.Single(button => Equals(button.Content, "Download update"));
                var install = buttons.Single(button => Equals(button.Content, "Install and restart"));
                check.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                await Assert.That(download.IsEnabled).IsTrue();
                download.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                await Assert.That(install.IsEnabled).IsTrue();
                install.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                await Assert.That(updates.Applied).IsFalse();
                await Assert.That(install.IsEnabled).IsTrue();
            }
            finally
            {
                window.Close();
            }
            return true;
        }, CancellationToken.None);
    }

    [Test]
    public async Task UpdateFailuresCanBeRetriedAndOnlyCompletedDownloadsAreInstallable()
    {
        var manager = new FakeUpdateManager();
        string? requestedChannel = null;
        var service = new VelopackUpdateService(channel =>
        {
            requestedChannel = channel;
            return manager;
        }, "dev");
        await Assert.That(await service.CheckForUpdatesAsync()).IsTrue();
        await Assert.That(requestedChannel).IsEqualTo("dev");
        await Assert.That(service.AvailableVersion).IsEqualTo("2.0.0");
        manager.FailDownload = true;
        var failed = false;
        try
        {
            await service.DownloadUpdateAsync();
        }
        catch (IOException)
        {
            failed = true;
        }
        await Assert.That(failed).IsTrue();
        await Assert.That(service.IsChecking).IsFalse();
        await Assert.That(service.IsDownloaded).IsFalse();
        manager.FailDownload = false;
        await service.DownloadUpdateAsync();
        await Assert.That(service.IsDownloaded).IsTrue();
        manager.FailCheck = true;
        try
        {
            await service.CheckForUpdatesAsync();
        }
        catch (IOException)
        {
        }
        await Assert.That(service.AvailableVersion).IsNull();
        await Assert.That(service.IsDownloaded).IsFalse();
        await Assert.That(service.IsChecking).IsFalse();
        manager.FailCheck = false;
        await Assert.That(await service.CheckForUpdatesAsync()).IsTrue();
        service.Channel = "stable";
        await Assert.That(service.AvailableVersion).IsNull();
        await Assert.That(service.IsDownloaded).IsFalse();
        manager.PackageId = "Hammer5Tools.Legacy";
        var rejected = false;
        try
        {
            await service.CheckForUpdatesAsync();
        }
        catch (InvalidDataException)
        {
            rejected = true;
        }
        await Assert.That(rejected).IsTrue();
        await Assert.That(service.AvailableVersion).IsNull();
    }

    private sealed class FakeUpdateManager() : UpdateManager(Path.GetTempPath(), locator:
        new TestVelopackLocator("Hammer5Tools.Managed", "1.0.0", Path.GetTempPath()))
    {
        public bool FailDownload { get; set; }
        public bool FailCheck { get; set; }
        public string PackageId { get; set; } = "Hammer5Tools.Managed";

        public override Task<UpdateInfo?> CheckForUpdatesAsync() => FailCheck
            ? Task.FromException<UpdateInfo?>(new IOException("Feed unavailable"))
            : Task.FromResult<UpdateInfo?>(new UpdateInfo(new VelopackAsset { PackageId = PackageId, Version = SemanticVersion.Parse("2.0.0") }, false));

        public override Task DownloadUpdatesAsync(UpdateInfo updates, Action<int>? progress = null, CancellationToken cancelToken = default) => FailDownload
            ? Task.FromException(new IOException("Download interrupted")) : Task.CompletedTask;
    }

    private sealed class FakeUpdates : IUpdateService
    {
        public bool IsChecking => false;
        public string Channel { get; set; } = "stable";
        public string Status => "Update ready";
        public string? AvailableVersion { get; private set; }
        public bool IsDownloaded { get; private set; }
        public bool Applied { get; private set; }

        public Task<bool> CheckForUpdatesAsync(bool silent = true, CancellationToken ct = default)
        {
            AvailableVersion = "2.0.0";
            return Task.FromResult(true);
        }

        public Task DownloadUpdateAsync(Action<int>? progress = null, CancellationToken ct = default)
        {
            IsDownloaded = true;
            return Task.CompletedTask;
        }

        public Task<IReadOnlyList<ReleaseNotes>> LoadReleaseNotesAsync(CancellationToken ct = default)
            => Task.FromResult<IReadOnlyList<ReleaseNotes>>([
                new("2.0.0", "## Editors\n- **Preserves dirty documents** when a save is cancelled.\n- Standalone tools share the same application.\n\n## Updates\nDownload progress stays inside the updater.\n[Release details](https://github.com/dertwist/Hammer5Tools/releases)", new Uri("https://github.com/dertwist/Hammer5Tools/releases")),
                new("1.9.0", "## Workshop\n- Submission state is retained across editor switches.\n- Shared compact controls and typography.", new Uri("https://github.com/dertwist/Hammer5Tools/releases")),
            ]);

        public void ApplyUpdateAndRestart() => Applied = true;
    }
}

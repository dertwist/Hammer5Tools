namespace Hammer5Tools.App.Tests;

using Avalonia.Controls;
using Avalonia.Headless;
using Avalonia.Input;
using Avalonia.Threading;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.Features.Console;
using Hammer5Tools.Core.Commands;

[NotInParallel]
public class ConsoleTests
{
    [Test]
    public async Task EnterRespectsToggleAndFailedSendsKeepInputAndHelperUsesLiveCatalog()
    {
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            var service = new TestCommands();
            using var model = new ConsoleViewModel(service);
            var view = new ConsoleView { DataContext = model };
            var window = new Window { Content = view, Width = 880, Height = 560 };
            window.Show();
            var input = view.FindControl<TextBox>("CommandInput")!;
            model.InputCommand = "status";
            model.SendOnEnter = false;
            input.RaiseEvent(new KeyEventArgs { RoutedEvent = InputElement.KeyDownEvent, Key = Key.Enter });
            await Assert.That(service.Sent.Count).IsEqualTo(0);
            model.SendOnEnter = true;
            input.RaiseEvent(new KeyEventArgs { RoutedEvent = InputElement.KeyDownEvent, Key = Key.Enter });
            await ((IAsyncRelayCommand)model.SendCommand).ExecutionTask!;
            await Assert.That(service.Sent.Single()).IsEqualTo("status");
            await Assert.That(model.InputCommand).IsEqualTo(string.Empty);
            service.Success = false;
            model.InputCommand = "say hello";
            await ((IAsyncRelayCommand)model.SendCommand).ExecuteAsync(null);
            await Assert.That(model.InputCommand).IsEqualTo("say hello");
            await Assert.That(model.OutputLines.Last()).Contains("not sent");
            service.Convars = [new("sv_gravity", 0, 0, 1000, "800"), new("mp_roundtime", 0, 0, 60)];
            model.ConvarFilter = "gravity";
            await Assert.That(model.Convars.Single().Name).IsEqualTo("sv_gravity");
            model.SelectedConvar = model.Convars.Single();
            await Assert.That(model.InputCommand).IsEqualTo("sv_gravity ");
            service.Emit("Game output æ世界");
            Dispatcher.UIThread.RunJobs();
            await Assert.That(model.OutputLines.Last()).IsEqualTo("Game output æ世界");
            view.FindControl<Expander>("ConvarHelper")!.IsExpanded = true;
            Dispatcher.UIThread.RunJobs();
            var output = Path.Combine(Path.GetTempPath(), "h5t-console-preview.png");
            using var frame = window.CaptureRenderedFrame();
            frame!.Save(output, Avalonia.Media.Imaging.PngBitmapEncoderOptions.Default);
            window.Close();
            return true;
        }, CancellationToken.None);
    }

    private sealed class TestCommands : ICommandService
    {
        public bool IsConnected => true;
        public string VConsoleStatus => "VConsole connected";
        public int ConvarRevision => 1;
        public IReadOnlyList<ConsoleVariable> Convars { get; set; } = [];
        public event EventHandler<string>? OutputLineReceived;
        public List<string> Sent { get; } = [];
        public bool Success { get; set; } = true;
        public void Emit(string line) => OutputLineReceived?.Invoke(this, line);
        public void Start() { }
        public void Stop() { }
        public void SetVConsoleEnabled(bool enabled) { }
        public Task<bool> SendCommandAsync(string command, CancellationToken ct = default)
        {
            Sent.Add(command);
            return Task.FromResult(Success);
        }
        public Task<bool> SendCommandsAsync(IEnumerable<string> commands, CancellationToken ct = default) => Task.FromResult(Success);
    }
}

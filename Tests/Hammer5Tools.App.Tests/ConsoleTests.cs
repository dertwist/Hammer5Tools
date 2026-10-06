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
    public async Task EnterRespectsToggleAndFailedSendsKeepInputAndHelperUsesPresets()
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
            service.HelperCommands = [new("Gravity", "sv_gravity 800", "", "Test"), new("Round time", "mp_roundtime 60", "", "Test")];
            model.ConvarFilter = "gravity";
            await Assert.That(model.Convars.Single().Command).IsEqualTo("sv_gravity 800");
            model.SelectedConvar = model.Convars.Single();
            await Assert.That(model.InputCommand).IsEqualTo("sv_gravity 800");
            service.Emit("Game output æ世界");
            await Task.Delay(300);
            Dispatcher.UIThread.RunJobs();
            await Assert.That(model.OutputLines.Last()).IsEqualTo("Game output æ世界");
            for (var index = 0; index < 20000; index++)
            {
                service.Emit($"Flood {index}");
            }
            // Emitting a flood queues no per-line UI work.
            Dispatcher.UIThread.RunJobs();
            await Assert.That(model.OutputLines.Last()).IsEqualTo("Game output æ世界");
            await Task.Delay(300);
            Dispatcher.UIThread.RunJobs();
            await Assert.That(model.OutputLines.Count).IsEqualTo(1000);
            await Assert.That(model.OutputLines.Last()).IsEqualTo("Flood 19999");
            model.PauseOutput = true;
            service.Emit("Paused output");
            await Task.Delay(300);
            Dispatcher.UIThread.RunJobs();
            await Assert.That(model.OutputLines.Last()).IsEqualTo("Flood 19999");
            model.ClearCommand.Execute(null);
            model.PauseOutput = false;
            await Task.Delay(300);
            Dispatcher.UIThread.RunJobs();
            await Assert.That(model.OutputLines.Count).IsEqualTo(0);
            await Assert.That(view.FindControl<Grid>("HelperGrid")!.Children.Count).IsEqualTo(1);
            Dispatcher.UIThread.RunJobs();
            var output = Path.Combine(Path.GetTempPath(), "h5t-console-preview.png");
            using var frame = window.CaptureRenderedFrame();
            frame!.Save(output, Avalonia.Media.Imaging.PngBitmapEncoderOptions.Default);
            window.Close();
            return true;
        }, CancellationToken.None);
    }

    [Test]
    public async Task HelperPreservesPageGridAndButtonsSendCommands()
    {
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            var cells = Hammer5Tools.Core.IO.Commands.ConvarHelperFiles.ReadPage(new Dictionary<string, string>
            {
                ["GridWidth"] = "2",
                ["GridHeight"] = "12",
                ["Button-00-00-Label"] = "Lighting",
                ["Button-00-01-AltButtonText"] = "Fullbright",
                ["Button-00-01-Command"] = "toggle mat_fullbright 1 0",
                ["Button-01-00-Label"] = "Rendering",
                ["Button-01-01-AltButtonText"] = "Wireframe Views",
                ["Button-01-01-Command"] = "toggle mat_wireframe 0 2 1",
                ["Button-00-10-Label"] = "View",
                ["Button-00-11-AltButtonText"] = "First Person",
                ["Button-00-11-Command"] = "firstperson"
            }, "Workshop");
            var service = new TestCommands { HelperCommands = [.. cells, new("User command", "status", "", "User page 1")] };
            using var model = new ConsoleViewModel(service);
            var view = new ConsoleView { DataContext = model };
            var window = new Window { Content = view, Width = 1100, Height = 640 };
            window.Show();
            await Assert.That(model.SelectedPage).IsEqualTo("User page 1");
            model.SelectedPage = "Workshop";
            var grid = view.FindControl<Grid>("HelperGrid")!;
            await Assert.That(grid.ColumnDefinitions.Count).IsEqualTo(2);
            await Assert.That(grid.RowDefinitions.Count).IsEqualTo(12);
            await Assert.That(grid.Children.Count).IsEqualTo(6);
            var button = grid.Children.OfType<Button>().Single(control => Equals(control.Content, "Wireframe Views"));
            await Assert.That(Grid.GetColumn(button)).IsEqualTo(1);
            await Assert.That(Grid.GetRow(button)).IsEqualTo(1);
            await model.SendHelperCommand.ExecuteAsync(button.CommandParameter);
            await Assert.That(service.Sent.Single()).IsEqualTo("toggle mat_wireframe 0 2 1");
            await Assert.That(model.InputCommand).IsEqualTo(string.Empty);
            model.ConvarFilter = "firstperson";
            await Assert.That(grid.Children.OfType<Button>().Count()).IsEqualTo(1);
            await Assert.That(model.InputCommand).IsEqualTo(string.Empty);
            model.ConvarFilter = string.Empty;
            service.Emit("[General] Command pipe console ready");
            await Task.Delay(300);
            Dispatcher.UIThread.RunJobs();
            using var frame = window.CaptureRenderedFrame();
            frame!.Save(Path.Combine(Path.GetTempPath(), "h5t-console-layout-preview.png"), Avalonia.Media.Imaging.PngBitmapEncoderOptions.Default);
            window.Close();
            return true;
        }, CancellationToken.None);
    }

    private sealed class TestCommands : ICommandService
    {
        public bool IsConnected => true;
        public IReadOnlyList<ConsoleHelperCommand> HelperCommands { get; set; } = [];
        public event EventHandler<string>? OutputLineReceived;
        public List<string> Sent { get; } = [];
        public bool Success { get; set; } = true;
        public void Emit(string line) => OutputLineReceived?.Invoke(this, line);
        public void Start() { }
        public void Stop() { }
        public Task<bool> SendCommandAsync(string command, CancellationToken ct = default)
        {
            Sent.Add(command);
            return Task.FromResult(Success);
        }
        public Task<bool> SendCommandsAsync(IEnumerable<string> commands, CancellationToken ct = default) => Task.FromResult(Success);
    }
}

namespace Hammer5Tools.App.Features.Console;

using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Commands;

public class ConsoleViewModel : DocumentViewModel
{
    private readonly ICommandService CommandService;
    private string InputCommandValue = string.Empty;

    public ObservableCollection<string> OutputLines { get; } = [];

    public string InputCommand
    {
        get => InputCommandValue;
        set => SetProperty(ref InputCommandValue, value);
    }

    public IRelayCommand SendCommand { get; }

    public IRelayCommand ClearCommand { get; }

    public ConsoleViewModel(ICommandService commandService)
    {
        CommandService = commandService;
        Title = "CS2 Console";

        SendCommand = new AsyncRelayCommand(OnSendCommandAsync);
        ClearCommand = new RelayCommand(OutputLines.Clear);

        CommandService.OutputLineReceived += OnOutputLineReceived;
        CommandService.Start();
    }

    private async Task OnSendCommandAsync()
    {
        var cmd = InputCommand.Trim();
        if (string.IsNullOrWhiteSpace(cmd))
        {
            return;
        }

        OutputLines.Add($"> {cmd}");
        InputCommand = string.Empty;
        await CommandService.SendCommandAsync(cmd);
    }

    private void OnOutputLineReceived(object? sender, string line)
    {
        Avalonia.Threading.Dispatcher.UIThread.Post(() =>
        {
            OutputLines.Add(line);
            if (OutputLines.Count > 1000)
            {
                OutputLines.RemoveAt(0);
            }
        });
    }
}

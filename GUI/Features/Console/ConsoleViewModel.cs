namespace Hammer5Tools.App.Features.Console;

using System.Collections.ObjectModel;
using Avalonia.Threading;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Commands;

public class ConsoleViewModel : DocumentViewModel
{
    public override string IconUri => "avares://Hammer5Tools/Assets/Icons/vmix_sm.png";

    private readonly ICommandService CommandService;
    private string InputCommandValue = string.Empty;
    private bool SendOnEnterValue = true;
    private bool PauseOutputValue;
    private readonly Lock OutputLock = new();
    private readonly Queue<string> PendingOutput = new();
    private ObservableCollection<string> OutputLinesValue = [];
    private string ConvarFilterValue = string.Empty;
    private string ConnectionStatusValue = string.Empty;
    private ConsoleHelperCommand? SelectedConvarValue;
    private string? SelectedPageValue;
    private ObservableCollection<ConsoleHelperCommand> ConvarsValue = [];
    private readonly DispatcherTimer RefreshTimer;
    private bool IsDisposed;

    public bool SendOnEnter
    {
        get => SendOnEnterValue;
        set => SetProperty(ref SendOnEnterValue, value);
    }

    public bool PauseOutput
    {
        get => PauseOutputValue;
        set
        {
            lock (OutputLock)
            {
                if (SetProperty(ref PauseOutputValue, value))
                {
                    PendingOutput.Clear();
                }
            }
        }
    }

    public string ConnectionStatus
    {
        get => ConnectionStatusValue;
        private set => SetProperty(ref ConnectionStatusValue, value);
    }

    public string ConvarFilter
    {
        get => ConvarFilterValue;
        set
        {
            if (SetProperty(ref ConvarFilterValue, value))
            {
                RefreshConvars();
            }
        }
    }

    public ConsoleHelperCommand? SelectedConvar
    {
        get => SelectedConvarValue;
        set
        {
            if (SetProperty(ref SelectedConvarValue, value) && value is not null)
            {
                InputCommand = value.Command;
            }
        }
    }

    public ObservableCollection<string> Pages { get; } = [];

    public string? SelectedPage
    {
        get => SelectedPageValue;
        set
        {
            if (SetProperty(ref SelectedPageValue, value))
            {
                RefreshConvars();
            }
        }
    }

    public ObservableCollection<ConsoleHelperCommand> Convars
    {
        get => ConvarsValue;
        private set => SetProperty(ref ConvarsValue, value);
    }

    public IAsyncRelayCommand<ConsoleHelperCommand> SendHelperCommand { get; }

    public ObservableCollection<string> OutputLines
    {
        get => OutputLinesValue;
        private set => SetProperty(ref OutputLinesValue, value);
    }

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
        Title = "Console";

        SendCommand = new AsyncRelayCommand(OnSendCommandAsync);
        SendHelperCommand = new AsyncRelayCommand<ConsoleHelperCommand>(async preset =>
        {
            if (preset is null || preset.IsHeading)
            {
                return;
            }
            InputCommand = preset.Command;
            await OnSendCommandAsync();
        });
        ClearCommand = new RelayCommand(() =>
        {
            lock (OutputLock)
            {
                PendingOutput.Clear();
            }
            OutputLines.Clear();
        });

        CommandService.OutputLineReceived += OnOutputLineReceived;
        CommandService.Start();
        foreach (var page in CommandService.HelperCommands.Select(command => command.Source).Distinct())
        {
            Pages.Add(page);
        }
        SelectedPage = Pages.FirstOrDefault(page => page.StartsWith("User page", StringComparison.Ordinal)) ?? Pages.FirstOrDefault();
        RefreshConvars();
        RefreshTimer = new DispatcherTimer(TimeSpan.FromMilliseconds(200), DispatcherPriority.Background, (_, _) =>
        {
            ConnectionStatus = CommandService.IsConnected ? "Command pipe connected" : "Command pipe disconnected";
            FlushOutput();
        });
        RefreshTimer.Start();
    }

    private async Task OnSendCommandAsync()
    {
        var cmd = InputCommand.Trim();
        if (string.IsNullOrWhiteSpace(cmd))
        {
            return;
        }

        OutputLines.Add($"> {cmd}");
        if (await CommandService.SendCommandAsync(cmd))
        {
            if (InputCommand.Trim() == cmd)
            {
                InputCommand = string.Empty;
            }
        }
        else
        {
            OutputLines.Add("Command was not sent: CS2 is disconnected. Launch CS2 through Hammer 5 Tools to connect the command pipe.");
        }
    }

    private void RefreshConvars()
    {
        var selectedName = SelectedConvar?.Command;
        Convars = new(CommandService.HelperCommands.Where(variable =>
            (SelectedPage is null || variable.Source == SelectedPage) &&
            (variable.IsHeading || variable.Details.Contains(ConvarFilter, StringComparison.OrdinalIgnoreCase))));
        // Updating the catalog must not overwrite a command the user is typing.
        SelectedConvarValue = Convars.FirstOrDefault(variable => variable.Command == selectedName);
        OnPropertyChanged(nameof(SelectedConvar));
    }

    private void OnOutputLineReceived(object? sender, string line)
    {
        lock (OutputLock)
        {
            if (IsDisposed || PauseOutputValue)
            {
                return;
            }
            PendingOutput.Enqueue(line.Length > 4096 ? line[..4096] + "..." : line);
            if (PendingOutput.Count > 1000)
            {
                PendingOutput.Dequeue();
            }
        }
    }

    private void FlushOutput()
    {
        string[] batch;
        lock (OutputLock)
        {
            if (PendingOutput.Count == 0)
            {
                return;
            }
            batch = PendingOutput.ToArray();
            PendingOutput.Clear();
        }
        // Replace once per tick so a log flood cannot queue one UI operation per line.
        OutputLines = new(OutputLines.Concat(batch).TakeLast(1000));
    }

    public override void Dispose()
    {
        lock (OutputLock)
        {
            IsDisposed = true;
            PendingOutput.Clear();
        }
        RefreshTimer.Stop();
        CommandService.OutputLineReceived -= OnOutputLineReceived;
        base.Dispose();
        GC.SuppressFinalize(this);
    }
}

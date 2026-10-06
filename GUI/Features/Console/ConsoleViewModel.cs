namespace Hammer5Tools.App.Features.Console;

using System.Collections.ObjectModel;
using Avalonia.Threading;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Commands;

public class ConsoleViewModel : DocumentViewModel
{
    private readonly ICommandService CommandService;
    private string InputCommandValue = string.Empty;
    private bool SendOnEnterValue = true;
    private bool ListenViaVConsoleValue;
    private string ConvarFilterValue = string.Empty;
    private string ConnectionStatusValue = string.Empty;
    private ConsoleVariable? SelectedConvarValue;
    private readonly DispatcherTimer RefreshTimer;
    private int CatalogRevision = -1;
    private bool IsDisposed;

    public bool SendOnEnter
    {
        get => SendOnEnterValue;
        set => SetProperty(ref SendOnEnterValue, value);
    }

    public bool ListenViaVConsole
    {
        get => ListenViaVConsoleValue;
        set
        {
            if (SetProperty(ref ListenViaVConsoleValue, value))
            {
                CommandService.SetVConsoleEnabled(value);
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

    public ConsoleVariable? SelectedConvar
    {
        get => SelectedConvarValue;
        set
        {
            if (SetProperty(ref SelectedConvarValue, value) && value is not null)
            {
                InputCommand = value.Name + " ";
            }
        }
    }

    public ObservableCollection<ConsoleVariable> Convars { get; } = [];

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
        ListenViaVConsole = true;
        RefreshTimer = new DispatcherTimer(TimeSpan.FromMilliseconds(500), DispatcherPriority.Background, (_, _) =>
        {
            ConnectionStatus = CommandService.VConsoleStatus;
            if (CatalogRevision != CommandService.ConvarRevision)
            {
                RefreshConvars();
            }
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
            OutputLines.Add("Command was not sent: CS2 is disconnected. Launch CS2 through Hammer 5 Tools or connect VConsole.");
        }
    }

    private void RefreshConvars()
    {
        CatalogRevision = CommandService.ConvarRevision;
        var selectedName = SelectedConvar?.Name;
        Convars.Clear();
        foreach (var variable in CommandService.Convars.Where(variable => variable.Name.Contains(ConvarFilter, StringComparison.OrdinalIgnoreCase)))
        {
            Convars.Add(variable);
        }
        // Updating the catalog must not overwrite a command the user is typing.
        SelectedConvarValue = Convars.FirstOrDefault(variable => variable.Name == selectedName);
        OnPropertyChanged(nameof(SelectedConvar));
    }

    private void OnOutputLineReceived(object? sender, string line)
    {
        Avalonia.Threading.Dispatcher.UIThread.Post(() =>
        {
            if (IsDisposed)
            {
                return;
            }
            OutputLines.Add(line);
            if (OutputLines.Count > 1000)
            {
                OutputLines.RemoveAt(0);
            }
        });
    }
    public override void Dispose()
    {
        IsDisposed = true;
        RefreshTimer.Stop();
        CommandService.OutputLineReceived -= OnOutputLineReceived;
        base.Dispose();
        GC.SuppressFinalize(this);
    }
}

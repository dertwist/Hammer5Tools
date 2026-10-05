namespace Hammer5Tools.App;

using Avalonia;
using Avalonia.Controls;
using Hammer5Tools.App.Controls;
using Hammer5Tools.App.Features.Shell;
using Hammer5Tools.Core.Settings;
using Microsoft.Extensions.DependencyInjection;

public partial class MainWindow : Window, IDisposable
{
    private bool ClosingConfirmed;
    private bool IsCheckingClose;
    private bool ForceExit;
    private TrayIcon? Tray;

    public MainWindow()
    {
        InitializeComponent();
        MinWidth = 800;
        MinHeight = 500;
        Closing += OnClosing;
    }

    public MainWindow(ShellViewModel viewModel) : this()
    {
        DataContext = viewModel;
        var settings = Program.Services?.GetService<ISettingsService>();
        if (settings is not null)
        {
            var saved = settings.Settings.WindowState;
            Width = Math.Max(MinWidth, saved.Width);
            Height = Math.Max(MinHeight, saved.Height);
            if (saved.X is { } x && saved.Y is { } y)
            {
                var position = new PixelPoint((int)x, (int)y);
                if (Screens.All.Any(screen => screen.WorkingArea.Contains(position)))
                {
                    Position = position;
                    WindowStartupLocation = WindowStartupLocation.Manual;
                }
            }

            WindowState = saved.IsMaximized ? WindowState.Maximized : WindowState.Normal;
        }

        viewModel.ExitRequested += (_, _) =>
        {
            ForceExit = true;
            Close();
        };
        var menu = new NativeMenu();
        var show = new NativeMenuItem("Show Hammer 5 Tools");
        show.Click += (_, _) => { Show(); Activate(); };
        var exit = new NativeMenuItem("Exit");
        exit.Click += (_, _) => { ForceExit = true; Close(); };
        menu.Items.Add(show);
        menu.Items.Add(exit);
        Tray = new TrayIcon { Icon = Icon, ToolTipText = "Hammer 5 Tools", Menu = menu };
        Tray.Clicked += (_, _) => { Show(); Activate(); };
        TrayIcon.SetIcons(Application.Current!, [Tray]);
        Closed += (_, _) => { Dispose(); viewModel.Dispose(); };
    }

    private async void OnClosing(object? sender, WindowClosingEventArgs e)
    {
        if (ClosingConfirmed || DataContext is not ShellViewModel shell)
        {
            return;
        }

        e.Cancel = true;
        if (IsCheckingClose)
        {
            return;
        }

        var settings = Program.Services?.GetService<ISettingsService>();
        SaveWindowState(settings);
        if (!ForceExit && settings?.Settings.Editor.MinimizeToTray == true)
        {
            Hide();
            return;
        }

        IsCheckingClose = true;
        try
        {
            if (await shell.CanExitAsync())
            {
                WorkspaceView.SaveAllLayouts();
                ClosingConfirmed = true;
                Close();
            }
        }
        finally
        {
            IsCheckingClose = false;
        }
    }

    private void SaveWindowState(ISettingsService? settings)
    {
        settings?.Update(value =>
        {
            if (WindowState == WindowState.Normal)
            {
                value.WindowState.Width = Math.Max(MinWidth, Width);
                value.WindowState.Height = Math.Max(MinHeight, Height);
                value.WindowState.X = Position.X;
                value.WindowState.Y = Position.Y;
            }

            value.WindowState.IsMaximized = WindowState == WindowState.Maximized;
        });
    }
    public void Dispose()
    {
        Tray?.Dispose();
        GC.SuppressFinalize(this);
    }
}

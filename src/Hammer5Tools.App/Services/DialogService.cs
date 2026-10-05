namespace Hammer5Tools.App.Services;

using System;
using System.Collections.Generic;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;

public interface IDialogService
{
    void ShowUtility(string title, object viewModel, double width = 960, double height = 650);
}

public class DialogService : IDialogService
{
    private readonly Dictionary<Type, Window> OpenWindows = [];

    public void ShowUtility(string title, object viewModel, double width = 960, double height = 650)
    {
        ArgumentNullException.ThrowIfNull(viewModel);

        var type = viewModel.GetType();
        if (OpenWindows.TryGetValue(type, out var existingWindow))
        {
            existingWindow.Activate();
            return;
        }

        var window = new Window
        {
            Title = $"{title} — Hammer 5 Tools",
            Width = width,
            Height = height,
            MinWidth = 600,
            MinHeight = 400,
            WindowStartupLocation = WindowStartupLocation.CenterScreen,
            DataContext = viewModel,
            Content = new ContentControl { Content = viewModel }
        };

        window.Closed += (_, _) => OpenWindows.Remove(type);
        OpenWindows[type] = window;

        if (Application.Current?.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop && desktop.MainWindow is not null)
        {
            window.Show(desktop.MainWindow);
        }
        else
        {
            window.Show();
        }
    }
}

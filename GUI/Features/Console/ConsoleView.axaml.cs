namespace Hammer5Tools.App.Features.Console;

using System.ComponentModel;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Media;

public partial class ConsoleView : UserControl
{
    private ConsoleViewModel? Model;

    public ConsoleView()
    {
        InitializeComponent();
        DataContextChanged += (_, _) =>
        {
            if (Model is not null)
            {
                Model.PropertyChanged -= OnModelPropertyChanged;
            }
            Model = DataContext as ConsoleViewModel;
            if (Model is not null)
            {
                Model.PropertyChanged += OnModelPropertyChanged;
            }
            RebuildHelperGrid();
        };
    }

    private void OnModelPropertyChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (e.PropertyName == nameof(ConsoleViewModel.Convars))
        {
            RebuildHelperGrid();
        }
    }

    private void RebuildHelperGrid()
    {
        HelperGrid.Children.Clear();
        HelperGrid.ColumnDefinitions.Clear();
        HelperGrid.RowDefinitions.Clear();
        if (Model is null || Model.Convars.Count == 0)
        {
            return;
        }
        for (var column = 0; column < Model.Convars.Max(cell => cell.GridWidth); column++)
        {
            HelperGrid.ColumnDefinitions.Add(new ColumnDefinition(GridLength.Star));
        }
        for (var row = 0; row < Model.Convars.Max(cell => cell.GridHeight); row++)
        {
            HelperGrid.RowDefinitions.Add(new RowDefinition(new GridLength(22)));
        }
        foreach (var cell in Model.Convars)
        {
            Control control;
            if (cell.IsHeading)
            {
                var heading = new Border
                {
                    BorderThickness = new Thickness(0, 1, 0, 1),
                    Child = new TextBlock
                    {
                        Text = cell.Label,
                        FontWeight = FontWeight.SemiBold,
                        HorizontalAlignment = Avalonia.Layout.HorizontalAlignment.Center,
                        VerticalAlignment = Avalonia.Layout.VerticalAlignment.Center
                    }
                };
                heading.Bind(Border.BorderBrushProperty, this.GetResourceObservable("H5TBorderBrush"));
                control = heading;
            }
            else
            {
                var button = new Button
                {
                    Content = cell.Label,
                    Command = Model.SendHelperCommand,
                    CommandParameter = cell,
                    HorizontalAlignment = Avalonia.Layout.HorizontalAlignment.Stretch,
                    HorizontalContentAlignment = Avalonia.Layout.HorizontalAlignment.Center,
                    Margin = new Thickness(1),
                    Padding = new Thickness(2, 0),
                    FontSize = 12
                };
                ToolTip.SetTip(button, $"{cell.Command}\n{cell.Description}");
                control = button;
            }
            Grid.SetColumn(control, cell.Column);
            Grid.SetRow(control, cell.Row);
            HelperGrid.Children.Add(control);
        }
    }

    private void OnCommandKeyDown(object? sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter && e.KeyModifiers == KeyModifiers.None &&
            DataContext is ConsoleViewModel { SendOnEnter: true } viewModel)
        {
            e.Handled = true;
            if (viewModel.SendCommand.CanExecute(null))
            {
                viewModel.SendCommand.Execute(null);
            }
        }
    }
}

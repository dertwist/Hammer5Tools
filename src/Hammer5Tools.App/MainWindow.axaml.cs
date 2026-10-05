namespace Hammer5Tools.App;

using Avalonia.Controls;
using Hammer5Tools.App.Features.Shell;

public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
    }

    public MainWindow(ShellViewModel viewModel) : this()
    {
        DataContext = viewModel;
    }
}

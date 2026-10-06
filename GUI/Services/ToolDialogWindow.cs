namespace Hammer5Tools.App.Services;

using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Layout;
using Hammer5Tools.App.Controls;
using Hammer5Tools.App.ViewModels;

internal sealed class ToolDialogWindow : Window
{
    internal static readonly DataFormat<ToolDialogWindow> DragFormat =
        DataFormat.CreateInProcessFormat<ToolDialogWindow>("h5t-tool-dialog");

    private readonly Action<DocumentViewModel> Dock;
    private readonly IDialogService Dialogs;
    private bool CheckingClose;
    private bool CloseConfirmed;
    private PointerPressedEventArgs? DragTrigger;
    private Point DragStart;

    internal DocumentViewModel Document { get; }
    internal bool IsDocked { get; private set; }

    internal ToolDialogWindow(string title, DocumentViewModel document, IDialogService dialogs,
        Action<DocumentViewModel> dock, double width, double height)
    {
        Document = document;
        Dialogs = dialogs;
        Dock = dock;
        Title = $"{title} - Hammer 5 Tools";
        Width = width;
        Height = height;
        MinWidth = 450;
        MinHeight = 300;
        WindowStartupLocation = WindowStartupLocation.CenterOwner;
        DataContext = document;
        var handle = new Border { Padding = new Thickness(8), Background = Avalonia.Media.Brushes.Transparent };
        handle.Child = new TextBlock { Text = "Drag into editor tabs", VerticalAlignment = VerticalAlignment.Center };
        handle.PointerPressed += (_, args) =>
        {
            if (!args.GetCurrentPoint(handle).Properties.IsLeftButtonPressed) return;
            DragTrigger = args;
            DragStart = args.GetPosition(handle);
        };
        handle.PointerReleased += (_, _) => DragTrigger = null;
        handle.PointerMoved += async (_, args) =>
        {
            if (DragTrigger is not { } trigger || !args.GetCurrentPoint(handle).Properties.IsLeftButtonPressed
                || Math.Abs(args.GetPosition(handle).X - DragStart.X) + Math.Abs(args.GetPosition(handle).Y - DragStart.Y) < 6) return;
            DragTrigger = null;
            var data = new DataTransfer();
            data.Add(DataTransferItem.Create(DragFormat, this));
            await DragDrop.DoDragDropAsync(trigger, data, DragDropEffects.Move);
        };
        var dockButton = new Button { Content = "Move to editor tabs", Margin = new Thickness(4) };
        dockButton.Click += (_, _) => DockIntoTabs();
        var header = new DockPanel();
        DockPanel.SetDock(dockButton, Avalonia.Controls.Dock.Right);
        header.Children.Add(dockButton);
        header.Children.Add(handle);
        var content = new DockPanel();
        DockPanel.SetDock(header, Avalonia.Controls.Dock.Top);
        content.Children.Add(header);
        content.Children.Add(new ContentControl { Content = document });
        Content = content;
        Closing += async (_, args) =>
        {
            if (CloseConfirmed || IsDocked || !Document.IsDirty) return;
            args.Cancel = true;
            if (CheckingClose) return;
            CheckingClose = true;
            try
            {
                if (await Dialogs.ConfirmCloseAsync([Document])) CloseAfterConfirmation();
            }
            finally
            {
                CheckingClose = false;
            }
        };
    }

    internal void DockIntoTabs()
    {
        if (IsDocked) return;
        WorkspaceView.SaveAllLayouts();
        Content = null;
        IsDocked = true;
        Close();
        Dock(Document);
    }

    internal void CloseAfterConfirmation()
    {
        CloseConfirmed = true;
        Close();
    }
}

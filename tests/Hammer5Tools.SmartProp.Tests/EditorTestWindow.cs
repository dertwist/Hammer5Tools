using Avalonia.Controls;
using Hammer5Tools.App.Features.SmartProps;

namespace Hammer5Tools.SmartProp.Tests;

public sealed class MainWindow : Window
{
    public SmartPropEditorView Editor { get; }
    public MainWindow(bool loadDefaultResource = true)
    {
        Width = 1740;
        Height = 984;
        MinWidth = 1200;
        MinHeight = 700;
        Editor = new(loadDefaultResource);
        Content = Editor;
        Title = $"{Editor.DocumentTitle} — SmartProp Editor / Hammer 5 Tools";
        Editor.DocumentStateChanged += (_, _) => Title = $"{(Editor.HasUnsavedChanges ? "* " : "")}{Editor.DocumentTitle} — SmartProp Editor / Hammer 5 Tools";
        Closing += async (_, args) =>
        {
            if (closingApproved)
            {
                return;
            }
            args.Cancel = true;
            if (await Editor.ConfirmCloseAsync())
            {
                closingApproved = true;
                Editor.Dispose();
                Close();
            }
        };
    }
    private bool closingApproved;
    public string DocumentJson => Editor.DocumentJson;
    public bool IsEvaluating => Editor.IsEvaluating;
    public Task InitialLoadTask => Editor.InitialLoadTask;
    internal Task PreviewUpdateTask => Editor.PreviewUpdateTask;
    public Task Evaluate() => Editor.Evaluate();
    internal Task HierarchyAction(string action, string? className = null) => Editor.HierarchyAction(action, className);
    public T? FindControl<T>(string name) where T : Control => Editor.FindControl<T>(name);
}

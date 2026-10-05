namespace Hammer5Tools.App.Controls;

using System.Collections.ObjectModel;
using Avalonia;
using Avalonia.Controls;
using Avalonia.VisualTree;
using Dock.Avalonia.Controls;
using Dock.Model.Controls;
using Dock.Model.Core;
using Dock.Model.Mvvm;
using Dock.Model.Mvvm.Controls;
using Dock.Serializer.SystemTextJson;
using Hammer5Tools.Core.Settings;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

/// <summary>
/// Keeps docking models and layout persistence out of feature views and view models.
/// </summary>
public class WorkspaceView : UserControl
{
    private static readonly List<WeakReference<WorkspaceView>> Workspaces = [];
    private readonly DockSerializer Serializer = new(typeof(ObservableCollection<>));
    private readonly Factory Factory = new();
    private RootDock? Layout;
    private DockControl? DockControl;

    public ISettingsService? SettingsService { get; set; }

    private ISettingsService? Settings => SettingsService ?? Program.Services?.GetService<ISettingsService>();

    public string LayoutKey { get; set; } = string.Empty;

    public Control? CenterContent { get; set; }

    public Control? LeftContent { get; set; }

    public Control? RightContent { get; set; }

    public Control? RightBottomContent { get; set; }

    public string LeftTitle { get; set; } = "Explorer";

    public string RightTitle { get; set; } = "Properties";

    public string RightBottomTitle { get; set; } = "Description";

    public WorkspaceView()
    {
        DataContextChanged += (_, _) => UpdateContexts();
    }

    protected override void OnAttachedToVisualTree(VisualTreeAttachmentEventArgs e)
    {
        base.OnAttachedToVisualTree(e);
        Workspaces.Add(new WeakReference<WorkspaceView>(this));
        if (Layout is null)
        {
            InitializeLayout();
        }
    }

    protected override void OnDetachedFromVisualTree(VisualTreeAttachmentEventArgs e)
    {
        SaveLayout();
        CloseFloatingWindows();
        Workspaces.RemoveAll(reference => !reference.TryGetTarget(out var workspace) || ReferenceEquals(workspace, this));
        base.OnDetachedFromVisualTree(e);
    }

    public static void SaveAllLayouts()
    {
        VisitWorkspaces(workspace => workspace.SaveLayout());
    }

    public static void CloseAllFloatingWindows()
    {
        VisitWorkspaces(workspace => workspace.CloseFloatingWindows());
    }

    public static void ResetAllLayouts()
    {
        var settings = Program.Services?.GetService<ISettingsService>();
        settings?.Update(value => value.WorkspaceLayouts.Clear());
        VisitWorkspaces(workspace => workspace.InitializeLayout(restore: false));
    }

    private static void VisitWorkspaces(Action<WorkspaceView> action)
    {
        foreach (var reference in Workspaces.ToArray())
        {
            if (reference.TryGetTarget(out var workspace))
            {
                action(workspace);
            }
            else
            {
                Workspaces.Remove(reference);
            }
        }
    }

    private void InitializeLayout(bool restore = true)
    {
        CloseFloatingWindows();
        Factory.ContextLocator = new Dictionary<string, Func<object?>>
        {
            ["Center"] = () => CenterContent,
            ["Left"] = () => LeftContent,
            ["Right"] = () => RightContent,
            ["RightBottom"] = () => RightBottomContent,
        };
        Factory.HostWindowLocator = new Dictionary<string, Func<IHostWindow?>>
        {
            [nameof(IDockWindow)] = () => new HostWindow(),
        };

        var settings = Settings;
        Layout = null;
        if (restore && settings?.Settings.WorkspaceLayouts.TryGetValue(LayoutKey, out var saved) == true)
        {
            try
            {
                Layout = Serializer.Deserialize<RootDock>(saved);
            }
            catch (Exception ex)
            {
                Program.Services?.GetService<ILogger<WorkspaceView>>()?.LogWarning(ex, "Could not restore workspace {Key}", LayoutKey);
            }
        }

        Layout ??= CreateDefaultLayout();
        UpdateContexts();
        Factory.InitLayout(Layout);
        DockControl ??= new DockControl();
        DockControl.Layout = Layout;
        Content = DockControl;
    }

    private RootDock CreateDefaultLayout()
    {
        var center = new Document { Id = "Center", Title = "Workspace", CanClose = false, CanFloat = false };
        var documents = new DocumentDock
        {
            Id = "Documents",
            ActiveDockable = center,
            VisibleDockables = Factory.CreateList<IDockable>(center),
            IsCollapsable = false,
            CanCreateDocument = false,
        };
        var main = new ProportionalDock
        {
            Orientation = Orientation.Horizontal,
            VisibleDockables = Factory.CreateList<IDockable>(),
        };
        if (LeftContent is not null)
        {
            main.VisibleDockables.Add(CreateToolDock("Left", LeftTitle, Alignment.Left, 0.25));
            main.VisibleDockables.Add(new ProportionalDockSplitter());
        }

        main.VisibleDockables.Add(documents);
        if (RightContent is not null)
        {
            main.VisibleDockables.Add(new ProportionalDockSplitter());
            var right = CreateToolDock("Right", RightTitle, Alignment.Right, 0.25);
            if (RightBottomContent is null)
            {
                main.VisibleDockables.Add(right);
            }
            else
            {
                main.VisibleDockables.Add(new ProportionalDock
                {
                    Proportion = 0.25,
                    Orientation = Orientation.Vertical,
                    VisibleDockables = Factory.CreateList<IDockable>(right, new ProportionalDockSplitter(),
                        CreateToolDock("RightBottom", RightBottomTitle, Alignment.Right, double.NaN)),
                });
            }
        }

        return new RootDock
        {
            Id = "Root",
            IsCollapsable = false,
            ActiveDockable = main,
            DefaultDockable = main,
            VisibleDockables = Factory.CreateList<IDockable>(main),
        };
    }

    private ToolDock CreateToolDock(string id, string title, Alignment alignment, double proportion)
    {
        var tool = new Tool { Id = id, Title = title, CanClose = true, CanPin = true, CanFloat = true };
        return new ToolDock
        {
            Alignment = alignment,
            Proportion = proportion,
            ActiveDockable = tool,
            VisibleDockables = Factory.CreateList<IDockable>(tool),
        };
    }

    private void UpdateContexts()
    {
        foreach (var control in new[] { CenterContent, LeftContent, RightContent, RightBottomContent })
        {
            if (control is not null)
            {
                if (!control.IsSet(DataContextProperty))
                {
                    control.Bind(DataContextProperty, new Avalonia.Data.Binding(nameof(DataContext)) { Source = this });
                }
            }
        }
    }

    private void SaveLayout()
    {
        if (Layout is null || string.IsNullOrWhiteSpace(LayoutKey))
        {
            return;
        }

        var settings = Settings;
        if (settings is not null)
        {
            var json = Serializer.Serialize(Layout);
            settings.Update(value => value.WorkspaceLayouts[LayoutKey] = json);
        }
    }

    private void CloseFloatingWindows()
    {
        if (Layout?.Windows is { } windows)
        {
            foreach (var window in windows.ToArray())
            {
                window.Host?.Exit();
            }
        }
    }
}

using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Platform.Storage;
using Avalonia.Threading;
using Avalonia.VisualTree;
using Vector = Avalonia.Vector;

namespace Hammer5Tools.App.Features.SmartProps;

public sealed class SmartPropHierarchy : TreeView
{
    protected override Type StyleKeyOverride => typeof(TreeView);
    private sealed record HierarchyDrag(SmartPropHierarchy Source, int Version, string[][] Paths);
    private static readonly DataFormat<HierarchyDrag> DragFormat = DataFormat.CreateInProcessFormat<HierarchyDrag>("h5t-hierarchy");
    private PointerPressedEventArgs? press;
    private Point pressPoint;
    private HierarchyRow? pressedRow;
    private bool deferredClick;
    private TreeViewItem? dropItem;
    private string dropPosition = "inside";
    private readonly DispatcherTimer hoverTimer;
    public int Version { get; set; }
    public event Action<string>? ActionRequested;
    public event Action<HierarchyRow, string>? RenameRequested;
    public event Action<string[][], HierarchyRow?, string, bool>? MoveRequested;
    public event Action<string[], HierarchyRow?>? FilesDropped;
    public string[][] SelectedPaths => SelectedItems?.OfType<HierarchyRow>().Select(row => row.Path).ToArray() ?? [];
    internal DataTransfer CreateDragData()
    {
        var data = new DataTransfer();
        data.Add(DataTransferItem.Create(DragFormat, new HierarchyDrag(this, Version, SelectedPaths)));
        return data;
    }

    public SmartPropHierarchy()
    {
        Classes.Add("smartHierarchy");
        SelectionMode = SelectionMode.Multiple;
        DragDrop.SetAllowDrop(this, true);
        AddHandler(PointerPressedEvent, Pressed, RoutingStrategies.Tunnel, true);
        AddHandler(PointerMovedEvent, Moved, RoutingStrategies.Tunnel, true);
        AddHandler(PointerReleasedEvent, Released, RoutingStrategies.Tunnel, true);
        DragDrop.AddDragOverHandler(this, DragOver);
        DragDrop.AddDropHandler(this, Drop);
        DragDrop.AddDragLeaveHandler(this, (_, _) => ClearDrop());
        hoverTimer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(600) };
        hoverTimer.Tick += (_, _) =>
        {
            if (dropPosition == "inside" && dropItem is not null)
            {
                dropItem.IsExpanded = true;
            }
            hoverTimer.Stop();
        };
        KeyDown += (_, args) =>
        {
            if (args.Source is TextBox)
            {
                return;
            }
            var control = args.KeyModifiers.HasFlag(KeyModifiers.Control);
            var action = args.Key switch
            {
                Key.Delete => "remove",
                Key.F2 => "rename",
                Key.D when control => "duplicate",
                Key.G when control => "group",
                Key.C when control => "copy",
                Key.X when control => "cut",
                Key.V when control => args.KeyModifiers.HasFlag(KeyModifiers.Shift) ? "paste-replace" : "paste",
                Key.A when control => "select-all",
                Key.F when control => "add",
                Key.H when control => "isolate",
                Key.Up when args.KeyModifiers.HasFlag(KeyModifiers.Alt) => "up",
                Key.Down when args.KeyModifiers.HasFlag(KeyModifiers.Alt) => "down",
                _ => null
            };
            if (action is null)
            {
                return;
            }
            args.Handled = true;
            if (action == "select-all")
            {
                foreach (var row in VisibleRows(ItemsSource?.OfType<HierarchyRow>() ?? []))
                {
                    if (!SelectedItems!.Contains(row))
                    {
                        SelectedItems.Add(row);
                    }
                }
            }
            else if (action == "rename")
            {
                BeginRename();
            }
            else
            {
                ActionRequested?.Invoke(action);
            }
        };
    }

    internal static IEnumerable<HierarchyRow> VisibleRows(IEnumerable<HierarchyRow> roots)
    {
        foreach (var row in roots)
        {
            yield return row;
            if (row.Expanded)
            {
                foreach (var child in VisibleRows(row.Children))
                {
                    yield return child;
                }
            }
        }
    }

    public void ExpandAll(bool expand)
    {
        foreach (var row in AllRows(ItemsSource?.OfType<HierarchyRow>() ?? []))
        {
            row.Expanded = expand;
        }
        foreach (var item in this.GetVisualDescendants().OfType<TreeViewItem>())
        {
            item.IsExpanded = expand;
        }
    }

    private static IEnumerable<HierarchyRow> AllRows(IEnumerable<HierarchyRow> rows)
    {
        foreach (var row in rows)
        {
            yield return row;
            foreach (var child in AllRows(row.Children))
            {
                yield return child;
            }
        }
    }

    public void BeginRename()
    {
        var row = SelectedItems?.OfType<HierarchyRow>().LastOrDefault();
        this.GetVisualDescendants().OfType<HierarchyLabel>().FirstOrDefault(cell => ReferenceEquals(cell.DataContext, row))?.BeginEdit();
    }

    internal void Rename(HierarchyRow row, string label) => RenameRequested?.Invoke(row, label);

    private static TreeViewItem? ItemAt(object? source) => source is Visual visual ? visual.GetSelfAndVisualAncestors().OfType<TreeViewItem>().FirstOrDefault() : null;

    private void Pressed(object? sender, PointerPressedEventArgs args)
    {
        if (args.Source is Visual source && source.GetSelfAndVisualAncestors().Any(item => item is TextBox or global::Avalonia.Controls.Primitives.ToggleButton or global::Avalonia.Controls.Primitives.ScrollBar))
        {
            return;
        }
        var item = ItemAt(args.Source);
        var row = item?.DataContext as HierarchyRow;
        var properties = args.GetCurrentPoint(this).Properties;
        if (properties.IsRightButtonPressed)
        {
            if (row is not null && !SelectedItems!.Contains(row))
            {
                SelectedItem = row;
            }
            return;
        }
        if (!properties.IsLeftButtonPressed)
        {
            return;
        }
        if (row is null)
        {
            SelectedItems?.Clear();
            return;
        }
        press = args;
        pressPoint = args.GetPosition(this);
        pressedRow = row;
        deferredClick = args.KeyModifiers == KeyModifiers.None && SelectedItems!.Count > 1 && SelectedItems.Contains(row);
        if (deferredClick)
        {
            args.Handled = true;
        }
    }

    private async void Moved(object? sender, PointerEventArgs args)
    {
        var delta = args.GetPosition(this) - pressPoint;
        if (press is null || !args.GetCurrentPoint(this).Properties.IsLeftButtonPressed || Math.Sqrt(delta.X * delta.X + delta.Y * delta.Y) < 5)
        {
            return;
        }
        var trigger = press;
        press = null;
        deferredClick = false;
        if (pressedRow is not null && !SelectedItems!.Contains(pressedRow))
        {
            SelectedItem = pressedRow;
        }
        var data = CreateDragData();
        try
        {
            await DragDrop.DoDragDropAsync(trigger, data, DragDropEffects.Move | DragDropEffects.Copy);
        }
        finally
        {
            ClearDrop();
        }
    }

    private void Released(object? sender, PointerReleasedEventArgs args)
    {
        if (deferredClick && pressedRow is not null)
        {
            SelectedItem = pressedRow;
        }
        press = null;
        deferredClick = false;
    }

    private static (TreeViewItem? Item, string Position) Target(DragEventArgs args)
    {
        var item = ItemAt(args.Source);
        if (item is null)
        {
            return (null, "inside");
        }
        var header = item.GetVisualDescendants().OfType<HierarchyLabel>().FirstOrDefault();
        var y = header is null ? args.GetPosition(item).Y : args.GetPosition(header).Y;
        var height = header?.Bounds.Height ?? 22;
        return (item, y < height * 0.25 ? "before" : y > height * 0.75 ? "after" : "inside");
    }

    private void DragOver(object? sender, DragEventArgs args)
    {
        var drag = args.DataTransfer.TryGetValue(DragFormat);
        var (item, position) = Target(args);
        var row = item?.DataContext as HierarchyRow;
        var valid = drag is not null && drag.Source == this && drag.Version == Version
            && !drag.Paths.Any(path => row is not null && (row.Path.SequenceEqual(path) || position == "inside" && row.Path.Take(path.Length).SequenceEqual(path)));
        if (position == "inside" && row?.Subtitle is "Model" or "SmartProp")
        {
            valid = false;
        }
        var files = args.DataTransfer.Contains(DataFormat.File);
        args.DragEffects = valid ? args.KeyModifiers.HasFlag(KeyModifiers.Control) ? DragDropEffects.Copy : DragDropEffects.Move
            : files ? DragDropEffects.Copy : DragDropEffects.None;
        if (dropItem != item || dropPosition != position)
        {
            ClearDrop();
            dropItem = item;
            dropPosition = position;
            if (valid || files)
            {
                item?.Classes.Add("drop" + position);
                hoverTimer.Start();
            }
        }
        var scroll = this.GetVisualDescendants().OfType<ScrollViewer>().FirstOrDefault();
        var point = args.GetPosition(this);
        if (scroll is not null && (point.Y < 24 || point.Y > Bounds.Height - 24))
        {
            scroll.Offset = new Vector(scroll.Offset.X, Math.Max(0, scroll.Offset.Y + (point.Y < 24 ? -12 : 12)));
        }
        args.Handled = true;
    }

    private void Drop(object? sender, DragEventArgs args)
    {
        DragOver(sender, args);
        var row = dropItem?.DataContext as HierarchyRow;
        var position = dropPosition;
        ClearDrop();
        if (args.DataTransfer.TryGetValue(DragFormat) is { } drag && args.DragEffects != DragDropEffects.None)
        {
            MoveRequested?.Invoke(drag.Paths, row, position, args.DragEffects == DragDropEffects.Copy);
        }
        else if (args.DataTransfer.TryGetFiles() is { } files)
        {
            FilesDropped?.Invoke(files.Select(file => file.TryGetLocalPath()).OfType<string>().ToArray(), row);
        }
        args.Handled = true;
    }

    private void ClearDrop()
    {
        hoverTimer.Stop();
        dropItem?.Classes.Remove("dropinside");
        dropItem?.Classes.Remove("dropbefore");
        dropItem?.Classes.Remove("dropafter");
        dropItem = null;
    }
}

public sealed class HierarchyBranches : Control
{
    public override void Render(global::Avalonia.Media.DrawingContext context)
    {
        base.Render(context);
        if (DataContext is not HierarchyRow row || this.FindAncestorOfType<SmartPropHierarchy>()?.ItemsSource is not IEnumerable<HierarchyRow> roots)
        {
            return;
        }
        var depth = row.Path.Length / 2 - 1;
        var siblings = roots.ToList();
        var pen = new global::Avalonia.Media.Pen((global::Avalonia.Media.IBrush)Application.Current!.Resources["H5TBorderBrush"]!, 1);
        var middle = Bounds.Height / 2;
        for (var level = 0; level <= depth; level++)
        {
            var prefix = row.Path.Take((level + 1) * 2).ToArray();
            var index = siblings.FindIndex(item => item.Path.SequenceEqual(prefix));
            if (index < 0)
            {
                break;
            }
            if (level > 0)
            {
                var x = -12 - (depth - level) * 16;
                var hasNext = index < siblings.Count - 1;
                if (level == depth || hasNext)
                {
                    context.DrawLine(pen, new Point(x, 0), new Point(x, hasNext ? Bounds.Height : middle));
                }
                if (level == depth)
                {
                    context.DrawLine(pen, new Point(x, middle), new Point(0, middle));
                }
            }
            siblings = siblings[index].Children;
        }
    }

}

public sealed class HierarchyLabel : Grid
{
    private static readonly Dictionary<string, global::Avalonia.Media.Imaging.Bitmap> Icons = [];
    private readonly TextBlock label = new() { VerticalAlignment = global::Avalonia.Layout.VerticalAlignment.Center, TextTrimming = global::Avalonia.Media.TextTrimming.CharacterEllipsis };
    private readonly TextBox edit = new() { IsVisible = false, MinHeight = 20, Padding = new Thickness(2, 0) };
    private bool editing;

    public HierarchyLabel()
    {
        ColumnDefinitions = new ColumnDefinitions("16,*");
        var branches = new HierarchyBranches { IsHitTestVisible = false };
        Grid.SetColumnSpan(branches, 2);
        Children.Add(branches);
        var icon = new Image { Width = 14, Height = 14, Margin = new Thickness(0, 0, 2, 0) };
        Children.Add(icon);
        Grid.SetColumn(label, 1);
        Grid.SetColumn(edit, 1);
        Children.Add(label);
        Children.Add(edit);
        DataContextChanged += (_, _) =>
        {
            if (DataContext is not HierarchyRow row)
            {
                return;
            }
            label.Text = row.Label;
            Opacity = row.Enabled ? 1 : 0.45;
            ToolTip.SetTip(this, row.Note ?? $"{row.Label} · {row.Subtitle} · ID {row.ElementId}");
            var name = row.Subtitle switch { "Group" => "group", "Model" => "model", "SmartProp" => "smartprop", _ => "generic" };
            if (!Icons.TryGetValue(name, out var bitmap))
            {
                using var stream = typeof(HierarchyLabel).Assembly.GetManifestResourceStream("Hierarchy." + name)!;
                bitmap = new global::Avalonia.Media.Imaging.Bitmap(stream);
                Icons[name] = bitmap;
            }
            icon.Source = bitmap;
        };
        DoubleTapped += (_, args) => { BeginEdit(); args.Handled = true; };
        edit.KeyDown += (_, args) =>
        {
            if (args.Key is Key.Enter or Key.Escape)
            {
                Finish(args.Key == Key.Enter);
                args.Handled = true;
            }
        };
        edit.LostFocus += (_, _) => Finish(true);
    }

    public void BeginEdit()
    {
        edit.Text = label.Text;
        editing = true;
        label.IsVisible = false;
        edit.IsVisible = true;
        edit.Focus();
        edit.SelectAll();
    }

    private void Finish(bool commit)
    {
        if (!editing)
        {
            return;
        }
        editing = false;
        edit.IsVisible = false;
        label.IsVisible = true;
        if (commit && DataContext is HierarchyRow row && edit.Text != row.Label)
        {
            this.FindAncestorOfType<SmartPropHierarchy>()?.Rename(row, edit.Text ?? "");
        }
    }
}

namespace Hammer5Tools.App.Controls;

using System.Collections.Specialized;
using Avalonia;
using Avalonia.Controls;
using Hammer5Tools.App.ViewModels;

/// <summary>Keeps loaded editor trees attached while inactive, preserving Dock layouts and editor state.</summary>
public sealed class EditorHost : Grid
{
    public static readonly StyledProperty<DocumentViewModel?> ActiveDocumentProperty =
        AvaloniaProperty.Register<EditorHost, DocumentViewModel?>(nameof(ActiveDocument));

    public static readonly StyledProperty<IEnumerable<DocumentViewModel>?> DocumentsProperty =
        AvaloniaProperty.Register<EditorHost, IEnumerable<DocumentViewModel>?>(nameof(Documents));

    public DocumentViewModel? ActiveDocument
    {
        get => GetValue(ActiveDocumentProperty);
        set => SetValue(ActiveDocumentProperty, value);
    }

    public IEnumerable<DocumentViewModel>? Documents
    {
        get => GetValue(DocumentsProperty);
        set => SetValue(DocumentsProperty, value);
    }

    protected override void OnPropertyChanged(AvaloniaPropertyChangedEventArgs change)
    {
        base.OnPropertyChanged(change);
        if (change.Property == DocumentsProperty)
        {
            if (change.OldValue is INotifyCollectionChanged oldDocuments) oldDocuments.CollectionChanged -= OnDocumentsChanged;
            if (change.NewValue is INotifyCollectionChanged newDocuments) newDocuments.CollectionChanged += OnDocumentsChanged;
        }
        if (change.Property == DocumentsProperty || change.Property == ActiveDocumentProperty) UpdateViews();
    }

    private void OnDocumentsChanged(object? sender, NotifyCollectionChangedEventArgs e) => UpdateViews();

    private void UpdateViews()
    {
        var documents = Documents?.ToHashSet() ?? [];
        foreach (var child in Children.ToArray())
        {
            if (child.DataContext is DocumentViewModel document && !documents.Contains(document)) Children.Remove(child);
            else child.IsVisible = false;
        }
        WorkspaceView.UpdateEditorFloatingWindows(this);
        if (ActiveDocument is not { } active || !documents.Contains(active)) return;
        var view = active.EditorView;
        if (!Children.Contains(view)) Children.Add(view);
        view.IsVisible = true;
    }
}

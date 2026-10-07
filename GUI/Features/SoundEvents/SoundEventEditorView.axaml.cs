namespace Hammer5Tools.App.Features.SoundEvents;

using System.Collections.Specialized;
using System.ComponentModel;
using System.Globalization;
using System.Text.Json;
using System.Text.Encodings.Web;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Data;
using Avalonia.Input;
using Avalonia.Input.Platform;
using Avalonia.Markup.Xaml.MarkupExtensions;
using Avalonia.Interactivity;
using Avalonia.Layout;
using Hammer5Tools.App.Controls;
using Hammer5Tools.Core.SoundEvents;

public partial class SoundEventEditorView : UserControl
{
    private static readonly JsonSerializerOptions ValueJsonOptions = new() { Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping };
    private SoundEventEditorViewModel? Model;
    private SoundEvent? Event;
    private readonly List<(Control Control, SoundPropertySpec Spec)> DependentEditors = [];

    public SoundEventEditorView()
    {
        InitializeComponent();
        DataContextChanged += (_, _) => AttachModel();
        AddonAudioList.DoubleTapped += (_, _) => AddSound((AddonAudioList.SelectedItem as SoundAudioRow)?.Path);
        InternalAudioList.DoubleTapped += (_, _) => AddSound((InternalAudioList.SelectedItem as SoundAudioFolder)?.SoundPath);
        AddonEventList.ContextMenu = new ContextMenu { ItemsSource = new[]
        {
            MenuAction("New", () => { Model?.AddEventCommand.Execute(null); return Task.CompletedTask; }),
            MenuAction("Rename", () => { Model?.RenameEventCommand.Execute(null); return Task.CompletedTask; }),
            MenuAction("Duplicate", () => { Model?.DuplicateSelectedEvent(); return Task.CompletedTask; }),
            MenuAction("Copy", CopyEventAsync),
            MenuAction("Paste", PasteEventAsync),
            MenuAction("Save as Template...", () => { Model?.SaveTemplateCommand.Execute(null); return Task.CompletedTask; }),
            MenuAction("Remove", () => { Model?.DeleteEventCommand.Execute(null); return Task.CompletedTask; }),
        } };
        AddonEventList.KeyDown += async (_, e) =>
        {
            if (e.Key == Key.F2) Model?.RenameEventCommand.Execute(null);
            else if (e.Key == Key.Delete) Model?.DeleteEventCommand.Execute(null);
            else if (e.KeyModifiers == KeyModifiers.Control && e.Key == Key.D) Model?.DuplicateSelectedEvent();
            else if (e.KeyModifiers == KeyModifiers.Control && e.Key == Key.C) await CopyEventAsync();
            else if (e.KeyModifiers == KeyModifiers.Control && e.Key == Key.V) await PasteEventAsync();
            else return;
            e.Handled = true;
        };
        PropertyEditors.KeyDown += async (_, e) =>
        {
            if (e.KeyModifiers != KeyModifiers.Control || e.Key != Key.V || e.Source is TextBox || Model is null) return;
            if (TopLevel.GetTopLevel(this)?.Clipboard is { } clipboard && await clipboard.TryGetTextAsync() is { } text)
                await Model.PastePropertiesAsync(text);
            e.Handled = true;
        };
        BuildBrowser();
    }

    private void AttachModel()
    {
        if (Model is not null)
        {
            Model.PropertyChanged -= ModelChanged;
        }
        DetachEvent();
        Model = DataContext as SoundEventEditorViewModel;
        if (Model is not null)
        {
            Model.PropertyChanged += ModelChanged;
        }
        AttachEvent();
        RefreshInternalSounds();
        RefreshAddonSounds();
    }

    private void ModelChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (e.PropertyName == nameof(SoundEventEditorViewModel.SelectedEvent)) AttachEvent();
        if (e.PropertyName == nameof(SoundEventEditorViewModel.PropertiesTitle)) RefreshAddonSounds();
        if (e.PropertyName is nameof(SoundEventEditorViewModel.AudioFilter) or nameof(SoundEventEditorViewModel.VpkSounds)) RefreshInternalSounds();
    }

    private void DetachEvent()
    {
        if (Event is null) return;
        Event.PropertyChanged -= EventChanged;
        Event.Properties.CollectionChanged -= PropertiesChanged;
        foreach (var property in Event.Properties) property.PropertyChanged -= SoundPropertyChanged;
    }

    private void AttachEvent()
    {
        DetachEvent();
        Event = Model?.SelectedEvent;
        if (Event is not null)
        {
            Event.PropertyChanged += EventChanged;
            Event.Properties.CollectionChanged += PropertiesChanged;
            foreach (var property in Event.Properties) property.PropertyChanged += SoundPropertyChanged;
        }
        BuildEditors();
        BuildBrowser();
    }

    private void EventChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (e.PropertyName == nameof(SoundEvent.HasExplicitType)) { BuildEditors(); BuildBrowser(); }
    }

    private void PropertiesChanged(object? sender, NotifyCollectionChangedEventArgs e)
    {
        if (e.OldItems is not null)
            foreach (SoundProperty property in e.OldItems) property.PropertyChanged -= SoundPropertyChanged;
        if (e.NewItems is not null)
            foreach (SoundProperty property in e.NewItems) property.PropertyChanged += SoundPropertyChanged;
        BuildEditors();
        BuildBrowser();
    }

    private void SoundPropertyChanged(object? sender, PropertyChangedEventArgs e) => UpdateDependencies();

    private void BuildBrowser()
    {
        PropertyBrowser.Children.Clear();
        var schema = SoundEventPresentation.Legacy;
        foreach (var group in schema.Groups)
        {
            var entries = new StackPanel();
            foreach (var spec in schema.Properties.Where(item => item.Group == group.Key && Matches(item, BrowserFilter.Text)))
            {
                var button = new Button { Classes = { "sound-browser-property" }, Content = spec.Title, HorizontalAlignment = HorizontalAlignment.Stretch, HorizontalContentAlignment = HorizontalAlignment.Left, Padding = new Thickness(20, 1, 4, 1) };
                button.IsEnabled = Model?.SelectedEvent is { } selected && !Model.IsInternalEvent
                    && (spec.Key == "comment" || (spec.Key == "type" ? !selected.HasExplicitType : selected.GetValue(spec.Key) is null));
                ToolTip.SetTip(button, spec.Tooltip);
                button.DoubleTapped += (_, _) => Model?.AddNamedProperty(spec.Key);
                entries.Children.Add(button);
            }
            if (entries.Children.Count > 0)
                PropertyBrowser.Children.Add(new Expander { Classes = { "sound-section" }, Header = group.Title, Content = entries, IsExpanded = true, HorizontalAlignment = HorizontalAlignment.Stretch });
        }
    }

    private static bool Matches(SoundPropertySpec spec, string? filter) => string.IsNullOrWhiteSpace(filter)
        || spec.Title.Contains(filter, StringComparison.OrdinalIgnoreCase) || spec.Key.Contains(filter, StringComparison.OrdinalIgnoreCase);

    private void BuildEditors()
    {
        PropertyEditors.Children.Clear();
        DependentEditors.Clear();
        PropertyEditors.IsEnabled = Model?.IsInternalEvent != true;
        if (Event is null) return;
        var schema = SoundEventPresentation.Legacy;
        foreach (var group in schema.Groups)
        {
            var rows = new StackPanel();
            if (group.Key == "general" && Event.HasExplicitType && Matches(schema.GetSpec("type"), PropertyFilter.Text))
            {
                var type = new ComboBox { ItemsSource = new[] { "csgo_mega", "csgo_music", Event.Type }.Distinct().ToArray(), HorizontalAlignment = HorizontalAlignment.Stretch };
                type.Bind(ComboBox.SelectedItemProperty, new Binding(nameof(SoundEvent.Type)) { Source = Event, Mode = BindingMode.TwoWay });
                rows.Children.Add(Row("Type", type));
            }
            foreach (var property in Event.Properties.Where(item => schema.GetSpec(item.Key).Group == group.Key)
                .OrderBy(item => schema.Properties.FindIndex(spec => spec.Key == item.Key)))
            {
                var spec = schema.GetSpec(property.Key);
                if (!Matches(spec, PropertyFilter.Text)) continue;
                var editor = CreateEditor(property, spec);
                DependentEditors.Add((editor, spec));
                var row = Row(spec.Title, editor, spec.Tooltip, spec.Kind);
                row.Tag = property.Key;
                row.Focusable = true;
                row.KeyDown += async (_, e) =>
                {
                    if (e.Source is TextBox || e.Source is NumericUpDown || Model?.IsInternalEvent == true) return;
                    if (e.Key == Key.Delete) Model?.RemoveProperty(property);
                    else if (e.Key == Key.C && e.KeyModifiers == KeyModifiers.Control && TopLevel.GetTopLevel(this)?.Clipboard is { } clipboard)
                        await clipboard.SetTextAsync($"{property.Key} = {property.Value}");
                    else return;
                    e.Handled = true;
                };
                row.ContextMenu = new ContextMenu
                {
                    ItemsSource = new[]
                    {
                        MenuAction("Copy property", async () =>
                        {
                            if (TopLevel.GetTopLevel(this)?.Clipboard is { } clipboard)
                                await clipboard.SetTextAsync($"{property.Key} = {property.Value}");
                        }),
                        MenuAction("Delete property", () => { Model?.RemoveProperty(property); return Task.CompletedTask; }),
                    },
                };
                rows.Children.Add(row);
            }
            if (rows.Children.Count > 0)
                PropertyEditors.Children.Add(new Expander { Classes = { "sound-section" }, Header = group.Title, Content = rows, IsExpanded = group.Key is not ("advanced" or "custom"), HorizontalAlignment = HorizontalAlignment.Stretch });
        }
        UpdateDependencies();
    }

    private static MenuItem MenuAction(string title, Func<Task> action)
    {
        var menu = new MenuItem { Header = title };
        menu.Click += async (_, _) => await action();
        return menu;
    }

    private static Grid Row(string title, Control editor, string? tooltip = null, string? kind = null)
    {
        var row = new Grid { ColumnDefinitions = new ColumnDefinitions("3,150,*,34"), Margin = new Thickness(8, 4, 8, 4) };
        var rail = new Border { Width = 3, Margin = new Thickness(0, 0, 4, 0) };
        rail.Bind(Border.BackgroundProperty, new DynamicResourceExtension("H5TBorderBrush"));
        row.Children.Add(rail);
        var label = new TextBlock { Text = title, MinWidth = 120, MaxWidth = 170, TextWrapping = Avalonia.Media.TextWrapping.Wrap, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(12, 0, 8, 0) };
        var color = kind switch
        {
            "float" => "Float", "bool" or "string_bool" => "Bool", "comment" => "Comment", "vector3" => "Vector",
            "files" or "soundevent" => "List", "combobox" => "Combo", "base" => "Base", _ => "Custom",
        };
        label.Bind(TextBlock.ForegroundProperty, new DynamicResourceExtension($"H5TSoundProperty{color}Brush"));
        Grid.SetColumn(label, 1);
        row.Children.Add(label);
        Grid.SetColumn(editor, 2);
        row.Children.Add(editor);
        if (!string.IsNullOrEmpty(tooltip))
        {
            var info = IconButton("tools/common/icon_info_sm.png", tooltip);
            ToolTip.SetTip(info, tooltip);
            info.Click += (_, _) => ToolTip.SetIsOpen(info, !ToolTip.GetIsOpen(info));
            Grid.SetColumn(info, 3);
            row.Children.Add(info);
        }
        return row;
    }

    private Control CreateEditor(SoundProperty property, SoundPropertySpec spec)
    {
        var value = property.Value.Trim();
        if ((spec.Kind is "bool" or "string_bool") && (value.Trim('"') is "true" or "false"))
        {
            var toggle = new CheckBox { IsChecked = value.Trim('"') == "true", Content = value.Trim('"') == "true" ? "True" : "False" };
            toggle.IsCheckedChanged += (_, _) =>
            {
                var boolean = toggle.IsChecked == true ? "true" : "false";
                toggle.Content = toggle.IsChecked == true ? "True" : "False";
                property.Value = spec.Kind == "string_bool" ? JsonSerializer.Serialize(boolean, ValueJsonOptions) : boolean;
            };
            return toggle;
        }
        if (spec.Kind == "float" && decimal.TryParse(value, NumberStyles.Float, CultureInfo.InvariantCulture, out var number))
        {
            var panel = new Grid { ColumnDefinitions = new ColumnDefinitions("110,*") };
            var spin = new NumericUpDown { Classes = { "compact" }, Value = number, Increment = 0.01m, FormatString = "0.######" };
            spin.ValueChanged += (_, _) => { if (spin.Value is { } current) property.Value = current.ToString(CultureInfo.InvariantCulture); };
            panel.Children.Add(spin);
            if (spec.Options.TryGetValue("slider_range", out var range))
            {
                var slider = new Slider { Classes = { "h5-slider" }, Minimum = range[0].GetDouble(), Maximum = range[1].GetDouble(), Value = (double)number, Margin = new Thickness(6, 0), VerticalAlignment = VerticalAlignment.Center };
                var updating = false;
                slider.PropertyChanged += (_, args) =>
                {
                    if (args.Property != Slider.ValueProperty || updating) return;
                    updating = true;
                    spin.Value = (decimal)slider.Value;
                    updating = false;
                };
                spin.ValueChanged += (_, _) =>
                {
                    if (updating) return;
                    updating = true;
                    slider.Value = (double)(spin.Value ?? 0);
                    updating = false;
                };
                Grid.SetColumn(slider, 1);
                panel.Children.Add(slider);
            }
            return panel;
        }
        if (spec.Kind == "vector3" && TryArray(value, out var vector) && vector.Length == 3 && vector.All(item => item.ValueKind == JsonValueKind.Number))
        {
            var panel = new Grid { ColumnDefinitions = new ColumnDefinitions("*,*,*") };
            var values = vector.Select(item => item.GetDecimal()).ToArray();
            for (var i = 0; i < 3; i++)
            {
                var index = i;
                var spin = new NumericUpDown { Classes = { "compact" }, Value = values[i], Increment = 1, FormatString = "0.###", Margin = new Thickness(2, 0) };
                ToolTip.SetTip(spin, i switch { 0 => "X", 1 => "Y", _ => "Z" });
                spin.ValueChanged += (_, _) => { values[index] = spin.Value ?? 0; property.Value = JsonSerializer.Serialize(values, ValueJsonOptions); };
                Grid.SetColumn(spin, i);
                panel.Children.Add(spin);
            }
            return panel;
        }
        if (spec.Kind is "files" or "soundevent") return CreateListEditor(property, spec);
        if (spec.Kind == "combobox" && spec.Options.TryGetValue("objects", out var options))
        {
            var current = DecodeString(value);
            var combo = new ComboBox { ItemsSource = options.EnumerateArray().Select(item => item.GetString()!).Append(current).Distinct().ToArray(), SelectedItem = current, HorizontalAlignment = HorizontalAlignment.Stretch };
            combo.SelectionChanged += (_, _) =>
            {
                if (combo.SelectedItem is string text && text != DecodeString(property.Value)) property.Value = JsonSerializer.Serialize(text, ValueJsonOptions);
            };
            var panel = new Grid { ColumnDefinitions = new ColumnDefinitions("*,Auto") };
            panel.Children.Add(combo);
            var comboSearch = IconButton("search_24dp.svg", "Find value");
            comboSearch.Click += (_, _) => ShowPicker(comboSearch, options.EnumerateArray().Select(item => item.GetString()!), text => combo.SelectedItem = text);
            Grid.SetColumn(comboSearch, 1);
            panel.Children.Add(comboSearch);
            return panel;
        }
        if (spec.Kind == "curve" && TryArray(value, out var points) && points.All(point => point.ValueKind == JsonValueKind.Array && point.GetArrayLength() == 6 && point.EnumerateArray().All(item => item.ValueKind == JsonValueKind.Number && item.TryGetDecimal(out _))))
        {
            var panel = new StackPanel { Spacing = 4 };
            var values = points.Select(point => point.EnumerateArray().Select(item => item.GetDecimal()).ToArray()).ToList();
            var graph = new SoundCurveGraph(values, () => { property.Value = JsonSerializer.Serialize(values, ValueJsonOptions); BuildEditors(); });
            panel.Children.Add(graph);
            panel.Children.Add(new TextBlock { Text = "Input / Output / Left slope / Right slope / Left mode / Right mode" });
            for (var i = 0; i < values.Count; i++)
            {
                var pointIndex = i;
                var row = new Grid { ColumnDefinitions = new ColumnDefinitions("*,*,*,*,*,*,Auto") };
                for (var j = 0; j < 6; j++)
                {
                    var field = j;
                    var spin = new NumericUpDown { Classes = { "compact" }, Value = values[i][j], Increment = j < 4 ? 0.01m : 1, FormatString = "0.######", Margin = new Thickness(1) };
                    spin.ValueChanged += (_, _) => { values[pointIndex][field] = spin.Value ?? 0; property.Value = JsonSerializer.Serialize(values, ValueJsonOptions); graph.InvalidateVisual(); };
                    Grid.SetColumn(spin, j);
                    row.Children.Add(spin);
                }
                var delete = IconButton("delete_24dp.svg", "Delete point");
                delete.Click += (_, _) => { values.RemoveAt(pointIndex); property.Value = JsonSerializer.Serialize(values, ValueJsonOptions); BuildEditors(); };
                Grid.SetColumn(delete, 6);
                row.Children.Add(delete);
                panel.Children.Add(row);
            }
            var add = new Button { Content = "+ Add point", HorizontalAlignment = HorizontalAlignment.Stretch };
            add.Click += (_, _) => { values.Add([values.Count == 0 ? 0 : values[^1][0] + 1, 1, 0, 0, 2, 3]); property.Value = JsonSerializer.Serialize(values, ValueJsonOptions); BuildEditors(); };
            panel.Children.Add(add);
            return panel;
        }
        var input = new TextBox { Text = spec.Kind is "comment" or "base" ? DecodeString(value) : value, AcceptsReturn = spec.Kind == "comment", TextWrapping = Avalonia.Media.TextWrapping.Wrap, MinHeight = spec.Kind == "comment" ? 96 : 22 };
        input.TextChanged += (_, _) =>
        {
            var text = input.Text ?? string.Empty;
            var previous = spec.Kind is "comment" or "base" ? DecodeString(property.Value) : property.Value;
            if (text != previous) property.Value = spec.Kind is "comment" or "base" ? JsonSerializer.Serialize(text, ValueJsonOptions) : text;
        };
        if (spec.Kind != "base") return input;
        var reference = new Grid { ColumnDefinitions = new ColumnDefinitions("*,Auto") };
        reference.Children.Add(input);
        var search = IconButton("search_24dp.svg", "Find base event");
        search.Click += (_, _) => ShowPicker(search, Model?.EventNames ?? [], text => input.Text = text);
        Grid.SetColumn(search, 1);
        reference.Children.Add(search);
        return reference;
    }

    private Control CreateListEditor(SoundProperty property, SoundPropertySpec spec)
    {
        var panel = new StackPanel { Spacing = 6 };
        var isArray = TryArray(property.Value, out var array);
        if (isArray && array.Any(item => item.ValueKind != JsonValueKind.String)
            || !isArray && !property.Value.TrimStart().StartsWith('"'))
        {
            var raw = new TextBox();
            raw.Bind(TextBox.TextProperty, new Binding(nameof(SoundProperty.Value)) { Source = property, Mode = BindingMode.TwoWay });
            return raw;
        }
        var values = isArray ? array.Select(item => item.GetString()!).ToList() : new List<string> { DecodeString(property.Value) };
        void Commit() => property.Value = isArray || values.Count != 1 ? JsonSerializer.Serialize(values, ValueJsonOptions) : JsonSerializer.Serialize(values[0], ValueJsonOptions);
        for (var i = 0; i < values.Count; i++)
        {
            var index = i;
            var row = new Grid { ColumnDefinitions = new ColumnDefinitions("*,Auto,Auto") };
            var input = new TextBox { Text = values[i], PlaceholderText = "Type..." };
            input.TextChanged += (_, _) =>
            {
                var text = input.Text ?? string.Empty;
                if (values[index] == text) return;
                values[index] = text;
                Commit();
            };
            row.Children.Add(input);
            var search = IconButton("search_24dp.svg", "Find reference");
            search.Click += (_, _) =>
            {
                var choices = spec.Kind == "soundevent" ? Model?.EventNames ?? [] : (Model?.AddonSounds ?? []).Concat(Model?.VpkSounds ?? []);
                ShowPicker(search, choices, text => input.Text = text.Replace('\\', '/'));
            };
            Grid.SetColumn(search, 1);
            row.Children.Add(search);
            var delete = IconButton("delete_24dp.svg", "Delete reference");
            delete.Click += (_, _) => { values.RemoveAt(index); isArray = true; Commit(); BuildEditors(); };
            Grid.SetColumn(delete, 2);
            row.Children.Add(delete);
            panel.Children.Add(row);
        }
        var add = new Button { Content = "+ Add", HorizontalAlignment = HorizontalAlignment.Stretch };
        add.Click += (_, _) => { values.Add(string.Empty); isArray = true; Commit(); BuildEditors(); };
        panel.Children.Add(add);
        return panel;
    }

    private static void ShowPicker(Control anchor, IEnumerable<string> choices, Action<string> select)
    {
        var available = choices.ToArray();
        var filter = new TextBox { PlaceholderText = "Search..." };
        var list = new ListBox { ItemsSource = available.Take(200).ToArray(), Height = 300 };
        var panel = new StackPanel { Width = 420, Spacing = 4, Children = { filter, list } };
        var flyout = new Flyout { Content = panel };
        filter.TextChanged += (_, _) => list.ItemsSource = available.Where(item => item.Contains(filter.Text ?? string.Empty, StringComparison.OrdinalIgnoreCase)).Take(200).ToArray();
        list.DoubleTapped += (_, _) =>
        {
            if (list.SelectedItem is not string value) return;
            select(value);
            flyout.Hide();
        };
        flyout.ShowAt(anchor);
        filter.Focus();
    }

    private void AddSound(string? sound)
    {
        if (Event is null || sound is null || Model?.IsInternalEvent == true) return;
        var property = Event.Properties.FirstOrDefault(item => item.Key is "vsnd_files" or "vsnd_files_track_01");
        if (property is null)
        {
            Model?.AddNamedProperty("vsnd_files_track_01");
            property = Event.Properties.First(item => item.Key == "vsnd_files_track_01");
        }
        var values = TryArray(property.Value, out var array) ? array.Select(item => item.GetString()!).ToList() : new List<string> { DecodeString(property.Value) };
        values.Add(sound.Replace('\\', '/'));
        property.Value = JsonSerializer.Serialize(values, ValueJsonOptions);
        BuildEditors();
    }

    private void UpdateDependencies()
    {
        foreach (var (control, spec) in DependentEditors)
            control.IsEnabled = spec.Toggle is null || Event?.GetValue(spec.Toggle)?.Trim().Trim('"') != "false";
    }

    private static bool TryArray(string text, out JsonElement[] array)
    {
        try
        {
            using var document = JsonDocument.Parse(text, new JsonDocumentOptions { AllowTrailingCommas = true });
            if (document.RootElement.ValueKind == JsonValueKind.Array)
            {
                array = document.RootElement.EnumerateArray().Select(item => item.Clone()).ToArray();
                return true;
            }
        }
        catch (JsonException) { }
        array = [];
        return false;
    }

    private static string DecodeString(string text)
    {
        try { return JsonSerializer.Deserialize<string>(text) ?? string.Empty; }
        catch (JsonException) { return text; }
    }

    private static Button IconButton(string path, string tooltip)
    {
        var button = new Button { Width = 28, MinWidth = 0, Content = new LegacyIcon { Path = path }, Padding = new Thickness(2), Margin = new Thickness(3, 0), VerticalAlignment = VerticalAlignment.Top };
        ToolTip.SetTip(button, tooltip);
        return button;
    }

    private void BrowserFilterChanged(object? sender, TextChangedEventArgs e) => BuildBrowser();
    private void PropertyFilterChanged(object? sender, TextChangedEventArgs e) => BuildEditors();
    private void RefreshTemplatesClicked(object? sender, RoutedEventArgs e) => Model?.RefreshTemplates();
    private async void TemplateDoubleTapped(object? sender, TappedEventArgs e)
    {
        if (TemplateList.SelectedItem is string template && Model is not null) await Model.CreateFromTemplateAsync(template);
    }
    private void TemplateFilterChanged(object? sender, TextChangedEventArgs e)
    {
        if (Model is not null) TemplateList.ItemsSource = Model.Templates.Where(item => item.Contains(TemplateFilter.Text ?? string.Empty, StringComparison.OrdinalIgnoreCase)).ToArray();
    }
    private void AudioFilterChanged(object? sender, TextChangedEventArgs e)
    {
        RefreshAddonSounds();
    }
    private void InternalEventSelected(object? sender, SelectionChangedEventArgs e)
    {
        if (Model is not null && InternalEventList.SelectedItem is SoundEvent selected) Model.SelectedEvent = selected;
    }
    private void InternalEventFilterChanged(object? sender, TextChangedEventArgs e)
    {
        if (Model is not null) InternalEventList.ItemsSource = Model.InternalEvents.Where(item => item.Name.Contains(InternalEventFilter.Text ?? string.Empty, StringComparison.OrdinalIgnoreCase)).ToArray();
    }

    private void RefreshInternalSounds()
    {
        if (Model is not null) InternalAudioList.ItemsSource = SoundAudioFolder.Build(Model.VpkSounds, Model.AudioFilter);
    }
    private void InternalSoundSelected(object? sender, SelectionChangedEventArgs e)
    {
        if (Model is not null) Model.SelectedSound = (InternalAudioList.SelectedItem as SoundAudioFolder)?.SoundPath;
    }

    private async Task CopyEventAsync()
    {
        if (Model is not null && TopLevel.GetTopLevel(this)?.Clipboard is { } clipboard)
            await clipboard.SetTextAsync(Model.CopySelectedEvent());
    }
    private async Task PasteEventAsync()
    {
        if (Model is not null && TopLevel.GetTopLevel(this)?.Clipboard is { } clipboard && await clipboard.TryGetTextAsync() is { } text)
            await Model.PasteEventsAsync(text);
    }

    private void RefreshAddonSounds()
    {
        if (Model is not null) AddonAudioList.ItemsSource = Model.AddonAudioRows.Where(item => item.Path.Contains(AddonAudioFilter.Text ?? string.Empty, StringComparison.OrdinalIgnoreCase)).ToArray();
    }
    private void AddonSoundSelected(object? sender, SelectionChangedEventArgs e)
    {
        if (Model is not null) Model.SelectedSound = (AddonAudioList.SelectedItem as SoundAudioRow)?.Path;
    }

}

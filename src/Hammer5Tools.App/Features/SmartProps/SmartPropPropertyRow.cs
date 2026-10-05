using System.Globalization;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Layout;

namespace Hammer5Tools.App.Features.SmartProps;

internal sealed class SmartPropPropertyRow : StackPanel
{
    private readonly JsonNode? original;
    private readonly string type;
    private readonly ComboBox mode;
    private readonly Panel editor;
    private readonly List<SmartPropPropertyRow> children = [];
    private readonly TextBox? text;
    private readonly CheckBox? boolean;
    private readonly ComboBox? choices;
    private readonly TextBox expression;
    private readonly ComboBox variable;
    private readonly List<TextBox> components = [];
    private readonly bool vector;
    private bool initializing = true;
    private bool dirty;
    private int initialMode;
    private bool? initialBoolean;
    private string? initialChoice;
    private string? initialVariable;
    private readonly Dictionary<TextBox, string?> initialText = [];

    public event Action? Changed;
    public event Action? CommitRequested;
    public event Action<int>? ReferenceSelected;
    public bool IsDirty => dirty || mode.SelectedIndex != initialMode || initialText.Any(item => item.Key.Text != item.Value)
        || boolean?.IsChecked != initialBoolean || choices?.SelectedItem?.ToString() != initialChoice
        || variable.SelectedItem?.ToString() != initialVariable || children.Any(child => child.IsDirty);
    public string Key { get; }

    public SmartPropPropertyRow(string key, JsonNode? value, string kind, string[] enumValues, string[] variables)
    {
        Key = key;
        original = value?.DeepClone();
        type = kind == "Reference" ? "ID" : enumValues.Length > 0 ? FriendlyName(key) : kind;
        vector = kind is "Vector3D" or "Color" || value is JsonArray array && array.Count is >= 2 and <= 4 && array.All(item => item is JsonValue number && number.TryGetValue<double>(out _));
        var row = new Grid { ColumnDefinitions = new ColumnDefinitions("150,70,*"), MinHeight = 29, Classes = { "propertyRow" } };
        var label = new TextBlock { Text = FriendlyName(key), FontSize = 11, Margin = new global::Avalonia.Thickness(8, 0, 4, 0), VerticalAlignment = VerticalAlignment.Center, TextTrimming = global::Avalonia.Media.TextTrimming.CharacterEllipsis, Classes = { "propertyName", kind } };
        row.Children.Add(label);
        mode = new ComboBox { ItemsSource = kind == "Reference" ? new[] { "ID" } : new[] { "Default", type, "Variable", "Expression" }, MinHeight = 23, FontSize = 10, Tag = key + "/mode", Classes = { "valueMode" } };
        Grid.SetColumn(mode, 1);
        row.Children.Add(mode);
        editor = new Grid { Margin = new global::Avalonia.Thickness(3, 0) };
        Grid.SetColumn(editor, 2);
        row.Children.Add(editor);
        Children.Add(row);

        expression = new TextBox { Text = (value as JsonObject)?["m_Expression"]?.ToString() ?? "", PlaceholderText = "Expression", Tag = key + "/expression" };
        var source = value is JsonObject obj ? obj["m_SourceName"]?.ToString() : null;
        variable = new ComboBox { ItemsSource = variables.Append(source ?? "").Where(name => name.Length > 0).Distinct().ToArray(), SelectedItem = source, Tag = key + "/variable" };
        if (enumValues.Length > 0)
        {
            var current = value is JsonValue scalar && scalar.TryGetValue<string>(out var literal) ? literal : enumValues[0];
            choices = new ComboBox { ItemsSource = enumValues.Append(current).Distinct().ToArray(), SelectedItem = current, Tag = key + "/value" };
            editor.Children.Add(choices);
            choices.SelectionChanged += (_, _) => Edit(true);
        }
        else if (kind == "Bool")
        {
            var initial = value is JsonValue scalar && scalar.TryGetValue<bool>(out var literal) && literal;
            boolean = new CheckBox { IsChecked = initial, Content = initial ? "True" : "False", Tag = key };
            editor.Children.Add(boolean);
            boolean.IsCheckedChanged += (_, _) =>
            {
                boolean.Content = boolean.IsChecked == true ? "True" : "False";
                Edit(true);
            };
        }
        else if (vector)
        {
            var values = value is JsonArray direct ? direct : (value as JsonObject)?["m_Components"] as JsonArray;
            var count = Math.Clamp(values?.Count ?? (kind == "Color" ? 4 : 3), 2, 4);
            var fields = new Grid { ColumnDefinitions = new ColumnDefinitions(string.Join(',', Enumerable.Repeat("*", count))) };
            for (var index = 0; index < count; index++)
            {
                var input = new TextBox { Text = ScalarText(values?[index] ?? JsonValue.Create(0)), Tag = key + $"/m_Components/{index}", PlaceholderText = new[] { "X", "Y", "Z", "W" }[index] };
                Grid.SetColumn(input, index);
                fields.Children.Add(input);
                components.Add(input);
                BindText(input);
            }
            editor.Children.Add(fields);
        }
        else if (value is JsonObject compound && source is null && compound["m_Expression"] is null || value is JsonArray)
        {
            var nested = value is JsonObject dictionary
                ? dictionary.Where(item => item.Key != "_class").Select(item => (item.Key, item.Value))
                : value!.AsArray().Select((item, index) => ($"Item {index + 1}", item));
            foreach (var (childKey, childValue) in nested)
            {
                var child = new SmartPropPropertyRow(childKey, childValue, InferType(childKey, childValue), [], variables);
                child.Changed += () => Edit(false);
                child.CommitRequested += () => CommitRequested?.Invoke();
                children.Add(child);
                Children.Add(child);
            }
        }
        else
        {
            text = new TextBox { Text = value is JsonValue ? ScalarText(value) : kind is "Int" or "Float" ? "0" : "", Tag = key };
            if (kind == "Reference")
            {
                var fields = new StackPanel { Orientation = Orientation.Horizontal, Spacing = 4 };
                text.Width = 65;
                fields.Children.Add(text);
                var show = new Button { Content = "Show in hierarchy" };
                show.Click += (_, _) =>
                {
                    if (int.TryParse(text.Text, out var id))
                    {
                        ReferenceSelected?.Invoke(id);
                    }
                };
                fields.Children.Add(show);
                editor.Children.Add(fields);
            }
            else
            {
                editor.Children.Add(text);
            }
            BindText(text);
        }
        editor.Children.Add(expression);
        editor.Children.Add(variable);
        BindText(expression);
        variable.SelectionChanged += (_, _) => Edit(true);
        mode.SelectedIndex = type == "ID" || value is null ? 0 : source is not null ? 2 : value is JsonObject dynamic && dynamic["m_Expression"] is not null ? 3 : 1;
        UpdateMode();
        mode.SelectionChanged += (_, _) =>
        {
            UpdateMode();
            Edit(true);
        };
        initializing = false;
        initialMode = mode.SelectedIndex;
        initialBoolean = boolean?.IsChecked;
        initialChoice = choices?.SelectedItem?.ToString();
        initialVariable = variable.SelectedItem?.ToString();
    }

    public JsonNode? ReadValue()
    {
        if (!IsDirty)
        {
            return original?.DeepClone();
        }
        if (type == "ID")
        {
            return string.IsNullOrWhiteSpace(text?.Text) ? null : ReadNumber(text.Text, true);
        }
        if (mode.SelectedIndex == 0)
        {
            return null;
        }
        if (mode.SelectedIndex == 2)
        {
            return ReadDynamic("m_SourceName", variable.SelectedItem?.ToString() ?? "");
        }
        if (mode.SelectedIndex == 3)
        {
            return ReadDynamic("m_Expression", expression.Text ?? "");
        }
        if (choices is not null)
        {
            return JsonValue.Create(choices.SelectedItem?.ToString() ?? "");
        }
        if (boolean is not null)
        {
            return JsonValue.Create(boolean.IsChecked == true);
        }
        if (vector)
        {
            var values = new JsonArray(components.Select(input => ReadNumber(input.Text, false)).ToArray());
            if (original is JsonArray)
            {
                return values;
            }
            var result = original is JsonObject obj ? obj.DeepClone().AsObject() : new JsonObject();
            result.Remove("m_SourceName");
            result.Remove("m_Expression");
            result["m_Components"] = values;
            return result;
        }
        if (children.Count > 0)
        {
            if (original is JsonArray)
            {
                return new JsonArray(children.Select(child => child.ReadValue()).ToArray());
            }
            var result = original!.DeepClone().AsObject();
            foreach (var child in children)
            {
                result[child.Key] = child.ReadValue();
            }
            return result;
        }
        return type is "Int" or "Float" or "ID" ? ReadNumber(text?.Text, type is "Int" or "ID") : JsonValue.Create(text?.Text ?? "");
    }

    private JsonObject ReadDynamic(string key, string value)
    {
        var result = original is JsonObject obj ? obj.DeepClone().AsObject() : new JsonObject();
        result.Remove("m_SourceName");
        result.Remove("m_Expression");
        result.Remove("m_Components");
        result[key] = value;
        return result;
    }

    private static JsonValue ReadNumber(string? text, bool integer)
    {
        if (integer && long.TryParse(text, NumberStyles.Integer, CultureInfo.InvariantCulture, out var whole))
        {
            return JsonValue.Create(whole)!;
        }
        if (!integer && double.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out var value) && double.IsFinite(value))
        {
            return JsonValue.Create(value)!;
        }
        throw new InvalidDataException(integer ? "Enter an integer value." : "Enter a finite numeric value.");
    }

    private void UpdateMode()
    {
        foreach (var child in editor.Children)
        {
            child.IsVisible = child == expression ? mode.SelectedIndex == 3 : child == variable ? mode.SelectedIndex == 2 : type == "ID" || mode.SelectedIndex == 1;
        }
        foreach (var child in children)
        {
            child.IsVisible = mode.SelectedIndex == 1;
        }
    }

    private void BindText(TextBox input)
    {
        var initial = input.Text;
        initialText[input] = initial;
        input.TextChanged += (_, _) =>
        {
            if (input.Text != initial)
            {
                Edit(false);
            }
        };
        input.LostFocus += (_, _) =>
        {
            if (IsDirty)
            {
                CommitRequested?.Invoke();
            }
        };
        input.KeyDown += (_, args) =>
        {
            if (args.Key == global::Avalonia.Input.Key.Enter)
            {
                CommitRequested?.Invoke();
                args.Handled = true;
            }
        };
    }

    private void Edit(bool commit)
    {
        if (initializing)
        {
            return;
        }
        dirty = true;
        Changed?.Invoke();
        if (commit)
        {
            CommitRequested?.Invoke();
        }
    }

    public static string InferType(string key, JsonNode? value) => key.StartsWith("m_b", StringComparison.Ordinal) || value is JsonValue boolean && boolean.TryGetValue<bool>(out _) ? "Bool"
        : key.StartsWith("m_n", StringComparison.Ordinal) ? "Int"
        : key.StartsWith("m_v", StringComparison.Ordinal) ? "Vector3D"
        : key.StartsWith("m_fl", StringComparison.Ordinal) || key.StartsWith("m_f", StringComparison.Ordinal) || value is JsonValue number && number.TryGetValue<double>(out _) ? "Float" : "String";

    public static string FriendlyName(string key) => Regex.Replace(Regex.Replace(key, "^m_(?:fl|[bnsvf])?(?=[A-Z])", ""), "(?<=[a-z0-9])(?=[A-Z])", " ");
    private static string ScalarText(JsonNode? value) => value is JsonValue scalar && scalar.TryGetValue<string>(out var text) ? text : value?.ToJsonString() ?? "";
}

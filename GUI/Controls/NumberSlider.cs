namespace Hammer5Tools.App.Controls;

using Avalonia;
using Avalonia.Controls;
using Avalonia.Data;
using Avalonia.Input;
using Avalonia.Interactivity;

/// <summary>Pairs a precise numeric input with a compact slider without clamping authored values.</summary>
public sealed class NumberSlider : UserControl
{
    public static readonly StyledProperty<double> ValueProperty =
        AvaloniaProperty.Register<NumberSlider, double>(nameof(Value), defaultBindingMode: BindingMode.TwoWay);
    public static readonly StyledProperty<double> MinimumProperty =
        AvaloniaProperty.Register<NumberSlider, double>(nameof(Minimum));
    public static readonly StyledProperty<double> MaximumProperty =
        AvaloniaProperty.Register<NumberSlider, double>(nameof(Maximum), 1);
    public static readonly StyledProperty<double> IncrementProperty =
        AvaloniaProperty.Register<NumberSlider, double>(nameof(Increment), 0.01);

    private readonly NumericUpDown Number = new() { FormatString = "0.#######", ShowButtonSpinner = false, Classes = { "compact" } };
    private readonly Slider Slider = new() { Margin = new Thickness(6, 0, 0, 0), MinHeight = 26, Classes = { "h5-slider" } };
    private bool Updating;
    private bool Dragging;

    public double Value
    {
        get => GetValue(ValueProperty);
        set => SetValue(ValueProperty, value);
    }

    public double Minimum
    {
        get => GetValue(MinimumProperty);
        set => SetValue(MinimumProperty, value);
    }

    public double Maximum
    {
        get => GetValue(MaximumProperty);
        set => SetValue(MaximumProperty, value);
    }

    public double Increment
    {
        get => GetValue(IncrementProperty);
        set => SetValue(IncrementProperty, value);
    }

    public NumberSlider()
    {
        Height = 26;
        var grid = new Grid { ColumnDefinitions = new ColumnDefinitions("56,*") };
        Grid.SetColumn(Slider, 1);
        grid.Children.Add(Number);
        grid.Children.Add(Slider);
        Content = grid;
        Number.ValueChanged += (_, change) =>
        {
            if (!Updating && change.NewValue is { } value)
            {
                SetCurrentValue(ValueProperty, (double)value);
            }
        };
        Slider.PropertyChanged += (_, change) =>
        {
            if (!Updating && change.Property == Slider.ValueProperty)
            {
                if (Dragging)
                {
                    Updating = true;
                    try
                    {
                        Number.Value = (decimal)Slider.Value;
                    }
                    finally
                    {
                        Updating = false;
                    }
                }
                else
                {
                    SetCurrentValue(ValueProperty, Slider.Value);
                }
            }
        };
        // Begin before track clicks change the value, and commit after the final movement.
        Slider.AddHandler(PointerPressedEvent, (_, args) =>
        {
            if (args.GetCurrentPoint(Slider).Properties.IsLeftButtonPressed)
            {
                Dragging = true;
            }
        }, RoutingStrategies.Tunnel, handledEventsToo: true);
        Slider.AddHandler(PointerReleasedEvent, (_, args) =>
        {
            if (args.InitialPressMouseButton == MouseButton.Left)
            {
                CommitDrag();
            }
        }, RoutingStrategies.Bubble, handledEventsToo: true);
        Slider.PointerCaptureLost += (_, _) => CommitDrag();
        Refresh();
    }

    private void CommitDrag()
    {
        if (!Dragging)
        {
            return;
        }

        Dragging = false;
        SetCurrentValue(ValueProperty, Slider.Value);
    }

    protected override void OnPropertyChanged(AvaloniaPropertyChangedEventArgs change)
    {
        base.OnPropertyChanged(change);
        if (change.Property == ValueProperty || change.Property == MinimumProperty
            || change.Property == MaximumProperty || change.Property == IncrementProperty)
        {
            Refresh();
        }
    }

    private void Refresh()
    {
        if (!double.IsFinite(Value) || Value > (double)decimal.MaxValue || Value < (double)decimal.MinValue)
        {
            return;
        }
        Updating = true;
        try
        {
            // Rendering an existing out-of-range value must not change the source document.
            Slider.Minimum = Math.Min(Minimum, Value);
            Slider.Maximum = Math.Max(Math.Max(Maximum, Value), Slider.Minimum + double.Epsilon);
            Slider.Value = Value;
            Number.Value = (decimal)Value;
            Number.Increment = (decimal)Increment;
        }
        finally
        {
            Updating = false;
        }
    }
}

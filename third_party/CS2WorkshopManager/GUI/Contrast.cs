using Avalonia.Media;

namespace GUI;

/// <summary>
/// Keeps coloured text readable: text on a coloured surface is black or white by which reads better, and coloured text on a background is pushed lighter or darker until it reads.
/// Also lightens and darkens the way Qt does, which the workshop manager's own bar is drawn with.
/// </summary>
public static class Contrast
{
    /// <summary>Qt's QColor::lighter: the value goes up by <paramref name="percent"/>, and what does not fit is taken from the saturation.</summary>
    public static Color Lighter(Color color, double percent)
    {
        var hsv = color.ToHsv();
        var value = hsv.V * percent / 100;
        var saturation = hsv.S;

        if (value > 1)
        {
            saturation = Math.Max(0, saturation - (value - 1));
            value = 1;
        }

        return HsvColor.ToRgb(hsv.H, saturation, value);
    }

    /// <summary>Qt's QColor::darker: the value goes down by <paramref name="percent"/>.</summary>
    public static Color Darker(Color color, double percent)
    {
        var hsv = color.ToHsv();

        return HsvColor.ToRgb(hsv.H, hsv.S, hsv.V * 100 / percent);
    }

    /// <summary>The contrast ratio text should reach against what it sits on, the accessibility guidelines' figure for normal text.</summary>
    private const double Wanted = 4.5;

    /// <summary>Black or white, whichever reads better on <paramref name="surface"/>: the one with the higher contrast ratio, which black has once the surface is light enough.</summary>
    public static Color TextOn(Color surface)
    {
        return Luminance(surface) > 0.179 ? Colors.Black : Colors.White;
    }

    /// <summary>
    /// <paramref name="color"/> as text on <paramref name="background"/>: as it is when it reads, otherwise its lightness moved away from the background's, keeping its hue, until it does.
    /// </summary>
    public static Color Readable(Color color, Color background)
    {
        if (Ratio(color, background) >= Wanted)
        {
            return color;
        }

        // away from the background: darker on a light one, lighter on a dark one, in small steps until the contrast is there or the end is reached
        var hsl = color.ToHsl();
        var step = Luminance(background) > 0.179 ? -0.05 : 0.05;
        var lightness = hsl.L;

        while (lightness + step is >= 0 and <= 1)
        {
            lightness += step;

            var candidate = new HslColor(hsl.A, hsl.H, hsl.S, lightness).ToRgb();

            if (Ratio(candidate, background) >= Wanted)
            {
                return candidate;
            }
        }

        return step < 0 ? Colors.Black : Colors.White;
    }

    /// <summary>The contrast ratio between two colours, from 1 for the same colour to 21 for black on white.</summary>
    private static double Ratio(Color first, Color second)
    {
        var lighter = Math.Max(Luminance(first), Luminance(second));
        var darker = Math.Min(Luminance(first), Luminance(second));

        return (lighter + 0.05) / (darker + 0.05);
    }

    /// <summary>The relative luminance of a colour, 0 for black to 1 for white, from its channels made linear.</summary>
    private static double Luminance(Color color)
    {
        return 0.2126 * Linear(color.R) + 0.7152 * Linear(color.G) + 0.0722 * Linear(color.B);

        static double Linear(byte channel)
        {
            var value = channel / 255.0;

            return value <= 0.04045 ? value / 12.92 : Math.Pow((value + 0.055) / 1.055, 2.4);
        }
    }
}

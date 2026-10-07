namespace Hammer5Tools.Core.SoundEvents;

/// <summary>An authored sound curve key, including its independent left and right tangent modes.</summary>
public sealed record SoundCurvePoint(double Input, double Output, double LeftSlope, double RightSlope, int LeftMode, int RightMode);

/// <summary>Evaluates the legacy CS2 sound curve without modifying authored keys.</summary>
public static class SoundCurve
{
    /// <summary>Computes tangent modes on a sorted evaluation copy of the authored points.</summary>
    public static SoundCurvePoint[] Prepare(IEnumerable<SoundCurvePoint> authored)
    {
        var points = authored.OrderBy(point => point.Input).ToArray();
        var result = new SoundCurvePoint[points.Length];
        for (var i = 0; i < points.Length; i++)
        {
            var point = points[i];
            var previous = i > 0 ? points[i - 1] : null;
            var next = i + 1 < points.Length ? points[i + 1] : null;
            var leftX = previous is null ? 0 : point.Input - previous.Input;
            var leftY = previous is null ? 0 : point.Output - previous.Output;
            var rightX = next is null ? 0 : next.Input - point.Input;
            var rightY = next is null ? 0 : next.Output - point.Output;
            var left = leftX == 0 ? 0 : leftY / leftX;
            var right = rightX == 0 ? 0 : rightY / rightX;
            var smooth = previous is null ? right : next is null ? left
                : next.Input == previous.Input ? 0 : (next.Output - previous.Output) / (next.Input - previous.Input);
            var leftSlope = point.LeftMode switch
            {
                0 => left,
                1 => smooth,
                3 => 0,
                4 => leftY <= 0 ? -1.60305 / (leftX == 0 ? 1 : leftX) : -0.0413377 / (leftX == 0 ? 1 : leftX),
                _ => point.LeftSlope,
            };
            var rightSlope = point.RightMode switch
            {
                0 => right,
                1 => smooth,
                3 => leftSlope,
                4 => rightY <= 0 ? 0.0413377 / (rightX == 0 ? 1 : rightX) : 1.60305 / (rightX == 0 ? 1 : rightX),
                _ => point.RightSlope,
            };
            if (point.LeftMode == 3) leftSlope = rightSlope;
            result[i] = point with { LeftSlope = leftSlope, RightSlope = rightSlope };
        }
        return result;
    }

    /// <summary>Samples prepared keys with the legacy cubic tangent interpolation and endpoint clamping.</summary>
    public static double Sample(double input, IReadOnlyList<SoundCurvePoint> prepared)
    {
        if (prepared.Count < 2) return -1;
        var index = 1;
        while (index < prepared.Count - 1 && input > prepared[index].Input) index++;
        var left = prepared[index - 1];
        var right = prepared[index];
        var dx = right.Input - left.Input;
        var dy = right.Output - left.Output;
        var t = Math.Clamp(dx == 0 ? input - left.Input : (input - left.Input) / dx, 0, 1);
        var p1 = ((left.RightSlope + right.LeftSlope) * dx - 2 * dy) * t;
        var p2 = p1 + (-right.LeftSlope - 2 * left.RightSlope) * dx + 3 * dy;
        return (p2 * t + left.RightSlope * dx) * t + left.Output;
    }
}

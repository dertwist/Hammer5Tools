using System.Globalization;

namespace SourcePorter.Core.Materials;

/// <summary>
/// Value-transform helpers ported 1:1 from materials_import.py (<c>fixVector</c>,
/// <c>float_val</c>, <c>bool_val</c>, <c>mapped_val</c>, <c>uniform_vec2</c>) plus the
/// <c>TexTransform</c> legacy-matrix parser. These convert raw <c>.vmt</c> string values into the
/// formatted strings a <c>.vmat</c> expects (6-decimal floats, bracketed vectors, 0/1 booleans).
/// </summary>
internal static class MaterialValues
{
    private static readonly char[] FloatTrim = [' ', '\t', '"'];

    /// <summary>Ported from <c>float_val</c>: format a scalar to 6 decimals.</summary>
    public static string? FloatVal(string v)
        => float.TryParse(v.Trim(FloatTrim), NumberStyles.Float, CultureInfo.InvariantCulture, out var f)
            ? f.ToString("F6", CultureInfo.InvariantCulture)
            : null;

    /// <summary>Ported from <c>bool_val(bInvert)</c>: parse to a float, coerce to 0/1, optionally invert.</summary>
    public static string? BoolVal(string v, bool invert)
    {
        if (!float.TryParse(v.Trim(FloatTrim), NumberStyles.Float, CultureInfo.InvariantCulture, out var f))
            return null;
        var b = f != 0f;
        if (invert)
            b = !b;
        return b ? "1" : "0";
    }

    /// <summary>Ported from <c>mapped_val</c>: map a discrete value through a table, else null (use default).</summary>
    public static string? MappedVal(string v, IReadOnlyDictionary<string, string> map)
        => !string.IsNullOrEmpty(v) && map.TryGetValue(v, out var mapped) ? mapped : null;

    /// <summary>Ported from <c>uniform_vec2</c>: a scalar duplicated into a 2-component vector.</summary>
    public static string? UniformVec2(string v)
        => float.TryParse(v, NumberStyles.Float, CultureInfo.InvariantCulture, out var f)
            ? $"[{f.ToString("F6", CultureInfo.InvariantCulture)} {f.ToString("F6", CultureInfo.InvariantCulture)}]"
            : null;

    /// <summary>
    /// Ported from <c>fixVector</c>: normalise a vector/color string to <c>[a b c d]</c> with 6-decimal
    /// components. Integer color triplets wrapped in <c>{ }</c> are divided by 255. 1-D values are
    /// duplicated to 2-D; when <paramref name="addAlpha"/> is set, 3-D color values gain a 1.0 alpha.
    /// Returns null on unparseable input.
    /// </summary>
    public static string? FixVector(string s, bool addAlpha)
    {
        var likelyColorInt = s.Contains('{') || s.Contains('}');

        s = s.Trim()
             .Replace("\"", string.Empty).Replace("'", string.Empty)
             .Replace(",", string.Empty)
             .Trim('[', ']', '{', '}', '(', ')')
             .Trim();

        var parts = s.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        var values = new List<float>(parts.Length);
        foreach (var part in parts)
        {
            if (!float.TryParse(part, NumberStyles.Float, CultureInfo.InvariantCulture, out var f))
                return null;
            values.Add(f);
        }

        var dimension = values.Count;
        if (dimension == 0)
            return null;
        if (dimension < 3)
            likelyColorInt = false;

        var formatted = new List<string>(dimension);
        foreach (var f in values)
        {
            var value = likelyColorInt ? f / 255f : f;
            formatted.Add(value.ToString("F6", CultureInfo.InvariantCulture));
        }

        if (dimension <= 1)
            formatted.Add(formatted[0]); // duplicate for 2-D
        else if (addAlpha && dimension == 3)
            formatted.Add(1f.ToString("F6", CultureInfo.InvariantCulture)); // add alpha

        return "[" + string.Join(' ', formatted) + "]";
    }

    /// <summary>
    /// Ported from <c>TexTransform</c>: parses a Source 1 texture-transform matrix string
    /// (<c>center .5 .5 scale 1 1 rotate 0 translate 0 0</c>, terms optional/reorderable) into
    /// scale and translate pairs. Rotation is parsed but unused (no rotation in Source 2).
    /// </summary>
    public readonly record struct TexTransform((float X, float Y) Scale, (float X, float Y) Translate, float Rotate)
    {
        public static TexTransform Parse(string s)
        {
            var scale = (1f, 1f);
            var translate = (0f, 0f);
            var rotate = 0f;

            var terms = s.Trim('"').Split(' ', StringSplitOptions.RemoveEmptyEntries);
            for (var i = 0; i < terms.Length; i++)
            {
                if (!TryFloat(terms, i + 1, out var next))
                    continue;

                if (terms[i].Equals("rotate", StringComparison.OrdinalIgnoreCase))
                {
                    rotate = next;
                    continue;
                }

                if (!TryFloat(terms, i + 2, out var next2))
                    continue;

                switch (terms[i].ToLowerInvariant())
                {
                    case "center": break; // parsed for completeness; not emitted
                    case "scale": scale = (next, next2); break;
                    case "translate": translate = (next, next2); break;
                }
            }

            return new TexTransform(scale, translate, rotate);
        }

        private static bool TryFloat(string[] terms, int index, out float value)
        {
            value = 0f;
            return index < terms.Length
                && float.TryParse(terms[index], NumberStyles.Float, CultureInfo.InvariantCulture, out value);
        }
    }
}

using ValveKeyValue;

namespace Hammer5Tools.Core.Format.SmartProps.Evaluation;

internal static class SmartPropClass
{
    private static readonly string[] Prefixes =
    [
        "CSmartPropOperation_",
        "CSmartPropPulse_",
        "CSmartPropElement_",
        "CSmartPropSelectionCriteria_",
        "CSmartPropFilter_",
    ];

    public static string Read(KVObject node)
    {
        if ((!node.TryGetValue("generic_data_type", out var classValue) || classValue.ValueType != KVValueType.String)
            && (!node.TryGetValue("_class", out classValue) || classValue.ValueType != KVValueType.String))
        {
            return string.Empty;
        }

        var name = (string)classValue;
        foreach (var prefix in Prefixes)
        {
            if (name.StartsWith(prefix, StringComparison.Ordinal))
            {
                return name[prefix.Length..];
            }
        }

        return name;
    }
}

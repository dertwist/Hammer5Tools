namespace Hammer5Tools.Core.Format.SmartProps;

/// <summary>
/// A tint applied to one named material on a model rather than to the whole model, produced by
/// <c>CSmartPropOperation_MaterialTint</c>. <paramref name="Material"/> is normalized through
/// <see cref="SmartPropMaterialEvaluator.NormalizeMaterialName"/> so a consumer can compare it
/// against a submesh's own material path without repeating the casing/separator rules.
/// </summary>
public sealed record EvaluatedSmartPropMaterialTint(string Material, Vector4 Color);

/// <summary>
/// One material swapped for another on a model, produced by
/// <c>CSmartPropOperation_MaterialOverride</c>. Both names are normalized the same way as
/// <see cref="EvaluatedSmartPropMaterialTint.Material"/>.
/// </summary>
public sealed record EvaluatedSmartPropMaterialReplacement(string OriginalMaterial, string ReplacementMaterial);

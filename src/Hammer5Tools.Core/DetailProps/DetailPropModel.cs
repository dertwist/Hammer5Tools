namespace Hammer5Tools.Core.DetailProps;

using System.IO;

/// <summary>
/// A single model variation within a detail prop type.
/// </summary>
public class DetailPropModel
{
    public string ModelName { get; set; } = string.Empty;

    public float MinScale { get; set; } = 1.0f;

    public float MaxScale { get; set; } = 1.0f;

    public bool RandomYaw { get; set; } = true;

    public bool RandomPitch { get; set; }

    public bool RandomRoll { get; set; }

    public bool AlignToSurface { get; set; }

    public bool Upright { get; set; } = true;

    public float Density { get; set; } = 1.0f;

    public string DisplayName => string.IsNullOrWhiteSpace(ModelName) ? "<no model>" : Path.GetFileName(ModelName);
}

namespace Hammer5Tools.Core.Format.Resources;

/// <summary>An immutable viewport material decoded from a compiled Source 2 material.</summary>
public sealed record CompiledMaterial(
    string Name,
    CompiledTexture? BaseColor,
    CompiledTexture? Normal,
    CompiledTexture? MetallicRoughness,
    CompiledTexture? AmbientOcclusion,
    CompiledTexture? Emissive,
    Vector4 BaseColorFactor,
    float MetallicFactor,
    float RoughnessFactor,
    Vector3 EmissiveFactor,
    string AlphaMode,
    float AlphaCutoff,
    bool DoubleSided,
    int WrapU,
    int WrapV,
    int UvSet,
    Vector2 UvScale,
    Vector2 UvOffset,
    Vector2 UvCenter,
    float UvRotation);

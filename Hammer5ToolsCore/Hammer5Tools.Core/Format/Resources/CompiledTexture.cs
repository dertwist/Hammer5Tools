using System.Collections.Immutable;

namespace Hammer5Tools.Core.Format.Resources;

/// <summary>An immutable RGBA8 texture ready for GPU upload.</summary>
public sealed record CompiledTexture(int Width, int Height, ImmutableArray<byte> Rgba);

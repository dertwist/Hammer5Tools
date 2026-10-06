using System.Collections.Immutable;

namespace Hammer5Tools.Core.IO.CompiledResource;

/// <summary>Decoded content extracted from a compiled Source 2 resource.</summary>
public sealed record CompiledResourceContent(ImmutableArray<byte> Data, string Format);

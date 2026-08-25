using System.Collections;
using System.Globalization;
using System.Numerics;

using Datamodel;
using Hammer5Tools.Core.Vmap;

namespace SourcePorter.Core.Vmap;

/// <summary>
/// Projects the authoritative SourcePorter VMAP document into shared read-only models.
/// </summary>
public sealed class ValveMapReader : IValveMapReader
{
    /// <inheritdoc/>
    public ValveMapDocument Read(string path)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);

        var document = VmapDocument.LoadInMemory(path);
        var world = ConvertNode(document.World);
        var nodes = Traverse(world).ToArray();
        var entities = ReadEntities(world).ToArray();
        var assetReferences = ReadAssetReferences(document.Model).ToArray();
        var thumbnail = ReadThumbnail(document.Model);
        var thumbnailFormat = document.Model.PrefixAttributes.TryGetValue(
            "asset_preview_thumbnail_format", out var format)
            ? format?.ToString()
            : null;
        return new ValveMapDocument(
            document.Path,
            world,
            nodes,
            entities,
            assetReferences,
            thumbnail,
            thumbnailFormat);
    }

    private static ValveMapNode ConvertNode(Element element)
    {
        var properties = new Dictionary<string, string>(StringComparer.Ordinal);
        var children = new List<ValveMapNode>();
        foreach (var (name, value) in element)
        {
            switch (value)
            {
                case Element child:
                    children.Add(ConvertNode(child));
                    break;
                case ElementArray childArray:
                    children.AddRange(childArray.Select(ConvertNode));
                    break;
                case null:
                    break;
                case Vector2 vector:
                    properties[name] = FormattableString.Invariant($"{vector.X} {vector.Y}");
                    break;
                case Vector3 vector:
                    properties[name] = FormattableString.Invariant($"{vector.X} {vector.Y} {vector.Z}");
                    break;
                case Vector4 vector:
                    properties[name] = FormattableString.Invariant($"{vector.X} {vector.Y} {vector.Z} {vector.W}");
                    break;
                case IFormattable formattable:
                    properties[name] = formattable.ToString(null, CultureInfo.InvariantCulture);
                    break;
                default:
                    properties[name] = value.ToString() ?? string.Empty;
                    break;
            }
        }

        return new ValveMapNode(element.Name, element.ClassName, properties, children);
    }

    private static IEnumerable<ValveMapNode> Traverse(ValveMapNode node)
    {
        yield return node;
        foreach (var child in node.Children)
        {
            foreach (var descendant in Traverse(child))
            {
                yield return descendant;
            }
        }
    }

    private static IEnumerable<ValveMapEntity> ReadEntities(ValveMapNode world)
    {
        foreach (var node in Traverse(world))
        {
            var entityProperties = node.Children.FirstOrDefault(child =>
                child.Properties.ContainsKey("classname"));
            if (entityProperties is null)
            {
                continue;
            }

            yield return new ValveMapEntity(
                entityProperties.Properties["classname"],
                node.Properties.GetValueOrDefault("origin"),
                node.Properties.GetValueOrDefault("angles"),
                entityProperties.Properties);
        }
    }

    private static IEnumerable<string> ReadAssetReferences(Datamodel.Datamodel model)
    {
        if (!model.PrefixAttributes.TryGetValue("map_asset_references", out var value)
            || value is string
            || value is not IEnumerable references)
        {
            yield break;
        }

        foreach (var reference in references)
        {
            if (reference is not null)
            {
                yield return reference.ToString() ?? string.Empty;
            }
        }
    }

    private static byte[]? ReadThumbnail(Datamodel.Datamodel model)
    {
        if (!model.PrefixAttributes.TryGetValue("asset_preview_thumbnail", out var value))
        {
            return null;
        }

        return value switch
        {
            byte[] bytes => bytes,
            IEnumerable<byte> bytes => bytes.ToArray(),
            _ => null,
        };
    }
}

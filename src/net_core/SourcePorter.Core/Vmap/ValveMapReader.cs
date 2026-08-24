using System.Globalization;

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
        return new ValveMapDocument(document.Path, world, nodes);
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
                case IFormattable formattable:
                    properties[name] = formattable.ToString(null, CultureInfo.InvariantCulture);
                    break;
                default:
                    properties[name] = value.ToString() ?? string.Empty;
                    break;
            }
        }

        return new ValveMapNode(element.ClassName, properties, children);
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
}

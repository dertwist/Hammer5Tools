using System.Linq;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.Documents;
using Avalonia.Input;
using Avalonia.Layout;
using Avalonia.Media;

namespace GUI;

/// <summary>
/// Shows a workshop description written in Steam's text formatting the way its pages show it: the [h1], [b], [url], [list], [quote], [code] and [img] markup laid out instead of typed out,
/// with Steam's blue headings, its links followed by their host, its tables and its spoilers that show under the pointer. Tags Steam does not know are left as text, as its pages leave them.
/// </summary>
public sealed class BbCodeView : StackPanel
{
    public static readonly StyledProperty<string?> TextProperty = AvaloniaProperty.Register<BbCodeView, string?>(nameof(Text));

    /// <summary>Steam's tags; [s] is accepted as well because people write it.</summary>
    private static readonly HashSet<string> KnownTags = new(StringComparer.OrdinalIgnoreCase)
    {
        "h1", "h2", "h3", "b", "u", "i", "strike", "s", "spoiler", "noparse", "hr", "url", "list", "olist", "*", "quote", "code", "table", "tr", "th", "td", "img", "previewyoutube",
    };

    private static readonly HashSet<string> BlockTags = new(StringComparer.OrdinalIgnoreCase)
    {
        "h1", "h2", "h3", "hr", "list", "olist", "quote", "code", "table", "img", "previewyoutube",
    };

    /// <summary>What a blank line between two blocks is worth, about a line of the body text.</summary>
    private const double BlankLineHeight = 18;

    private static readonly HttpClient Http = CreateHttp();

    static BbCodeView()
    {
        TextProperty.Changed.AddClassHandler<BbCodeView>((view, _) => view.Rebuild());
    }

    public BbCodeView()
    {
        Spacing = 8;
    }

    public string? Text
    {
        get => GetValue(TextProperty);
        set => SetValue(TextProperty, value);
    }

    /// <summary>A tag with what is inside it, or a run of text when <see cref="Tag"/> is null.</summary>
    private sealed class Node
    {
        public string? Tag { get; init; }

        /// <summary>What followed the tag name: the value after = or the attributes after a space.</summary>
        public string? Argument { get; init; }

        public string Text { get; init; } = string.Empty;
        public List<Node> Children { get; } = [];

        /// <summary>Everything inside, as typed, for tags whose content is not formatting.</summary>
        public string InnerText => Tag == null ? Text : string.Concat(Children.Select(child => child.InnerText));

        public bool HasAttribute(string attribute)
        {
            return Argument != null && Argument.Contains(attribute, StringComparison.OrdinalIgnoreCase);
        }
    }

    /// <summary>Picture hosts such as imgur turn away requests that do not look like a browser's.</summary>
    private static HttpClient CreateHttp()
    {
        var http = new HttpClient();
        http.DefaultRequestHeaders.UserAgent.ParseAdd("Mozilla/5.0 (Windows NT 10.0; Win64; x64) CS2WorkshopManager/1.0");
        return http;
    }

    private void Rebuild()
    {
        Children.Clear();
        RenderBlocks(Parse(Text ?? string.Empty), Children);
    }

    /// <summary>
    /// Reads the markup into a tree. A closing tag closes the nearest open tag of its name, [*] closes the item before it, and [noparse] and [code] keep their insides as typed.
    /// </summary>
    private static List<Node> Parse(string text)
    {
        var root = new Node();
        var open = new Stack<Node>();
        open.Push(root);

        var position = 0;

        while (position < text.Length)
        {
            var start = text.IndexOf('[', position);
            var end = start < 0 ? -1 : text.IndexOf(']', start);

            if (start < 0 || end < 0)
            {
                AddText(open.Peek(), text[position..]);
                break;
            }

            if (start > position)
            {
                AddText(open.Peek(), text[position..start]);
            }

            var inside = text[(start + 1)..end];
            position = end + 1;

            if (inside.StartsWith('/'))
            {
                var name = inside[1..];

                // [hr][/hr], as Steam's own editor writes a rule: the closing tag is nothing, the rule stands on its own
                if (name.Equals("hr", StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }

                if (KnownTags.Contains(name) && open.Any(node => name.Equals(node.Tag, StringComparison.OrdinalIgnoreCase)))
                {
                    while (!name.Equals(open.Pop().Tag, StringComparison.OrdinalIgnoreCase))
                    {
                        // everything left open inside the closed tag closes with it
                    }
                }
                else
                {
                    AddText(open.Peek(), $"[{inside}]");
                }

                continue;
            }

            // [url=address], [quote=author name] and [table noborder=1] all keep what follows the name
            var separator = inside.IndexOfAny(['=', ' ']);
            var tag = separator < 0 ? inside : inside[..separator];
            var argument = separator < 0 ? null : inside[(separator + 1)..];

            if (!KnownTags.Contains(tag))
            {
                AddText(open.Peek(), $"[{inside}]");
                continue;
            }

            if (tag == "*" && open.Peek().Tag == "*")
            {
                open.Pop();
            }

            var node = new Node { Tag = tag.ToLowerInvariant(), Argument = argument };
            open.Peek().Children.Add(node);

            if (node.Tag == "hr")
            {
                continue;
            }

            if (node.Tag is "noparse" or "code")
            {
                var close = text.IndexOf($"[/{node.Tag}]", position, StringComparison.OrdinalIgnoreCase);
                var raw = close < 0 ? text[position..] : text[position..close];

                node.Children.Add(new Node { Text = raw });
                position = close < 0 ? text.Length : close + node.Tag.Length + 3;
                continue;
            }

            open.Push(node);
        }

        return root.Children;
    }

    /// <summary>
    /// The text of the markup with the tags taken out: pictures and videos are dropped, links keep their text, and blocks start on their own lines, with no empty lines left over.
    /// </summary>
    public static string ToPlainText(string text)
    {
        var plain = new StringBuilder();
        Flatten(Parse(text), plain);

        var lines = plain.ToString().Split('\n', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries);

        return string.Join('\n', lines);

        static void Flatten(List<Node> nodes, StringBuilder plain)
        {
            foreach (var node in nodes)
            {
                switch (node.Tag)
                {
                    case null:
                        plain.Append(node.Text);
                        break;
                    case "img" or "previewyoutube":
                        break;
                    case "url":
                        // a link around a picture is the picture, which is dropped like any other
                        if (!node.Children.Any(child => child.Tag == "img"))
                        {
                            plain.Append(node.InnerText);
                        }

                        break;
                    case "hr":
                        plain.Append('\n');
                        break;
                    case "h1" or "h2" or "h3" or "quote" or "code" or "list" or "olist" or "*" or "table" or "tr":
                        plain.Append('\n');
                        Flatten(node.Children, plain);
                        plain.Append('\n');
                        break;
                    case "td" or "th":
                        Flatten(node.Children, plain);
                        plain.Append(' ');
                        break;
                    default:
                        Flatten(node.Children, plain);
                        break;
                }
            }
        }
    }

    private static void AddText(Node parent, string text)
    {
        parent.Children.Add(new Node { Text = text });
    }

    /// <summary>
    /// Text and inline tags run together into paragraphs, block tags stand on their own. The line breaks that separate text from a block are the block's spacing, not empty lines.
    /// </summary>
    private void RenderBlocks(List<Node> nodes, Controls target)
    {
        TextBlock? paragraph = null;

        for (var index = 0; index < nodes.Count; index++)
        {
            var node = nodes[index];

            if (IsBlock(node))
            {
                paragraph = null;
                target.Add(RenderBlock(node));
                continue;
            }

            if (node.Tag == null)
            {
                var text = node.Text;

                // only the one break that ends the block's line goes, further blank lines stay blank lines as on Steam
                if (paragraph == null)
                {
                    text = text.StartsWith("\r\n", StringComparison.Ordinal) ? text[2..] : text.StartsWith('\n') ? text[1..] : text;
                }

                if (index + 1 == nodes.Count || IsBlock(nodes[index + 1]))
                {
                    text = text.EndsWith("\r\n", StringComparison.Ordinal) ? text[..^2] : text.EndsWith('\n') ? text[..^1] : text;
                }

                if (text.Trim().Length == 0)
                {
                    // what is left of a run of blank lines: empty lines in the paragraph they follow, or a gap between two blocks
                    var breaks = text.Count(character => character == '\n');

                    if (breaks > 0 && paragraph != null)
                    {
                        for (var line = 0; line < breaks; line++)
                        {
                            paragraph.Inlines!.Add(new LineBreak());
                        }
                    }
                    else if (breaks > 0)
                    {
                        target.Add(new Border { Height = BlankLineHeight * breaks });
                    }

                    continue;
                }

                node = new Node { Text = text };
            }

            if (paragraph == null)
            {
                paragraph = Paragraph();
                target.Add(paragraph);
            }

            RenderInline(node, paragraph.Inlines!, default);
        }
    }

    /// <summary>Whether a node stands on its own lines: a block tag, or a link around a picture, which shows as the picture.</summary>
    private static bool IsBlock(Node node)
    {
        return node.Tag != null && (BlockTags.Contains(node.Tag) || (node.Tag == "url" && node.Children.Any(child => child.Tag == "img")));
    }

    private Control RenderBlock(Node node)
    {
        switch (node.Tag)
        {
            case "url":
                // a link around a picture: the picture, opening the link when clicked
                var linked = new StackPanel { HorizontalAlignment = HorizontalAlignment.Left, Cursor = new Cursor(StandardCursorType.Hand) };

                RenderBlocks(node.Children, linked.Children);

                if (TryParseLink(node.Argument?.Trim() ?? string.Empty, out var linkUri))
                {
                    linked.PointerPressed += (_, _) => _ = TopLevel.GetTopLevel(this)?.Launcher.LaunchUriAsync(linkUri);
                }

                return linked;

            case "h1":
            case "h2":
            case "h3":
                // Steam's headings are its blue in a regular weight, only the size steps down
                var heading = Paragraph();
                heading.FontSize = node.Tag switch { "h1" => 22, "h2" => 18, _ => 15 };
                heading.Margin = new Thickness(0, 8, 0, 0);
                BindResource(heading, TextBlock.ForegroundProperty, "HeadingBrush");
                RenderInlines(node.Children, heading.Inlines!, default);
                return heading;

            case "hr":
                var rule = new Border { Height = 1, Margin = new Thickness(0, 6) };
                BindResource(rule, Border.BackgroundProperty, "OutlineBrush");
                return rule;

            case "list":
            case "olist":
                var list = new StackPanel { Margin = new Thickness(16, 0, 0, 0) };
                var number = 0;

                foreach (var item in node.Children.Where(child => child.Tag == "*"))
                {
                    number++;

                    var bullet = new TextBlock { Text = node.Tag == "olist" ? $"{number}." : "•", Width = 22 };
                    var body = Paragraph();
                    RenderInlines(item.Children, body.Inlines!, default);

                    list.Children.Add(new DockPanel { Children = { bullet, body } });
                }

                return list;

            case "quote":
                var quote = new StackPanel { Spacing = 4 };

                if (!string.IsNullOrWhiteSpace(node.Argument))
                {
                    var author = Paragraph();
                    author.Inlines!.Add(new Run("Originally posted by "));
                    author.Inlines.Add(new Run(node.Argument.Trim()) { FontWeight = FontWeight.Bold });
                    author.Inlines.Add(new Run(":"));
                    quote.Children.Add(author);
                }

                RenderBlocks(node.Children, quote.Children);

                // Steam's quote is a ruled box, not a filled one
                var quoteBox = new Border { Child = quote, Padding = new Thickness(16, 12), CornerRadius = new CornerRadius(2), BorderThickness = new Thickness(1), HorizontalAlignment = HorizontalAlignment.Left };
                BindResource(quoteBox, Border.BorderBrushProperty, "OutlineBrush");
                return quoteBox;

            case "code":
                var codeBox = new Border
                {
                    Child = new TextBlock { Text = node.InnerText.Trim('\r', '\n'), FontFamily = new FontFamily("Consolas,Cascadia Mono,Menlo,monospace"), TextWrapping = TextWrapping.Wrap },
                    Padding = new Thickness(12, 8),
                    CornerRadius = new CornerRadius(3),
                };
                BindResource(codeBox, Border.BackgroundProperty, "FieldBrush");
                return codeBox;

            case "table":
                return Table(node);

            case "img":
                // the same control as the thumbnails, so a gif plays; Steam only limits pictures to the page's width
                var image = new PreviewImage { HorizontalAlignment = HorizontalAlignment.Left };

                if (TryParseLink(node.InnerText.Trim(), out var imageUri))
                {
                    _ = LoadImageAsync(image, imageUri);
                }

                return image;

            case "previewyoutube":
                return YouTubePreview(node.Argument?.Split(';')[0] ?? string.Empty);

            default:
                var fallback = Paragraph();
                RenderInline(node, fallback.Inlines!, default);
                return fallback;
        }
    }

    /// <summary>
    /// Rows of cells, header cells bold, ruled unless noborder=1, and stretched to equal columns with equalcells=1, like Steam's.
    /// </summary>
    private Grid Table(Node node)
    {
        var rows = node.Children.Where(child => child.Tag == "tr").Select(row => row.Children.Where(cell => cell.Tag is "th" or "td").ToList()).ToList();
        var columns = rows.Count == 0 ? 0 : rows.Max(cells => cells.Count);
        var equal = node.HasAttribute("equalcells=1");
        var ruled = !node.HasAttribute("noborder=1");

        var grid = new Grid { HorizontalAlignment = equal ? HorizontalAlignment.Stretch : HorizontalAlignment.Left };

        for (var column = 0; column < columns; column++)
        {
            grid.ColumnDefinitions.Add(new ColumnDefinition(equal ? GridLength.Star : GridLength.Auto));
        }

        for (var row = 0; row < rows.Count; row++)
        {
            grid.RowDefinitions.Add(new RowDefinition(GridLength.Auto));

            for (var column = 0; column < rows[row].Count; column++)
            {
                var cell = rows[row][column];
                var content = Paragraph();
                content.FontWeight = cell.Tag == "th" ? FontWeight.Bold : FontWeight.Normal;
                RenderInlines(cell.Children, content.Inlines!, default);

                // Steam gives cells generous room, and draws only their lines
                var box = new Border { Child = content, Padding = new Thickness(16, 12), Background = Brushes.Transparent, BorderThickness = new Thickness(ruled ? 1 : 0) };
                BindResource(box, Border.BorderBrushProperty, "OutlineBrush");
                Grid.SetRow(box, row);
                Grid.SetColumn(box, column);
                grid.Children.Add(box);
            }
        }

        return grid;
    }

    /// <summary>The video's own thumbnail, which opens the video on YouTube, where Steam's page would embed its player.</summary>
    private Border YouTubePreview(string video)
    {
        var thumbnail = new PreviewImage { HorizontalAlignment = HorizontalAlignment.Left };
        var frame = new Border { Child = thumbnail, HorizontalAlignment = HorizontalAlignment.Left, Cursor = new Cursor(StandardCursorType.Hand) };

        if (video.Length > 0 && video.All(character => char.IsAsciiLetterOrDigit(character) || character is '-' or '_'))
        {
            _ = LoadImageAsync(thumbnail, new Uri($"https://img.youtube.com/vi/{video}/hqdefault.jpg"));

            var link = new Uri($"https://www.youtube.com/watch?v={video}");
            frame.PointerPressed += (_, _) => _ = TopLevel.GetTopLevel(this)?.Launcher.LaunchUriAsync(link);
        }

        return frame;
    }

    /// <summary>What inline tags have turned on around a piece of text.</summary>
    private readonly record struct InlineStyle(bool Bold, bool Italic, bool Underline, bool Strike);

    private void RenderInlines(List<Node> nodes, InlineCollection inlines, InlineStyle style)
    {
        foreach (var node in nodes)
        {
            RenderInline(node, inlines, style);
        }
    }

    private void RenderInline(Node node, InlineCollection inlines, InlineStyle style)
    {
        switch (node.Tag)
        {
            case null:
                var lines = node.Text.Replace("\r\n", "\n", StringComparison.Ordinal).Split('\n');

                for (var index = 0; index < lines.Length; index++)
                {
                    if (index > 0)
                    {
                        inlines.Add(new LineBreak());
                    }

                    if (lines[index].Length > 0)
                    {
                        inlines.Add(StyledRun(lines[index], style));
                    }
                }

                break;

            case "b":
                RenderInlines(node.Children, inlines, style with { Bold = true });
                break;

            case "i":
                RenderInlines(node.Children, inlines, style with { Italic = true });
                break;

            case "u":
                RenderInlines(node.Children, inlines, style with { Underline = true });
                break;

            case "strike":
            case "s":
                RenderInlines(node.Children, inlines, style with { Strike = true });
                break;

            case "noparse":
                inlines.Add(StyledRun(node.InnerText, style));
                break;

            case "url":
                var text = node.InnerText.Trim();
                var address = string.IsNullOrWhiteSpace(node.Argument) ? text : node.Argument.Trim();
                AddLink(inlines, address, text.Length == 0 ? address : text);
                break;

            case "spoiler":
                inlines.Add(Spoiler(node.InnerText));
                break;

            default:
                // block tags inside a paragraph, or tags with nothing to show, contribute their text
                RenderInlines(node.Children, inlines, style);
                break;
        }
    }

    private static Run StyledRun(string text, InlineStyle style)
    {
        var run = new Run(text);

        if (style.Bold)
        {
            run.FontWeight = FontWeight.Bold;
        }

        if (style.Italic)
        {
            run.FontStyle = FontStyle.Italic;
        }

        if (style.Underline || style.Strike)
        {
            var decorations = new TextDecorationCollection();

            if (style.Underline)
            {
                decorations.AddRange(TextDecorations.Underline);
            }

            if (style.Strike)
            {
                decorations.AddRange(TextDecorations.Strikethrough);
            }

            run.TextDecorations = decorations;
        }

        return run;
    }

    /// <summary>
    /// A link in the page's brightest text that opens in the browser, followed by its host in small type the way Steam marks links leading off its site.
    /// An address that is not http stays plain text.
    /// </summary>
    private void AddLink(InlineCollection inlines, string address, string text)
    {
        if (!TryParseLink(address, out var uri))
        {
            inlines.Add(new Run(text));
            return;
        }

        var link = new TextBlock { Text = text, Cursor = new Cursor(StandardCursorType.Hand) };
        BindResource(link, TextBlock.ForegroundProperty, "ContrastBrush");
        link.PointerEntered += (_, _) => link.TextDecorations = TextDecorations.Underline;
        link.PointerExited += (_, _) => link.TextDecorations = null;
        link.PointerPressed += (_, _) => _ = TopLevel.GetTopLevel(this)?.Launcher.LaunchUriAsync(uri);

        inlines.Add(new InlineUIContainer(link) { BaselineAlignment = BaselineAlignment.Center });

        if (!text.Equals(address, StringComparison.OrdinalIgnoreCase))
        {
            inlines.Add(new Run($" [{uri.Host}]") { FontSize = 10, BaselineAlignment = BaselineAlignment.Center });
        }
    }

    /// <summary>Hidden text that shows while the pointer is over it, the way Steam's pages hide it.</summary>
    private static InlineUIContainer Spoiler(string text)
    {
        var content = new TextBlock { Text = text, Opacity = 0 };
        var cover = new Border { Child = content, Padding = new Thickness(4, 0), CornerRadius = new CornerRadius(2) };
        BindResource(cover, Border.BackgroundProperty, "ContrastBrush");

        cover.PointerEntered += (_, _) =>
        {
            content.Opacity = 1;
            BindResource(cover, Border.BackgroundProperty, "FieldBrush");
        };

        cover.PointerExited += (_, _) =>
        {
            content.Opacity = 0;
            BindResource(cover, Border.BackgroundProperty, "ContrastBrush");
        };

        return new InlineUIContainer(cover) { BaselineAlignment = BaselineAlignment.Center };
    }

    private static TextBlock Paragraph()
    {
        return new TextBlock { TextWrapping = TextWrapping.Wrap };
    }

    private static bool TryParseLink(string address, out Uri uri)
    {
        return Uri.TryCreate(address, UriKind.Absolute, out uri!) && uri.Scheme is "http" or "https";
    }

    /// <summary>Points a property at a theme brush, following the theme like a DynamicResource in markup would.</summary>
    private static void BindResource(Control control, AvaloniaProperty property, string key)
    {
        control.Bind(property, control.GetResourceObservable(key));
    }

    private static async Task LoadImageAsync(PreviewImage image, Uri uri)
    {
        try
        {
            image.Source = PreviewImage.Decode(await Http.GetByteArrayAsync(uri));
        }
        catch (Exception)
        {
            // a picture that can not be fetched or decoded stays blank, as it would on a page, whatever the decoder throws
        }
    }
}

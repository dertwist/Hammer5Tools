namespace Hammer5Tools.App.Services.Updates;

using System.Text.RegularExpressions;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.Documents;
using Avalonia.Media;

/// <summary>Compact native presentation of release headings, lists and inline Markdown.</summary>
internal sealed class ReleaseNotesView : StackPanel
{
    public ReleaseNotesView(string markdown, Action<Uri> openLink)
    {
        Spacing = 0;
        var code = false;
        var lines = new List<string>();
        var fenced = false;
        foreach (var line in markdown.Replace("\r", "", StringComparison.Ordinal).Split('\n'))
        {
            if (line.StartsWith("```", StringComparison.Ordinal)) fenced = !fenced;
            if (!fenced && lines.Count > 0 && IsParagraph(line) && IsParagraph(lines[^1])) lines[^1] += " " + line;
            else lines.Add(line);
        }
        foreach (var line in lines)
        {
            if (line.StartsWith("```", StringComparison.Ordinal))
            {
                code = !code;
                continue;
            }
            var heading = !code ? Regex.Match(line, @"^(#{1,6})\s+(.+)$") : Match.Empty;
            var text = heading.Success ? heading.Groups[2].Value : line;
            if (!code) text = Regex.Replace(text, @"^\s*[-*]\s+", "• ");
            var block = new SelectableTextBlock { TextWrapping = TextWrapping.Wrap, FontSize = 13.333, FontWeight = FontWeight.SemiBold };
            if (text.StartsWith("• ", StringComparison.Ordinal)) block.Margin = new Thickness(30, 0, 0, 0);
            if (heading.Success)
            {
                block.FontSize = heading.Groups[1].Length <= 2 ? 20 : 16;
                block.Margin = new Thickness(0, 12, 0, 12);
                block.FontWeight = FontWeight.Bold;
            }
            if (code)
            {
                block.FontFamily = FontFamily.Parse("Consolas, Courier New, monospace");
                block.Text = text;
            }
            else
            {
                var offset = 0;
                foreach (Match match in Regex.Matches(text, @"!?\[([^\]]*)\]\((https?://[^\s)]+)\)|\*\*(.+?)\*\*|`([^`]+)`"))
                {
                    block.Inlines!.Add(new Run(text[offset..match.Index]));
                    if (match.Groups[2].Success && Uri.TryCreate(match.Groups[2].Value, UriKind.Absolute, out var uri))
                    {
                        var label = new TextBlock
                        {
                            Text = match.Groups[1].Value is { Length: > 0 } title ? title : uri.Host,
                            TextDecorations = TextDecorations.Underline,
                            FontSize = 13.333,
                            FontWeight = FontWeight.SemiBold,
                        };
                        label.Bind(TextBlock.ForegroundProperty, label.GetResourceObservable("H5TAccentBrush"));
                        var link = new Button { Content = label, Padding = default, BorderThickness = default, Background = Brushes.Transparent, MinHeight = 0, Height = 17 };
                        link.Click += (_, _) => openLink(uri);
                        block.Inlines.Add(new InlineUIContainer(link) { BaselineAlignment = BaselineAlignment.TextBottom });
                    }
                    else
                    {
                        block.Inlines.Add(new Run(match.Groups[3].Success ? match.Groups[3].Value : match.Groups[4].Value)
                        {
                            FontWeight = match.Groups[3].Success ? FontWeight.Bold : FontWeight.Normal,
                        });
                    }
                    offset = match.Index + match.Length;
                }
                block.Inlines!.Add(new Run(text[offset..]));
            }
            Children.Add(block);
        }
    }
    private static bool IsParagraph(string line)
        => !string.IsNullOrWhiteSpace(line) && !Regex.IsMatch(line, @"^\s*(#{1,6}\s|[-*]\s|\d+\.\s|```)");
}

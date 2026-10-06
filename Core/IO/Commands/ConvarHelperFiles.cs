namespace Hammer5Tools.Core.IO.Commands;

using System.IO;
using System.Security;
using Hammer5Tools.Core.Commands;
using Microsoft.Extensions.Logging;
using Microsoft.Win32;

/// <summary>Reads Valve's shared INI pages and current-user Convar Helper registry pages.</summary>
public static class ConvarHelperFiles
{
    /// <summary>Loads command presets without modifying Valve's files or user settings.</summary>
    public static IReadOnlyList<ConsoleHelperCommand> Load(string? cs2Path, ILogger? logger = null)
    {
        var commands = new List<ConsoleHelperCommand>();
        if (!string.IsNullOrWhiteSpace(cs2Path))
        {
            var directory = Path.Combine(cs2Path, "game", "core", "tools", "convarhelper", "workshop");
            try
            {
                if (Directory.Exists(directory))
                {
                    foreach (var file in Directory.EnumerateFiles(directory, "*.ini").Order(StringComparer.OrdinalIgnoreCase))
                    {
                        try
                        {
                            var values = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
                            foreach (var line in File.ReadLines(file))
                            {
                                var separator = line.IndexOf('=');
                                if (separator > 0)
                                {
                                    values[line[..separator].Trim()] = line[(separator + 1)..].Trim().Trim('"').Replace("\\n", "\n").Replace("\\\"", "\"");
                                }
                            }
                            commands.AddRange(ReadPage(values, Path.GetFileNameWithoutExtension(file)));
                        }
                        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
                        {
                            logger?.LogWarning(ex, "Could not read Convar Helper page {Path}", file);
                        }
                    }
                }
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
            {
                logger?.LogWarning(ex, "Could not discover Convar Helper pages");
            }
        }

        if (OperatingSystem.IsWindows())
        {
            try
            {
                using var tabs = Registry.CurrentUser.OpenSubKey(@"Software\Valve\ConVarHelper\Tabs");
                if (tabs is not null)
                {
                    foreach (var name in tabs.GetSubKeyNames().Order(StringComparer.OrdinalIgnoreCase))
                    {
                        using var page = tabs.OpenSubKey(name);
                        if (page is null)
                        {
                            continue;
                        }
                        var values = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
                        foreach (var key in page.GetValueNames())
                        {
                            values[key] = page.GetValue(key)?.ToString() ?? string.Empty;
                        }
                        commands.AddRange(ReadPage(values, $"User page {name}"));
                    }
                }
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or SecurityException)
            {
                logger?.LogWarning(ex, "Could not read user Convar Helper pages");
            }
        }
        return commands.ToArray();
    }

    /// <summary>Decodes the button fields shared by INI and registry pages.</summary>
    public static IReadOnlyList<ConsoleHelperCommand> ReadPage(IReadOnlyDictionary<string, string> values, string source)
    {
        var commands = new List<ConsoleHelperCommand>();
        var width = values.TryGetValue("GridWidth", out var widthText) && int.TryParse(widthText, out var parsedWidth) ? Math.Clamp(parsedWidth, 1, 64) : 2;
        var height = values.TryGetValue("GridHeight", out var heightText) && int.TryParse(heightText, out var parsedHeight) ? Math.Clamp(parsedHeight, 1, 512) : 36;
        foreach (var (key, value) in values.OrderBy(pair => pair.Key, StringComparer.OrdinalIgnoreCase))
        {
            var fields = key.Split('-');
            if (fields.Length != 4 || fields[0] != "Button" || !int.TryParse(fields[1], out var column) || !int.TryParse(fields[2], out var row) ||
                column < 0 || column >= width || row < 0 || row >= height || string.IsNullOrWhiteSpace(value) || fields[3] is not ("Command" or "Label"))
            {
                continue;
            }
            var prefix = $"Button-{fields[1]}-{fields[2]}-";
            if (fields[3] == "Label" && values.ContainsKey(prefix + "Command"))
            {
                continue;
            }
            if (fields[3] == "Command" && values.TryGetValue(prefix + "Type", out var type) && type != "0")
            {
                continue;
            }
            values.TryGetValue(prefix + "AltButtonText", out var label);
            values.TryGetValue(prefix + "Description", out var description);
            commands.Add(new(fields[3] == "Label" ? value : label ?? value, fields[3] == "Label" ? string.Empty : value, description ?? string.Empty, source)
            {
                Column = column,
                Row = row,
                GridWidth = width,
                GridHeight = height
            });
        }
        return commands;
    }
}

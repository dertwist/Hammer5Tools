namespace Hammer5Tools.Core.Hotkeys;

using System.Reflection;
using System.Text.Json;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.IO;

/// <summary>
/// Provides catalog metadata, default bindings, macros, and CS2 keybinding synchronization.
/// </summary>
public static class HotkeyCatalogService
{
    private static readonly Dictionary<string, string> StemsMap = new(StringComparer.OrdinalIgnoreCase);
    private static readonly List<string> DisplayNamesList = [];
    private static readonly Dictionary<string, Dictionary<string, List<string>>> CatalogsMap = new(StringComparer.OrdinalIgnoreCase);
    private static readonly Dictionary<string, List<HotkeyBinding>> DefaultsMap = new(StringComparer.OrdinalIgnoreCase);
    private static readonly Dictionary<string, List<HotkeyMacro>> MacrosMap = new(StringComparer.OrdinalIgnoreCase);

    static HotkeyCatalogService()
    {
        LoadEmbeddedDefinitions();
    }

    public static IReadOnlyDictionary<string, string> Stems => StemsMap;

    public static IReadOnlyList<string> EditorDisplayNames => DisplayNamesList;

    public static string GetStem(string editorName)
    {
        if (StemsMap.TryGetValue(editorName, out var stem))
        {
            return stem;
        }

        return editorName.Trim().ToLowerInvariant().Replace(' ', '_');
    }

    public static IReadOnlyDictionary<string, List<string>> GetCatalog(string stem)
    {
        if (CatalogsMap.TryGetValue(stem, out var catalog))
        {
            return catalog;
        }

        return new Dictionary<string, List<string>>();
    }

    public static IReadOnlyList<HotkeyBinding> GetDefaults(string stem)
    {
        if (DefaultsMap.TryGetValue(stem, out var defaults))
        {
            return defaults;
        }

        return [];
    }

    public static IReadOnlyList<HotkeyMacro> GetMacros(string stem)
    {
        if (MacrosMap.TryGetValue(stem, out var macros))
        {
            return macros;
        }

        return [];
    }

    public static HotkeyDocument CreateDefaultDocument(string stem)
    {
        var doc = new HotkeyDocument();
        foreach (var macro in GetMacros(stem))
        {
            doc.Macros.Add(new HotkeyMacro(macro.Name, macro.Input));
        }

        foreach (var binding in GetDefaults(stem))
        {
            doc.Bindings.Add(new HotkeyBinding(binding.Context, binding.Command, binding.Input));
        }

        return doc;
    }

    public static (Dictionary<string, List<string>> Catalog, Dictionary<(string Context, string Command), string> Defaults)
        ReadInstalledKeybindings(string? cs2Path, string stem)
    {
        var catalog = new Dictionary<string, List<string>>(StringComparer.OrdinalIgnoreCase);
        var defaults = new Dictionary<(string Context, string Command), string>();

        if (string.IsNullOrWhiteSpace(cs2Path))
        {
            return (catalog, defaults);
        }

        var keybindingsPath = Cs2Paths.GetKeybindingsPath(cs2Path);
        var file = Path.Combine(keybindingsPath, $"{stem}_key_bindings.txt");
        if (!File.Exists(file))
        {
            return (catalog, defaults);
        }

        try
        {
            var doc = HotkeyDocument.Load(file);
            foreach (var binding in doc.Bindings)
            {
                if (string.IsNullOrWhiteSpace(binding.Context) || string.IsNullOrWhiteSpace(binding.Command))
                {
                    continue;
                }

                if (!catalog.TryGetValue(binding.Context, out var commands))
                {
                    commands = [];
                    catalog[binding.Context] = commands;
                }

                if (!commands.Contains(binding.Command, StringComparer.OrdinalIgnoreCase))
                {
                    commands.Add(binding.Command);
                }

                if (!string.IsNullOrWhiteSpace(binding.Input))
                {
                    defaults[(binding.Context, binding.Command)] = binding.Input;
                }
            }
        }
        catch
        {
            // Fallback gracefully on parsing issues
        }

        return (catalog, defaults);
    }

    public static void PopulateEditor(HotkeyDocument document, string stem, string? cs2Path = null)
    {
        var (installedCatalog, installedDefaults) = ReadInstalledKeybindings(cs2Path, stem);

        // Build merged defaults dictionary: hardcoded defaults overridden by installed CS2 defaults
        var mergedDefaults = new Dictionary<(string Context, string Command), string>();
        foreach (var binding in GetDefaults(stem))
        {
            if (!string.IsNullOrWhiteSpace(binding.Context) && !string.IsNullOrWhiteSpace(binding.Command))
            {
                mergedDefaults[(binding.Context, binding.Command)] = binding.Input;
            }
        }

        foreach (var (key, input) in installedDefaults)
        {
            mergedDefaults[key] = input;
        }

        // Build merged catalog: hardcoded catalog + installed catalog
        var mergedCatalog = new Dictionary<string, List<string>>(StringComparer.OrdinalIgnoreCase);
        var hardcodedCatalog = GetCatalog(stem);

        foreach (var (ctx, cmds) in hardcodedCatalog)
        {
            if (!mergedCatalog.TryGetValue(ctx, out var targetCmds))
            {
                targetCmds = [];
                mergedCatalog[ctx] = targetCmds;
            }

            foreach (var cmd in cmds)
            {
                if (!targetCmds.Contains(cmd, StringComparer.OrdinalIgnoreCase))
                {
                    targetCmds.Add(cmd);
                }
            }
        }

        foreach (var (ctx, cmds) in installedCatalog)
        {
            if (!mergedCatalog.TryGetValue(ctx, out var targetCmds))
            {
                targetCmds = [];
                mergedCatalog[ctx] = targetCmds;
            }

            foreach (var cmd in cmds)
            {
                if (!targetCmds.Contains(cmd, StringComparer.OrdinalIgnoreCase))
                {
                    targetCmds.Add(cmd);
                }
            }
        }

        // Ensure missing commands are populated with their defaults
        foreach (var (ctx, commands) in mergedCatalog)
        {
            foreach (var cmd in commands)
            {
                var existing = document.FindBinding(ctx, cmd);
                if (existing is null)
                {
                    var defaultInput = mergedDefaults.TryGetValue((ctx, cmd), out var input) ? input : string.Empty;
                    var binding = document.EnsureBinding(ctx, cmd);
                    if (!string.IsNullOrEmpty(defaultInput))
                    {
                        binding.Input = defaultInput;
                    }
                }
            }
        }

        // Also ensure default macros if document has none
        if (document.Macros.Count == 0)
        {
            foreach (var macro in GetMacros(stem))
            {
                document.Macros.Add(new HotkeyMacro(macro.Name, macro.Input));
            }
        }
    }

    public static string GetPrimaryPresetDirectory(string stem)
    {
        var localUserData = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Hammer5Tools", "userdata", "Hotkeys", stem);
        if (!Directory.Exists(localUserData))
        {
            Directory.CreateDirectory(localUserData);
        }

        return localUserData;
    }

    public static IReadOnlyList<string> GetPresetDirectories(string stem)
    {
        var dirs = new List<string>();

        var localUserData = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Hammer5Tools", "userdata", "Hotkeys", stem);
        if (Directory.Exists(localUserData)) dirs.Add(localUserData);

        var appData = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "Hammer5Tools", "Hotkeys", stem);
        if (Directory.Exists(appData) && !dirs.Contains(appData, StringComparer.OrdinalIgnoreCase)) dirs.Add(appData);

        try
        {
            var bundled = Path.Combine(BundledPresetFiles.GetDirectory("hotkeys"), stem);
            if (Directory.Exists(bundled) && !dirs.Contains(bundled, StringComparer.OrdinalIgnoreCase)) dirs.Add(bundled);
        }
        catch
        {
            // Ignore if bundled presets root is not yet extracted
        }

        if (dirs.Count == 0)
        {
            dirs.Add(GetPrimaryPresetDirectory(stem));
        }

        return dirs;
    }

    private static void LoadEmbeddedDefinitions()
    {
        var assembly = typeof(HotkeyCatalogService).Assembly;
        using var stream = assembly.GetManifestResourceStream("HotkeyDefinitions");
        if (stream is null)
        {
            return;
        }

        using var jsonDoc = JsonDocument.Parse(stream);
        var root = jsonDoc.RootElement;

        if (root.TryGetProperty("stems", out var stemsElem))
        {
            foreach (var prop in stemsElem.EnumerateObject())
            {
                StemsMap[prop.Name] = prop.Value.GetString() ?? prop.Name.ToLowerInvariant();
                DisplayNamesList.Add(prop.Name);
            }
        }

        if (root.TryGetProperty("catalogs", out var catalogsElem))
        {
            foreach (var stemProp in catalogsElem.EnumerateObject())
            {
                var stemName = stemProp.Name;
                var contextDict = new Dictionary<string, List<string>>(StringComparer.OrdinalIgnoreCase);

                foreach (var ctxProp in stemProp.Value.EnumerateObject())
                {
                    var cmdList = new List<string>();
                    foreach (var item in ctxProp.Value.EnumerateArray())
                    {
                        var cmd = item.GetString();
                        if (!string.IsNullOrEmpty(cmd))
                        {
                            cmdList.Add(cmd);
                        }
                    }

                    contextDict[ctxProp.Name] = cmdList;
                }

                CatalogsMap[stemName] = contextDict;
            }
        }

        if (root.TryGetProperty("defaults", out var defaultsElem))
        {
            foreach (var stemProp in defaultsElem.EnumerateObject())
            {
                var stemName = stemProp.Name;
                var bindingList = new List<HotkeyBinding>();

                if (stemProp.Value.TryGetProperty("m_Bindings", out var bindingsArr))
                {
                    foreach (var item in bindingsArr.EnumerateArray())
                    {
                        var ctx = item.TryGetProperty("m_Context", out var c) ? c.GetString()
                            : item.TryGetProperty("m_COntext", out var c2) ? c2.GetString() : string.Empty;
                        var cmd = item.TryGetProperty("m_Command", out var cm) ? cm.GetString() : string.Empty;
                        var inp = item.TryGetProperty("m_Input", out var i) ? i.GetString() : string.Empty;

                        if (!string.IsNullOrEmpty(cmd))
                        {
                            bindingList.Add(new HotkeyBinding(ctx ?? string.Empty, cmd, inp ?? string.Empty));
                        }
                    }
                }

                DefaultsMap[stemName] = bindingList;
            }
        }

        if (root.TryGetProperty("macros", out var macrosElem))
        {
            foreach (var stemProp in macrosElem.EnumerateObject())
            {
                var stemName = stemProp.Name;
                var macroList = new List<HotkeyMacro>();

                if (stemProp.Value.TryGetProperty("m_InputMacros", out var macrosArr))
                {
                    foreach (var item in macrosArr.EnumerateArray())
                    {
                        var name = item.TryGetProperty("m_Name", out var n) ? n.GetString() : string.Empty;
                        var input = item.TryGetProperty("m_Input", out var i) ? i.GetString() : string.Empty;

                        if (!string.IsNullOrEmpty(name))
                        {
                            macroList.Add(new HotkeyMacro(name, input ?? string.Empty));
                        }
                    }
                }

                MacrosMap[stemName] = macroList;
            }
        }
    }
}

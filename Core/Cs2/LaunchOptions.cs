namespace Hammer5Tools.Core.Cs2;

using System.Text.RegularExpressions;

/// <summary>Editable Workshop Tools launch switches shared by Settings and the launcher.</summary>
public sealed class LaunchOptions
{
    public bool OpenTools { get; set; } = true;
    public bool OpenMap { get; set; } = true;
    public bool Steam { get; set; } = true;
    public bool Retail { get; set; } = true;
    public bool GpuRayTracing { get; set; } = true;
    public bool Insecure { get; set; } = true;
    public bool NoCustomerMachine { get; set; }

    /// <summary>Builds arguments without splitting or deduplicating user-supplied flag values.</summary>
    public string BuildArguments(string? addonName, string customArgs, string? additionalArgs = null, bool ncmMode = false)
    {
        var args = new List<string>();
        if (!string.IsNullOrWhiteSpace(addonName)) args.Add($"-addon {Quote(addonName)}");
        if (OpenMap && !string.IsNullOrWhiteSpace(addonName)) args.Add($"-tool hammer -asset {Quote($"maps/{addonName}.vmap")}");
        if (OpenTools) args.Add("-tools");
        if (Steam) args.Add("-steam");
        if (Retail) args.Add("-retail");
        if (GpuRayTracing) args.Add("-gpuraytracing");
        if (Insecure) args.Add("-insecure");
        if (NoCustomerMachine || ncmMode) args.Add("-nocustomermachine");
        var custom = customArgs.Replace("addon_name", addonName ?? string.Empty, StringComparison.Ordinal);
        if (!string.IsNullOrWhiteSpace(custom)) args.Add(custom.Trim());
        if (!string.IsNullOrWhiteSpace(additionalArgs)) args.Add(additionalArgs.Trim());
        args.Add($"-concommandpipe {IO.Cs2.Cs2Launcher.PipeIn},{IO.Cs2.Cs2Launcher.PipeOut}");
        args.Add($"-con_logfile {IO.Cs2.Cs2Launcher.LogFileName}");
        args.Add("-disable_workshop_command_filtering");
        return string.Join(" ", args);
    }

    private static string Quote(string value) => value.Any(char.IsWhiteSpace)
        ? $"\"{value.Replace("\"", "\\\"", StringComparison.Ordinal)}\"" : value;

    /// <summary>Extracts legacy checkboxes and leaves unknown arguments intact.</summary>
    public static (LaunchOptions Options, string CustomArgs) FromLegacy(string arguments)
    {
        var options = new LaunchOptions
        {
            OpenTools = false,
            OpenMap = false,
            Steam = false,
            Retail = false,
            GpuRayTracing = false,
            Insecure = false,
        };
        var custom = arguments;
        void Take(string pattern, Action apply)
        {
            if (!Regex.IsMatch(custom, pattern, RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)) return;
            custom = Regex.Replace(custom, pattern, "", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
            apply();
        }
        Take(@"(?<!\S)-tool\s+hammer\s+-asset\s+maps/addon_name\.vmap(?=\s|$)", () => options.OpenMap = true);
        Take(@"(?<!\S)-addon\s+addon_name(?=\s|$)", () => { });
        Take(@"(?<!\S)-tools(?=\s|$)", () => options.OpenTools = true);
        Take(@"(?<!\S)-steam(?=\s|$)", () => options.Steam = true);
        Take(@"(?<!\S)-retail(?=\s|$)", () => options.Retail = true);
        Take(@"(?<!\S)-gpuraytracing(?=\s|$)", () => options.GpuRayTracing = true);
        Take(@"(?<!\S)-(?:insecure|noinsecru)(?=\s|$)", () => options.Insecure = true);
        Take(@"(?<!\S)-nocustomermachine(?=\s|$)", () => options.NoCustomerMachine = true);
        return (options, custom.Trim());
    }
}

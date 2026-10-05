namespace Hammer5Tools.Infrastructure.Workshop;

using CS2WorkshopManager;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.Workshop;

/// <summary>
/// Uses CS2 Workshop Manager for packing rules, dependency analysis and chunked VPK output.
/// </summary>
public class WorkshopManagerService : IWorkshopManagerService
{
    private readonly ICs2Locator Cs2Locator;

    public WorkshopManagerService(ICs2Locator cs2Locator)
    {
        Cs2Locator = cs2Locator;
    }

    public async Task<IReadOnlyList<string>> AnalyzeAddonFilesAsync(string addonName, bool excludeUnused, CancellationToken cancellationToken = default)
    {
        return await Task.Run<IReadOnlyList<string>>(() =>
        {
            cancellationToken.ThrowIfCancellationRequested();
            var manager = CreateManager();
            var addonPath = GetAddonPath(manager, addonName);
            var rules = GetPackingRules(manager, addonName, excludeUnused);
            return AddonPackager.CollectFiles(addonPath, manager.GameInfoPath, rules)
                .Select(file => AddonPackager.GetRelativePath(addonPath, file.FullName)).ToList();
        }, cancellationToken);
    }

    public async Task<bool> BuildWorkshopPackageAsync(WorkshopPackConfig config, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(config);
        return await Task.Run(() =>
        {
            cancellationToken.ThrowIfCancellationRequested();
            var manager = CreateManager();
            var addonPath = GetAddonPath(manager, config.AddonName);
            var output = Path.GetFullPath(config.OutputVpkPath);
            // Packing into the input tree would include old packages in the next upload.
            if (Path.GetRelativePath(addonPath, output) is var relative &&
                !relative.StartsWith($"..{Path.DirectorySeparatorChar}", StringComparison.Ordinal) && !Path.IsPathRooted(relative))
            {
                throw new ArgumentException("Choose an output directory outside the compiled addon.", nameof(config));
            }

            if (!output.EndsWith("_dir.vpk", StringComparison.OrdinalIgnoreCase))
            {
                throw new ArgumentException("The package filename must end with _dir.vpk.", nameof(config));
            }

            Directory.CreateDirectory(Path.GetDirectoryName(output)!);
            var rules = GetPackingRules(manager, config.AddonName, config.ExcludeUnusedContent);
            AddonPackager.Pack(addonPath, manager.GameInfoPath, output, rules);
            return File.Exists(output);
        }, cancellationToken);
    }

    private WorkshopManager CreateManager()
    {
        return new WorkshopManager(Cs2Locator.FindCs2Path() ?? throw new InvalidOperationException("CS2 installation not found."));
    }

    private static string GetAddonPath(WorkshopManager manager, string addonName)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(addonName);
        if (addonName is "." or ".." || addonName.IndexOfAny(['/', '\\']) >= 0 || Path.IsPathRooted(addonName))
        {
            throw new ArgumentException("Select an addon folder name.", nameof(addonName));
        }

        var path = Path.Combine(manager.AddonsRoot, addonName);
        if (!Directory.Exists(path))
        {
            throw new DirectoryNotFoundException($"Compiled addon not found: {path}");
        }

        return path;
    }

    private static AddonRules GetPackingRules(WorkshopManager manager, string addonName, bool excludeUnused)
    {
        var own = manager.LoadRules(addonName);
        var rules = CS2WorkshopManager.AppSettings.Load().GlobalRules.Then(own);
        if (!excludeUnused)
        {
            return rules;
        }

        var unused = manager.BuildUnusedRules(addonName, own.ExcludeUnused, recrawl: true);
        if (!unused.Found.HasCompiledMap)
        {
            throw new InvalidOperationException("Compile a map before excluding unused content, or turn that option off.");
        }

        return rules.Then(unused.Rules);
    }
}

namespace Hammer5Tools.Core.Workshop;

public interface IWorkshopManagerService
{
    Task<IReadOnlyList<string>> AnalyzeAddonFilesAsync(string addonName, bool excludeUnused, CancellationToken cancellationToken = default);

    Task<bool> BuildWorkshopPackageAsync(WorkshopPackConfig config, CancellationToken cancellationToken = default);
}

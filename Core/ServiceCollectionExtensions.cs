namespace Hammer5Tools.Core;

using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.Commands;
using Hammer5Tools.Core.Compiler;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.GitSync;
using Hammer5Tools.Core.IO.Addons;
using Hammer5Tools.Core.IO.Commands;
using Hammer5Tools.Core.IO.Compiler;
using Hammer5Tools.Core.IO.Cs2;
using Hammer5Tools.Core.IO.GitSync;
using Hammer5Tools.Core.IO.LoadingScreens;
using Hammer5Tools.Core.IO.MapBuilder;
using Hammer5Tools.Core.IO.NavMesh;
using Hammer5Tools.Core.IO.Settings;
using Hammer5Tools.Core.IO.SoundEvents;
using Hammer5Tools.Core.IO.Workshop;
using Hammer5Tools.Core.LoadingScreens;
using Hammer5Tools.Core.MapBuilder;
using Hammer5Tools.Core.NavMesh;
using Hammer5Tools.Core.Settings;
using Hammer5Tools.Core.SoundEvents;
using Hammer5Tools.Core.Undo;
using Hammer5Tools.Core.Warnings;
using Hammer5Tools.Core.Workshop;
using Microsoft.Extensions.DependencyInjection;

public static class ServiceCollectionExtensions
{
    /// <summary>Registers shared domain, filesystem and process services for GUI and CLI hosts.</summary>
    public static IServiceCollection AddHammer5ToolsCore(this IServiceCollection services)
    {
        services.AddSingleton<ISettingsService, Kv3SettingsService>();
        services.AddSingleton<IWarningService, WarningService>();
        services.AddSingleton<ICs2Locator, Cs2Locator>();
        services.AddSingleton<IAddonService, AddonService>();
        services.AddSingleton<ICs2Launcher, Cs2Launcher>();
        services.AddSingleton<ICommandService, CommandService>();
        services.AddSingleton<IResourceCompiler, ResourceCompiler>();
        services.AddSingleton<Vrad3CacheService>();
        services.AddTransient<IUndoService, UndoService>();

        services.AddSingleton<ILoadingScreenService, LoadingScreenService>();
        services.AddSingleton<VpkSoundExplorer>();
        services.AddSingleton<ISoundEventService, SoundEventService>();
        services.AddSingleton<INavMeshRadarService, NavMeshRadarService>();
        services.AddSingleton<IMapBuilderService, MapBuilderService>();
        services.AddSingleton<ISystemUsageService, SystemUsageService>();
        services.AddSingleton<IWorkshopManagerService, WorkshopManagerService>();
        services.AddSingleton<IAssetToolsService, AssetToolsService>();
        services.AddSingleton<IGitSyncService, GitSyncService>();

        return services;
    }
}

namespace Hammer5Tools.Infrastructure;

using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.Commands;
using Hammer5Tools.Core.Compiler;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.Settings;
using Hammer5Tools.Core.Undo;
using Hammer5Tools.Infrastructure.Addons;
using Hammer5Tools.Infrastructure.Commands;
using Hammer5Tools.Infrastructure.Compiler;
using Hammer5Tools.Infrastructure.Cs2;
using Hammer5Tools.Infrastructure.Lifecycle;
using Hammer5Tools.Infrastructure.Settings;
using Hammer5Tools.Infrastructure.Updates;
using Microsoft.Extensions.DependencyInjection;

public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddInfrastructure(this IServiceCollection services)
    {
        services.AddSingleton<ISettingsService, JsonSettingsService>();
        services.AddSingleton<ICs2Locator, Cs2Locator>();
        services.AddSingleton<IAddonService, AddonService>();
        services.AddSingleton<ICs2Launcher, Cs2Launcher>();
        services.AddSingleton<ICommandService, CommandService>();
        services.AddSingleton<IResourceCompiler, ResourceCompiler>();
        services.AddSingleton<Vrad3CacheService>();
        services.AddSingleton<SingleInstanceGuard>();
        services.AddSingleton<IUpdateService, VelopackUpdateService>();
        services.AddTransient<IUndoService, UndoService>();
        return services;
    }
}

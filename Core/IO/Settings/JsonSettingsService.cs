namespace Hammer5Tools.Core.IO.Settings;

using Microsoft.Extensions.Logging;

/// <summary>
/// Legacy settings service alias, inherits from <see cref="Kv3SettingsService"/> for backwards compatibility.
/// </summary>
public class JsonSettingsService : Kv3SettingsService
{
    public JsonSettingsService(string? customSettingsPath = null, ILogger<JsonSettingsService>? logger = null)
        : base(customSettingsPath, null)
    {
    }
}

namespace Hammer5Tools.Core.Settings;

using System.Text.Json.Serialization;

/// <summary>
/// Source-generated JSON serializer context for settings.
/// </summary>
[JsonSourceGenerationOptions(
    WriteIndented = true,
    PropertyNamingPolicy = JsonKnownNamingPolicy.CamelCase,
    NumberHandling = JsonNumberHandling.AllowNamedFloatingPointLiterals)]
[JsonSerializable(typeof(AppSettings))]
public partial class SettingsJsonContext : JsonSerializerContext
{
}

namespace Hammer5Tools.Infrastructure.SoundEvents;

using Hammer5Tools.Core.SoundEvents;
using Microsoft.Extensions.Logging;

public class SoundEventService : ISoundEventService
{
    private readonly VpkSoundExplorer VpkExplorer;
    private readonly ILogger<SoundEventService> Logger;

    public SoundEventService(VpkSoundExplorer vpkExplorer, ILogger<SoundEventService> logger)
    {
        VpkExplorer = vpkExplorer;
        Logger = logger;
    }

    public async Task<SoundEventDocument> LoadDocumentAsync(string vsndevtsPath, CancellationToken cancellationToken = default)
    {
        if (!File.Exists(vsndevtsPath))
        {
            return new SoundEventDocument();
        }

        try
        {
            var content = await File.ReadAllTextAsync(vsndevtsPath, cancellationToken);
            using var stream = new MemoryStream(System.Text.Encoding.UTF8.GetBytes(content));
            ValveKeyValue.KVSerializer.Create(ValveKeyValue.KVSerializationFormat.KeyValues3Text).Deserialize(stream);
            return SoundEventDocument.Parse(content);
        }
        catch (Exception ex)
        {
            Logger.LogError(ex, "Failed to load SoundEvent document from {Path}", vsndevtsPath);
            throw;
        }
    }

    public async Task SaveDocumentAsync(string vsndevtsPath, SoundEventDocument document, CancellationToken cancellationToken = default)
    {
        try
        {
            var dir = Path.GetDirectoryName(vsndevtsPath);
            if (!string.IsNullOrEmpty(dir))
            {
                Directory.CreateDirectory(dir);
            }

            var text = document.Serialize();
            cancellationToken.ThrowIfCancellationRequested();
            Hammer5Tools.Core.Formats.DocumentFile.Write(vsndevtsPath, text);
            await Task.CompletedTask;
            Logger.LogInformation("Saved SoundEvent document to {Path}", vsndevtsPath);
        }
        catch (Exception ex)
        {
            Logger.LogError(ex, "Failed to save SoundEvent document to {Path}", vsndevtsPath);
            throw;
        }
    }

    public IReadOnlyList<string> GetPredefinedTemplates() =>
    [
        "Spatial 3D Sound (csgo_mega)",
        "Ambient Loop (csgo_ambient)",
        "UI 2D Sound (csgo_ui)",
        "Music Track (csgo_music)",
    ];

    public SoundEvent CreateFromTemplate(string eventName, string templateName)
    {
        var soundEvent = new SoundEvent(eventName);

        if (templateName.Contains("csgo_ambient", StringComparison.OrdinalIgnoreCase))
        {
            soundEvent.Type = "csgo_ambient";
            soundEvent.Properties.Add(new SoundProperty("vsnd_files", "[ \"sounds/ambient/wind.vsnd\" ]"));
            soundEvent.Properties.Add(new SoundProperty("volume", "0.6"));
            soundEvent.Properties.Add(new SoundProperty("volume_falloff_min", "200.0"));
            soundEvent.Properties.Add(new SoundProperty("volume_falloff_max", "1500.0"));
        }
        else if (templateName.Contains("csgo_ui", StringComparison.OrdinalIgnoreCase))
        {
            soundEvent.Type = "csgo_ui";
            soundEvent.Properties.Add(new SoundProperty("vsnd_files", "[ \"sounds/ui/button_click.vsnd\" ]"));
            soundEvent.Properties.Add(new SoundProperty("volume", "1.0"));
        }
        else if (templateName.Contains("csgo_music", StringComparison.OrdinalIgnoreCase))
        {
            soundEvent.Type = "csgo_music";
            soundEvent.Properties.Add(new SoundProperty("vsnd_files", "[ \"sounds/music/mainmenu.vsnd\" ]"));
            soundEvent.Properties.Add(new SoundProperty("volume", "0.75"));
        }
        else
        {
            soundEvent.Type = "csgo_mega";
            soundEvent.Properties.Add(new SoundProperty("vsnd_files", "[ \"sounds/weapons/fire.vsnd\" ]"));
            soundEvent.Properties.Add(new SoundProperty("volume", "0.85"));
            soundEvent.Properties.Add(new SoundProperty("volume_falloff_min", "150.0"));
            soundEvent.Properties.Add(new SoundProperty("volume_falloff_max", "2500.0"));
            soundEvent.Properties.Add(new SoundProperty("pitch", "1.0"));
        }

        return soundEvent;
    }

    public Task<IReadOnlyList<string>> QueryVpkSoundsAsync(string? filter = null, CancellationToken cancellationToken = default)
    {
        return VpkExplorer.EnumerateVpkSoundsAsync(filter, cancellationToken);
    }
}

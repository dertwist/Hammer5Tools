namespace Hammer5Tools.Core.IO.SoundEvents;

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

    public IReadOnlyList<SoundAudioFile> GetAddonSounds(string contentRoot)
    {
        var root = Path.Combine(contentRoot, "sounds");
        if (!Directory.Exists(root)) return [];
        return Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories)
            .Where(path => Path.GetExtension(path).ToLowerInvariant() is ".wav" or ".mp3" or ".vsnd" or ".vsnd_c")
            .Order(StringComparer.OrdinalIgnoreCase)
            .Select(path => new SoundAudioFile(Path.GetRelativePath(contentRoot, path), new FileInfo(path).Length)).ToArray();
    }

    public void OpenTemplateDirectory()
    {
        var root = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Hammer5Tools", "userdata", "SoundEventEditor", "Presets");
        Directory.CreateDirectory(root);
        using var process = System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(root) { UseShellExecute = true });
    }

    private static Dictionary<string, string> DiscoverTemplates()
    {
        var templates = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        string[] roots = [
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Hammer5Tools", "userdata", "SoundEventEditor", "Presets"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "Hammer5Tools", "SoundEventEditor", "Presets"),
            BundledPresetFiles.GetDirectory("soundeventeditor"),
            Path.Combine(AppContext.BaseDirectory, "Presets", "SoundEventEditor", "Presets")];
        foreach (var root in roots.Where(Directory.Exists))
        {
            foreach (var path in Directory.EnumerateFiles(root, "*.kv3"))
            {
                templates.TryAdd(Path.GetFileNameWithoutExtension(path), path);
            }
        }
        return templates;
    }

    public IReadOnlyList<string> GetPredefinedTemplates() => DiscoverTemplates().Keys.Order(StringComparer.OrdinalIgnoreCase).ToArray();

    public Task SaveTemplateAsync(string path, SoundEvent soundEvent, CancellationToken cancellationToken = default)
    {
        var document = new SoundEventDocument();
        var template = new SoundEvent("template", soundEvent.Type) { HasExplicitType = soundEvent.HasExplicitType };
        foreach (var property in soundEvent.Properties) template.Properties.Add(new SoundProperty(property.Key, property.Value));
        document.Events.Add(template);
        var text = document.Serialize();
        var start = text.IndexOf('=', text.IndexOf("-->", StringComparison.Ordinal) + 3) + 1;
        text = SoundEventDocument.DefaultHeader + "\n" + text[start..text.LastIndexOf('}')].Trim() + "\n";
        cancellationToken.ThrowIfCancellationRequested();
        Hammer5Tools.Core.Formats.DocumentFile.Write(path, text);
        return Task.CompletedTask;
    }

    public SoundEvent CreateFromTemplate(string eventName, string templateName)
    {
        if (DiscoverTemplates().TryGetValue(templateName, out var path))
        {
            var text = File.ReadAllText(path);
            var headerEnd = text.IndexOf("-->", StringComparison.Ordinal) + 3;
            var document = SoundEventDocument.Parse(SoundEventDocument.DefaultHeader + "\n{\n\"template\" = " + text[headerEnd..] + "\n}");
            var template = document.Events.Single();
            template.Name = eventName;
            return template;
        }
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

    public Task<IReadOnlyList<SoundEvent>> QueryInternalEventsAsync(CancellationToken cancellationToken = default)
        => VpkExplorer.ReadInternalEventsAsync(cancellationToken);

    public Task<IReadOnlyList<string>> QueryVpkSoundsAsync(string? filter = null, CancellationToken cancellationToken = default)
    {
        return VpkExplorer.EnumerateVpkSoundsAsync(filter, cancellationToken);
    }
}

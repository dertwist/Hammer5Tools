namespace Hammer5Tools.Core.SoundEvents;

public interface ISoundEventService
{
    Task<SoundEventDocument> LoadDocumentAsync(string vsndevtsPath, CancellationToken cancellationToken = default);

    Task SaveDocumentAsync(string vsndevtsPath, SoundEventDocument document, CancellationToken cancellationToken = default);

    IReadOnlyList<string> GetPredefinedTemplates();

    /// <summary>Lists loose audio sources under the document's addon content root.</summary>
    IReadOnlyList<SoundAudioFile> GetAddonSounds(string contentRoot) => [];

    /// <summary>Opens the user template directory in the platform file browser.</summary>
    void OpenTemplateDirectory() => throw new NotSupportedException("Opening template folders is unavailable.");

    SoundEvent CreateFromTemplate(string eventName, string templateName);

    /// <summary>Saves a standalone KV3 property template with validation and a retained backup.</summary>
    Task SaveTemplateAsync(string path, SoundEvent soundEvent, CancellationToken cancellationToken = default)
        => throw new NotSupportedException("Saving templates is unavailable.");

    /// <summary>Loads built-in sound events from loose and compiled game resources.</summary>
    Task<IReadOnlyList<SoundEvent>> QueryInternalEventsAsync(CancellationToken cancellationToken = default)
        => Task.FromResult<IReadOnlyList<SoundEvent>>([]);

    Task<IReadOnlyList<string>> QueryVpkSoundsAsync(string? filter = null, CancellationToken cancellationToken = default);
}

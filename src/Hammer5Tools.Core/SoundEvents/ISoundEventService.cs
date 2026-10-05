namespace Hammer5Tools.Core.SoundEvents;

public interface ISoundEventService
{
    Task<SoundEventDocument> LoadDocumentAsync(string vsndevtsPath, CancellationToken cancellationToken = default);

    Task SaveDocumentAsync(string vsndevtsPath, SoundEventDocument document, CancellationToken cancellationToken = default);

    IReadOnlyList<string> GetPredefinedTemplates();

    SoundEvent CreateFromTemplate(string eventName, string templateName);

    Task<IReadOnlyList<string>> QueryVpkSoundsAsync(string? filter = null, CancellationToken cancellationToken = default);
}

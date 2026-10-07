namespace Hammer5Tools.Core.SoundEvents;

/// <summary>An addon audio source with its content-relative path and on-disk size.</summary>
public sealed record SoundAudioFile(string Path, long Size);

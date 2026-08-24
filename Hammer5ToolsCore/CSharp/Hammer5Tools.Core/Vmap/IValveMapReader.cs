namespace Hammer5Tools.Core.Vmap;

/// <summary>
/// Reads an uncompiled Valve map into a UI-neutral document model.
/// </summary>
public interface IValveMapReader
{
    /// <summary>
    /// Reads the map at the specified path without modifying it.
    /// </summary>
    ValveMapDocument Read(string path);
}

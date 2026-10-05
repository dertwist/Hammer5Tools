namespace Hammer5Tools.Core.Addons;

/// <summary>
/// Service managing CS2 addons discovery, active addon selection, and lifecycle.
/// </summary>
public interface IAddonService
{
    /// <summary>
    /// Gets all currently discovered addons.
    /// </summary>
    IReadOnlyList<Addon> Addons { get; }

    /// <summary>
    /// Gets the currently active addon, if any.
    /// </summary>
    Addon? ActiveAddon { get; }

    /// <summary>
    /// Event raised when the collection of addons changes.
    /// </summary>
    event EventHandler<IReadOnlyList<Addon>>? AddonsChanged;

    /// <summary>
    /// Event raised when the active addon changes.
    /// </summary>
    event EventHandler<Addon?>? ActiveAddonChanged;

    /// <summary>
    /// Refreshes the list of addons from the CS2 directory.
    /// </summary>
    void RefreshAddons();

    /// <summary>
    /// Sets the active addon by name.
    /// </summary>
    bool SetActiveAddon(string? addonName);

    /// <summary>
    /// Creates a new addon with standard directory structure.
    /// </summary>
    Addon CreateAddon(string addonName);

    /// <summary>
    /// Deletes an addon's content and game directories.
    /// </summary>
    bool DeleteAddon(string addonName);
}

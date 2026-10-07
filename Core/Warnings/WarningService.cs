namespace Hammer5Tools.Core.Warnings;

/// <summary>
/// Thread-safe default implementation of <see cref="IWarningService"/>.
/// </summary>
public sealed class WarningService : IWarningService
{
    private readonly Lock syncLock = new();
    private readonly List<AppWarning> warnings = [];

    /// <inheritdoc/>
    public IReadOnlyList<AppWarning> Warnings
    {
        get
        {
            lock (syncLock)
            {
                return [.. warnings];
            }
        }
    }

    /// <inheritdoc/>
    public bool HasWarnings
    {
        get
        {
            lock (syncLock)
            {
                return warnings.Count > 0;
            }
        }
    }

    /// <inheritdoc/>
    public AppWarning? PrimaryWarning
    {
        get
        {
            lock (syncLock)
            {
                return warnings.FirstOrDefault();
            }
        }
    }

    /// <inheritdoc/>
    public event EventHandler? WarningsChanged;

    /// <inheritdoc/>
    public void SetWarning(AppWarning warning)
    {
        ArgumentNullException.ThrowIfNull(warning);
        var changed = false;
        lock (syncLock)
        {
            var index = warnings.FindIndex(w => string.Equals(w.Id, warning.Id, StringComparison.OrdinalIgnoreCase));
            if (index >= 0)
            {
                if (warnings[index] != warning)
                {
                    warnings[index] = warning;
                    changed = true;
                }
            }
            else
            {
                warnings.Add(warning);
                changed = true;
            }
        }

        if (changed)
        {
            WarningsChanged?.Invoke(this, EventArgs.Empty);
        }
    }

    /// <inheritdoc/>
    public bool RemoveWarning(string id)
    {
        if (string.IsNullOrWhiteSpace(id)) return false;
        var removed = false;
        lock (syncLock)
        {
            var index = warnings.FindIndex(w => string.Equals(w.Id, id, StringComparison.OrdinalIgnoreCase));
            if (index >= 0)
            {
                warnings.RemoveAt(index);
                removed = true;
            }
        }

        if (removed)
        {
            WarningsChanged?.Invoke(this, EventArgs.Empty);
        }

        return removed;
    }

    /// <inheritdoc/>
    public void Clear()
    {
        var changed = false;
        lock (syncLock)
        {
            if (warnings.Count > 0)
            {
                warnings.Clear();
                changed = true;
            }
        }

        if (changed)
        {
            WarningsChanged?.Invoke(this, EventArgs.Empty);
        }
    }
}

namespace SourcePorter.Core.Toolchain;

/// <summary>Outcome of trying to apply the guide §-1.1 <c>vpk.signatures</c> workaround.</summary>
public enum VpkSignaturesState
{
    /// <summary>No <c>vpk.signatures</c> file present — nothing to do (workaround not needed).</summary>
    NotPresent,

    /// <summary>The file was renamed for the run and will be restored on <see cref="VpkSignaturesGuard.Dispose"/>.</summary>
    Disabled,

    /// <summary>The file is present but couldn't be renamed — held open by another process, or read-only.</summary>
    Locked,
}

/// <summary>
/// Applies the guide §-1.1 workaround: since a Dec-2023 CS2 update,
/// <c>source1import</c> fails to read the CS:GO <c>pak01.vpk</c>
/// (<c>FATAL ERROR … Failed to load file (invalid)!</c>) while
/// <c>game/bin/win64/vpk.signatures</c> is present. This temporarily renames that
/// file to <c>.disabled</c> for the duration of an import and restores it on
/// <see cref="Dispose"/> — so the user's install is left pristine.
/// <para>
/// <b>VAC-critical.</b> CS2's anti-cheat rejects the install (players can't connect)
/// while <c>vpk.signatures</c> is missing, so the original file <i>must</i> come back.
/// We use a rename (not a regenerate), so the restored bytes are byte-for-byte the
/// original. Restoration is made robust against crashes/kills three ways:
/// <list type="number">
/// <item>normal completion restores it in <see cref="Dispose"/>;</item>
/// <item>the constructor calls <see cref="RestoreLeftover"/> first, so a file stranded
/// by a previous killed run is put back before this run starts (and on app startup,
/// where the UI also calls it);</item>
/// <item>if a restore is impossible right now (the file is locked), it is reported via
/// the <c>log</c> callback so the user can act, and the next run recovers it.</item>
/// </list>
/// </para>
/// <para>
/// The constructor is also <b>non-throwing</b> when it can't disable the file (held open
/// by CS2 / the Source 2 tools, or read-only): it records <see cref="VpkSignaturesState.Locked"/>
/// instead of aborting the whole import with a cryptic "the process cannot access the file"
/// message — the caller warns and lets <c>source1import</c> surface its own
/// <c>pak01.vpk</c> error if the workaround was actually needed.
/// </para>
/// </summary>
public sealed class VpkSignaturesGuard : IDisposable
{
    private readonly string _signatures;
    private readonly string _disabled;
    private readonly Action<string>? _log;

    /// <param name="vpkSignaturesPath">Full path to <c>game/bin/win64/vpk.signatures</c>.</param>
    /// <param name="log">Optional sink for the VAC-critical "couldn't restore" warning raised on dispose.</param>
    public VpkSignaturesGuard(string vpkSignaturesPath, Action<string>? log = null)
    {
        _signatures = vpkSignaturesPath;
        _disabled = vpkSignaturesPath + ".disabled";
        _log = log;

        // Safety net: a previous import that was killed/crashed before Dispose would have
        // left vpk.signatures renamed to .disabled — VAC then rejects the install. Put it
        // back before we start, so we never stack a second rename on a stranded file.
        RestoreLeftover(vpkSignaturesPath);

        if (!File.Exists(vpkSignaturesPath))
        {
            State = VpkSignaturesState.NotPresent;
            return;
        }

        try
        {
            if (File.Exists(_disabled))
                File.Delete(_disabled); // a stale .disabled while the active file also exists
            File.Move(vpkSignaturesPath, _disabled);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            // Held open by another process (CS2 / Source 2 tools) or read-only. Don't
            // abort — record it so the caller can warn and continue. Nothing was moved,
            // so there is nothing to restore.
            State = VpkSignaturesState.Locked;
            Error = ex.Message;
            return;
        }

        State = VpkSignaturesState.Disabled;
    }

    /// <summary>
    /// What to tell the user when the file is <see cref="VpkSignaturesState.Locked"/>. Windows
    /// refuses to rename a file another process holds open without share-delete (CS2 does exactly
    /// that), and <c>source1import</c> then dies mounting the Source 1 <c>csgo\pak01.vpk</c> —
    /// verified: <c>FATAL ERROR … Failed to load file (invalid)!</c>, exit 1, before any work. So an
    /// import started while CS2 runs cannot succeed; there is no flag around it (<c>-insecure</c>
    /// and friends make no difference).
    /// </summary>
    public const string LockedAdvice =
        "CS2 is running. It holds game\\bin\\win64\\vpk.signatures open, so the guide -1.1 " +
        "workaround can't be applied, and source1import always fails with \"FATAL ERROR: " +
        "…\\csgo\\pak01.vpk / Failed to load file (invalid)!\". Close CS2 (and any open Hammer / " +
        "Workshop tools), then run this again.";

    /// <summary>
    /// True when <c>vpk.signatures</c> exists but another process holds it open — i.e. the
    /// workaround can't be applied and an import would be wasted. Cheap pre-flight check so the
    /// caller can refuse before doing minutes of BSP decompiling/staging. Never throws.
    /// </summary>
    public static bool IsLocked(string vpkSignaturesPath)
    {
        if (!File.Exists(vpkSignaturesPath))
            return false;

        try
        {
            // Exclusive open fails for the same reason the rename does: someone else has a handle.
            using var _ = File.Open(vpkSignaturesPath, FileMode.Open, FileAccess.Read, FileShare.None);
            return false;
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            return true;
        }
    }

    /// <summary>The outcome of applying the workaround.</summary>
    public VpkSignaturesState State { get; }

    /// <summary>The OS error message when <see cref="State"/> is <see cref="VpkSignaturesState.Locked"/>.</summary>
    public string? Error { get; }

    /// <summary>True only when this guard actually disabled the signatures file.</summary>
    public bool Applied => State == VpkSignaturesState.Disabled;

    /// <summary>
    /// After <see cref="Dispose"/>, true when <c>vpk.signatures</c> is back in place
    /// (or was never disabled). False means the original is still renamed to
    /// <c>.disabled</c> and the install is VAC-unsafe until recovered.
    /// </summary>
    public bool Restored { get; private set; } = true;

    public void Dispose()
    {
        if (State != VpkSignaturesState.Disabled)
            return; // nothing this guard moved away

        Restored = TryMoveBack(_disabled, _signatures);
        if (!Restored)
            _log?.Invoke(
                "CRITICAL: couldn't restore vpk.signatures — it is still renamed to " +
                $"\"{_disabled}\". CS2 / VAC will reject the install (players can't connect) until " +
                "it is put back. Close CS2 and the Source 2 tools; SourcePorter restores it " +
                "automatically on the next import, or rename it back manually now " +
                $"(\"{Path.GetFileName(_disabled)}\" → \"{Path.GetFileName(_signatures)}\").");
    }

    /// <summary>
    /// Restores a <c>vpk.signatures</c> left renamed by a crashed/killed prior run: when the
    /// <c>.disabled</c> copy exists and the active file does not, it is moved back. Safe to
    /// call anytime — a no-op when the install is already intact. Call on app startup (and the
    /// constructor calls it) so a stranded file is recovered before the user launches CS2.
    /// Returns true when a stranded file was actually restored.
    /// </summary>
    public static bool RestoreLeftover(string vpkSignaturesPath)
    {
        var disabled = vpkSignaturesPath + ".disabled";
        if (File.Exists(disabled) && !File.Exists(vpkSignaturesPath))
            return TryMoveBack(disabled, vpkSignaturesPath);
        return false;
    }

    /// <summary>
    /// Moves <paramref name="disabled"/> back to <paramref name="active"/> when safe, never
    /// throwing. Returns true when the active file is present afterwards (restored, or already
    /// there). A lock/permission failure returns false, leaving the <c>.disabled</c> for a
    /// later recovery rather than crashing out of <see cref="Dispose"/>.
    /// </summary>
    private static bool TryMoveBack(string disabled, string active)
    {
        try
        {
            if (File.Exists(disabled) && !File.Exists(active))
                File.Move(disabled, active);
            return File.Exists(active);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            return false;
        }
    }
}

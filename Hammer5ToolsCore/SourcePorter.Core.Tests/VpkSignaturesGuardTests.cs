using Hammer5Tools.Core.IO.Toolchain;

namespace SourcePorter.Core.Tests;

public class VpkSignaturesGuardTests
{
    [Fact]
    public void Absent_file_is_a_no_op()
    {
        var path = Path.Combine(Path.GetTempPath(), "sp_sig_" + Guid.NewGuid().ToString("N"), "vpk.signatures");

        using var guard = new VpkSignaturesGuard(path);

        Assert.Equal(VpkSignaturesState.NotPresent, guard.State);
        Assert.False(guard.Applied);
        Assert.False(File.Exists(path));
    }

    [Fact]
    public void Present_file_is_disabled_then_restored_byte_for_byte_on_dispose()
    {
        var dir = Path.Combine(Path.GetTempPath(), "sp_sig_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        var path = Path.Combine(dir, "vpk.signatures");
        // Arbitrary binary content stands in for the real signature — VAC needs the exact bytes back.
        var original = new byte[] { 0x00, 0x01, 0x02, 0xFE, 0xFF, 0x10, 0x20 };
        File.WriteAllBytes(path, original);
        try
        {
            VpkSignaturesGuard disposed;
            using (var guard = new VpkSignaturesGuard(path))
            {
                disposed = guard;
                Assert.Equal(VpkSignaturesState.Disabled, guard.State);
                Assert.True(guard.Applied);
                Assert.False(File.Exists(path), "active file should be renamed away during the guard");
                Assert.True(File.Exists(path + ".disabled"));
            }

            // Disposed → restored, install left pristine and byte-for-byte identical (VAC-safe).
            Assert.True(disposed.Restored);
            Assert.True(File.Exists(path));
            Assert.False(File.Exists(path + ".disabled"));
            Assert.Equal(original, File.ReadAllBytes(path));
        }
        finally { Directory.Delete(dir, recursive: true); }
    }

    [Fact]
    public void RestoreLeftover_recovers_a_file_stranded_by_a_crashed_run()
    {
        // A prior run was killed before Dispose: only vpk.signatures.disabled remains.
        var dir = Path.Combine(Path.GetTempPath(), "sp_sig_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        var path = Path.Combine(dir, "vpk.signatures");
        var original = new byte[] { 0xAB, 0xCD, 0xEF };
        File.WriteAllBytes(path + ".disabled", original);
        try
        {
            var recovered = VpkSignaturesGuard.RestoreLeftover(path);

            Assert.True(recovered);
            Assert.True(File.Exists(path));
            Assert.False(File.Exists(path + ".disabled"));
            Assert.Equal(original, File.ReadAllBytes(path));

            // Idempotent: a second call with the install already intact does nothing.
            Assert.False(VpkSignaturesGuard.RestoreLeftover(path));
        }
        finally { Directory.Delete(dir, recursive: true); }
    }

    [Fact]
    public void Constructor_recovers_a_stranded_leftover_before_disabling()
    {
        // Active file missing but a .disabled leftover present (prior crash). The ctor should
        // restore it, then disable it for this run — not report NotPresent.
        var dir = Path.Combine(Path.GetTempPath(), "sp_sig_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        var path = Path.Combine(dir, "vpk.signatures");
        File.WriteAllText(path + ".disabled", "sig");
        try
        {
            using (var guard = new VpkSignaturesGuard(path))
            {
                Assert.Equal(VpkSignaturesState.Disabled, guard.State);
                Assert.True(File.Exists(path + ".disabled"));
            }

            Assert.True(File.Exists(path), "the recovered file must be restored again on dispose");
            Assert.False(File.Exists(path + ".disabled"));
        }
        finally { Directory.Delete(dir, recursive: true); }
    }

    [Fact]
    public void Locked_file_does_not_throw_and_reports_locked()
    {
        if (!OperatingSystem.IsWindows())
            return;

        // Reproduces the reported failure: a process (e.g. CS2) holds vpk.signatures open
        // with an exclusive lock, so File.Move would throw "the process cannot access the
        // file…". The guard must record Locked instead of aborting the whole import.
        var dir = Path.Combine(Path.GetTempPath(), "sp_sig_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        var path = Path.Combine(dir, "vpk.signatures");
        File.WriteAllText(path, "sig");
        try
        {
            using var holder = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.None);

            using var guard = new VpkSignaturesGuard(path); // must NOT throw

            Assert.Equal(VpkSignaturesState.Locked, guard.State);
            Assert.False(guard.Applied);
            Assert.NotNull(guard.Error);
            Assert.True(File.Exists(path), "the original file must be left untouched when locked");
            Assert.False(File.Exists(path + ".disabled"));
        }
        finally { Directory.Delete(dir, recursive: true); }
    }

    [Fact]
    public void IsLocked_detects_a_file_another_process_holds_open()
    {
        // The pre-flight the GUI/CLI use to refuse an import while CS2 is running: source1import
        // FATALs on csgo\pak01.vpk whenever vpk.signatures can't be moved out of the way.
        var dir = Path.Combine(Path.GetTempPath(), "sp_sig_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        var path = Path.Combine(dir, "vpk.signatures");
        File.WriteAllText(path, "sig");
        try
        {
            Assert.False(VpkSignaturesGuard.IsLocked(path));
            Assert.False(VpkSignaturesGuard.IsLocked(Path.Combine(dir, "absent.signatures")));

            using (new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read))
                Assert.True(VpkSignaturesGuard.IsLocked(path));

            Assert.False(VpkSignaturesGuard.IsLocked(path)); // handle released
        }
        finally { Directory.Delete(dir, recursive: true); }
    }
}

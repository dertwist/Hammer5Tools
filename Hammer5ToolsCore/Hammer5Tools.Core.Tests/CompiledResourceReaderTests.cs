using Hammer5Tools.Core.IO.CompiledResource;
using Hammer5Tools.Core.IO.Vpk;

namespace Hammer5Tools.Core.Tests;

public sealed class CompiledResourceReaderTests
{
    [Test]
    public async Task MissingResourceReturnsDiagnostic()
    {
        using var index = new VpkIndex();
        var result = new CompiledResourceReader(index).ReadSound("sounds/missing.vsnd_c");

        await Assert.That(result.IsSuccess).IsFalse();
        await Assert.That(result.Diagnostics[0].Code).IsEqualTo("compiled_resource_missing");
    }

    [Test]
    public async Task MalformedResourceReturnsDiagnostic()
    {
        var root = Directory.CreateTempSubdirectory();
        try
        {
            await File.WriteAllBytesAsync(Path.Combine(root.FullName, "bad.vsnd_c"), [1, 2, 3]);
            using var index = new VpkIndex();
            index.AddLooseRoot(root.FullName);
            var result = new CompiledResourceReader(index).ReadSound("bad.vsnd_c");
            await Assert.That(result.IsSuccess).IsFalse();
            await Assert.That(result.Diagnostics[0].Code).IsEqualTo("compiled_sound_read_failed");
        }
        finally
        {
            root.Delete(true);
        }
    }
}

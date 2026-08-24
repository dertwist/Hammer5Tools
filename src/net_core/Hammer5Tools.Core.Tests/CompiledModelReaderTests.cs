using Hammer5Tools.Core.Resources;

namespace Hammer5Tools.Core.Tests;

public sealed class CompiledModelReaderTests
{
    [Test]
    public async Task MissingModelReturnsStructuredDiagnostic()
    {
        var reader = new CompiledModelReader(Path.GetTempPath(), "addon");

        var result = reader.Read("models/missing.vmdl");

        await Assert.That(result.IsSuccess).IsFalse();
        await Assert.That(result.Value).IsNull();
        await Assert.That(result.Diagnostics).HasSingleItem();
    }

    [Test]
    public async Task ReadsProductionModelWhenFixtureRootIsAvailable()
    {
        var gameDirectory = Environment.GetEnvironmentVariable("H5T_TEST_GAME_DIR");
        if (string.IsNullOrWhiteSpace(gameDirectory))
            return;
        var reader = new CompiledModelReader(gameDirectory, "addon");

        var result = reader.Read("agents/models/ctm_fbi/ctm_fbi.vmdl", baseColorOnly: true);
        Console.WriteLine(string.Join(Environment.NewLine, result.Diagnostics.Select(item => $"{item.Code}: {item.Message}")));

        await Assert.That(result.IsSuccess).IsTrue();
        await Assert.That(result.Value).IsNotNull();
        await Assert.That(result.Value!.Vertices).IsNotEmpty();
        await Assert.That(result.Value.Indices).IsNotEmpty();
        await Assert.That(result.Value.SubMeshes).IsNotEmpty();
    }
}

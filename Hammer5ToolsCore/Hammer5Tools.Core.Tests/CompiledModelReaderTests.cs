using Hammer5Tools.Core.Format.Resources;

namespace Hammer5Tools.Core.Tests;

public sealed class CompiledModelReaderTests
{
    [Test]
    public async Task MissingModelReturnsStructuredDiagnostic()
    {
        using var reader = new CompiledModelReader(Path.GetTempPath(), "addon");

        var result = reader.Read("models/missing.vmdl");

        await Assert.That(result.IsSuccess).IsFalse();
        await Assert.That(result.Value).IsNull();
        await Assert.That(result.Diagnostics).HasSingleItem();
    }

    [Test]
    public async Task ReusesLoaderForRepeatedReadsFromTheSameMount()
    {
        using var reader = new CompiledModelReader(Path.GetTempPath(), "addon");

        reader.Read("models/first_missing.vmdl");
        reader.Read("models/second_missing.vmdl");

        await Assert.That(reader.LoaderCount).IsEqualTo(1);
    }

    [Test]
    public async Task ReadsProductionModelWhenFixtureRootIsAvailable()
    {
        var gameDirectory = Environment.GetEnvironmentVariable("H5T_TEST_GAME_DIR");
        if (string.IsNullOrWhiteSpace(gameDirectory))
            return;
        using var reader = new CompiledModelReader(gameDirectory, "addon");

        var result = reader.Read("agents/models/ctm_fbi/ctm_fbi.vmdl", baseColorOnly: true);
        Console.WriteLine(string.Join(Environment.NewLine, result.Diagnostics.Select(item => $"{item.Code}: {item.Message}")));

        await Assert.That(result.IsSuccess).IsTrue();
        await Assert.That(result.Value).IsNotNull();
        await Assert.That(result.Value!.Vertices).IsNotEmpty();
        await Assert.That(result.Value.Indices).IsNotEmpty();
        await Assert.That(result.Value.SubMeshes).IsNotEmpty();
    }

    [Test]
    public async Task ReadsMaterialTexturesWhenFixtureRootIsAvailable()
    {
        // Regression check for a SkiaSharp native/managed version mismatch
        // (native reported 88.1, managed expected [151.0, 152.0)) that made every
        // texture decode silently fail and fall back to DefaultMaterial, while
        // mesh geometry kept loading fine — see the publish/ folder note on
        // Hammer5Tools.Core.csproj about vendored CUE4Parse-Conversion assets.
        var gameDirectory = Environment.GetEnvironmentVariable("H5T_TEST_GAME_DIR");
        if (string.IsNullOrWhiteSpace(gameDirectory))
            return;
        using var reader = new CompiledModelReader(gameDirectory, "addon");

        var result = reader.Read("models/breakable_props/break_wooden_door_01/break_wooden_door_01.vmdl");

        await Assert.That(result.IsSuccess).IsTrue();
        await Assert.That(result.Value).IsNotNull();
        var material = result.Value!.SubMeshes[0].Material;
        await Assert.That(material.BaseColor).IsNotNull();
        await Assert.That(material.Normal).IsNotNull();
    }
}

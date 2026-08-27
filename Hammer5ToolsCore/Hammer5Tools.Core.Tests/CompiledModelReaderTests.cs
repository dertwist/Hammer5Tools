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
    public async Task ConcurrentReadsShareOneMountAndReturnTheirLoaders()
    {
        using var reader = new CompiledModelReader(Path.GetTempPath(), "addon");

        // More concurrent readers than the per-mount loader budget, so the exhaustion
        // path (wait for a lease to come back) is exercised rather than only creation.
        var readers = Enumerable.Range(0, Environment.ProcessorCount * 4)
            .Select(index => Task.Run(() => reader.Read($"models/missing_{index}.vmdl")))
            .ToArray();

        var results = await Task.WhenAll(readers);

        await Assert.That(results.All(result => !result.IsSuccess)).IsTrue();
        await Assert.That(reader.LoaderCount).IsEqualTo(1);

        // Every lease came back, so a later sequential read still succeeds in acquiring one.
        var afterwards = reader.Read("models/missing_final.vmdl");
        await Assert.That(afterwards.Diagnostics).HasSingleItem();
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
    }

    [Test]
    public async Task ReadsModelWithAlphaTestAndDoubleSidedMaterials()
    {
        var gameDirectory = @"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game";
        if (!Directory.Exists(gameDirectory))
            return;

        using var reader = new CompiledModelReader(gameDirectory, "de_firewatch");
        var result = reader.Read("models/firewatch/structures/fences/fence/fence01.vmdl");
        await Assert.That(result.IsSuccess).IsTrue();
        var model = result.Value!;
        await Assert.That(model.SubMeshes).IsNotEmpty();

        var netMesh = model.SubMeshes.FirstOrDefault(sm => sm.Material.Name.Contains("net", StringComparison.OrdinalIgnoreCase));
        await Assert.That(netMesh).IsNotNull();
        await Assert.That(netMesh!.Material.AlphaMode).IsEqualTo("MASK");
        await Assert.That(netMesh.Material.DoubleSided).IsTrue();
        await Assert.That(netMesh.Material.BaseColor).IsNotNull();

        var wireMesh = model.SubMeshes.FirstOrDefault(sm => sm.Material.Name.Contains("extra_wire", StringComparison.OrdinalIgnoreCase));
        await Assert.That(wireMesh).IsNotNull();
        await Assert.That(wireMesh!.Material.AlphaMode).IsEqualTo("MASK");
        await Assert.That(wireMesh.Material.DoubleSided).IsTrue();
    }

    [Test]
    public async Task ReadsGlassMaterialAsTranslucentAndDoubleSided()
    {
        var gameDirectory = @"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game";
        if (!Directory.Exists(gameDirectory))
            return;

        using var reader = new CompiledModelReader(gameDirectory, "de_firewatch");
        var result = reader.ReadStandaloneMaterial("materials/dev/gray_glass.vmat");
        await Assert.That(result.IsSuccess).IsTrue();
        var material = result.Value!;
        await Assert.That(material.AlphaMode).IsEqualTo("BLEND");
        await Assert.That(material.DoubleSided).IsTrue();
        await Assert.That(material.BaseColorFactor.W).IsLessThan(1.0f);
    }

}


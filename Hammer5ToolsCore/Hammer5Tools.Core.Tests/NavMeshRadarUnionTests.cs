using System.Numerics;

using Hammer5Tools.Core.Format.NavMesh;

namespace Hammer5Tools.Core.Tests;

public sealed class NavMeshRadarUnionTests
{
    private const float Offset = 16f;

    private static IReadOnlyList<Vector3> Square(float minimumX, float minimumY, float size, float z) =>
    [
        new(minimumX, minimumY, z),
        new(minimumX + size, minimumY, z),
        new(minimumX + size, minimumY + size, z),
        new(minimumX, minimumY + size, z),
    ];

    private static float Area(IReadOnlyList<Vector3> face)
    {
        var total = 0f;
        for (int index = 0, previous = face.Count - 1; index < face.Count; previous = index++)
            total += (face[previous].X * face[index].Y) - (face[index].X * face[previous].Y);
        return MathF.Abs(total) * 0.5f;
    }

    [Test]
    public async Task CarriesTheOutlineOutByTheOffset()
    {
        // A 96 square grown to 128 leaves a 7168-unit band, and that band is all the collar is.
        var collar = NavMeshRadarUnion.Collar([Square(0, 0, 96, 64)], Offset);

        await Assert.That(collar.Sum(Area)).IsEqualTo(7168f).Within(1f);
        await Assert.That(collar.All(face => face.Count == 4)).IsTrue();
        await Assert.That(collar.All(face => face.All(corner => MathF.Abs(corner.Z - 64f) < 0.01f))).IsTrue();
    }

    [Test]
    public async Task CountsOverlappingAreasOnce()
    {
        // Two squares sharing a 48x96 strip. The outline is one 144x96 rectangle, so the collar is
        // the band around that, not two bands that cross in the middle.
        var collar = NavMeshRadarUnion.Collar([Square(0, 0, 96, 64), Square(48, 0, 96, 64)], Offset);

        var outline = (144f + (2 * Offset)) * (96f + (2 * Offset));
        await Assert.That(collar.Sum(Area)).IsEqualTo(outline - (144f * 96f)).Within(1f);
    }

    [Test]
    public async Task ClosesHolesInOnThemselves()
    {
        // A ring of squares around an empty 96x96 courtyard: the walkable side grows into the
        // courtyard, so that hole shrinks to 64x64 rather than growing.
        List<IReadOnlyList<Vector3>> ring = [];
        for (var x = 0; x < 3; x++)
        {
            for (var y = 0; y < 3; y++)
            {
                if (x == 1 && y == 1)
                    continue;
                ring.Add(Square(x * 96f, y * 96f, 96f, 0f));
            }
        }

        var collar = NavMeshRadarUnion.Collar(ring, Offset);

        // 320x320 outside, 64x64 courtyard left open, minus the 8 squares already covered.
        await Assert.That(collar.Sum(Area)).IsEqualTo((320f * 320f) - (64f * 64f) - (8 * 96f * 96f)).Within(1f);
    }

    [Test]
    public async Task KeepsStackedLayersApart()
    {
        // The same footprint twice, a storey apart: each surface gets its own collar.
        var collar = NavMeshRadarUnion.Collar([Square(0, 0, 96, 0), Square(0, 0, 96, 512)], Offset);

        await Assert.That(collar.Sum(Area)).IsEqualTo(2 * 7168f).Within(1f);
        await Assert.That(collar.Any(face => face[0].Z < 1f)).IsTrue();
        await Assert.That(collar.Any(face => face[0].Z > 511f)).IsTrue();
    }

    [Test]
    public async Task CarriesSlopeIntoTheCollar()
    {
        // A 96-unit ramp rising 48 units along +X; the collar must not arrive flat.
        IReadOnlyList<Vector3> ramp =
        [
            new(0, 0, 0),
            new(96, 0, 48),
            new(96, 96, 48),
            new(0, 96, 0),
        ];

        var corners = NavMeshRadarUnion.Collar([ramp], Offset).SelectMany(face => face).ToList();

        await Assert.That(corners.Where(corner => corner.X < -8f).All(corner => MathF.Abs(corner.Z) < 2f)).IsTrue();
        await Assert.That(corners.Where(corner => corner.X > 104f).All(corner => MathF.Abs(corner.Z - 48f) < 2f)).IsTrue();
    }

    [Test]
    public async Task AddsNothingWithoutAnOffset()
    {
        await Assert.That(NavMeshRadarUnion.Collar([Square(0, 0, 96, 0)], 0f)).IsEmpty();
    }

    [Test]
    public async Task KeepsFlatRingsWholeAndSplitsWarpedOnes()
    {
        IReadOnlyList<Vector3> flat = Square(0, 0, 96, 12);
        IReadOnlyList<Vector3> warped =
        [
            new(0, 0, 0),
            new(96, 0, 0),
            new(96, 96, 0),
            new(0, 96, 64),
        ];

        var result = NavMeshRadarGenerator.TriangulateNonPlanar([flat, warped]);

        await Assert.That(result.Count(face => face.Count == 4)).IsEqualTo(1);
        await Assert.That(result.Count(face => face.Count == 3)).IsEqualTo(2);
    }
}

namespace Hammer5Tools.Core.Tests.LoadingScreens;

using System.Numerics;
using Hammer5Tools.Core.LoadingScreens;

public class CameraInfoTests
{
    [Test]
    public async Task DefaultConstructorSetsExpectedDefaults()
    {
        var cam = new CameraInfo();
        await Assert.That(cam.Name).IsEqualTo("Camera");
        await Assert.That(cam.Position).IsEqualTo(Vector3.Zero);
        await Assert.That(cam.Fov).IsEqualTo(90f);
    }

    [Test]
    public async Task ParamConstructorSetsValues()
    {
        var cam = new CameraInfo("SpawnCam", new Vector3(100, 200, 300), new Vector3(0, 45, 0), 105f);
        await Assert.That(cam.Name).IsEqualTo("SpawnCam");
        await Assert.That(cam.Position.X).IsEqualTo(100f);
        await Assert.That(cam.Position.Y).IsEqualTo(200f);
        await Assert.That(cam.Position.Z).IsEqualTo(300f);
        await Assert.That(cam.Angles.Y).IsEqualTo(45f);
        await Assert.That(cam.Fov).IsEqualTo(105f);
    }
}

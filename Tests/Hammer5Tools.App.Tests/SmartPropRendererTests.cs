using Avalonia.OpenGL;
using Hammer5Tools.App.Features.SmartProps;

namespace Hammer5Tools.App.Tests;

public sealed class SmartPropRendererTests
{
    [Test]
    public async Task VrfRequiresDesktopOpenGl46()
    {
        await Assert.That(VrfSceneRenderer.IsSupported(new GlVersion(GlProfileType.OpenGL, 4, 6))).IsTrue();
        await Assert.That(VrfSceneRenderer.IsSupported(new GlVersion(GlProfileType.OpenGL, 4, 1))).IsFalse();
        await Assert.That(VrfSceneRenderer.IsSupported(new GlVersion(GlProfileType.OpenGLES, 3, 2))).IsFalse();
    }
}

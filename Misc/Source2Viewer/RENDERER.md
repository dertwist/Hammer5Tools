# Managed SmartProp rendering

Source: https://github.com/ValveResourceFormat/ValveResourceFormat/tree/20.0/Renderer
NuGet package: `ValveResourceFormat.Renderer` `20.0.6980`, matching the format library.
License: MIT; see LICENSE and the package third-party notices.

The package supplies the renderer assembly and embedded Source 2 shader assets;
no upstream application UI or source project is copied into this repository.
`GUI/Features/SmartProps/VrfSceneRenderer.cs` hosts its public Renderer,
ModelSceneNode, InfiniteGrid, SelectedNodeRenderer and PickingTexture APIs in an
Avalonia-owned context. HDR rendering and postprocessing use owned offscreen
framebuffers before blitting to Avalonia's framebuffer. GPU picking maps scene
node IDs to authored SmartProp IDs. Core IO owns game/addon mount discovery.

The pinned renderer requires desktop OpenGL 4.6. Windows requests WGL 4.6,
falling back to older WGL/ANGLE/software. The existing renderer remains the
compatibility path for older GL/GLES and previews without a game mount.
CompiledModelReader remains shared by DCC/NativeAOT callers and the CPU preview;
its public geometry and collision-fallback contracts are unchanged.

The OpenGL 4.6 path requires validation on a supported GPU with CS2 assets;
macOS cannot run that path. The host rescales the InfiniteGrid coordinate frame to honor GridStep.

Run supported-GPU validation with:

```sh
dotnet run --project Tests/Hammer5Tools.SmartProp.Tests -c Release -- --vrf-gpu
```

This requires CS2 assets and asserts that VRF is active before frame capture and
camera/shading checks; the compatibility renderer cannot silently satisfy it.

using System.Diagnostics.CodeAnalysis;
using System.Numerics;
using Avalonia.OpenGL;
using Hammer5Tools.Core.IO;
using Microsoft.Extensions.Logging.Abstractions;
using OpenTK;
using OpenTK.Graphics.OpenGL;
using ValveResourceFormat;
using ValveResourceFormat.CompiledShader;
using ValveResourceFormat.IO;
using ValveResourceFormat.Renderer;
using ValveResourceFormat.Renderer.Materials;
using ValveResourceFormat.Renderer.SceneNodes;
using ValveResourceFormat.ResourceTypes;
using VrfRenderer = ValveResourceFormat.Renderer.Renderer;

namespace Hammer5Tools.App.Features.SmartProps;

[SuppressMessage("Design", "CA1001", Justification = "GPU objects are explicitly released with the owning Avalonia GL context current.")]
internal sealed class VrfSceneRenderer : IDisposable
{
    private sealed class Bindings(GlInterface gl) : IBindingsContext
    {
        public IntPtr GetProcAddress(string procName) => gl.GetProcAddress(procName);
    }

    private readonly GameFileLoader files;
    private readonly RendererContext context;
    private readonly VrfRenderer renderer;
    private readonly InfiniteGrid grid;
    private readonly PickingTexture picker;
    private readonly TextRenderer text;
    private readonly SelectedNodeRenderer selection;
    private readonly Framebuffer hdr;
    private readonly Framebuffer output;
    private readonly RenderTexture environment;
    private readonly List<Resource> resources = [];
    private readonly Dictionary<uint, int> elementIds = [];
    private readonly List<(ModelSceneNode Node, int ElementId)> nodes = [];
    private int? selected;
    private string mode = "";
    private (int X, int Y)? pendingPick;

    public event Action<int>? ElementPicked;

    internal static bool IsSupported(GlVersion version)
        => version.Type == GlProfileType.OpenGL && (version.Major > 4 || version.Major == 4 && version.Minor >= 6);

    public VrfSceneRenderer(GlInterface gl, string gameDirectory, string addon)
    {
        GL.LoadBindings(new Bindings(gl));
        files = SmartPropRenderFiles.Open(gameDirectory, addon);
        try
        {
            context = new RendererContext(files, NullLogger.Instance)
            {
                FieldOfView = 2f * MathF.Atan(MathF.Tan(MathF.PI / 6f) * 4f / 3f) * 180f / MathF.PI,
            };
            renderer = new VrfRenderer(context);
            text = new TextRenderer(context, renderer.Camera);
            selection = new SelectedNodeRenderer(context);
            hdr = Framebuffer.Prepare("SmartProp HDR", 4, 4, 0, ImageFormat.RGBA16161616F, ImageFormat.D32);
            output = Framebuffer.Prepare("SmartProp output", 4, 4, 0, ImageFormat.RGBA8888, null);
            hdr.Initialize();
            output.Initialize();
            renderer.MainFramebuffer = hdr;
            renderer.Scene.Initialize();
            renderer.Scene.EnableOcclusionCulling = false;
            renderer.Scene.FogEnabled = false;
            renderer.Postprocess.Load(0);
            renderer.Initialize();
            renderer.LoadRendererResources();
            using var environmentStream = typeof(VrfRenderer).Assembly.GetManifestResourceStream("Renderer.Resources.sky_furnace.vtex_c")
                ?? throw new InvalidDataException("VRF's default environment texture is missing.");
            using var environmentResource = new Resource { FileName = "h5t-default-environment.vtex_c" };
            environmentResource.Read(environmentStream);
            VrfRenderer.LoadDefaultLighting(renderer.Scene, environmentResource);
            environment = renderer.Scene.LightingInfo.EnvMaps.Single().EnvMapTexture;
            grid = new InfiniteGrid(renderer.Scene);
            picker = new PickingTexture(context, (_, result) =>
            {
                if (elementIds.TryGetValue(result.PixelInfo.ObjectId, out var element))
                {
                    ElementPicked?.Invoke(element);
                }
            });
        }
        catch
        {
            hdr?.Delete();
            output?.Delete();
            renderer?.Dispose();
            environment?.Delete();
            context?.Dispose();
            files.Dispose();
            throw;
        }
    }

    public void SetScene(IReadOnlyList<ViewportInstance> instances)
    {
        selection.SelectNode(null);
        renderer.Scene.Clear();
        foreach (var resource in resources)
        {
            resource.Dispose();
        }
        resources.Clear();
        elementIds.Clear();
        nodes.Clear();
        selected = null;
        pendingPick = null;
        mode = "";
        var models = new Dictionary<string, Model>(StringComparer.OrdinalIgnoreCase);
        foreach (var instance in instances)
        {
            if (!models.TryGetValue(instance.ModelName, out var model))
            {
                var resource = instance.ModelName.EndsWith("_c", StringComparison.OrdinalIgnoreCase)
                    ? files.LoadFile(instance.ModelName) : files.LoadFileCompiled(instance.ModelName);
                if (resource is null)
                {
                    continue;
                }
                resources.Add(resource);
                if (resource.DataBlock is not Model loaded)
                {
                    continue;
                }
                models[instance.ModelName] = model = loaded;
            }
            var node = new ModelSceneNode(renderer.Scene, model, instance.MaterialGroup, isWorldPreview: true)
            {
                Transform = instance.Transform,
                Tint = instance.Tint ?? Vector4.One,
            };
            renderer.Scene.Add(node, dynamic: false);
            nodes.Add((node, instance.ElementId));
        }
        renderer.Scene.UpdateNodeIndices();
        foreach (var (node, elementId) in nodes)
        {
            elementIds[node.Id] = elementId;
        }
        renderer.Scene.Initialize();
    }

    public void RequestPick(int x, int y) => pendingPick = (x, y);

    public void Render(int framebuffer, int width, int height, ViewportCamera camera, string shadingMode, bool showGrid, float gridStep, int? selectedElement,
        OpenTK.Mathematics.Color4 background)
    {
        GL.ClipControl(ClipOrigin.LowerLeft, ClipDepthMode.ZeroToOne);
        GL.ClearDepth(0);
        GL.DepthFunc(DepthFunction.Greater);
        // Avalonia also uses this context; restore the baseline behind VRF's state cache.
        GL.Enable(EnableCap.DepthTest);
        GL.DepthMask(true);
        GL.ColorMask(true, true, true, true);
        GL.Enable(EnableCap.CullFace);
        GL.CullFace(TriangleFace.Back);
        GL.FrontFace(FrontFaceDirection.Ccw);
        GL.Disable(EnableCap.Blend);
        GL.BlendFunc(BlendingFactor.SrcAlpha, BlendingFactor.OneMinusSrcAlpha);
        GL.Disable(EnableCap.StencilTest);
        GL.Disable(EnableCap.ScissorTest);
        GL.Disable(EnableCap.PolygonOffsetFill);
        GL.Disable(EnableCap.DepthClamp);
        GL.Enable(EnableCap.Multisample);
        GL.PolygonMode(TriangleFace.FrontAndBack, PolygonMode.Fill);
        context.RenderState.Apply(RenderState.Default);
        hdr.Resize(width, height);
        output.Resize(width, height);
        picker.Resize(width, height);
        if (pendingPick is { } pick)
        {
            picker.RequestNextFrame(Math.Clamp(pick.X, 0, width - 1), Math.Clamp(pick.Y, 1, height), PickingTexture.PickingIntent.Select);
            pendingPick = null;
        }
        hdr.ClearColor = background;
        renderer.Camera.SetViewportSize(width, height);
        Matrix4x4.Invert(ViewportCamera.SourceToGl, out var toSource);
        renderer.Camera.SetLocation(Vector3.Transform(camera.Position, toSource));
        renderer.Camera.LookAt(Vector3.Transform(camera.Center, toSource));
        renderer.Camera.RecalculateMatrices();
        renderer.IsWireframe = shadingMode == "Wireframe";
        if (mode != shadingMode)
        {
            mode = shadingMode;
            var renderMode = shadingMode == "Solid" ? "FullBright" : "Default";
            renderer.ViewBuffer!.Data.RenderMode = RenderModes.GetShaderId(renderMode);
            renderer.Postprocess.Enabled = renderer.ViewBuffer.Data.RenderMode == 0;
            selection.SetRenderMode(renderMode);
        }
        if (selected != selectedElement)
        {
            selected = selectedElement;
            selection.SelectNode(null);
            foreach (var (node, elementId) in nodes)
            {
                if (elementId == selectedElement)
                {
                    selection.ToggleNode(node);
                }
            }
        }
        renderer.DeltaTime = 1f / 60f;
        renderer.Uptime += renderer.DeltaTime;
        renderer.PerfStats.MarkFrameBegin();
        try
        {
            var update = new Scene.UpdateContext { Camera = renderer.Camera, TextRenderer = text, Timestep = renderer.DeltaTime };
            renderer.Update(update);
            var draw = new Scene.RenderContext
            {
                Scene = renderer.Scene,
                Camera = renderer.Camera,
                Framebuffer = hdr,
                Textures = renderer.Textures,
            };
            selection.Update(draw, update);
            if (picker.ActiveNextFrame)
            {
                draw.Framebuffer = picker;
                draw.ReplacementShader = picker.Shader;
                renderer.RenderScenesWithView(draw);
                picker.Finish();
                draw.Framebuffer = hdr;
                draw.ReplacementShader = null;
            }
            renderer.Render(draw);
            selection.Render();
            if (showGrid)
            {
                // Upstream's fine grid spacing is 15 units; rescale its coordinate frame only.
                var scale = MathF.Max(1f, gridStep) / 15f;
                var view = renderer.ViewBuffer!.Data;
                view.WorldToView = Matrix4x4.CreateScale(scale) * renderer.Camera.CameraViewMatrix;
                view.CameraPosition = renderer.Camera.Location / scale;
                renderer.ViewBuffer.Update();
                grid.Render();
                renderer.Camera.SetViewConstants(view);
                renderer.ViewBuffer.Update();
            }
            renderer.PostprocessRender(hdr, output);
            GL.BindFramebuffer(FramebufferTarget.ReadFramebuffer, output.FboHandle);
            GL.BindFramebuffer(FramebufferTarget.DrawFramebuffer, framebuffer);
            GL.BlitFramebuffer(0, 0, width, height, 0, 0, width, height, ClearBufferMask.ColorBufferBit, BlitFramebufferFilter.Nearest);
            picker.TriggerEventIfAny();
        }
        finally
        {
            renderer.PerfStats.MarkFrameEnd();
            GL.ClipControl(ClipOrigin.LowerLeft, ClipDepthMode.NegativeOneToOne);
            GL.ClearDepth(1);
            GL.DepthRange(0.0, 1.0);
            GL.DepthFunc(DepthFunction.Less);
            GL.DepthMask(true);
            GL.PolygonMode(TriangleFace.FrontAndBack, PolygonMode.Fill);
            GL.BindFramebuffer(FramebufferTarget.Framebuffer, framebuffer);
            GL.BindVertexArray(0);
            GL.UseProgram(0);
            GL.Disable(EnableCap.DepthTest);
            GL.Disable(EnableCap.Blend);
            GL.Disable(EnableCap.CullFace);
        }
    }

    public void Dispose()
    {
        selection.Delete();
        picker.Delete();
        renderer.Scene.Clear();
        foreach (var resource in resources)
        {
            resource.Dispose();
        }
        hdr.Delete();
        output.Delete();
        renderer.Dispose();
        environment.Delete();
        context.Dispose();
        files.Dispose();
    }
}

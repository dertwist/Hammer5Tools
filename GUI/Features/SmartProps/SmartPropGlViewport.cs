using System.Diagnostics.CodeAnalysis;
using System.Numerics;
using System.Reflection;
using System.Runtime.InteropServices;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Media;
using Avalonia.Media.Imaging;
using Avalonia.OpenGL;
using Avalonia.OpenGL.Controls;
using Avalonia.Platform;
using Avalonia.Threading;
using Hammer5Tools.Core.Format.Resources;
using static Avalonia.OpenGL.GlConsts;

namespace Hammer5Tools.App.Features.SmartProps;

[SuppressMessage("Design", "CA1001", Justification = "The renderer is disposed by OnOpenGlDeinit while the owning GL context is current.")]
public sealed class SmartPropGlViewport : OpenGlControlBase
{
    private readonly ViewportCamera camera = new();
    private readonly DispatcherTimer flyTimer = new() { Interval = TimeSpan.FromMilliseconds(16) };
    private readonly HashSet<Key> keys = [];
    private IReadOnlyList<ViewportInstance> instances = [];
    private GlSceneRenderer? renderer;
    private VrfSceneRenderer? vrfRenderer;
    private string gameDirectory = "";
    private string addon = "";
    private bool resourceContextChanged;
    private Point? drag;
    private Point press;
    private bool fly;
    private bool pan;
    private bool orbit;
    private bool sceneChanged;
    private int? selectedElementId;
    private string shadingMode = "Textured";
    private bool showGrid = true;
    private float gridStep = 8;
    private (string Path, TaskCompletionSource Completion)? capture;

    public event Action<int>? ElementClicked;
    public event Action<string>? RendererFailed;
    public int MeshCount => instances.Count(instance => instance.Geometry is not null);
    internal Vector3 CameraPosition => camera.Position;
    public bool IsRendererReady => renderer is not null;
    internal bool IsUsingVrf => vrfRenderer is not null;

    public SmartPropGlViewport()
    {
        Focusable = true;
        LostFocus += (_, _) => StopNavigation();
        flyTimer.Tick += (_, _) =>
        {
            var direction = new Vector3((keys.Contains(Key.D) ? 1 : 0) - (keys.Contains(Key.A) ? 1 : 0),
                (keys.Contains(Key.E) ? 1 : 0) - (keys.Contains(Key.Q) ? 1 : 0), (keys.Contains(Key.W) ? 1 : 0) - (keys.Contains(Key.S) ? 1 : 0));
            camera.Move(direction, keys.Contains(Key.LeftShift) ? 0.05f : 0.016f);
            RequestNextFrameRendering();
        };
    }

    public override void Render(DrawingContext context)
    {
        base.Render(context);
        // The separate OpenGL composition surface does not contribute an input hit region.
        context.DrawRectangle(Brushes.Transparent, null, new Rect(Bounds.Size));
    }

    public int? SelectedElementId
    {
        get => selectedElementId;
        set
        {
            selectedElementId = value;
            RequestNextFrameRendering();
        }
    }

    public string ShadingMode
    {
        get => shadingMode;
        set
        {
            shadingMode = value;
            RequestNextFrameRendering();
        }
    }

    public bool ShowGrid
    {
        get => showGrid;
        set
        {
            showGrid = value;
            RequestNextFrameRendering();
        }
    }

    public float GridStep
    {
        get => gridStep;
        set
        {
            gridStep = Math.Max(1, value);
            RequestNextFrameRendering();
        }
    }

    public void SetScene(IReadOnlyList<ViewportInstance> scene, bool frame = true)
    {
        instances = scene;
        sceneChanged = true;
        if (frame)
        {
            FrameScene();
        }
        else
        {
            RequestNextFrameRendering();
        }
    }

    public void SetResourceContext(string game, string activeAddon)
    {
        if (gameDirectory == game && addon == activeAddon)
        {
            return;
        }
        gameDirectory = game;
        addon = activeAddon;
        resourceContextChanged = true;
        sceneChanged = true;
    }

    public void ClearScene() => SetScene([]);

    public void FrameScene()
    {
        camera.Frame(instances);
        RequestNextFrameRendering();
    }

    internal Task CaptureFrame(string path)
    {
        var completion = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        capture = (path, completion);
        RequestNextFrameRendering();
        return completion.Task;
    }

    protected override void OnOpenGlInit(GlInterface gl)
    {
        try
        {
            renderer = new GlSceneRenderer(gl, GlVersion.Type == GlProfileType.OpenGLES);
            resourceContextChanged = true;
            sceneChanged = true;
        }
        catch (Exception exception)
        {
            RendererFailed?.Invoke(exception.Message);
            capture?.Completion.TrySetException(exception);
        }
    }

    protected override void OnOpenGlRender(GlInterface gl, int fb)
    {
        if (renderer is null)
        {
            return;
        }
        try
        {
            if (resourceContextChanged)
            {
                vrfRenderer?.Dispose();
                vrfRenderer = null;
                if (VrfSceneRenderer.IsSupported(GlVersion) && !string.IsNullOrWhiteSpace(gameDirectory))
                {
                    renderer.SetScene([]);
                    vrfRenderer = new VrfSceneRenderer(gl, gameDirectory, addon);
                    vrfRenderer.ElementPicked += element => ElementClicked?.Invoke(element);
                }
                resourceContextChanged = false;
            }
            if (sceneChanged)
            {
                if (vrfRenderer is not null)
                {
                    vrfRenderer.SetScene(instances);
                }
                else
                {
                    renderer.SetScene(instances);
                }
                sceneChanged = false;
            }
            var scaling = TopLevel.GetTopLevel(this)?.RenderScaling ?? 1;
            var width = Math.Max(1, (int)Math.Ceiling(Bounds.Width * scaling));
            var height = Math.Max(1, (int)Math.Ceiling(Bounds.Height * scaling));
            if (vrfRenderer is not null)
            {
                var background = ((ISolidColorBrush)Application.Current!.Resources["H5TBackgroundBrush"]!).Color;
                vrfRenderer.Render(fb, width, height, camera, shadingMode, showGrid, gridStep, selectedElementId,
                    new OpenTK.Mathematics.Color4(background.R / 255f, background.G / 255f, background.B / 255f, 1));
            }
            else
            {
                renderer.Render(fb, width, height, camera, shadingMode, showGrid, gridStep, selectedElementId);
            }
            if (capture is { } request)
            {
                renderer.Capture(request.Path, width, height);
                request.Completion.TrySetResult();
                capture = null;
            }
        }
        catch (Exception exception)
        {
            capture?.Completion.TrySetException(exception);
            capture = null;
            RendererFailed?.Invoke(exception.Message);
        }
    }

    protected override void OnOpenGlDeinit(GlInterface gl)
    {
        vrfRenderer?.Dispose();
        vrfRenderer = null;
        renderer?.Dispose();
        renderer = null;
        resourceContextChanged = true;
        flyTimer.Stop();
    }

    protected override void OnOpenGlLost()
    {
        vrfRenderer = null;
        resourceContextChanged = true;
        renderer = null;
        sceneChanged = true;
        flyTimer.Stop();
    }

    protected override void OnPointerPressed(PointerPressedEventArgs e)
    {
        base.OnPointerPressed(e);
        Focus();
        var properties = e.GetCurrentPoint(this).Properties;
        press = e.GetPosition(this);
        drag = press;
        fly = properties.IsRightButtonPressed;
        pan = properties.IsMiddleButtonPressed && e.KeyModifiers.HasFlag(KeyModifiers.Shift);
        orbit = properties.IsMiddleButtonPressed && !pan;
        e.Pointer.Capture(this);
        if (fly)
        {
            flyTimer.Start();
        }
        e.Handled = true;
    }

    protected override void OnPointerMoved(PointerEventArgs e)
    {
        base.OnPointerMoved(e);
        if (drag is not { } previous)
        {
            return;
        }
        var current = e.GetPosition(this);
        if (fly)
        {
            camera.Look(current - previous);
        }
        else if (pan)
        {
            camera.Pan(current - previous);
        }
        else if (orbit)
        {
            camera.Orbit(current - previous);
        }
        drag = current;
        RequestNextFrameRendering();
        e.Handled = true;
    }

    protected override void OnPointerReleased(PointerReleasedEventArgs e)
    {
        base.OnPointerReleased(e);
        if (e.InitialPressMouseButton == MouseButton.Left && Math.Abs(e.GetPosition(this).X - press.X) + Math.Abs(e.GetPosition(this).Y - press.Y) < 4)
        {
            if (vrfRenderer is not null)
            {
                var scaling = TopLevel.GetTopLevel(this)?.RenderScaling ?? 1;
                var point = e.GetPosition(this);
                vrfRenderer.RequestPick(Math.Max(0, (int)(point.X * scaling)), Math.Max(1, (int)(point.Y * scaling)));
                RequestNextFrameRendering();
            }
            else if (camera.Pick(e.GetPosition(this), Bounds.Size, instances) is { } element)
            {
                ElementClicked?.Invoke(element);
            }
        }
        StopNavigation();
        e.Pointer.Capture(null);
    }

    protected override void OnPointerCaptureLost(PointerCaptureLostEventArgs e)
    {
        base.OnPointerCaptureLost(e);
        StopNavigation();
    }

    private void StopNavigation()
    {
        drag = null;
        fly = false;
        orbit = false;
        keys.Clear();
        flyTimer.Stop();
    }

    protected override void OnPointerWheelChanged(PointerWheelEventArgs e)
    {
        base.OnPointerWheelChanged(e);
        camera.Zoom(e.Delta.Y);
        RequestNextFrameRendering();
        e.Handled = true;
    }

    protected override void OnKeyDown(KeyEventArgs e)
    {
        base.OnKeyDown(e);
        if (e.Key == Key.F)
        {
            FrameScene();
            e.Handled = true;
        }
        if (fly)
        {
            keys.Add(e.Key);
            e.Handled = true;
        }
    }

    protected override void OnKeyUp(KeyEventArgs e)
    {
        base.OnKeyUp(e);
        keys.Remove(e.Key);
    }
}

internal sealed unsafe class GlSceneRenderer : IDisposable
{
    private const int GL_LEQUAL = 0x0203;
    private const int GL_BLEND = 0x0BE2;
    private const int GL_SRC_ALPHA = 0x0302;
    private const int GL_ONE_MINUS_SRC_ALPHA = 0x0303;
    private const int GL_LINES = 0x0001;
    private const int GL_UNSIGNED_INT = 0x1405;
    private const int GL_REPEAT = 0x2901;
    [UnmanagedFunctionPointer(CallingConvention.Winapi)] private delegate void Uniform2(int location, float x, float y);
    [UnmanagedFunctionPointer(CallingConvention.Winapi)] private delegate void Uniform3(int location, float x, float y, float z);
    [UnmanagedFunctionPointer(CallingConvention.Winapi)] private delegate void Uniform4(int location, float x, float y, float z, float w);
    [UnmanagedFunctionPointer(CallingConvention.Winapi)] private delegate void UniformMatrix3(int location, int count, byte transpose, float* matrix);
    [UnmanagedFunctionPointer(CallingConvention.Winapi)] private delegate void Blend(int source, int destination);
    [UnmanagedFunctionPointer(CallingConvention.Winapi)] private delegate void ReadPixels(int x, int y, int width, int height, int format, int type, IntPtr buffer);

    private sealed record GpuMesh(int Array, int Vertices, int Indices, int Lines, int LineCount, CompiledModel Model);
    private readonly GlInterface gl;
    private readonly Uniform2 uniform2;
    private readonly Uniform3 uniform3;
    private readonly Uniform4 uniform4;
    private readonly UniformMatrix3 uniformMatrix3;
    private readonly Blend blend;
    private readonly ReadPixels readPixels;
    private readonly Dictionary<CompiledModel, GpuMesh> meshes = new(ReferenceEqualityComparer.Instance);
    private readonly Dictionary<CompiledTexture, int> textures = new(ReferenceEqualityComparer.Instance);
    private readonly Dictionary<(int Program, string Name), int> uniforms = [];
    private readonly int modelProgram;
    private readonly int gridProgram;
    private readonly int gridArray;
    private readonly int gridBuffer;
    private readonly int depthBuffer;
    private int depthWidth;
    private int depthHeight;
    private IReadOnlyList<ViewportInstance> instances = [];

    public GlSceneRenderer(GlInterface gl, bool gles)
    {
        this.gl = gl;
        uniform2 = Proc<Uniform2>("glUniform2f");
        uniform3 = Proc<Uniform3>("glUniform3f");
        uniform4 = Proc<Uniform4>("glUniform4f");
        uniformMatrix3 = Proc<UniformMatrix3>("glUniformMatrix3fv");
        blend = Proc<Blend>("glBlendFunc");
        readPixels = Proc<ReadPixels>("glReadPixels");
        modelProgram = CreateProgram("model", gles);
        gridProgram = CreateProgram("grid", gles);
        gridArray = gl.GenVertexArray();
        gridBuffer = gl.GenBuffer();
        depthBuffer = gl.GenRenderbuffer();
        gl.BindVertexArray(gridArray);
        gl.BindBuffer(GL_ARRAY_BUFFER, gridBuffer);
        float[] grid = [-3000, 0, -3000, 3000, 0, -3000, 3000, 0, 3000, -3000, 0, -3000, 3000, 0, 3000, -3000, 0, 3000];
        fixed (float* pointer = grid)
        {
            gl.BufferData(GL_ARRAY_BUFFER, grid.Length * sizeof(float), (IntPtr)pointer, GL_STATIC_DRAW);
        }
        gl.VertexAttribPointer(0, 3, GL_FLOAT, 0, 3 * sizeof(float), IntPtr.Zero);
        gl.EnableVertexAttribArray(0);
        gl.BindVertexArray(0);
    }

    private T Proc<T>(string name) where T : Delegate => Marshal.GetDelegateForFunctionPointer<T>(gl.GetProcAddress(name));
    private int Location(int program, string name)
    {
        var key = (program, name);
        if (!uniforms.TryGetValue(key, out var value))
        {
            uniforms[key] = value = gl.GetUniformLocationString(program, name);
        }
        return value;
    }

    private int CreateProgram(string name, bool gles)
    {
        var vertex = gl.CreateShader(GL_VERTEX_SHADER);
        var fragment = gl.CreateShader(GL_FRAGMENT_SHADER);
        var program = gl.CreateProgram();
        try
        {
            foreach (var (shader, suffix) in new[] { (vertex, "vert"), (fragment, "frag") })
            {
                using var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream($"Shaders.{name}.{suffix}")!;
                using var reader = new StreamReader(stream);
                var source = reader.ReadToEnd().Replace("#version 430 core", gles ? "#version 300 es\nprecision highp float;" : "#version 150", StringComparison.Ordinal);
                for (var index = 0; index < 3; index++)
                {
                    source = source.Replace($"layout(location = {index}) ", "", StringComparison.Ordinal);
                }
                if (gl.CompileShaderAndGetError(shader, source) is { } compileError)
                {
                    throw new InvalidOperationException($"{name}.{suffix}: {compileError}");
                }
                gl.AttachShader(program, shader);
            }
            gl.BindAttribLocationString(program, 0, "aPos");
            gl.BindAttribLocationString(program, 1, "aNormal");
            gl.BindAttribLocationString(program, 2, "aTexCoord");
            if (gl.LinkProgramAndGetError(program) is { } error)
            {
                throw new InvalidOperationException($"{name}: {error}");
            }
            return program;
        }
        catch
        {
            gl.DeleteProgram(program);
            throw;
        }
        finally
        {
            gl.DeleteShader(vertex);
            gl.DeleteShader(fragment);
        }
    }

    public void SetScene(IReadOnlyList<ViewportInstance> scene)
    {
        ReleaseScene();
        instances = scene;
        foreach (var instance in scene)
        {
            if (instance.Geometry is not { } model || meshes.ContainsKey(model))
            {
                continue;
            }
            var data = new float[model.Vertices.Length / 3 * 8];
            for (var index = 0; index < data.Length / 8; index++)
            {
                for (var component = 0; component < 3; component++)
                {
                    data[index * 8 + component] = model.Vertices[index * 3 + component];
                    data[index * 8 + 3 + component] = model.Normals[index * 3 + component];
                }
                data[index * 8 + 6] = model.Uvs[index * 2];
                data[index * 8 + 7] = model.Uvs[index * 2 + 1];
            }
            var vao = gl.GenVertexArray();
            var vertices = gl.GenBuffer();
            var indices = gl.GenBuffer();
            var lines = gl.GenBuffer();
            gl.BindVertexArray(vao);
            gl.BindBuffer(GL_ARRAY_BUFFER, vertices);
            fixed (float* pointer = data)
            {
                gl.BufferData(GL_ARRAY_BUFFER, data.Length * sizeof(float), (IntPtr)pointer, GL_STATIC_DRAW);
            }
            for (var attribute = 0; attribute < 3; attribute++)
            {
                gl.VertexAttribPointer(attribute, attribute == 2 ? 2 : 3, GL_FLOAT, 0, 8 * sizeof(float), (attribute == 2 ? 6 : attribute * 3) * sizeof(float));
                gl.EnableVertexAttribArray(attribute);
            }
            var triangleIndices = model.Indices.ToArray();
            var lineIndices = new uint[triangleIndices.Length * 2];
            for (var index = 0; index + 2 < triangleIndices.Length; index += 3)
            {
                var a = triangleIndices[index];
                var b = triangleIndices[index + 1];
                var c = triangleIndices[index + 2];
                lineIndices[index * 2] = a;
                lineIndices[index * 2 + 1] = b;
                lineIndices[index * 2 + 2] = b;
                lineIndices[index * 2 + 3] = c;
                lineIndices[index * 2 + 4] = c;
                lineIndices[index * 2 + 5] = a;
            }
            UploadIndices(indices, triangleIndices);
            UploadIndices(lines, lineIndices);
            meshes[model] = new(vao, vertices, indices, lines, lineIndices.Length, model);
        }
        gl.BindVertexArray(0);
    }

    private void UploadIndices(int buffer, uint[] data)
    {
        gl.BindBuffer(GL_ELEMENT_ARRAY_BUFFER, buffer);
        fixed (uint* pointer = data)
        {
            gl.BufferData(GL_ELEMENT_ARRAY_BUFFER, data.Length * sizeof(uint), (IntPtr)pointer, GL_STATIC_DRAW);
        }
    }

    private void Matrix(int program, string name, Matrix4x4 matrix) => gl.UniformMatrix4fv(Location(program, name), 1, false, &matrix);
    private void Float(string name, float value) => gl.Uniform1f(Location(modelProgram, name), value);
    private void Int(string name, int value) => gl.Uniform1i(Location(modelProgram, name), value);
    private void Vector(string name, Vector2 value) => uniform2(Location(modelProgram, name), value.X, value.Y);
    private void Vector(string name, Vector3 value) => uniform3(Location(modelProgram, name), value.X, value.Y, value.Z);
    private void Vector(string name, Vector4 value) => uniform4(Location(modelProgram, name), value.X, value.Y, value.Z, value.W);

    private void NormalMatrix(Matrix4x4 model)
    {
        Matrix4x4.Invert(model, out var inverse);
        var normal = Matrix4x4.Transpose(inverse);
        float* values = stackalloc float[9] { normal.M11, normal.M12, normal.M13, normal.M21, normal.M22, normal.M23, normal.M31, normal.M32, normal.M33 };
        uniformMatrix3(Location(modelProgram, "uNormalMatrix"), 1, 0, values);
    }

    public void Render(int framebuffer, int width, int height, ViewportCamera camera, string mode, bool showGrid, float gridStep, int? selected)
    {
        gl.BindFramebuffer(GL_FRAMEBUFFER, framebuffer);
        gl.BindRenderbuffer(GL_RENDERBUFFER, depthBuffer);
        if (depthWidth != width || depthHeight != height)
        {
            gl.RenderbufferStorage(GL_RENDERBUFFER, 0x81A6, width, height); // DEPTH_COMPONENT24
            depthWidth = width;
            depthHeight = height;
        }
        gl.FramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, depthBuffer);
        gl.Viewport(0, 0, width, height);
        var background = ((ISolidColorBrush)Application.Current!.Resources["H5TBackgroundBrush"]!).Color;
        gl.ClearColor(background.R / 255f, background.G / 255f, background.B / 255f, 1);
        gl.ClearDepth(1);
        gl.Clear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
        gl.Enable(GL_DEPTH_TEST);
        gl.DepthFunc(GL_LEQUAL);
        gl.Disable(GL_CULL_FACE);
        gl.Enable(GL_BLEND);
        blend(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        var view = camera.View;
        var projection = camera.Projection((double)width / height);
        if (showGrid)
        {
            gl.UseProgram(gridProgram);
            Matrix(gridProgram, "uView", view);
            Matrix(gridProgram, "uProjection", projection);
            gl.Uniform1f(Location(gridProgram, "uGridStep"), gridStep);
            gl.BindVertexArray(gridArray);
            gl.DepthMask(0);
            gl.DrawArrays(GL_TRIANGLES, 0, 6);
            gl.DepthMask(1);
        }
        gl.UseProgram(modelProgram);
        Matrix(modelProgram, "uView", view);
        Matrix(modelProgram, "uProjection", projection);
        Vector("uCameraPos", camera.Position);
        foreach (var instance in instances)
        {
            if (instance.Geometry is not { } geometry || !meshes.TryGetValue(geometry, out var mesh))
            {
                continue;
            }
            var model = instance.Transform * ViewportCamera.SourceToGl;
            Matrix(modelProgram, "uModel", model);
            NormalMatrix(model);
            Float("uHighlight", instance.ElementId == selected ? 1 : 0);
            gl.BindVertexArray(mesh.Array);
            if (mode == "Wireframe")
            {
                if (geometry.SubMeshes.Length > 0)
                {
                    BindMaterial(geometry.SubMeshes[0].Material, false, instance.Tint);
                }
                gl.BindBuffer(GL_ELEMENT_ARRAY_BUFFER, mesh.Lines);
                gl.DrawElements(GL_LINES, mesh.LineCount, GL_UNSIGNED_INT, IntPtr.Zero);
                continue;
            }
            gl.BindBuffer(GL_ELEMENT_ARRAY_BUFFER, mesh.Indices);
            foreach (var submesh in geometry.SubMeshes.Where(item => mode != "Textured" || item.Material.AlphaMode != "BLEND"))
            {
                BindMaterial(submesh.Material, mode == "Textured", instance.Tint);
                gl.DrawElements(GL_TRIANGLES, submesh.IndexCount, GL_UNSIGNED_INT, submesh.IndexOffset * sizeof(uint));
            }
        }
        // Glass is drawn after opaque surfaces with depth testing but no depth writes.
        if (mode == "Textured")
        {
            gl.DepthMask(0);
            foreach (var instance in instances.OrderByDescending(item => Vector3.DistanceSquared(Vector3.Transform(Vector3.Zero, item.Transform * ViewportCamera.SourceToGl), camera.Position)))
            {
                if (instance.Geometry is not { } geometry || !meshes.TryGetValue(geometry, out var mesh))
                {
                    continue;
                }
                Matrix(modelProgram, "uModel", instance.Transform * ViewportCamera.SourceToGl);
                NormalMatrix(instance.Transform * ViewportCamera.SourceToGl);
                Float("uHighlight", instance.ElementId == selected ? 1 : 0);
                gl.BindVertexArray(mesh.Array);
                gl.BindBuffer(GL_ELEMENT_ARRAY_BUFFER, mesh.Indices);
                foreach (var submesh in geometry.SubMeshes.Where(item => item.Material.AlphaMode == "BLEND"))
                {
                    BindMaterial(submesh.Material, true, instance.Tint);
                    gl.DrawElements(GL_TRIANGLES, submesh.IndexCount, GL_UNSIGNED_INT, submesh.IndexOffset * sizeof(uint));
                }
            }
            gl.DepthMask(1);
        }
        gl.BindVertexArray(0);
        gl.UseProgram(0);
        gl.Disable(GL_BLEND);
        gl.Disable(GL_DEPTH_TEST);
    }

    private void BindMaterial(CompiledMaterial material, bool textured, Vector4? tint)
    {
        var color = tint ?? Vector4.One;
        Vector("uBaseColor", new Vector3(0.7f));
        Vector("uBaseColorFactor", textured ? material.BaseColorFactor * color : color);
        Float("uRoughness", textured ? material.RoughnessFactor : 0.6f);
        Float("uMetallic", textured ? material.MetallicFactor : 0);
        Vector("uEmissiveFactor", textured ? material.EmissiveFactor : Vector3.Zero);
        Int("uAlphaMode", !textured ? 0 : material.AlphaMode == "BLEND" ? 2 : material.AlphaMode == "MASK" ? 1 : 0);
        Float("uAlphaCutoff", material.AlphaCutoff);
        Vector("uUvScale", material.UvScale);
        Vector("uUvOffset", material.UvOffset);
        Vector("uUvCenter", material.UvCenter);
        Float("uUvRotation", material.UvRotation);
        BindTexture(material.BaseColor, 0, "uBaseTex", "uHasBaseTex", textured, material.WrapU, material.WrapV);
        BindTexture(material.Normal, 1, "uNormalTex", "uHasNormalTex", textured, material.WrapU, material.WrapV);
        BindTexture(material.MetallicRoughness, 2, "uMRTex", "uHasMRTex", textured, material.WrapU, material.WrapV);
        BindTexture(material.AmbientOcclusion, 3, "uAOTex", "uHasAO", textured, material.WrapU, material.WrapV);
        BindTexture(material.Emissive, 4, "uEmissiveTex", "uHasEmissive", textured, material.WrapU, material.WrapV);
    }

    private void BindTexture(CompiledTexture? texture, int unit, string sampler, string enabled, bool textured, int wrapU, int wrapV)
    {
        gl.ActiveTexture(GL_TEXTURE0 + unit);
        Int(sampler, unit);
        Int(enabled, textured && texture is not null ? 1 : 0);
        if (!textured || texture is null)
        {
            gl.BindTexture(GL_TEXTURE_2D, 0);
            return;
        }
        if (!textures.TryGetValue(texture, out var id))
        {
            id = gl.GenTexture();
            gl.BindTexture(GL_TEXTURE_2D, id);
            fixed (byte* pointer = texture.Rgba.AsSpan())
            {
                gl.TexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, texture.Width, texture.Height, 0, GL_RGBA, GL_UNSIGNED_BYTE, (IntPtr)pointer);
            }
            gl.TexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
            gl.TexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
            textures[texture] = id;
        }
        gl.BindTexture(GL_TEXTURE_2D, id);
        gl.TexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, wrapU == 0 ? GL_REPEAT : wrapU);
        gl.TexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, wrapV == 0 ? GL_REPEAT : wrapV);
    }

    internal void Capture(string path, int width, int height)
    {
        var pixels = new byte[checked(width * height * 4)];
        fixed (byte* pointer = pixels)
        {
            gl.Finish();
            readPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE, (IntPtr)pointer);
        }
        using var bitmap = new WriteableBitmap(new(width, height), new(96, 96), PixelFormat.Rgba8888, AlphaFormat.Opaque);
        using (var buffer = bitmap.Lock())
        {
            for (var row = 0; row < height; row++)
            {
                Marshal.Copy(pixels, (height - row - 1) * width * 4, buffer.Address + row * buffer.RowBytes, width * 4);
            }
        }
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
        bitmap.Save(path, PngBitmapEncoderOptions.Default);
    }

    private void ReleaseScene()
    {
        foreach (var mesh in meshes.Values)
        {
            gl.DeleteVertexArray(mesh.Array);
            gl.DeleteBuffer(mesh.Vertices);
            gl.DeleteBuffer(mesh.Indices);
            gl.DeleteBuffer(mesh.Lines);
        }
        foreach (var texture in textures.Values)
        {
            gl.DeleteTexture(texture);
        }
        meshes.Clear();
        textures.Clear();
    }

    public void Dispose()
    {
        ReleaseScene();
        gl.DeleteBuffer(gridBuffer);
        gl.DeleteVertexArray(gridArray);
        gl.DeleteRenderbuffer(depthBuffer);
        gl.DeleteProgram(modelProgram);
        gl.DeleteProgram(gridProgram);
    }
}

using Datamodel;
using DM = Datamodel.Datamodel;

namespace SourcePorter.Core.Vmap;

/// <summary>
/// A loaded uncompiled CS2 <c>.vmap</c> — a Datamodel/DMX graph serialised as
/// KeyValues2/binary, read and written via the <c>KeyValues2</c> package (the same
/// serializer the Source 2 Viewer uses; see ARCHITECTURE.md §5). Wraps the underlying
/// <see cref="DM"/> with the vmap-specific navigation the post-import tools need — the
/// world entity and its child-node array — and preserves the file's original
/// encoding+version on save so CS2/Hammer still read it.
///
/// The imported main map is text KeyValues2 and its sub-maps are binary DMX; both load
/// transparently because <see cref="DM.Load(string, Codecs.DeferredMode)"/> picks the
/// codec from the file's DMX header.
/// </summary>
public sealed class VmapDocument
{
    private VmapDocument(DM model, string path)
    {
        Model = model;
        Path = path;
    }

    /// <summary>The path the document was loaded from / saves to by default.</summary>
    public string Path { get; }

    /// <summary>The underlying Datamodel (root, encoding, <c>ImportElement</c>, …).</summary>
    public DM Model { get; }

    /// <summary>The vmap root element (<c>CMapRootElement</c>).</summary>
    public Element Root =>
        Model.Root ?? throw new InvalidVmapException($"{Path}: file has no root element.");

    /// <summary>The world entity (<c>CMapWorld</c>) under the root's <c>world</c> attribute.</summary>
    public Element World =>
        Root.ContainsKey("world") && Root["world"] is Element world
            ? world
            : throw new InvalidVmapException($"{Path}: missing the top-level 'world' element.");

    /// <summary>
    /// The world's <c>children</c> node array (entities, meshes, prefab references, …).
    /// Created empty if absent so callers can always add to it.
    /// </summary>
    public ElementArray WorldChildren
    {
        get
        {
            var world = World;
            if (world.ContainsKey("children") && world["children"] is ElementArray existing)
                return existing;
            var created = new ElementArray();
            world["children"] = created;
            return created;
        }
    }

    /// <summary>
    /// The world's <c>children</c> array if present, else <c>null</c> — a non-throwing
    /// read for files that may not be well-formed maps (used when merging sub-maps).
    /// </summary>
    public ElementArray? TryGetWorldChildren()
    {
        var root = Model.Root;
        if (root is null || !root.ContainsKey("world") || root["world"] is not Element world)
            return null;
        return world.ContainsKey("children") && world["children"] is ElementArray children ? children : null;
    }

    /// <summary>Replaces the world's child nodes with an empty array (skybox template).</summary>
    public void ClearWorldChildren() => World["children"] = new ElementArray();

    /// <summary>Loads a <c>.vmap</c> from disk.</summary>
    public static VmapDocument Load(string path) => new(DM.Load(path), path);

    /// <summary>
    /// Loads a <c>.vmap</c> from an in-memory copy of the file so the file handle is <b>not</b>
    /// held open — required when we mean to overwrite the same path (a binary DMX <see cref="DM.Load(string)"/>
    /// keeps the file locked for deferred reads, so <see cref="Save"/> to the same path would fail).
    /// </summary>
    public static VmapDocument LoadInMemory(string path) =>
        new(DM.Load(File.ReadAllBytes(path), Datamodel.Codecs.DeferredMode.Disabled), path);

    /// <summary>
    /// Saves to <paramref name="path"/> (default: the load path) using the document's
    /// own encoding+version, so a text KeyValues2 map stays text and a binary map stays
    /// binary — i.e. the file keeps a form CS2/Hammer accept.
    /// </summary>
    public void Save(string? path = null)
    {
        var encoding = string.IsNullOrEmpty(Model.Encoding) ? "keyvalues2" : Model.Encoding;
        var version = Model.EncodingVersion > 0 ? Model.EncodingVersion : 4;
        Model.Save(path ?? Path, encoding, version);
    }
}

/// <summary>Thrown when a <c>.vmap</c> is missing the structure the tools require.</summary>
public sealed class InvalidVmapException(string message) : Exception(message);

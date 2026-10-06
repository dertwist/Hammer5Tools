using System.Collections;
using System.Diagnostics.CodeAnalysis;
using System.Globalization;
using System.Security.Cryptography;
using System.Text;

using Datamodel;
using DM = Datamodel.Datamodel;

namespace Hammer5Tools.Core.Format.Vmap;

/// <summary>
/// Block-level 3-way merge for Source 2 <c>.vmap</c> files.
///
/// A <c>.vmap</c> is binary DMX, so git can only ever take one whole side of a
/// conflict. This splits a map into <i>blocks</i> — the map nodes under
/// <c>CMapWorld</c> (entities, meshes, groups, smart props, path nodes, the world
/// itself) — keyed by the DMX element GUID, which Hammer keeps stable across
/// saves. Comparing per-block digests shows which side touched what, so edits
/// from two branches combine and only genuine both-sides edits are reported as
/// conflicts for the caller to resolve by picking a primary.
///
/// Given a common ancestor (<c>basePath</c>) this is a real 3-way merge: a block
/// only conflicts when both sides changed it differently. Without one it falls
/// back to 2-way union — every block present on either side survives, and blocks
/// that differ are conflicts.
///
/// When the two files share no GUIDs at all — a Save As, a re-import, a rebuilt
/// map — nodes are re-paired by content instead (identical digest first, then
/// class + nodeID, one-to-one) so a shared object merges rather than being added
/// a second time.
///
/// Two facts drive the implementation, both verified against Hammer-saved maps:
///
/// * Map-node GUIDs are stable across saves, but the GUIDs of their sub-elements
///   (meshData, relayPlugData, transformPin, nodeData, …) are regenerated on every
///   save. Digests therefore compare values and deliberately ignore element IDs;
///   comparing IDs would report every node as modified.
/// * Datamodel.NET's binary writer drops the DMX prefix-attribute block, where the
///   map thumbnail and the asset-reference cache live (see
///   <see cref="VmapReferenceRewriter.PrefixEnd"/>, which the same problem forced
///   for reference rewriting). Those bytes are copied back from the primary file
///   after saving.
/// </summary>
internal static class VmapMerger
{
    public const string Ours = "ours";
    public const string Theirs = "theirs";

    /// <summary>
    /// The world node is identified by its role (<c>Root["world"]</c>), never by
    /// GUID: it is the root of the block tree, and a Save As hands a map an
    /// all-new set of GUIDs. Matching it by GUID would import one map's world as
    /// a child of the other's, which Hammer cannot load.
    /// </summary>
    internal const string WorldId = "\0world";

    private const int MaxDepth = 24;

    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.Binary", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.KeyValues2", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, typeof(ElementFactory))]
    /// <summary>
    /// Merges two <c>.vmap</c> files block by block. <paramref name="basePath"/> is
    /// the common ancestor (git's <c>%O</c>); without it the merge is 2-way — the
    /// union of both sides, with differing blocks reported as conflicts. Only a
    /// base can tell "they changed it" apart from "we changed it".
    ///
    /// Maps whose GUIDs share nothing are re-paired by content first, so a Save As
    /// still merges rather than duplicating every object.
    ///
    /// Throws <see cref="InvalidOperationException"/> if even that finds no common
    /// object: the two files are not versions of one map, and a "merge" would
    /// just stack two sets of geometry on top of each other. Pass
    /// <paramref name="allowUnrelated"/> = true if that pile-everything-in
    /// behavior is genuinely wanted.
    /// </summary>
    public static VmapMergeSession Merge(string oursPath, string theirsPath, string? basePath, bool allowUnrelated)
    {
        var session = new VmapMergeSession(
            new VmapMergeDoc(oursPath), new VmapMergeDoc(theirsPath),
            basePath is null ? null : new VmapMergeDoc(basePath));
        var ours = session.OursDoc;
        var theirs = session.TheirsDoc;
        var ancestor = session.BaseDoc;

        session.Shared = SharedIds(ours, theirs);
        if (session.Shared.Count == 0 && ours.Blocks.Count > 1 && theirs.Blocks.Count > 1)
        {
            session.Realigned = Realign(ours, theirs);
            if (session.Realigned.Count > 0)
            {
                theirs.Blocks = Scan(theirs.Dm);
                session.Shared = SharedIds(ours, theirs);
            }
        }
        if (session.Shared.Count == 0 && ours.Blocks.Count > 1 && theirs.Blocks.Count > 1 && !allowUnrelated)
        {
            throw new InvalidOperationException(
                $"{Path.GetFileName(oursPath)} and {Path.GetFileName(theirsPath)} share no block identity " +
                $"(0 of {ours.Blocks.Count - 1}/{theirs.Blocks.Count - 1} nodes) and no node pairs by content " +
                "either, so they are not two versions of the same map. Merging them would just stack both " +
                "maps' contents in one file. Pass allowUnrelated=true if that is what you want.");
        }

        foreach (var bid in ours.Blocks.Keys.Union(theirs.Blocks.Keys))
        {
            ours.Blocks.TryGetValue(bid, out var o);
            theirs.Blocks.TryGetValue(bid, out var t);
            var od = o?.Digest;
            var td = t?.Digest;
            string? decision;
            string? note;

            if (ancestor is null)
            {
                if (o is null) { decision = Theirs; note = "added"; }
                else if (t is null || od == td) { decision = Ours; note = null; }
                else { decision = null; note = "both sides differ (no common ancestor)"; }
            }
            else
            {
                ancestor.Blocks.TryGetValue(bid, out var baseBlock);
                var bd = baseBlock?.Digest;
                if (td == bd || od == td) { decision = Ours; note = null; }
                else if (od == bd)
                {
                    decision = Theirs;
                    note = o is null ? "added" : t is null ? "removed" : "changed";
                }
                else if (o is null || t is null) { decision = null; note = "deleted on one side, changed on the other"; }
                else { decision = null; note = "both sides changed it"; }
            }

            if (decision is null)
            {
                var source = o ?? t!;
                session.Conflicts.Add(new VmapMergeConflict(bid, source.Kind, source.Label, note!, o, t));
            }
            else
            {
                session.Decisions[bid] = decision;
                if (note == "added") session.Added.Add(t!);
                else if (note == "removed") session.Removed.Add(o!);
                else if (note == "changed") session.Changed.Add(t!);
            }
        }

        session.Conflicts = [.. session.Conflicts
            .OrderBy(c => c.Kind, StringComparer.Ordinal)
            .ThenBy(c => c.Label, StringComparer.Ordinal)];
        return session;
    }

    private static HashSet<string> SharedIds(VmapMergeDoc ours, VmapMergeDoc theirs) =>
        [.. ours.Blocks.Keys.Intersect(theirs.Blocks.Keys).Where(id => id != WorldId)];

    /// <summary>Walks the world's node tree, keying every node by its (save-stable) GUID.</summary>
    internal static Dictionary<string, VmapMergeBlock> Scan(DM dm)
    {
        var blocks = new Dictionary<string, VmapMergeBlock>();

        void Visit(Element element, string blockId)
        {
            var kids = element.ContainsKey("children") && element["children"] is ElementArray array
                ? array.Where(child => child is not null).Select(child => child!).ToList()
                : [];
            var block = new VmapMergeBlock
            {
                Id = blockId,
                Kind = element.ClassName,
                Element = element,
                Label = LabelOf(element),
                // Fallback identity for maps whose GUIDs were regenerated. Class is part of
                // the key because Hammer reuses nodeIDs: nodeID 10 can be a mesh in one map
                // and a prop_static in the other.
                Ident = element.ContainsKey("nodeID")
                    ? $"n:{element.ClassName}:{ClassNameOf(element)}:{ToInvariantString(element["nodeID"])}"
                    : null,
                ChildIds = [.. kids.Select(child => child.ID.ToString())],
                Digest = Sha256Hex(ElementSignature(element, [], 0)),
            };
            blocks[blockId] = block;
            foreach (var kid in kids)
                Visit(kid, kid.ID.ToString());
        }

        var root = dm.Root ?? throw new InvalidVmapException("VMAP has no root element.");
        if (root["world"] is not Element world)
            throw new InvalidVmapException("VMAP root has no 'world' element.");
        Visit(world, WorldId);
        return blocks;
    }

    /// <summary>Entity classname, or "" for anything that is not an entity.</summary>
    private static string ClassNameOf(Element element)
    {
        if (!element.ContainsKey("entity_properties"))
            return "";
        try
        {
            if (element["entity_properties"] is not Element entityProperties)
                return "";
            return entityProperties.ContainsKey("classname")
                ? ToInvariantString(entityProperties["classname"])
                : "";
        }
        catch (Exception exception) when (exception is InvalidCastException or KeyNotFoundException)
        {
            return "";
        }
    }

    /// <summary>Human-readable name for conflict reporting.</summary>
    private static string LabelOf(Element element)
    {
        var className = ClassNameOf(element);
        if (className.Length > 0)
        {
            var name = "";
            try
            {
                if (element["entity_properties"] is Element entityProperties && entityProperties.ContainsKey("targetname"))
                    name = ToInvariantString(entityProperties["targetname"]);
            }
            catch (Exception exception) when (exception is InvalidCastException or KeyNotFoundException)
            {
                // name stays ""
            }
            return name.Length > 0 ? $"{className} ({name})" : className;
        }
        return !string.IsNullOrEmpty(element.Name) ? element.Name : element.ClassName;
    }

    private static string ValueSignature(object? value, HashSet<Guid> seen, int depth)
    {
        switch (value)
        {
            case null:
                return "~";
            case Element element:
                return ElementSignature(element, seen, depth + 1);
            case byte[] bytes:
                return "b" + Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
            case string text:
                return text;
            case ElementArray elements:
                return "[" + string.Join(",", elements.Select(item => ValueSignature(item, seen, depth + 1))) + "]";
            case IEnumerable enumerable:
                return "[" + string.Join(",", enumerable.Cast<object?>().Select(item => ValueSignature(item, seen, depth + 1))) + "]";
            default:
                return ToInvariantString(value);
        }
    }

    /// <summary>
    /// Value signature of an element subtree, blind to element GUIDs.
    /// <c>children</c> is skipped: it is the block-tree link, merged separately, so
    /// a group is only "modified" when its own attributes change — not when
    /// someone adds an entity to it.
    /// </summary>
    private static string ElementSignature(Element? element, HashSet<Guid> seen, int depth)
    {
        if (element is null)
            return "~";
        if (depth > MaxDepth || seen.Contains(element.ID))
            return "*";
        var nextSeen = new HashSet<Guid>(seen) { element.ID };

        var parts = new List<string> { element.ClassName, element.Name ?? "" };
        foreach (var key in element.Keys.OrderBy(k => k, StringComparer.Ordinal))
        {
            if (key == "children")
                continue;
            parts.Add(key + "=" + ValueSignature(element[key], nextSeen, depth));
        }
        return "{" + string.Join("|", parts) + "}";
    }

    private static string ToInvariantString(object? value) => value switch
    {
        null => "",
        IFormattable formattable => formattable.ToString(null, CultureInfo.InvariantCulture),
        _ => value.ToString() ?? "",
    };

    private static string Sha256Hex(string text) =>
        Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(text))).ToLowerInvariant();

    /// <summary>key -&gt; block id, dropping any key more than one block claims.</summary>
    private static Dictionary<string, string> Unique(
        Dictionary<string, VmapMergeBlock> blocks, IEnumerable<string> ids, Func<VmapMergeBlock, string?> key)
    {
        var index = new Dictionary<string, string>();
        var duplicates = new HashSet<string>();
        foreach (var id in ids)
        {
            var k = key(blocks[id]);
            if (k is null)
                continue;
            if (index.ContainsKey(k))
                duplicates.Add(k);
            index[k] = id;
        }
        foreach (var k in duplicates)
            index.Remove(k);
        return index;
    }

    /// <summary>
    /// Stamps ours' GUIDs onto theirs' nodes wherever the two are the same object.
    /// Only for maps whose GUIDs have nothing in common — a Save As, a re-import, a
    /// rebuilt map hands every node a fresh one. Without this every node looks new
    /// and the "merge" is two copies of the map stacked in one file. Matching is
    /// strongest-first and strictly one-to-one: identical content, then class +
    /// nodeID (Hammer's per-map counter, which survives ordinary edits). Anything
    /// ambiguous on either side is left alone and stays a genuine addition.
    /// </summary>
    private static Dictionary<string, string> Realign(VmapMergeDoc ours, VmapMergeDoc theirs)
    {
        var oursLeft = new HashSet<string>(ours.Blocks.Keys.Where(id => id != WorldId));
        var theirsLeft = new HashSet<string>(theirs.Blocks.Keys.Where(id => id != WorldId));
        var pairs = new Dictionary<string, string>();

        Func<VmapMergeBlock, string?>[] keySelectors =
        [
            block => "d:" + block.Digest,
            block => block.Ident,
        ];
        foreach (var keySelector in keySelectors)
        {
            var oursIndex = Unique(ours.Blocks, oursLeft, keySelector);
            var theirsIndex = Unique(theirs.Blocks, theirsLeft, keySelector);
            foreach (var (key, theirsId) in theirsIndex)
            {
                if (!oursIndex.TryGetValue(key, out var oursId))
                    continue;
                pairs[theirsId] = oursId;
                oursLeft.Remove(oursId);
                theirsLeft.Remove(theirsId);
            }
        }
        foreach (var (theirsId, oursId) in pairs)
            theirs.Blocks[theirsId].Element.ID = ours.Blocks[oursId].Element.ID;
        return pairs;
    }

    /// <summary>Restores src's thumbnail / asset-reference block into a freshly saved file.</summary>
    internal static bool SplicePrefix(string srcPath, string outPath)
    {
        var src = File.ReadAllBytes(srcPath);
        var output = File.ReadAllBytes(outPath);
        var srcEnd = VmapReferenceRewriter.PrefixEnd(src);
        var outEnd = VmapReferenceRewriter.PrefixEnd(output);
        if (srcEnd is null || outEnd is null)
            return false;

        var combined = new byte[srcEnd.Value + (output.Length - outEnd.Value)];
        Array.Copy(src, 0, combined, 0, srcEnd.Value);
        Array.Copy(output, outEnd.Value, combined, srcEnd.Value, output.Length - outEnd.Value);
        File.WriteAllBytes(outPath, combined);
        return true;
    }
}

/// <summary>One map node, identified by its (save-stable) DMX element GUID.</summary>
internal sealed class VmapMergeBlock
{
    public required string Id { get; init; }
    public required string Kind { get; init; }
    public required string Label { get; init; }
    public required string Digest { get; init; }
    public string? Ident { get; init; }
    public required List<string> ChildIds { get; init; }
    public required Element Element { get; init; }
}

/// <summary>A block both sides changed differently. Resolved by picking ours or theirs.</summary>
internal sealed class VmapMergeConflict(
    string id, string kind, string label, string reason, VmapMergeBlock? ours, VmapMergeBlock? theirs)
{
    public string Id { get; } = id;
    public string Kind { get; } = kind;
    public string Label { get; } = label;
    public string Reason { get; } = reason;
    public VmapMergeBlock? Ours { get; } = ours;
    public VmapMergeBlock? Theirs { get; } = theirs;
}

/// <summary>A loaded <c>.vmap</c> and its blocks.</summary>
internal sealed class VmapMergeDoc : IDisposable
{
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.Binary", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.KeyValues2", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, typeof(ElementFactory))]
    public VmapMergeDoc(string path)
    {
        Path = path;
        // Disabled, not Automatic: the merge reads every attribute anyway and
        // imported elements must not depend on a stream about to be closed.
        Dm = DM.Load(path, Datamodel.Codecs.DeferredMode.Disabled);
        Blocks = VmapMerger.Scan(Dm);
    }

    public string Path { get; }
    public DM Dm { get; private set; }
    public Dictionary<string, VmapMergeBlock> Blocks { get; set; }

    public void Dispose() => Dm.Dispose();
}

/// <summary>
/// The outcome of <see cref="VmapMerger.Merge"/>: decisions, conflicts, and the
/// loaded documents needed to <see cref="Write"/> the result. Disposable — owns
/// the three loaded <see cref="VmapMergeDoc"/> instances.
/// </summary>
internal sealed class VmapMergeSession(VmapMergeDoc ours, VmapMergeDoc theirs, VmapMergeDoc? @base) : IDisposable
{
    public VmapMergeDoc OursDoc { get; } = ours;
    public VmapMergeDoc TheirsDoc { get; } = theirs;
    public VmapMergeDoc? BaseDoc { get; } = @base;

    public Dictionary<string, string> Decisions { get; } = [];
    public List<VmapMergeConflict> Conflicts { get; set; } = [];
    public List<VmapMergeBlock> Added { get; } = [];
    public List<VmapMergeBlock> Removed { get; } = [];
    public List<VmapMergeBlock> Changed { get; } = [];
    public List<VmapMergeBlock> Orphaned { get; } = [];
    public HashSet<string> Shared { get; set; } = [];
    public Dictionary<string, string> Realigned { get; set; } = [];

    private readonly Dictionary<string, string> _choices = [];

    public void Resolve(string blockId, string side)
    {
        if (side != VmapMerger.Ours && side != VmapMerger.Theirs)
            throw new ArgumentException("side must be 'ours' or 'theirs'.", nameof(side));
        _choices[blockId] = side;
    }

    /// <summary>Picks one side for every remaining conflict — the "primary vmap" choice.</summary>
    public void ResolveAll(string side)
    {
        foreach (var conflict in Conflicts)
            _choices.TryAdd(conflict.Id, side);
    }

    public List<VmapMergeConflict> Unresolved => [.. Conflicts.Where(c => !_choices.ContainsKey(c.Id))];

    public string SideFor(string blockId) =>
        _choices.TryGetValue(blockId, out var choice) ? choice
        : Decisions.TryGetValue(blockId, out var decision) ? decision
        : VmapMerger.Ours;

    private Dictionary<string, VmapMergeBlock> Alive()
    {
        var alive = new Dictionary<string, VmapMergeBlock>();
        foreach (var blockId in OursDoc.Blocks.Keys.Union(TheirsDoc.Blocks.Keys))
        {
            var source = SideFor(blockId) == VmapMerger.Theirs ? TheirsDoc : OursDoc;
            if (source.Blocks.TryGetValue(blockId, out var block))
                alive[blockId] = block;
        }
        return alive;
    }

    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.Binary", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.KeyValues2", "Datamodel.NET")]
    /// <summary>Applies the merge onto ours' datamodel and saves it to <paramref name="outPath"/>.</summary>
    public void Write(string outPath)
    {
        if (Unresolved.Count > 0)
            throw new InvalidOperationException($"{Unresolved.Count} unresolved conflict(s); resolve them first.");

        var alive = Alive();
        var oursDm = OursDoc.Dm;

        // Detach every incoming node's children before importing: the children
        // arrays are rebuilt from merged membership below, and a recursive import
        // that dragged whole subtrees along would clobber blocks kept from ours.
        foreach (var block in TheirsDoc.Blocks.Values)
            if (block.Element.ContainsKey("children") && block.Element["children"] is ElementArray childArray)
                childArray.Clear();

        var elements = new Dictionary<string, Element>();
        foreach (var (blockId, block) in alive)
        {
            elements[blockId] = TheirsDoc.Blocks.TryGetValue(blockId, out var theirsBlock) && ReferenceEquals(block, theirsBlock)
                ? oursDm.ImportElement(block.Element, DM.ImportRecursionMode.Recursive, DM.ImportOverwriteMode.All)
                    ?? throw new InvalidOperationException($"ImportElement returned null for block '{blockId}'.")
                : block.Element;
        }

        // Rebuild the node tree from merged membership. Existing order follows
        // ours, and their additions are appended; child ordering is not merged.
        var placed = new HashSet<string>();
        var worldId = VmapMerger.WorldId;

        void Rebuild(string blockId)
        {
            var element = elements[blockId];
            if (!element.ContainsKey("children"))
                return;
            var oursKids = OursDoc.Blocks.TryGetValue(blockId, out var oursBlock) ? oursBlock.ChildIds : [];
            var theirsKids = TheirsDoc.Blocks.TryGetValue(blockId, out var theirsBlock) ? theirsBlock.ChildIds : [];
            var order = oursKids.Where(id => alive.ContainsKey(id) && !placed.Contains(id)).ToList();
            var seen = new HashSet<string>(order);
            foreach (var id in theirsKids)
                if (alive.ContainsKey(id) && !placed.Contains(id) && seen.Add(id))
                    order.Add(id);
            foreach (var id in order)
                placed.Add(id);

            if (element["children"] is not ElementArray array)
                throw new InvalidOperationException($"Block '{blockId}' has a non-array 'children' attribute.");
            array.Clear();
            foreach (var id in order)
                array.Add(elements[id]);
            foreach (var id in order)
                Rebuild(id);
        }

        Rebuild(worldId);

        // If one side deleted a group the other side was working inside, the
        // surviving children have nowhere to hang. Re-home them on the world
        // rather than drop somebody's work on the floor.
        if (elements[worldId]["children"] is not ElementArray worldChildren)
            throw new InvalidOperationException("World element has a non-array 'children' attribute.");
        foreach (var blockId in alive.Keys.Where(id => id != worldId && !placed.Contains(id)).ToList())
        {
            if (placed.Contains(blockId))
                continue;
            placed.Add(blockId);
            worldChildren.Add(elements[blockId]);
            Rebuild(blockId);
            Orphaned.Add(alive[blockId]);
        }

        oursDm.Root!["world"] = elements[worldId];

        // Both sides allocate nodeIDs from the same counter, so imported nodes
        // routinely collide with ours. Hand collisions a fresh id.
        var used = new HashSet<int>();
        foreach (var element in elements.Values)
        {
            if (!element.ContainsKey("nodeID"))
                continue;
            var nodeId = Convert.ToInt32(element["nodeID"], CultureInfo.InvariantCulture);
            if (used.Contains(nodeId))
            {
                nodeId = used.Max() + 1;
                element["nodeID"] = nodeId;
            }
            used.Add(nodeId);
        }

        var encoding = string.IsNullOrEmpty(oursDm.Encoding) ? "keyvalues2" : oursDm.Encoding;
        var version = oursDm.EncodingVersion > 0 ? oursDm.EncodingVersion : 4;
        oursDm.Save(outPath, encoding, version);
        // The codec drops the thumbnail / asset-reference cache; put it back.
        VmapMerger.SplicePrefix(OursDoc.Path, outPath);
    }

    public void Dispose()
    {
        OursDoc.Dispose();
        TheirsDoc.Dispose();
        BaseDoc?.Dispose();
    }
}

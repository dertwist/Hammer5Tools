using Datamodel;
using Hammer5Tools.Core.Format.Vmap;
using DM = Datamodel.Datamodel;

namespace SourcePorter.Core.Tests;

public sealed class VmapMergerTests
{
    [Fact]
    public void Merge_with_identical_files_has_no_conflicts()
    {
        using var fixture = new TempMapSet();
        var id = Guid.NewGuid();
        WriteMap(fixture.Ours, id, "prop_a", "1");
        WriteMap(fixture.Theirs, id, "prop_a", "1");

        using var session = VmapMerger.Merge(fixture.Ours, fixture.Theirs, basePath: null, allowUnrelated: false);

        Assert.Empty(session.Conflicts);
        Assert.Contains(id.ToString(), session.Shared);
    }

    [Fact]
    public void Merge_three_way_only_theirs_changed_picks_theirs()
    {
        using var fixture = new TempMapSet();
        var id = Guid.NewGuid();
        WriteMap(fixture.Base, id, "prop_a", "1");
        WriteMap(fixture.Ours, id, "prop_a", "1");
        WriteMap(fixture.Theirs, id, "prop_a", "2");

        using var session = VmapMerger.Merge(fixture.Ours, fixture.Theirs, fixture.Base, allowUnrelated: false);

        Assert.Empty(session.Conflicts);
        Assert.Equal(VmapMerger.Theirs, session.SideFor(id.ToString()));
        Assert.Single(session.Changed);
    }

    [Fact]
    public void Merge_three_way_only_ours_changed_picks_ours()
    {
        using var fixture = new TempMapSet();
        var id = Guid.NewGuid();
        WriteMap(fixture.Base, id, "prop_a", "1");
        WriteMap(fixture.Ours, id, "prop_a", "2");
        WriteMap(fixture.Theirs, id, "prop_a", "1");

        using var session = VmapMerger.Merge(fixture.Ours, fixture.Theirs, fixture.Base, allowUnrelated: false);

        Assert.Empty(session.Conflicts);
        Assert.Equal(VmapMerger.Ours, session.SideFor(id.ToString()));
    }

    [Fact]
    public void Merge_three_way_both_sides_made_the_same_edit_has_no_conflict()
    {
        using var fixture = new TempMapSet();
        var id = Guid.NewGuid();
        WriteMap(fixture.Base, id, "prop_a", "1");
        WriteMap(fixture.Ours, id, "prop_a", "2");
        WriteMap(fixture.Theirs, id, "prop_a", "2");

        using var session = VmapMerger.Merge(fixture.Ours, fixture.Theirs, fixture.Base, allowUnrelated: false);

        Assert.Empty(session.Conflicts);
        Assert.Equal(VmapMerger.Ours, session.SideFor(id.ToString()));
    }

    [Fact]
    public void Merge_three_way_both_sides_changed_differently_is_a_conflict()
    {
        using var fixture = new TempMapSet();
        var id = Guid.NewGuid();
        WriteMap(fixture.Base, id, "prop_a", "1");
        WriteMap(fixture.Ours, id, "prop_a", "2");
        WriteMap(fixture.Theirs, id, "prop_a", "3");

        using var session = VmapMerger.Merge(fixture.Ours, fixture.Theirs, fixture.Base, allowUnrelated: false);

        var conflict = Assert.Single(session.Conflicts);
        Assert.Equal(id.ToString(), conflict.Id);
        Assert.Equal("both sides changed it", conflict.Reason);
        Assert.NotEmpty(session.Unresolved);
    }

    [Fact]
    public void Write_throws_while_conflicts_are_unresolved_and_succeeds_after_resolving()
    {
        using var fixture = new TempMapSet();
        var id = Guid.NewGuid();
        WriteMap(fixture.Base, id, "prop_a", "1");
        WriteMap(fixture.Ours, id, "prop_a", "2");
        WriteMap(fixture.Theirs, id, "prop_a", "3");

        using var session = VmapMerger.Merge(fixture.Ours, fixture.Theirs, fixture.Base, allowUnrelated: false);
        var outPath = Path.Combine(fixture.Directory, "merged.vmap");

        Assert.Throws<InvalidOperationException>(() => session.Write(outPath));

        session.ResolveAll(VmapMerger.Theirs);
        session.Write(outPath);

        Assert.True(File.Exists(outPath));
        var document = new ValveMapReader().Read(outPath);
        var entity = Assert.Single(document.Nodes, node => node.ClassName == "CMapEntity");
        Assert.Equal("3", entity.Properties["someAttr"]);
    }

    [Fact]
    public void Merge_reports_a_block_theirs_added_that_ours_and_base_never_had()
    {
        using var fixture = new TempMapSet();
        var baseId = Guid.NewGuid();
        var addedId = Guid.NewGuid();
        WriteMap(fixture.Base, baseId, "prop_a", "1");
        WriteMap(fixture.Ours, baseId, "prop_a", "1");
        WriteMap(fixture.Theirs, baseId, "prop_a", "1", extra: (addedId, "prop_b", "new"));

        using var session = VmapMerger.Merge(fixture.Ours, fixture.Theirs, fixture.Base, allowUnrelated: false);

        Assert.Empty(session.Conflicts);
        Assert.Contains(session.Added, block => block.Id == addedId.ToString());
        Assert.Equal(VmapMerger.Theirs, session.SideFor(addedId.ToString()));
    }

    [Fact]
    public void Merge_reports_a_block_theirs_removed_that_ours_never_touched()
    {
        using var fixture = new TempMapSet();
        var baseId = Guid.NewGuid();
        var removedId = Guid.NewGuid();
        WriteMap(fixture.Base, baseId, "prop_a", "1", extra: (removedId, "prop_b", "gone"));
        WriteMap(fixture.Ours, baseId, "prop_a", "1", extra: (removedId, "prop_b", "gone"));
        WriteMap(fixture.Theirs, baseId, "prop_a", "1");

        using var session = VmapMerger.Merge(fixture.Ours, fixture.Theirs, fixture.Base, allowUnrelated: false);

        Assert.Empty(session.Conflicts);
        Assert.Contains(session.Removed, block => block.Id == removedId.ToString());
    }

    [Fact]
    public void Merge_without_a_base_and_without_shared_identity_throws_unless_allowed()
    {
        using var fixture = new TempMapSet();
        WriteMap(fixture.Ours, Guid.NewGuid(), "prop_a", "1", extra: (Guid.NewGuid(), "prop_b", "x"));
        WriteMap(fixture.Theirs, Guid.NewGuid(), "prop_c", "9", extra: (Guid.NewGuid(), "prop_d", "y"));

        Assert.Throws<InvalidOperationException>(
            () => VmapMerger.Merge(fixture.Ours, fixture.Theirs, basePath: null, allowUnrelated: false));

        using var session = VmapMerger.Merge(fixture.Ours, fixture.Theirs, basePath: null, allowUnrelated: true);
        Assert.NotNull(session);
    }

    private static void WriteMap(
        string path, Guid entityId, string entityName, string attrValue, (Guid Id, string Name, string Value)? extra = null)
    {
        var model = new DM("vmap", 29);
        var root = new Element(model, "", null, "CMapRootElement");
        model.Root = root;
        var world = new Element(model, "", null, "CMapWorld");
        root["world"] = world;
        var children = new ElementArray();
        world["children"] = children;
        children.Add(BuildEntity(model, entityId, entityName, attrValue));
        if (extra is { } value)
            children.Add(BuildEntity(model, value.Id, value.Name, value.Value));
        model.Save(path, "keyvalues2", 4);
    }

    private static Element BuildEntity(DM model, Guid id, string targetName, string attrValue)
    {
        var entity = new Element(model, "", id, "CMapEntity")
        {
            ["nodeID"] = 1,
            ["someAttr"] = attrValue,
        };
        var entityProperties = new Element(model, "", null, "EditGameClassProps")
        {
            ["classname"] = "prop_static",
            ["targetname"] = targetName,
        };
        entity["entity_properties"] = entityProperties;
        return entity;
    }

    private sealed class TempMapSet : IDisposable
    {
        public string Directory { get; } = Path.Combine(Path.GetTempPath(), $"h5t_vmap_merge_{Guid.NewGuid():N}");
        public string Ours { get; }
        public string Theirs { get; }
        public string Base { get; }

        public TempMapSet()
        {
            System.IO.Directory.CreateDirectory(Directory);
            Ours = Path.Combine(Directory, "ours.vmap");
            Theirs = Path.Combine(Directory, "theirs.vmap");
            Base = Path.Combine(Directory, "base.vmap");
        }

        public void Dispose()
        {
            if (System.IO.Directory.Exists(Directory))
                System.IO.Directory.Delete(Directory, recursive: true);
        }
    }
}

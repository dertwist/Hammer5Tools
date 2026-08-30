using System.Diagnostics.CodeAnalysis;

namespace Hammer5Tools.Core.Format.Snapshots;

/// <summary>A particle attribute that a snapshot stream can carry.</summary>
/// <param name="Name">The stream name the engine's snapshot loader recognises.</param>
/// <param name="Type">The SOA element type the stream must declare.</param>
/// <param name="Attribute">The runtime particle attribute index the stream feeds.</param>
/// <param name="DisplayName">The label the particle editor's visualiser shows.</param>
[SuppressMessage("Naming", "CA1711:Identifiers should not have incorrect suffix", Justification = "Refers to a particle attribute, not System.Attribute.")]
public sealed record SnapshotAttribute(string Name, string Type, int Attribute, string DisplayName);

/// <summary>
/// The particle attributes a <c>.vsnap</c> can name, taken from the snapshot writer's
/// attribute-indexed jump table in <c>particles.dll</c>. Attributes missing from that table
/// (pointers, the skinning halves' aliases, and the four listed in
/// <see cref="UnnameableAttributes"/>) cannot be spelled in the file at all.
/// </summary>
public static class SnapshotAttributes
{
    private const string Float = "generic_float";
    // The compiler rejects these five as floats: "Bad data type ... expected int".
    private const string Int = "generic_int";
    private const string Vector = "generic_vector_3d";

    /// <summary>Every stream name the engine's snapshot loader accepts, in attribute order.</summary>
    public static readonly IReadOnlyList<SnapshotAttribute> All =
    [
        new("position", "position_3d", 0, "Position"),
        new("lifespan", Float, 1, "Life Duration"),
        new("velocity", Vector, 2, "Position Previous"),
        new("radius", Float, 3, "Radius"),
        new("rotation", Float, 4, "Roll"),
        new("rotation_speed", Float, 5, "Roll Speed"),
        new("color", Vector, 6, "Color"),
        new("opacity", Float, 7, "Alpha"),
        new("creation_time", Float, 8, "Creation Time"),
        new("sequence_number", Int, 9, "Sequence Number"),
        new("trail_length", Float, 10, "Trail Length"),
        new("particle_id", Int, 11, "Particle ID"),
        new("yaw", Float, 12, "Yaw"),
        new("sequence_number1", Int, 13, "Second Sequence Number"),
        new("hitbox", Int, 14, "Hitbox Index"),
        new("hitbox_offset", Vector, 15, "Hitbox Offset Position"),
        new("alpha2", Float, 16, "Alpha Alternate"),
        new("scratch_vec", Vector, 17, "Scratch Vector"),
        new("scratch_float", Float, 18, "Scratch Float 1"),
        new("pitch", Float, 20, "Pitch"),
        new("normal", "normal_3d", 21, "Normal"),
        new("glow_rgb", Vector, 22, "Glow RGB"),
        new("glow_alpha", Float, 23, "Glow Alpha"),
        // One stream feeds both Bone Indices (31) and Bone Weights (32).
        new("skinning", "bone_index_and_weight", 31, "Bone Indices / Bone Weights"),
        new("force_scale", Float, 34, "Force Scale"),
        new("manual_animation_frame", Float, 38, "Manual Animation Frame"),
        new("shader_extra_data_1", Float, 39, "Shader Extra Data 1"),
        new("shader_extra_data_2", Float, 40, "Shader Extra Data 2"),
        new("box_mins", Vector, 41, "Box Mins"),
        new("box_maxs", Vector, 42, "Box Maxs"),
        new("box_angles", Vector, 43, "Box Angles"),
        new("rope_segment_id", Int, 47, "Rope Segment ID"),
    ];

    /// <summary>
    /// Attributes the visualiser lists but no snapshot stream can name, mapped to the attribute
    /// index a <c>C_OP_SetFromCPSnapshot</c> must write to reach them from a scratch stream.
    /// </summary>
    public static readonly IReadOnlyDictionary<string, int> UnnameableAttributes =
        new Dictionary<string, int>
        {
            ["Parent Particle Index"] = 33,
            ["Parent Particle ID"] = 46,
            ["Rope Segment Data"] = 48,
        };

    private static readonly IReadOnlyDictionary<string, SnapshotAttribute> ByName =
        All.ToDictionary(attribute => attribute.Name, StringComparer.Ordinal);

    /// <summary>Finds the attribute a stream name feeds, or null when the engine would drop it.</summary>
    public static SnapshotAttribute? Find(string name) =>
        ByName.TryGetValue(name, out var attribute) ? attribute : null;

    /// <summary>Throws when a stream would not survive a round trip through the engine.</summary>
    public static void ValidateStream(string name, string type)
    {
        var attribute = Find(name)
            ?? throw new InvalidDataException(
                $"Snapshot stream '{name}' is not a particle attribute the engine can load; it would be dropped. " +
                $"Valid names: {string.Join(", ", All.Select(candidate => candidate.Name))}.");
        if (attribute.Type != type)
        {
            throw new InvalidDataException(
                $"Snapshot stream '{name}' must declare type '{attribute.Type}', not '{type}'.");
        }
    }
}

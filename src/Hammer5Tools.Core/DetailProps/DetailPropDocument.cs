namespace Hammer5Tools.Core.DetailProps;

using System.Globalization;
using System.Text;
using ValveKeyValue;

/// <summary>
/// Reads the baseline CDetailPropType schema and preserves metadata and unknown fields.
/// </summary>
public class DetailPropDocument
{
    public const string DefaultHeader = "<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->";
    private static readonly KVSerializer Serializer = KVSerializer.Create(KVSerializationFormat.KeyValues3Text);
    private readonly KVObject Metadata = new();
    private KVHeader Header = new();
    public List<DetailPropType> Types { get; } = [];

    public static DetailPropDocument Parse(string text)
    {
        var document = new DetailPropDocument();
        if (string.IsNullOrWhiteSpace(text))
        {
            return document;
        }

        using var input = new MemoryStream(Encoding.UTF8.GetBytes(text));
        var parsed = Serializer.Deserialize(input);
        document.Header = parsed.Header ?? new KVHeader();
        foreach (var (name, value) in parsed.Root.Children)
        {
            if (!value.IsCollection || name is "generic_data_type" or "editor_info")
            {
                document.Metadata[name] = value;
                continue;
            }

            var type = new DetailPropType(name) { Original = value, Density = ReadFloat(value, "m_flDensity", 1f) };
            if (value.TryGetValue("m_Models", out var models))
            {
                foreach (var item in models.Values)
                {
                    var model = new DetailPropModel { Original = item };
                    model.ModelName = ReadString(item, "m_ModelName", string.Empty);
                    model.MinScale = ReadFloat(item, "m_flMinScale", 1f);
                    model.MaxScale = ReadFloat(item, "m_flMaxScale", 1f);
                    model.Density = ReadFloat(item, "m_flDensity", 1f);
                    model.RandomYaw = ReadBool(item, "m_bRandomYaw", true);
                    model.RandomPitch = ReadBool(item, "m_bRandomPitch", false);
                    model.RandomRoll = ReadBool(item, "m_bRandomRoll", false);
                    model.AlignToSurface = ReadBool(item, "m_bAlignToSurface", false);
                    model.Upright = ReadBool(item, "m_bUpright", true);
                    model.MaterialGroup = ReadString(item, "m_MaterialGroup", string.Empty);
                    model.Weight = ReadFloat(item, "m_flWeight", 1f);
                    model.StartFadeSize = ReadFloat(item, "m_flStartFadeSize", 0.02f);
                    model.EndFadeSize = ReadFloat(item, "m_flEndFadeSize", 0.0125f);
                    model.WorldSpaceOrientation = ReadBool(item, "m_bWorldSpaceOrientation", false);
                    model.OrientToSurface = ReadFloat(item, "m_flOrientToSurface", 1f);
                    model.MinSurfaceSlope = ReadFloat(item, "m_flMinSurfaceSlope", 0f);
                    model.MaxSurfaceSlope = ReadFloat(item, "m_flMaxSurfaceSlope", 180f);
                    model.VerticalOffsetMin = ReadFloat(item, "m_flRandomVerticalOffsetMin", 0f);
                    model.VerticalOffsetMax = ReadFloat(item, "m_flRandomVerticalOffsetMax", 0f);
                    model.RotationMin = ReadVector(item, "m_vRandomRotationMin", Vector3.Zero);
                    model.RotationMax = ReadVector(item, "m_vRandomRotationMax", new(0, 360, 0));
                    model.RandomScaleMin = ReadFloat(item, "m_flRandomScaleMin", 1f);
                    model.RandomScaleMax = ReadFloat(item, "m_flRandomScaleMax", 1f);
                    model.DensityMinScale = ReadFloat(item, "m_flDensityMinScale", 1f);
                    model.BlendWeightMinScale = ReadFloat(item, "m_flBlendWeightMinScale", 1f);
                    model.BlendWeightMin = ReadFloat(item, "m_flBlendWeightMin", 0.25f);
                    model.BlendWeightMax = ReadFloat(item, "m_flBlendWeightMax", 1f);
                    model.BlendWeightFullDensity = ReadFloat(item, "m_flBlendWeightFullDenstity", 0.75f);
                    model.CastStaticShadows = ReadBool(item, "m_bCastStaticShadows", false);
                    type.Models.Add(model);
                }
            }

            document.Types.Add(type);
        }

        return document;
    }

    public static DetailPropDocument Load(string path)
    {
        return Parse(File.ReadAllText(path));
    }

    public void Save(string path)
    {
        Formats.DocumentFile.Write(path, Serialize());
    }

    public string Serialize()
    {
        var root = Copy(Metadata);
        root.TryAdd("generic_data_type", new KVObject("CDetailPropType"));
        foreach (var type in Types)
        {
            var value = Copy(type.Original);
            value["m_flDensity"] = new KVObject(type.Density);
            var models = KVObject.Array();
            foreach (var model in type.Models)
            {
                var item = Copy(model.Original);
                item["m_ModelName"] = new KVObject(model.ModelName) { Flag = KVFlag.ResourceName };
                item["m_MaterialGroup"] = new KVObject(model.MaterialGroup);
                item["m_flWeight"] = new KVObject(model.Weight);
                item["m_flStartFadeSize"] = new KVObject(model.StartFadeSize);
                item["m_flEndFadeSize"] = new KVObject(model.EndFadeSize);
                item["m_bWorldSpaceOrientation"] = new KVObject(model.WorldSpaceOrientation);
                item["m_flOrientToSurface"] = new KVObject(model.OrientToSurface);
                item["m_flMinSurfaceSlope"] = new KVObject(model.MinSurfaceSlope);
                item["m_flMaxSurfaceSlope"] = new KVObject(model.MaxSurfaceSlope);
                item["m_flRandomVerticalOffsetMin"] = new KVObject(model.VerticalOffsetMin);
                item["m_flRandomVerticalOffsetMax"] = new KVObject(model.VerticalOffsetMax);
                item["m_vRandomRotationMin"] = KVObject.Array([new KVObject(model.RotationMin.X), new KVObject(model.RotationMin.Y), new KVObject(model.RotationMin.Z)]);
                item["m_vRandomRotationMax"] = KVObject.Array([new KVObject(model.RotationMax.X), new KVObject(model.RotationMax.Y), new KVObject(model.RotationMax.Z)]);
                item["m_flRandomScaleMin"] = new KVObject(model.RandomScaleMin);
                item["m_flRandomScaleMax"] = new KVObject(model.RandomScaleMax);
                item["m_flDensityMinScale"] = new KVObject(model.DensityMinScale);
                item["m_flBlendWeightMinScale"] = new KVObject(model.BlendWeightMinScale);
                item["m_flBlendWeightMin"] = new KVObject(model.BlendWeightMin);
                item["m_flBlendWeightMax"] = new KVObject(model.BlendWeightMax);
                item["m_flBlendWeightFullDenstity"] = new KVObject(model.BlendWeightFullDensity);
                item["m_bCastStaticShadows"] = new KVObject(model.CastStaticShadows);
                if (model.Original.ContainsKey("m_flMinScale"))
                {
                    item["m_flMinScale"] = new KVObject(model.MinScale);
                }
                if (model.Original.ContainsKey("m_flMaxScale"))
                {
                    item["m_flMaxScale"] = new KVObject(model.MaxScale);
                }
                if (model.Original.ContainsKey("m_flDensity"))
                {
                    item["m_flDensity"] = new KVObject(model.Density);
                }
                if (model.Original.ContainsKey("m_bRandomYaw"))
                {
                    item["m_bRandomYaw"] = new KVObject(model.RandomYaw);
                }
                if (model.Original.ContainsKey("m_bRandomPitch"))
                {
                    item["m_bRandomPitch"] = new KVObject(model.RandomPitch);
                }
                if (model.Original.ContainsKey("m_bRandomRoll"))
                {
                    item["m_bRandomRoll"] = new KVObject(model.RandomRoll);
                }
                if (model.Original.ContainsKey("m_bAlignToSurface"))
                {
                    item["m_bAlignToSurface"] = new KVObject(model.AlignToSurface);
                }
                if (model.Original.ContainsKey("m_bUpright"))
                {
                    item["m_bUpright"] = new KVObject(model.Upright);
                }
                models.Add(item);
            }

            value["m_Models"] = models;
            root[type.Name] = value;
        }

        using var output = new MemoryStream();
        Serializer.Serialize(output, new KVDocument(Header, string.Empty, root));
        return Encoding.UTF8.GetString(output.ToArray());
    }

    public DetailPropType AddType(string name, float density = 1f)
    {
        var type = new DetailPropType(name, density);
        Types.Add(type);
        return type;
    }

    public bool RemoveType(string name)
    {
        var type = Types.FirstOrDefault(item => item.Name.Equals(name, StringComparison.OrdinalIgnoreCase));
        return type is not null && Types.Remove(type);
    }

    private static KVObject Copy(KVObject value)
    {
        var copy = new KVObject();
        foreach (var (key, child) in value.Children)
        {
            copy[key] = child;
        }

        return copy;
    }

    private static string ReadString(KVObject value, string key, string fallback)
    {
        return value.TryGetValue(key, out var item) ? item.ToString() : fallback;
    }

    private static float ReadFloat(KVObject value, string key, float fallback)
    {
        return value.TryGetValue(key, out var item) ? item.ToSingle(CultureInfo.InvariantCulture) : fallback;
    }

    private static bool ReadBool(KVObject value, string key, bool fallback)
    {
        return value.TryGetValue(key, out var item) ? item.ToBoolean(CultureInfo.InvariantCulture) : fallback;
    }

    private static Vector3 ReadVector(KVObject value, string key, Vector3 fallback)
    {
        return value.TryGetValue(key, out var item) && item.Count == 3
            ? new Vector3(item[0].ToSingle(CultureInfo.InvariantCulture), item[1].ToSingle(CultureInfo.InvariantCulture), item[2].ToSingle(CultureInfo.InvariantCulture))
            : fallback;
    }
}

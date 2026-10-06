using System.Collections;
using System.Diagnostics.CodeAnalysis;
using System.Text;

using Datamodel;
using Hammer5Tools.Core;

namespace Hammer5Tools.Core.Format.Vmap;

/// <summary>Rewrites content-relative asset paths in a VMAP without exposing Datamodel objects.</summary>
public static class VmapReferenceRewriter
{
    /// <summary>Rewrites every matching string in the VMAP body and prefix attributes.</summary>
    // See UnrealMapWriter.CreateDocument for why these are required under NativeAOT:
    // document.Save() needs Datamodel.Datamodel's static codec registration to have
    // its codec constructors preserved.
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.Binary", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.KeyValues2", "Datamodel.NET")]
    public static CoreResult<bool> Rewrite(string path, IReadOnlyDictionary<string, string> renames)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);
        ArgumentNullException.ThrowIfNull(renames);

        if (renames.Count == 0)
            return CoreResult.Success(false);

        try
        {
            var source = File.ReadAllBytes(path);
            var document = VmapDocument.LoadInMemory(path);
            var changed = RewritePrefixAttributes(document.Model, renames)
                | RewriteElement(document.Root, renames);
            var outputPath = path + $".{Guid.NewGuid():N}.tmp";
            try
            {
                document.Save(outputPath);
                var output = File.ReadAllBytes(outputPath);
                var sourcePrefixEnd = PrefixEnd(source);
                var outputPrefixEnd = PrefixEnd(output);
                if (sourcePrefixEnd is not null && outputPrefixEnd is not null)
                {
                    var prefix = RewritePrefix(source[..sourcePrefixEnd.Value], renames);
                    output = [.. prefix, .. output[outputPrefixEnd.Value..]];
                    changed |= !source.AsSpan().SequenceEqual(output);
                }

                if (changed)
                    File.WriteAllBytes(path, output);
                return CoreResult.Success(changed);
            }
            finally
            {
                if (File.Exists(outputPath))
                    File.Delete(outputPath);
            }
        }
        catch (Exception exception)
        {
            return CoreResult.Failure<bool>("vmap_rewrite_failed", $"Could not rewrite '{path}': {exception.Message}");
        }
    }

    private static bool RewriteElement(Element element, IReadOnlyDictionary<string, string> renames)
    {
        var changed = false;
        foreach (var key in element.Keys.ToList())
        {
            if (!element.ContainsKey(key))
                continue;
            var value = element[key];
            if (value is string text)
            {
                var replacement = RewriteText(text, renames);
                if (replacement == text)
                    continue;
                element[key] = replacement;
                changed = true;
            }
            else
            {
                changed |= RewriteValue(value, renames);
            }
        }
        return changed;
    }

    private static bool RewritePrefixAttributes(Datamodel.Datamodel model, IReadOnlyDictionary<string, string> renames)
    {
        var changed = false;
        foreach (var key in model.PrefixAttributes.Keys.ToList())
        {
            var value = model.PrefixAttributes[key];
            if (value is string text)
            {
                var replacement = RewriteText(text, renames);
                if (replacement == text)
                    continue;
                model.PrefixAttributes[key] = replacement;
                changed = true;
                continue;
            }

            changed |= RewriteValue(value, renames);
        }
        return changed;
    }

    private static bool RewriteValue(object? value, IReadOnlyDictionary<string, string> renames)
    {
        switch (value)
        {
            case Element element:
                return RewriteElement(element, renames);
            case StringArray strings:
                {
                    var changed = false;
                    for (var i = 0; i < strings.Count; i++)
                    {
                        var replacement = RewriteText(strings[i], renames);
                        if (replacement == strings[i])
                            continue;
                        strings[i] = replacement;
                        changed = true;
                    }
                    return changed;
                }
            case ElementArray elements:
                {
                    var changed = false;
                    foreach (var element in elements)
                        changed |= element is not null && RewriteElement(element, renames);
                    return changed;
                }
            case IEnumerable values when value is not string:
                {
                    var changed = false;
                    foreach (var item in values)
                        changed |= RewriteValue(item, renames);
                    return changed;
                }
            default:
                return false;
        }
    }

    private static string RewriteText(string text, IReadOnlyDictionary<string, string> renames)
    {
        var output = new StringBuilder(text.Length);
        for (var offset = 0; offset < text.Length;)
        {
            var match = renames
                .Where(item => item.Key.Length > 0 && text.AsSpan(offset).StartsWith(item.Key, StringComparison.Ordinal))
                .OrderByDescending(item => item.Key.Length)
                .FirstOrDefault();
            if (match.Key is null)
            {
                output.Append(text[offset++]);
                continue;
            }

            output.Append(match.Value);
            offset += match.Key.Length;
        }
        return output.ToString();
    }

    private static byte[] RewritePrefix(ReadOnlySpan<byte> prefix, IReadOnlyDictionary<string, string> renames)
    {
        var offset = 0;
        var strings = new List<(int Start, int End)>();
        if (!CollectPrefixStrings(prefix, ref offset, strings))
            return prefix.ToArray();

        var output = new List<byte>(prefix.Length);
        var previous = 0;
        foreach (var (start, end) in strings)
        {
            output.AddRange(prefix[previous..start].ToArray());
            var replacement = RewriteText(Encoding.UTF8.GetString(prefix[start..end]), renames);
            output.AddRange(Encoding.UTF8.GetBytes(replacement));
            output.Add(0);
            previous = end + 1;
        }
        output.AddRange(prefix[previous..].ToArray());
        return output.ToArray();
    }

    private static bool CollectPrefixStrings(
        ReadOnlySpan<byte> buffer,
        ref int offset,
        ICollection<(int Start, int End)> strings)
    {
        try
        {
            offset = buffer.IndexOf((byte)0) + 1;
            if (offset <= 0)
                return false;
            var blocks = ReadInt(buffer, ref offset);
            for (var block = 0; block < blocks; block++)
            {
                var attributes = ReadInt(buffer, ref offset);
                for (var attribute = 0; attribute < attributes; attribute++)
                {
                    var nameEnd = buffer[offset..].IndexOf((byte)0);
                    if (nameEnd < 0)
                        return false;
                    offset += nameEnd + 1;
                    var type = buffer[offset++];
                    CollectValueStrings(buffer, ref offset, type, strings);
                }
            }
            return true;
        }
        catch (Exception)
        {
            return false;
        }
    }

    private static void CollectValueStrings(
        ReadOnlySpan<byte> buffer,
        ref int offset,
        byte type,
        ICollection<(int Start, int End)> strings)
    {
        if (type == 5)
        {
            var length = buffer[offset..].IndexOf((byte)0);
            if (length < 0)
                throw new InvalidDataException();
            strings.Add((offset, offset + length));
            offset += length + 1;
            return;
        }
        if (type == 6)
        {
            var length = ReadInt(buffer, ref offset);
            offset += length;
            return;
        }
        var baseType = type > 32 ? type - 32 : type;
        if (type > 32)
        {
            var count = ReadInt(buffer, ref offset);
            for (var i = 0; i < count; i++)
                CollectValueStrings(buffer, ref offset, (byte)baseType, strings);
            return;
        }
        SkipValue(buffer, ref offset, (byte)baseType);
    }

    internal static int? PrefixEnd(ReadOnlySpan<byte> buffer)
    {
        try
        {
            var offset = buffer.IndexOf((byte)0) + 1;
            if (offset <= 0)
                return null;
            var blocks = ReadInt(buffer, ref offset);
            for (var block = 0; block < blocks; block++)
            {
                var attributes = ReadInt(buffer, ref offset);
                for (var attribute = 0; attribute < attributes; attribute++)
                {
                    offset = buffer[offset..].IndexOf((byte)0) + offset + 1;
                    var type = buffer[offset++];
                    SkipValue(buffer, ref offset, type);
                }
            }
            return offset;
        }
        catch (Exception)
        {
            return null;
        }
    }

    private static int ReadInt(ReadOnlySpan<byte> buffer, ref int offset)
    {
        var value = BitConverter.ToInt32(buffer[offset..]);
        offset += sizeof(int);
        return value;
    }

    private static void SkipValue(ReadOnlySpan<byte> buffer, ref int offset, byte type)
    {
        if (type == 5)
        {
            offset += buffer[offset..].IndexOf((byte)0) + 1;
            return;
        }
        if (type == 6)
        {
            var length = ReadInt(buffer, ref offset);
            offset += length;
            return;
        }

        var baseType = type > 32 ? type - 32 : type;
        if (type > 32)
        {
            var count = ReadInt(buffer, ref offset);
            for (var i = 0; i < count; i++)
                SkipValue(buffer, ref offset, (byte)baseType);
            return;
        }

        var size = baseType switch
        {
            2 or 3 or 7 or 8 => 4,
            4 or 14 => 1,
            9 or 15 => 8,
            10 or 16 => 12,
            11 or 12 => 16,
            13 => 64,
            _ => throw new InvalidDataException($"Unsupported DMX prefix type {type}.")
        };
        offset += size;
    }
}

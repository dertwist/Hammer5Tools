using System;
using System.Diagnostics.CodeAnalysis;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using SteamDatabase.ValvePak;

namespace CS2WorkshopManager;

// Keep chunked workshop output with the ValvePak version used by the SmartProp reader.
internal sealed class ChunkedPackage : Package
{
    public int WriteChunkSize { get; set; }

    [SuppressMessage("Security", "CA5351", Justification = "Valve's VPK format requires MD5 checksums, not cryptographic authentication.")]
    public new void Write(string path)
    {
        var prefix = path.EndsWith("_dir.vpk", StringComparison.OrdinalIgnoreCase)
            ? path[..^8] : throw new ArgumentException("Chunked packages require a _dir.vpk filename.", nameof(path));
        var entries = (Entries ?? []).SelectMany(pair => pair.Value).ToArray();
        var chunkIndex = -1;
        FileStream? chunk = null;
        try
        {
            foreach (var entry in entries)
            {
                var data = entry.SmallData;
                if (chunk is null || chunk.Length > 0 && chunk.Length + data.Length > WriteChunkSize)
                {
                    chunk?.Dispose();
                    chunk = File.Create($"{prefix}_{++chunkIndex:D3}.vpk");
                }
                entry.ArchiveIndex = checked((ushort)chunkIndex);
                entry.Offset = checked((uint)chunk.Position);
                entry.Length = checked((uint)data.Length);
                chunk.Write(data);
                entry.SmallData = [];
            }
        }
        finally
        {
            chunk?.Dispose();
        }

        using var treeStream = new MemoryStream();
        using (var tree = new BinaryWriter(treeStream, Encoding.UTF8, true))
        {
            foreach (var type in entries.GroupBy(entry => entry.TypeName))
            {
                WriteString(tree, type.Key);
                foreach (var directory in type.GroupBy(entry => entry.DirectoryName))
                {
                    WriteString(tree, directory.Key);
                    foreach (var entry in directory)
                    {
                        WriteString(tree, entry.FileName);
                        tree.Write(entry.CRC32);
                        tree.Write((ushort)0);
                        tree.Write(entry.ArchiveIndex);
                        tree.Write(entry.Offset);
                        tree.Write(entry.Length);
                        tree.Write(ushort.MaxValue);
                    }
                    tree.Write((byte)0);
                }
                tree.Write((byte)0);
            }
            tree.Write((byte)0);
        }

        var treeData = treeStream.ToArray();
        using var output = File.Create(path);
        using var writer = new BinaryWriter(output, Encoding.UTF8, true);
        writer.Write(MAGIC);
        writer.Write(2u);
        writer.Write(checked((uint)treeData.Length));
        writer.Write(0u);
        writer.Write(0u);
        writer.Write(48u);
        writer.Write(0u);
        writer.Write(treeData);
        writer.Write(MD5.HashData(treeData));
        writer.Write(MD5.HashData([]));
        writer.Flush();
        output.Position = 0;
        var checksum = MD5.HashData(output);
        output.Position = output.Length;
        writer.Write(checksum);
    }

    private static void WriteString(BinaryWriter writer, string text)
    {
        writer.Write(Encoding.UTF8.GetBytes(string.IsNullOrEmpty(text) ? " " : text));
        writer.Write((byte)0);
    }
}

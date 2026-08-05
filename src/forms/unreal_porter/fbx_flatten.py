"""
Post-process UE-exported FBX files for Source 2 import.

Performs three in-place transformations on binary FBX (7.x) files.

Orientation is *not* one of them: UE writes the scene right-handed (it negates Y
on export) and tools/ue_scripts/export_assets.py sets
FbxExportOption.force_front_x_axis so the front axis is +X, matching Source 2's
forward vector. Both mirrors happen upstream, in the Editor. Do not add a
rotation or a vertex flip here to compensate for one of them — that is what the
old 90-degree Lcl Rotation patch did, and it fought the exporter rather than
configuring it.


1. **Flag patching** — UE 5.7+ writes C-type (char/bool) properties at P-record
   position 3 inside Properties70, which Blender 3.6's importer crashes on.
   These are rewritten as S-type (string) so all importers can read the file.

2. **Hierarchy flattening** — UE exports LOD meshes nested under an FbxLODGroup
   Model, but Source 2's ModelDoc import_filter can only select *top-level*
   meshes.  Child mesh Models are reparented to the scene root ( Connections OO
   parent IDs overwritten with 0).

3. **Geometry sync** — Geometry node names are aligned with their parent Model
   names.

4. **Naming** (opt-in) — Model/Geometry node names are rewritten to Source 2
   style, dropping Unreal's type prefixes.  The UCX_/UBX_ collision tag stays:
   it is not a type prefix, it is how the hull identifies itself.

ASCII/other inputs are returned untouched.
"""

import os
import struct

_MAGIC = b"Kaydara FBX Binary"


def _reader(version):
    """Return (hdr_struct, hdr_size, null_len) for this FBX version."""
    if version >= 7500:
        return "<QQQ", 24, 25   # 64-bit offsets
    return "<III", 12, 13       # 32-bit offsets


def _parse_props(d, p, nprops):
    """Read nprops property records; return (list of (type,value,value_offset), end)."""
    out = []
    for _ in range(nprops):
        t = chr(d[p]); p += 1; voff = p
        if t == 'Y': v = struct.unpack("<h", d[p:p+2])[0]; p += 2
        elif t == 'C': v = d[p]; p += 1
        elif t == 'I': v = struct.unpack("<i", d[p:p+4])[0]; p += 4
        elif t == 'F': v = struct.unpack("<f", d[p:p+4])[0]; p += 4
        elif t == 'D': v = struct.unpack("<d", d[p:p+8])[0]; p += 8
        elif t == 'L': v = struct.unpack("<q", d[p:p+8])[0]; p += 8
        elif t in ('S', 'R'):
            ln = struct.unpack("<I", d[p:p+4])[0]; p += 4
            v = d[p:p+ln]; p += ln
            if t == 'S':
                v = v.decode('ascii', 'ignore')
        elif t in ('f', 'd', 'l', 'i', 'b'):
            al, enc, cl = struct.unpack("<III", d[p:p+12])[0:3]
            p += 12 + cl
            v = None
        else:
            v = None
        out.append((t, v, voff))
    return out, p


class _Fbx:
    def __init__(self, d):
        self.d = d
        self.version = struct.unpack("<I", d[23:27])[0]
        self.hdr_fmt, self.hdr_size, self.null_len = _reader(self.version)

    def node_hdr(self, off):
        end, nprops, plen = struct.unpack(self.hdr_fmt, self.d[off:off+self.hdr_size])
        p = off + self.hdr_size
        nlen = self.d[p]; p += 1
        name = self.d[p:p+nlen].decode('ascii', 'ignore'); p += nlen
        return end, nprops, plen, name, p

    def top_nodes(self):
        off, out = 27, {}
        n = len(self.d)
        while off < n - self.null_len:
            end, npr, pl, name, ps = self.node_hdr(off)
            if end == 0:
                break
            out[name] = (off, end, npr, pl, ps)
            off = end
        return out

    def child_nodes(self, node):
        off, end, npr, pl, ps = node
        p = ps + pl                       # nested nodes start after the property list
        res = []
        while p < end - self.null_len:
            e, cnpr, cpl, nm, cps = self.node_hdr(p)
            if e == 0:
                break
            res.append((nm, (p, e, cnpr, cpl, cps)))
            p = e
        return res


def patch_fbx_string(d: bytearray, voff: int, old_full: str, new_full: str, target_node_off: int):
    """
    Replace string property at voff with new_full in binary FBX bytearray d,
    updating string length, slicing bytes, and updating all affected EndOffset and PropertyListLen header fields.
    """
    old_bytes = old_full.encode('latin1') if isinstance(old_full, str) else old_full
    new_bytes = new_full.encode('latin1') if isinstance(new_full, str) else new_full

    delta = len(new_bytes) - len(old_bytes)

    version = struct.unpack("<I", d[23:27])[0]
    is_64 = version >= 7500
    hdr_size = 24 if is_64 else 12
    null_len = 25 if is_64 else 13

    # Collect list of (hdr_off, orig_end, orig_pl, is_target) before slicing
    node_records = []

    def collect_nodes(start_off, limit_end):
        off = start_off
        while off < limit_end - null_len:
            if is_64:
                end, npr, pl = struct.unpack("<QQQ", d[off:off+24])
            else:
                end, npr, pl = struct.unpack("<III", d[off:off+12])
            if end == 0:
                break

            node_records.append((off, end, pl, off == target_node_off))

            nlen = d[off + hdr_size]
            node_name_end = off + hdr_size + 1 + nlen
            children_start = node_name_end + pl

            if children_start < end - null_len:
                collect_nodes(children_start, end)
            off = end

    collect_nodes(27, len(d))

    # 1. Update property string length uint32 at voff
    struct.pack_into("<I", d, voff, len(new_bytes))

    # 2. Slice bytearray d
    d[voff + 4 : voff + 4 + len(old_bytes)] = new_bytes

    if delta == 0:
        return d

    # 3. Patch all node headers at their new offsets
    for off, end, pl, is_target in node_records:
        new_off = off + delta if off >= voff else off
        new_end = end + delta if end > voff else end
        new_pl = pl + delta if is_target else pl

        if is_64:
            struct.pack_into("<Q", d, new_off, new_end)
            if is_target:
                struct.pack_into("<Q", d, new_off + 16, new_pl)
        else:
            struct.pack_into("<I", d, new_off, new_end)
            if is_target:
                struct.pack_into("<I", d, new_off + 8, new_pl)

    return d


def _patch_p70_bool_flags(d: bytearray) -> bool:
    """Replace 'C' (char/bool) type properties at P-record position 3 with 'S'
    (string) equivalents inside every Properties70 node.

    UE 5.7's FBX exporter writes the animated/override flag (e.g. 'A') as a 'C'
    type (single byte) instead of the standard 'S' type (length-prefixed string).
    Blender 3.6's importer decodes 'C' with ``struct.unpack('?', ...)`` which
    yields a Python ``bool``; it then crashes on ``b'U' in <bool>`` in
    ``blen_read_custom_properties``.  Newer Blender versions handle this
    correctly, but patching the binary at the source keeps the output compatible
    with all importers.

    A 'C' property encodes as:  0x43 <byte>   (2 bytes)
    An 'S' replacement encodes: 0x53 <uint32 len> <bytes>  (5 + len bytes)

    When the byte value is a printable ASCII char the replacement is a 1-char
    string, growing the record by 4 bytes.  All node EndOffsets past the splice
    point are adjusted.
    """
    if d[:len(_MAGIC)] != _MAGIC:
        return False

    fbx = _Fbx(d)
    tops = fbx.top_nodes()
    if "Objects" not in tops:
        return False

    # Collect (prop_voff, char_byte) for every C-type prop at position 3 in
    # any P-record under any Properties70 node.
    targets = []
    for _nm, obj_node in fbx.child_nodes(tops["Objects"]):
        for cnm, cnode in fbx.child_nodes(obj_node):
            if cnm != "Properties70":
                continue
            for pnm, pnode in fbx.child_nodes(cnode):
                if pnm != "P":
                    continue
                pprops, _ = _parse_props(d, pnode[4], pnode[2])
                if len(pprops) >= 4 and pprops[3][0] == "C":
                    # voff points to the value byte; type code is at voff - 1.
                    targets.append((pprops[3][2], pprops[3][1]))

    if not targets:
        return False

    # Process targets from highest offset to lowest so earlier offsets stay valid.
    targets.sort(reverse=True)

    # Collect all (header_offset, EndOffset) pairs before any splicing.
    # We store both values upfront because the bytearray shifts under us
    # after each splice — we cannot re-read from d[off] later.
    node_records = []

    def collect_nodes(start_off, limit_end):
        off = start_off
        while off < limit_end - fbx.null_len:
            e, _npr, _pl = struct.unpack(fbx.hdr_fmt, d[off:off + fbx.hdr_size])
            if e == 0:
                break
            node_records.append((off, e))
            nlen = d[off + fbx.hdr_size]
            children_start = off + fbx.hdr_size + 1 + nlen + _pl
            if children_start < e - fbx.null_len:
                collect_nodes(children_start, e)
            off = e

    collect_nodes(27, len(d))

    end_fmt = "<Q" if fbx.hdr_fmt == "<QQQ" else "<I"

    for prop_voff, char_byte in targets:
        # Replace 'C' <byte>  with  'S' <uint32 len=1> <byte>
        type_code_off = prop_voff - 1
        replacement = b"S" + struct.pack("<I", 1) + bytes([char_byte])
        old_len = 2  # C-type: 1 type code + 1 value byte
        delta = len(replacement) - old_len  # always +4 for single-char strings

        d[type_code_off:type_code_off + old_len] = replacement

        # Patch every node's EndOffset, writing at the (possibly shifted)
        # header position.
        patched = []
        for hoff, end in node_records:
            new_hoff = hoff + delta if hoff >= type_code_off else hoff
            new_end = end + delta if end > type_code_off else end
            struct.pack_into(end_fmt, d, new_hoff, new_end)
            patched.append((new_hoff, new_end))

        node_records = patched

    return True


# The collision tag is not an asset-type prefix — it is how a mesh declares
# itself a hull, and inspect_fbx_meshes sorts render from physics by it. It
# survives the rename; the UE prefix behind it does not.
_COLLISION_TAGS = ("UCX_", "UBX_", "USP_", "UCP_")


def source2_mesh_name(name: str) -> str:
    """FBX object/mesh name -> Source 2 naming style.

    "SM_ChairLeg_LOD0" -> "chair_leg_lod0", "UCX_SM_ChairLeg_01" -> "UCX_chair_leg_01".
    """
    from .vmdl_writer import strip_ue_prefix
    tag = ""
    for t in _COLLISION_TAGS:
        if name.upper().startswith(t):
            tag, name = name[:len(t)], name[len(t):]
            break
    return tag + strip_ue_prefix(name)


def flatten_fbx(path, strip_prefix: bool = False) -> dict:
    """
    Flatten path in place. Reparents LOD/UCX meshes to scene root (0) and syncs
    Geometry mesh data names.
    strip_prefix additionally renames the Model/Geometry nodes to Source 2 style.
    Returns {"flattened": bool, "reparented": [mesh names], "renamed_models": [(old, new)],
             "renamed_geometries": [(old, new)], "reason": str}.
    """
    with open(path, "rb") as f:
        d = bytearray(f.read())
    if d[:len(_MAGIC)] != _MAGIC:
        return {"flattened": False, "reparented": [], "renamed_models": [], "renamed_geometries": [], "reason": "not a binary FBX"}

    fbx = _Fbx(d)
    tops = fbx.top_nodes()
    if "Objects" not in tops or "Connections" not in tops:
        return {"flattened": False, "reparented": [], "renamed_models": [], "renamed_geometries": [], "reason": "no Objects/Connections"}

    # UE 5.7+ writes C-type (char/bool) properties at P-record position 3
    # inside Properties70, which Blender 3.6's importer crashes on.
    # Convert them to S-type (string) so all importers can read the file.
    patched_flags = _patch_p70_bool_flags(d)

    # Re-parse after flag patching (offsets may have shifted).
    fbx = _Fbx(d)
    tops = fbx.top_nodes()

    # Map Model id -> (clean_name, subtype). With strip_prefix the name recorded
    # here is the Source 2 one, so the Geometry sync below renames the mesh data
    # to match its renamed object.
    models = {}
    model_edits = []       # (voff, old_full, new_full, node_off)
    renamed_models = []
    for nm, node in fbx.child_nodes(tops["Objects"]):
        if nm != "Model":
            continue
        props, _ = _parse_props(d, node[4], node[2])
        if len(props) < 3:
            continue
        mid, mname, msub = props[0][1], props[1][1], props[2][1]
        # FBX object names are "Name\x00\x01Type"; keep the readable part.
        clean_mname = mname.split('\x00', 1)[0]
        if strip_prefix:
            new_mname = source2_mesh_name(clean_mname)
            if new_mname and new_mname != clean_mname:
                model_edits.append((props[1][2], mname, new_mname + mname[len(clean_mname):], node[0]))
                renamed_models.append((clean_mname, new_mname))
                clean_mname = new_mname
        models[mid] = (clean_mname, msub)

    mesh_ids = {mid for mid, (_n, sub) in models.items() if sub == "Mesh"}

    # Map Geometry id -> (clean_name, voff, full_raw_name, node_off)
    geometries = {}
    for nm, node in fbx.child_nodes(tops["Objects"]):
        if nm != "Geometry":
            continue
        props, _ = _parse_props(d, node[4], node[2])
        if len(props) < 3:
            continue
        gid, gname, gsub = props[0][1], props[1][1], props[2][1]
        if gsub == "Mesh":
            clean_gname = gname.split('\x00', 1)[0]
            voff = props[1][2]
            node_off = node[0]
            geometries[gid] = (clean_gname, voff, gname, node_off)

    # Inspect connections: OO/OP child -> parent
    reparent_patches = []          # (byte_offset, mesh_name)
    geom_to_model = {}

    for nm, node in fbx.child_nodes(tops["Connections"]):
        if nm != "C":
            continue
        props, _ = _parse_props(d, node[4], node[2])
        if len(props) < 3:
            continue
        ctype, child, parent = props[0][1], props[1][1], props[2][1]
        if ctype == "OO" and child in mesh_ids and parent != 0 and parent in models:
            reparent_patches.append((props[2][2], models[child][0]))

        if child in geometries and parent in models:
            geom_to_model[child] = models[parent][0]

    # Perform parent ID flattening (overwrite parent int64 -> 0)
    for off, _name in reparent_patches:
        struct.pack_into("<q", d, off, 0)

    # Perform Geometry node name renames (sync mesh data name to match Model object name)
    geom_edits = []
    renamed_list = []
    for gid, model_name in geom_to_model.items():
        clean_gname, voff, full_gname, node_off = geometries[gid]
        if clean_gname != model_name:
            new_full = f"{model_name}\x00\x01Geometry"
            geom_edits.append((voff, full_gname, new_full, node_off))
            renamed_list.append((clean_gname, model_name))

    # Sort edits by voff descending so earlier byte offsets remain unchanged
    edits = sorted(model_edits + geom_edits, key=lambda x: x[0], reverse=True)
    for voff, old_full, new_full, node_off in edits:
        patch_fbx_string(d, voff, old_full, new_full, target_node_off=node_off)

    if not reparent_patches and not edits and not patched_flags:
        return {"flattened": False, "reparented": [], "renamed_models": [], "renamed_geometries": [],
                "reason": "already flat and synced"}

    with open(path, "wb") as f:
        f.write(d)
    return {
        "flattened": True,
        "reparented": [n for _o, n in reparent_patches],
        "renamed_models": renamed_models,
        "renamed_geometries": renamed_list,
        "reason": ""
    }


def _rename_model(path, old, new):
    """Test helper: set one Model node's name, growing/shrinking the file."""
    with open(path, "rb") as fh:
        d = bytearray(fh.read())
    fbx = _Fbx(d)
    for nm, node in fbx.child_nodes(fbx.top_nodes()["Objects"]):
        if nm != "Model":
            continue
        props, _ = _parse_props(d, node[4], node[2])
        full = props[1][1]
        if full.split('\x00', 1)[0] == old:
            patch_fbx_string(d, props[1][2], full, new + full[len(old):], target_node_off=node[0])
            break
    with open(path, "wb") as fh:
        fh.write(d)


def _p70_flag_types(path):
    """Test helper: type codes found at P-record position 3 (the flags slot).
    A 'C' here is what makes Blender 3.6's importer crash."""
    with open(path, "rb") as fh:
        d = bytearray(fh.read())
    fbx = _Fbx(d)
    types = set()
    for _nm, obj in fbx.child_nodes(fbx.top_nodes()["Objects"]):
        for cnm, cnode in fbx.child_nodes(obj):
            if cnm != "Properties70":
                continue
            for pnm, pnode in fbx.child_nodes(cnode):
                if pnm == "P":
                    props, _ = _parse_props(d, pnode[4], pnode[2])
                    if len(props) >= 4:
                        types.add(props[3][0])
    return types


def demo():
    import shutil
    import tempfile
    from .vmdl_writer import inspect_fbx_meshes

    assert source2_mesh_name("SM_ChairLeg_LOD0") == "chair_leg_lod0"
    # The collision tag stays — it is what marks the mesh as a hull.
    assert source2_mesh_name("UCX_SM_ChairLeg_01") == "UCX_chair_leg_01"

    src = os.path.join(os.path.dirname(__file__), "assets", "basicshapes", "cube.fbx")
    with tempfile.TemporaryDirectory() as tmp:
        f = os.path.join(tmp, "cube.fbx")
        shutil.copy(src, f)
        # Give it a UE-style name first, so the rename below has to shrink the
        # file — every node EndOffset past the splice has to follow.
        _rename_model(f, "Cube", "SM_TestCubeThing")
        assert [n for n, _s in list_models(f)] == ["SM_TestCubeThing", "UCX_Cube"]

        flatten_fbx(f, strip_prefix=True)
        assert [n for n, _s in list_models(f)] == ["test_cube_thing", "UCX_cube"], list_models(f)
        # Renamed hulls are still recognised as physics, not render meshes.
        info = inspect_fbx_meshes(f)
        assert info["collision"] == ["UCX_cube"], info
        assert info["base"] == "test_cube_thing", info

        # Untouched by default.
        shutil.copy(src, f)
        flatten_fbx(f)
        assert [n for n, _s in list_models(f)] == ["Cube", "UCX_Cube"]
        assert _p70_flag_types(f) and "C" not in _p70_flag_types(f), _p70_flag_types(f)

    print("ok")


def list_models(path):
    """
    Return [(name, subtype)] for every Model node in a binary FBX (subtype is
    e.g. 'Mesh' or 'LodGroup'). Returns None if the file isn't a binary FBX.
    Accurate mesh enumeration — preferred over scanning raw strings.
    """
    with open(path, "rb") as f:
        d = bytearray(f.read())
    if d[:len(_MAGIC)] != _MAGIC:
        return None
    fbx = _Fbx(d)
    tops = fbx.top_nodes()
    if "Objects" not in tops:
        return []
    models = []
    for nm, node in fbx.child_nodes(tops["Objects"]):
        if nm != "Model":
            continue
        props, _ = _parse_props(d, node[4], node[2])
        if len(props) >= 3:
            models.append((props[1][1].split('\x00', 1)[0], props[2][1]))
    return models


def list_materials(path):
    """
    Return clean Material node names embedded in a binary FBX (e.g. ['mi_rock_3']).
    Returns [] if the file isn't a binary FBX or has no Material nodes.
    """
    if not path or not os.path.isfile(path):
        return []
    try:
        with open(path, "rb") as f:
            d = bytearray(f.read())
        if d[:len(_MAGIC)] != _MAGIC:
            return []
        fbx = _Fbx(d)
        tops = fbx.top_nodes()
        if "Objects" not in tops:
            return []
        mats = []
        for nm, node in fbx.child_nodes(tops["Objects"]):
            if nm != "Material":
                continue
            props, _ = _parse_props(d, node[4], node[2])
            if len(props) >= 2:
                raw_name = props[1][1]
                if isinstance(raw_name, str):
                    clean_name = raw_name.split('\x00', 1)[0]
                    if clean_name and clean_name not in mats:
                        mats.append(clean_name)
        return mats
    except Exception:
        return []


if __name__ == "__main__":
    demo()

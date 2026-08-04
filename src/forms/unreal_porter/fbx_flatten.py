"""
Flatten an FBX mesh hierarchy in place.

UE exports LOD meshes nested under an FbxLODGroup Model, and Source 2's ModelDoc
import_filter can only select *top-level* meshes — so nested LOD/UCX meshes are
unreachable. This module reparents every mesh Model that hangs off another Model
(the LOD group) to the scene root, so all meshes (LOD0..N, UCX_*) become
top-level siblings that import_filter can pick.

The edit only overwrites existing 64-bit parent IDs in the "Connections" section
with 0 (the root). That is byte-size-preserving, so no offsets need
recomputation — a low-risk in-place patch. Binary FBX only (7.x); ASCII/other
inputs are returned untouched.
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


def _find_properties70(fbx: "_Fbx", model_node):
    for cnm, cnode in fbx.child_nodes(model_node):
        if cnm == "Properties70":
            return cnode
    return None


def _find_rotation_prop(d: bytearray, fbx: "_Fbx", p70_node):
    """Return (pnode, pprops) for the first existing Lcl Rotation/PreRotation
    child of p70_node, or None if it has neither."""
    for pnm, pnode in fbx.child_nodes(p70_node):
        pprops, _ = _parse_props(d, pnode[4], pnode[2])
        if len(pprops) >= 7 and pprops[0][1] in ("Lcl Rotation", "PreRotation"):
            return pnode, pprops
    return None


def _insert_lcl_rotation(d: bytearray, fbx: "_Fbx", p70_node, pitch: float, yaw: float, roll: float) -> None:
    """
    Insert a brand-new "Lcl Rotation" P-record as a child of p70_node.

    FBX only ever writes a Properties70 override for non-default values, so a
    freshly exported static mesh (identity rotation) has no "Lcl Rotation" node
    to patch at all — the common case in practice. Inserting one means growing
    the file, which shifts every byte after the insertion point, so every node
    EndOffset from here to EOF must be corrected to match.
    """
    _off, p70_end, _npr, _pl, _ps = p70_node
    insertion_off = p70_end - fbx.null_len

    def enc(t, v):
        if t == 'S':
            b = v.encode('ascii')
            return b'S' + struct.pack("<I", len(b)) + b
        if t == 'C':
            return b'C' + bytes([ord(v)])
        if t == 'D':
            return b'D' + struct.pack("<d", v)
        raise ValueError(t)

    props_bytes = b"".join((
        enc('S', "Lcl Rotation"),
        enc('S', "Lcl Rotation"),
        enc('S', ""),
        enc('C', 'A'),
        enc('D', float(pitch)),
        enc('D', float(yaw)),
        enc('D', float(roll)),
    ))
    name = b"P"
    node_end = insertion_off + fbx.hdr_size + 1 + len(name) + len(props_bytes)
    header = struct.pack(fbx.hdr_fmt, node_end, 7, len(props_bytes))
    new_node = header + bytes([len(name)]) + name + props_bytes
    delta = len(new_node)

    # Collect (header_offset, EndOffset) for every node in the file so their
    # stored EndOffset can be corrected once the new bytes are spliced in.
    records = []

    def collect(start, limit):
        p = start
        while p < limit - fbx.null_len:
            e, _npr2, pl2 = struct.unpack(fbx.hdr_fmt, d[p:p + fbx.hdr_size])
            if e == 0:
                break
            records.append((p, e))
            nlen = d[p + fbx.hdr_size]
            children_start = p + fbx.hdr_size + 1 + nlen + pl2
            if children_start < e - fbx.null_len:
                collect(children_start, e)
            p = e

    collect(27, len(d))

    d[insertion_off:insertion_off] = new_node

    end_fmt = "<Q" if fbx.hdr_fmt == "<QQQ" else "<I"
    for hoff, old_end in records:
        new_hoff = hoff + delta if hoff >= insertion_off else hoff
        new_end = old_end + delta if old_end > insertion_off else old_end
        if new_end != old_end:
            struct.pack_into(end_fmt, d, new_hoff, new_end)


def rotate_fbx_models(d: bytearray, pitch: float = 0.0, yaw: float = 90.0, roll: float = 0.0) -> bool:
    """
    Apply (pitch, yaw, roll) rotation offset to every Model node in binary FBX d, in place.

    Patches an existing "Lcl Rotation"/"PreRotation" Properties70 entry when
    present (byte-size-preserving). When a Model has neither — the normal case
    for a freshly exported static mesh, since FBX omits Properties70 overrides
    that equal the default (identity) — a new "Lcl Rotation" P-record is
    inserted into its Properties70 node instead, growing the file as needed.
    Returns True if any Model was modified.
    """
    if d[:len(_MAGIC)] != _MAGIC:
        return False

    modified = False

    # Phase 1: patch existing rotation properties in place (no resize).
    fbx = _Fbx(d)
    tops = fbx.top_nodes()
    if "Objects" not in tops:
        return False
    for nm, node in fbx.child_nodes(tops["Objects"]):
        if nm != "Model":
            continue
        p70_node = _find_properties70(fbx, node)
        if not p70_node:
            continue
        found = _find_rotation_prop(d, fbx, p70_node)
        if not found:
            continue
        pnode, pprops = found
        x_off, y_off, z_off = pprops[4][2], pprops[5][2], pprops[6][2]
        cur_x, cur_y, cur_z = float(pprops[4][1]), float(pprops[5][1]), float(pprops[6][1])
        struct.pack_into("<d", d, x_off, cur_x + pitch)
        struct.pack_into("<d", d, y_off, cur_y + yaw)
        struct.pack_into("<d", d, z_off, cur_z + roll)
        modified = True

    # Phase 2: insert a fresh "Lcl Rotation" for every Model that has neither
    # property. Each insertion changes the file's byte layout, so re-parse
    # from scratch after every insert and track handled models by id to avoid
    # reprocessing them (or looping forever).
    handled = set()
    while True:
        fbx = _Fbx(d)
        tops = fbx.top_nodes()
        if "Objects" not in tops:
            break
        target_p70 = None
        for nm, node in fbx.child_nodes(tops["Objects"]):
            if nm != "Model":
                continue
            props, _ = _parse_props(d, node[4], node[2])
            model_id = props[0][1] if props else node[0]
            if model_id in handled:
                continue
            handled.add(model_id)
            p70_node = _find_properties70(fbx, node)
            if not p70_node:
                continue
            if _find_rotation_prop(d, fbx, p70_node):
                continue
            target_p70 = p70_node
            break
        if target_p70 is None:
            break
        _insert_lcl_rotation(d, fbx, target_p70, pitch, yaw, roll)
        modified = True

    return modified


def flatten_fbx(path) -> dict:
    """
    Flatten path in place. Reparents LOD/UCX meshes to scene root (0), syncs
    Geometry mesh data names, and applies FBX model rotation (P 0 Y 0 R 90).
    Returns {"flattened": bool, "reparented": [mesh names], "renamed_geometries": [(old, new)], "reason": str}.
    """
    with open(path, "rb") as f:
        d = bytearray(f.read())
    if d[:len(_MAGIC)] != _MAGIC:
        return {"flattened": False, "reparented": [], "renamed_geometries": [], "reason": "not a binary FBX"}

    fbx = _Fbx(d)
    tops = fbx.top_nodes()
    if "Objects" not in tops or "Connections" not in tops:
        return {"flattened": False, "reparented": [], "renamed_geometries": [], "reason": "no Objects/Connections"}

    # Map Model id -> (clean_name, subtype)
    models = {}
    for nm, node in fbx.child_nodes(tops["Objects"]):
        if nm != "Model":
            continue
        props, _ = _parse_props(d, node[4], node[2])
        if len(props) < 3:
            continue
        mid, mname, msub = props[0][1], props[1][1], props[2][1]
        # FBX object names are "Name\x00\x01Type"; keep the readable part.
        models[mid] = (mname.split('\x00', 1)[0], msub)

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
    for gid, model_name in geom_to_model.items():
        clean_gname, voff, full_gname, node_off = geometries[gid]
        if clean_gname != model_name:
            new_full = f"{model_name}\x00\x01Geometry"
            geom_edits.append((voff, full_gname, new_full, clean_gname, model_name, node_off))

    # Sort edits by voff descending so earlier byte offsets remain unchanged
    geom_edits.sort(key=lambda x: x[0], reverse=True)
    renamed_list = []
    for voff, old_full, new_full, old_clean, new_clean, node_off in geom_edits:
        patch_fbx_string(d, voff, old_full, new_full, target_node_off=node_off)
        renamed_list.append((old_clean, new_clean))

    # Apply Unreal -> Source FBX model rotation as a 90-degree offset on the
    # Z axis (roll slot -> Lcl Rotation Z). Done last (after reparenting/
    # renaming may have resized d) since it re-parses d fresh internally and
    # may itself insert bytes, growing the file further.
    rotated = rotate_fbx_models(d, pitch=0.0, yaw=0.0, roll=90.0)

    if not reparent_patches and not renamed_list and not rotated:
        return {"flattened": False, "reparented": [], "renamed_geometries": [], "reason": "already flat, synced, and rotated"}

    with open(path, "wb") as f:
        f.write(d)
    return {
        "flattened": True,
        "reparented": [n for _o, n in reparent_patches],
        "renamed_geometries": renamed_list,
        "reason": ""
    }


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

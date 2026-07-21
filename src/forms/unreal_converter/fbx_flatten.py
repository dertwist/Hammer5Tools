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


def rotate_fbx_models(d: bytearray, pitch: float = 0.0, yaw: float = 90.0, roll: float = 0.0) -> bool:
    """
    Apply (pitch, yaw, roll) rotation offset to all Model nodes in binary FBX d in place.
    Modifies double-precision rotation properties in Properties70 (byte-size-preserving).
    Returns True if any rotation properties were updated.
    """
    if d[:len(_MAGIC)] != _MAGIC:
        return False

    fbx = _Fbx(d)
    tops = fbx.top_nodes()
    if "Objects" not in tops:
        return False

    modified = False
    for nm, node in fbx.child_nodes(tops["Objects"]):
        if nm != "Model":
            continue

        model_children = fbx.child_nodes(node)
        p70_node = None
        for cnm, cnode in model_children:
            if cnm == "Properties70":
                p70_node = cnode
                break

        if not p70_node:
            continue

        for pnm, pnode in fbx.child_nodes(p70_node):
            pprops, _ = _parse_props(d, pnode[4], pnode[2])
            if len(pprops) >= 7 and pprops[0][1] in ("Lcl Rotation", "PreRotation"):
                x_off = pprops[4][2]
                y_off = pprops[5][2]
                z_off = pprops[6][2]

                cur_x = float(pprops[4][1])
                cur_y = float(pprops[5][1])
                cur_z = float(pprops[6][1])

                struct.pack_into("<d", d, x_off, cur_x + pitch)
                struct.pack_into("<d", d, y_off, cur_y + yaw)
                struct.pack_into("<d", d, z_off, cur_z + roll)
                modified = True

    return modified


def flatten_fbx(path) -> dict:
    """
    Flatten path in place. Reparents LOD/UCX meshes to scene root (0), syncs
    Geometry mesh data names, and applies FBX model rotation (P 0 Y 90 R 0).
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

    # Apply Unreal -> Source FBX model rotation (Pitch 0, Yaw 90, Roll 0)
    rotated = rotate_fbx_models(d, pitch=0.0, yaw=90.0, roll=0.0)

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

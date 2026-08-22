"""
Path evaluation engine for CSmartPropElement_PlaceOnPath.

Computes smooth Centripetal Catmull-Rom splines from path control points,
samples equidistant points along the arc length (or projected distance),
determines full 3D orientation (Source 2 forward +X, left +Y, up +Z basis),
and filters child elements against selection criteria (PathPosition, EndCap, IsValid, etc.).

This module has no Qt or OpenGL dependencies so it stays unit-testable.
"""
import math
import numpy as np

from src.editors.smartprop_editor.viewport_3d.camera import (
    translation_matrix, rotation_matrix_euler, scale_matrix, decompose_trs,
)


DEFAULT_PATH_POINTS = [
    [-400.0, 0.0, 0.0],
    [-200.0, 32.0, 0.0],
    [200.0, -32.0, 0.0],
    [400.0, 0.0, 0.0],
]


def centripetal_catmull_rom_spline(points, alpha=0.5, samples_per_segment=64):
    """Smooth path through `points` (Source 2 coords) via Centripetal Catmull-Rom spline.

    Centripetal Catmull-Rom (alpha=0.5) avoids cusps and overshoot on non-uniform
    control point distances, perfectly matching Valve Source 2's spline interpolation.
    Boundary control points use linear reflection: P_{-1} = 2*P_0 - P_1.
    """
    n = len(points)
    if n < 2:
        return [list(p[:3]) for p in points]

    pts = [np.asarray(p[:3], dtype=np.float64) for p in points]
    p_first = 2.0 * pts[0] - pts[1]
    p_last = 2.0 * pts[-1] - pts[-2]
    ext_pts = [p_first] + pts + [p_last]

    out = []
    for i in range(1, len(ext_pts) - 2):
        p0, p1, p2, p3 = ext_pts[i - 1], ext_pts[i], ext_pts[i + 1], ext_pts[i + 2]

        def get_t(t_prev, pA, pB):
            d = np.linalg.norm(pB - pA)
            return t_prev + (d ** alpha if d > 1e-7 else 1e-7)

        t0 = 0.0
        t1 = get_t(t0, p0, p1)
        t2 = get_t(t1, p1, p2)
        t3 = get_t(t2, p2, p3)

        for s in range(samples_per_segment):
            t = t1 + (t2 - t1) * (s / samples_per_segment)
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3

            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3

            c = (t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2
            out.append(c.tolist())

    out.append(pts[-1].tolist())
    return out


# Alias for backwards compatibility
catmull_rom_spline = centripetal_catmull_rom_spline


def compute_path_samples_with_tangents(points, samples_per_segment=64, projected_up=None):
    """Compute dense curve samples with positions, tangents, and cumulative arc length.

    Args:
        points: list of [x, y, z] control points
        samples_per_segment: interpolation density
        projected_up: optional normal vector to project distances onto the perpendicular plane

    Returns:
        samples: list of (pos_np, tangent_np, cumulative_distance)
        total_length: float total path length
    """
    curve_pts = centripetal_catmull_rom_spline(points, alpha=0.5, samples_per_segment=samples_per_segment)
    if not curve_pts:
        return [], 0.0

    if len(curve_pts) == 1:
        return [(np.asarray(curve_pts[0], dtype=np.float64), np.array([1.0, 0.0, 0.0], dtype=np.float64), 0.0)], 0.0

    samples = []
    total_dist = 0.0
    num_pts = len(curve_pts)

    proj_norm = None
    if projected_up is not None:
        p_up = np.asarray(projected_up, dtype=np.float64)
        p_len = np.linalg.norm(p_up)
        if p_len > 1e-6:
            proj_norm = p_up / p_len

    for i in range(num_pts):
        curr_p = np.asarray(curve_pts[i], dtype=np.float64)
        if i == 0:
            next_p = np.asarray(curve_pts[1], dtype=np.float64)
            tangent = next_p - curr_p
            dist = 0.0
        elif i == num_pts - 1:
            prev_p = np.asarray(curve_pts[i - 1], dtype=np.float64)
            tangent = curr_p - prev_p
            seg_vec = curr_p - prev_p
            if proj_norm is not None:
                seg_vec = seg_vec - np.dot(seg_vec, proj_norm) * proj_norm
            seg_len = np.linalg.norm(seg_vec)
            total_dist += float(seg_len)
            dist = total_dist
        else:
            prev_p = np.asarray(curve_pts[i - 1], dtype=np.float64)
            next_p = np.asarray(curve_pts[i + 1], dtype=np.float64)
            tangent = next_p - prev_p
            seg_vec = curr_p - prev_p
            if proj_norm is not None:
                seg_vec = seg_vec - np.dot(seg_vec, proj_norm) * proj_norm
            seg_len = np.linalg.norm(seg_vec)
            total_dist += float(seg_len)
            dist = total_dist

        t_norm = np.linalg.norm(tangent)
        if t_norm > 1e-7:
            tangent = tangent / t_norm
        else:
            tangent = np.array([1.0, 0.0, 0.0], dtype=np.float64)

        samples.append((curr_p, tangent, dist))

    return samples, total_dist


def interpolate_at_distance(samples, total_length, target_dist):
    """Interpolate position and forward tangent along dense curve samples at `target_dist`."""
    if not samples:
        return np.array([0.0, 0.0, 0.0], dtype=np.float64), np.array([1.0, 0.0, 0.0], dtype=np.float64)

    if target_dist <= samples[0][2]:
        return samples[0][0], samples[0][1]
    if target_dist >= total_length:
        return samples[-1][0], samples[-1][1]

    # Binary search
    low = 0
    high = len(samples) - 1
    while low <= high:
        mid = (low + high) // 2
        if samples[mid][2] < target_dist:
            low = mid + 1
        else:
            high = mid - 1

    idx0 = max(0, min(high, len(samples) - 2))
    idx1 = idx0 + 1

    p0, t0, d0 = samples[idx0]
    p1, t1, d1 = samples[idx1]

    seg_len = d1 - d0
    frac = (target_dist - d0) / seg_len if seg_len > 1e-8 else 0.0
    frac = max(0.0, min(1.0, frac))

    pos = (1.0 - frac) * p0 + frac * p1
    tangent = (1.0 - frac) * t0 + frac * t1
    t_norm = np.linalg.norm(tangent)
    if t_norm > 1e-7:
        tangent = tangent / t_norm
    else:
        tangent = np.array([1.0, 0.0, 0.0], dtype=np.float64)

    return pos, tangent


def build_orientation_matrix(pos, forward, up_vec=None):
    """Build a 4x4 Source 2 TRS matrix (row-vector convention) for a position and forward tangent.

    In Source 2 convention:
      - Forward (+X) = row 0
      - Left (+Y)    = row 1
      - Up (+Z)      = row 2
      - Position     = row 3
    """
    F = np.asarray(forward, dtype=np.float64)
    f_norm = np.linalg.norm(F)
    if f_norm > 1e-7:
        F = F / f_norm
    else:
        F = np.array([1.0, 0.0, 0.0], dtype=np.float64)

    if up_vec is None:
        U = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    else:
        U = np.asarray(up_vec, dtype=np.float64)
        u_norm = np.linalg.norm(U)
        if u_norm > 1e-7:
            U = U / u_norm
        else:
            U = np.array([0.0, 0.0, 1.0], dtype=np.float64)

    # Check if Forward and Up are nearly collinear
    dot_val = np.dot(F, U)
    if abs(dot_val) > 0.999:
        if abs(F[1]) < 0.9:
            U = np.array([0.0, 1.0, 0.0], dtype=np.float64)
        else:
            U = np.array([1.0, 0.0, 0.0], dtype=np.float64)

    # In Source 2 (Right-handed, Z-up, X-forward, Y-left):
    # Left = Up x Forward
    L = np.cross(U, F)
    l_norm = np.linalg.norm(L)
    if l_norm > 1e-7:
        L = L / l_norm
    else:
        L = np.array([0.0, 1.0, 0.0], dtype=np.float64)

    # Orthogonal Up = Forward x Left
    U_ortho = np.cross(F, L)
    u_norm = np.linalg.norm(U_ortho)
    if u_norm > 1e-7:
        U_ortho = U_ortho / u_norm
    else:
        U_ortho = np.array([0.0, 0.0, 1.0], dtype=np.float64)

    M = np.eye(4, dtype=np.float32)
    M[0, :3] = F.astype(np.float32)
    M[1, :3] = L.astype(np.float32)
    M[2, :3] = U_ortho.astype(np.float32)
    M[3, :3] = np.asarray(pos, dtype=np.float32)
    return M


def sample_place_on_path(data, ctx, parent_world_matrix=None):
    """Evaluate CSmartPropElement_PlaceOnPath and return instance matrices and path geometry.

    Args:
        data: element dictionary
        ctx: EvalContext
        parent_world_matrix: 4x4 matrix of parent in Source 2 world space

    Returns:
        dict with:
          - "instances": list of dicts {"index": i, "count": N, "distance": d, "world_matrix": M, "position": P, "rotation": R, "scale": S}
          - "curve_samples": list of [x, y, z] points in Source 2 world space for drawing curve
          - "control_points": list of [x, y, z] control points in Source 2 world space
          - "total_length": total arc length of path
    """
    if parent_world_matrix is None:
        parent_world_matrix = np.eye(4, dtype=np.float32)

    # 1. Extract control points
    raw_points = data.get("m_DefaultPath")
    if not raw_points or not isinstance(raw_points, (list, tuple)) or len(raw_points) == 0:
        raw_points = DEFAULT_PATH_POINTS

    # Resolve each point to float vector
    control_points_local = []
    for pt in raw_points:
        vec = ctx.resolve_vector(pt, [0.0, 0.0, 0.0])
        control_points_local.append([float(vec[0]), float(vec[1]), float(vec[2])])

    # In Valve SmartProp: Default Path positions are authored in World Space
    default_path_in_world = data.get("m_DefaultPathInWorldSpace")
    if default_path_in_world is None:
        is_world_space = (str(data.get("m_PathSpace") or "WORLD").upper() == "WORLD")
    else:
        is_world_space = bool(default_path_in_world) or (str(data.get("m_PathSpace") or "").upper() == "WORLD")

    if is_world_space:
        control_points_world = [[float(c) for c in pt] for pt in control_points_local]
        eval_parent_matrix = np.eye(4, dtype=np.float32)
    else:
        control_points_world = []
        for pt in control_points_local:
            p_vec = np.array([pt[0], pt[1], pt[2], 1.0], dtype=np.float32)
            p_w = (p_vec @ parent_world_matrix)[:3]
            control_points_world.append([float(p_w[0]), float(p_w[1]), float(p_w[2])])
        eval_parent_matrix = parent_world_matrix

    # 2. Fixed Up Direction & Projected Distance
    use_fixed_up = data.get("m_bUseFixedUpDirection", False)
    up_vec = ctx.resolve_vector(data.get("m_vUpDirection"), [0.0, 0.0, 1.0])

    use_projected = bool(data.get("m_bUseProjectedDistance", False))
    projected_up = up_vec if use_projected else None

    # 3. Build dense spline and tangents
    dense_samples, total_length = compute_path_samples_with_tangents(
        control_points_local, samples_per_segment=64, projected_up=projected_up
    )

    # Generate world-space curve samples for rendering
    curve_samples_world = []
    for sample_pos, _, _ in dense_samples:
        if is_world_space:
            curve_samples_world.append([float(sample_pos[0]), float(sample_pos[1]), float(sample_pos[2])])
        else:
            p_vec = np.array([sample_pos[0], sample_pos[1], sample_pos[2], 1.0], dtype=np.float32)
            p_w = (p_vec @ parent_world_matrix)[:3]
            curve_samples_world.append([float(p_w[0]), float(p_w[1]), float(p_w[2])])

    # 4. Spacing & Placement distances (in cs2.json schema, m_flSpacing defaults to 1.0)
    spacing_val = ctx.resolve_scalar(data.get("m_flSpacing"), 1.0)
    spacing = max(0.001, float(spacing_val)) if spacing_val is not None else 1.0
    offset = ctx.resolve_scalar(data.get("m_flOffsetAlongPath"), 0.0)

    # Path offset vector
    path_offset_raw = ctx.resolve_vector(data.get("m_vPathOffset"), [0.0, 0.0, 0.0])
    path_space = str(data.get("m_PathSpace") or "WORLD").upper()

    sample_distances = []
    if total_length < 1e-4 or len(control_points_local) < 2:
        sample_distances = [0.0]
    else:
        d = offset
        while d <= total_length + 1e-4:
            if d >= -1e-4:
                sample_distances.append(max(0.0, min(total_length, d)))
            d += spacing

        if not sample_distances:
            sample_distances = [0.0]

    instance_count = len(sample_distances)

    # 5. Generate instances
    instances = []
    for i, dist in enumerate(sample_distances):
        pos_local, tangent_local = interpolate_at_distance(dense_samples, total_length, dist)
        sample_matrix = build_orientation_matrix(pos_local, tangent_local, up_vec=up_vec)

        # Apply path offset
        if any(abs(v) > 1e-6 for v in path_offset_raw):
            if path_space == "WORLD":
                sample_matrix[3, 0] += path_offset_raw[0]
                sample_matrix[3, 1] += path_offset_raw[1]
                if len(path_offset_raw) > 2:
                    sample_matrix[3, 2] += path_offset_raw[2]
            else:
                # Local perpendicular / up offset
                L = sample_matrix[1, :3]
                U = sample_matrix[2, :3]
                sample_matrix[3, :3] += path_offset_raw[0] * L + path_offset_raw[1] * U

        if is_world_space:
            inst_world_matrix = sample_matrix
        else:
            inst_world_matrix = sample_matrix @ eval_parent_matrix

        world_pos, world_rot, world_scale = decompose_trs(inst_world_matrix)

        instances.append({
            "index": i,
            "count": instance_count,
            "distance": dist,
            "world_matrix": inst_world_matrix,
            "position": world_pos,
            "rotation": world_rot,
            "scale": world_scale,
        })

    return {
        "instances": instances,
        "curve_samples": curve_samples_world,
        "control_points": control_points_world,
        "total_length": total_length,
    }


def matches_path_selection_criteria(child_data, instance_index, instance_count, ctx):
    """Check whether `child_data` should be placed at `instance_index` out of `instance_count`.

    Evaluates CSmartPropSelectionCriteria_PathPosition, CSmartPropSelectionCriteria_EndCap,
    CSmartPropSelectionCriteria_IsValid, etc. based on Valve cs2.json schema.
    """
    if not isinstance(child_data, dict):
        return True

    criteria_list = child_data.get("m_SelectionCriteria")
    if not criteria_list or not isinstance(criteria_list, list):
        return True

    for crit in criteria_list:
        if not isinstance(crit, dict):
            continue
        if crit.get("m_bEnabled", True) is False or crit.get("m_bEnabled") == "false":
            continue

        ccls = crit.get("_class", "")

        # 1. Path Position Criteria (SmartPropPathPositions_t)
        if ccls in ("CSmartPropSelectionCriteria_PathPosition", "PathPosition",
                    "CSmartPropPulse_CriteriaPathPosition", "Pulse_CriteriaPathPosition"):
            pos_raw = crit.get("m_PlaceAtPositions")
            pos_mode = "ALL"
            if isinstance(pos_raw, (int, float)):
                enum_map = {0: "ALL", 1: "NTH", 2: "START_AND_END", 3: "CONTROL_POINTS"}
                pos_mode = enum_map.get(int(pos_raw), "ALL")
            elif isinstance(pos_raw, str):
                pos_mode = pos_raw.upper()
                if pos_mode in ("0", "ALL"):
                    pos_mode = "ALL"
                elif pos_mode in ("1", "NTH"):
                    pos_mode = "NTH"
                elif pos_mode in ("2", "START_AND_END"):
                    pos_mode = "START_AND_END"
                elif pos_mode in ("3", "CONTROL_POINTS"):
                    pos_mode = "CONTROL_POINTS"
            elif isinstance(pos_raw, dict):
                val_str = str(ctx.resolve_string(pos_raw, "ALL")).upper()
                enum_map = {"0": "ALL", "1": "NTH", "2": "START_AND_END", "3": "CONTROL_POINTS"}
                pos_mode = enum_map.get(val_str, val_str)

            allow_start = crit.get("m_bAllowAtStart", True)
            if isinstance(allow_start, str):
                allow_start = (allow_start.lower() not in ("false", "0"))
            elif isinstance(allow_start, (int, float)):
                allow_start = bool(allow_start)

            allow_end = crit.get("m_bAllowAtEnd", True)
            if isinstance(allow_end, str):
                allow_end = (allow_end.lower() not in ("false", "0"))
            elif isinstance(allow_end, (int, float)):
                allow_end = bool(allow_end)

            is_start = (instance_index == 0)
            is_end = (instance_index == instance_count - 1)

            if is_start and not allow_start:
                return False
            if is_end and not allow_end:
                return False

            if pos_mode == "ALL":
                pass
            elif pos_mode == "START_AND_END":
                if not (is_start or is_end):
                    return False
            elif pos_mode == "START":
                if not is_start:
                    return False
            elif pos_mode == "END":
                if not is_end:
                    return False
            elif pos_mode == "INTERNAL":
                if is_start or is_end:
                    return False
            elif pos_mode == "NTH":
                nth_step_raw = crit.get("m_nPlaceEveryNthPosition")
                nth_offset_raw = crit.get("m_nNthPositionIndexOffset")

                step_val = int(round(ctx.resolve_scalar(nth_step_raw, 1.0)))
                step = max(1, step_val) if step_val > 0 else 1
                offset = int(round(ctx.resolve_scalar(nth_offset_raw, 0.0)))

                if (instance_index - offset) % step != 0:
                    return False
            elif pos_mode == "CONTROL_POINTS":
                if not (is_start or is_end):
                    return False

        # 2. EndCap Criteria
        elif ccls in ("CSmartPropSelectionCriteria_EndCap", "EndCap",
                      "CSmartPropPulse_SelectionEndCap", "Pulse_SelectionEndCap"):
            is_start = (instance_index == 0)
            is_end = (instance_index == instance_count - 1)
            b_start = bool(crit.get("m_bStart", False))
            b_end = bool(crit.get("m_bEnd", False))

            if not (is_start or is_end):
                return False
            if is_start and not b_start:
                return False
            if is_end and not b_end:
                return False

        # 3. IsValid Criteria (expression)
        elif ccls in ("CSmartPropSelectionCriteria_IsValid", "IsValid"):
            expr = crit.get("m_Expression")
            if expr:
                val = ctx.resolve_scalar(expr, 1.0)
                if abs(val) < 1e-6:
                    return False

    return True

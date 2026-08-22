"""
Sequential modifier evaluation engine for CS2 SmartProps.

In Valve Source 2 Hammer, modifiers (m_Modifiers) on an element are executed
strictly in sequential order from top to bottom. Each modifier operates on the
active local transform matrix, and editing widgets (locators, rotators, sizers)
capture the active coordinate frame at the exact point in the modifier list
where they are defined.

This module provides standalone, unit-testable evaluation functions for SmartProp
elements and their modifier chains without any Qt or OpenGL dependencies.
"""
import math
import numpy as np

from src.editors.smartprop_editor.viewport_3d.camera import (
    translation_matrix, rotation_matrix_euler, scale_matrix, decompose_trs,
)
from src.editors.smartprop_editor.viewport_3d.engine.path_evaluator import (
    build_orientation_matrix,
)


def resolve_color(value, ctx, default=(0.6, 0.6, 0.6)):
    """Resolve a colour field (None / [r,g,b] 0-255 or 0-1 / binding) to 0.0-1.0 RGB."""
    if value is None:
        return list(default)
    vec = ctx.resolve_vector(value, default)
    rgb = [vec[i] if i < len(vec) else 0.0 for i in range(3)]
    # Hammer stores colours as 0-255 ints; normalize if any component exceeds 1.0
    if any(c > 1.0 for c in rgb):
        rgb = [c / 255.0 for c in rgb]
    return [max(0.0, min(1.0, float(c))) for c in rgb]


def evaluate_single_modifier(mod, current_local_matrix, parent_world_matrix, ctx,
                             state_map=None, eid=0, inst_idx=0):
    """Evaluate a single modifier dict against the active local transform matrix.

    Args:
        mod: modifier dictionary
        current_local_matrix: 4x4 float32 matrix (Source 2 row-vector convention)
        parent_world_matrix: 4x4 float32 matrix representing parent element in world space
        ctx: EvalContext for resolving variable / expression bindings
        state_map: optional dict for storing/restoring named states (SaveState/RestoreState)
        eid: int element ID for deterministic pseudo-random hashing
        inst_idx: int instance index for deterministic pseudo-random hashing

    Returns:
        tuple: (new_local_matrix, widget_spec_or_None)
    """
    if not isinstance(mod, dict):
        return current_local_matrix, None

    if mod.get("m_bEnabled", True) is False or mod.get("m_bEnabled") == "false":
        return current_local_matrix, None

    cls = mod.get("_class", "")
    new_local = current_local_matrix

    # 1. Transform: Translate
    if cls in ("CSmartPropOperation_Translate", "Translate",
               "CSmartPropPulse_Translate", "Pulse_Translate") and "m_vPosition" in mod:
        pos = ctx.resolve_vector(mod["m_vPosition"], [0.0, 0.0, 0.0])
        T = translation_matrix(pos[0], pos[1], pos[2])
        space = str(mod.get("m_CoordinateSpace") or "ELEMENT").upper()
        if space in ("WORLD", "PARENT"):
            new_local = current_local_matrix @ T
        else:
            new_local = T @ current_local_matrix
        return new_local, None

    # 2. Transform: SetPosition
    if cls in ("CSmartPropOperation_SetPosition", "SetPosition",
               "CSmartPropPulse_SetPosition", "Pulse_SetPosition") and "m_vPosition" in mod:
        pos = ctx.resolve_vector(mod["m_vPosition"], [0.0, 0.0, 0.0])
        new_local = current_local_matrix.copy()
        new_local[3, :3] = np.asarray(pos, dtype=np.float32)
        return new_local, None

    # 3. Transform: Rotate
    if cls in ("CSmartPropOperation_Rotate", "Rotate",
               "CSmartPropPulse_Rotate", "Pulse_Rotate") and "m_vRotation" in mod:
        rot = ctx.resolve_vector(mod["m_vRotation"], [0.0, 0.0, 0.0])
        R = rotation_matrix_euler(rot[0], rot[1], rot[2])
        space = str(mod.get("m_CoordinateSpace") or "ELEMENT").upper()
        if space in ("WORLD", "PARENT"):
            new_local = current_local_matrix @ R
        else:
            new_local = R @ current_local_matrix
        return new_local, None

    # 4. Transform: SetOrientation
    if cls in ("CSmartPropOperation_SetOrientation", "SetOrientation",
               "CSmartPropPulse_SetOrientation", "Pulse_SetOrientation"):
        new_local = current_local_matrix.copy()
        pos, _, scale = decompose_trs(new_local)
        if mod.get("m_vRotation") is not None:
            rot = ctx.resolve_vector(mod["m_vRotation"], [0.0, 0.0, 0.0])
            R = rotation_matrix_euler(rot[0], rot[1], rot[2])
            new_local = scale_matrix(*scale) @ R @ translation_matrix(*pos)
        elif mod.get("m_vForwardVector") is not None and mod.get("m_vUpVector") is not None:
            fwd = ctx.resolve_vector(mod["m_vForwardVector"], [1.0, 0.0, 0.0])
            up = ctx.resolve_vector(mod["m_vUpVector"], [0.0, 0.0, 1.0])
            M_orient = build_orientation_matrix([0.0, 0.0, 0.0], fwd, up)
            new_local = scale_matrix(*scale) @ M_orient @ translation_matrix(*pos)
        return new_local, None

    # 5. Transform: ResetRotation
    if cls in ("CSmartPropOperation_ResetRotation", "ResetRotation",
               "CSmartPropPulse_ResetRotation", "Pulse_ResetRotation"):
        pos, rot, scale = decompose_trs(current_local_matrix)
        reset_p = mod.get("m_bResetPitch", True)
        reset_y = mod.get("m_bResetYaw", True)
        reset_r = mod.get("m_bResetRoll", True)
        new_rot = [
            0.0 if reset_p else rot[0],
            0.0 if reset_y else rot[1],
            0.0 if reset_r else rot[2],
        ]
        new_local = scale_matrix(*scale) @ rotation_matrix_euler(*new_rot) @ translation_matrix(*pos)
        return new_local, None

    # 6. Transform: Scale
    if cls in ("CSmartPropOperation_Scale", "Scale",
               "CSmartPropPulse_Scale", "Pulse_Scale"):
        if "m_vScale" in mod:
            s_vec = ctx.resolve_vector(mod["m_vScale"], [1.0, 1.0, 1.0])
            S = scale_matrix(s_vec[0], s_vec[1], s_vec[2])
        else:
            s = ctx.resolve_scalar(mod.get("m_flScale"), 1.0)
            S = scale_matrix(s, s, s)
        new_local = S @ current_local_matrix
        return new_local, None

    # 7. Transform: ResetScale
    if cls in ("CSmartPropOperation_ResetScale", "ResetScale",
               "CSmartPropPulse_ResetScale", "Pulse_ResetScale"):
        pos, rot, _ = decompose_trs(current_local_matrix)
        new_local = rotation_matrix_euler(*rot) @ translation_matrix(*pos)
        return new_local, None

    # 8. Transform: RandomOffset
    if cls in ("CSmartPropOperation_RandomOffset", "RandomOffset",
               "CSmartPropPulse_RandomOffset", "Pulse_RandomOffset"):
        min_v = ctx.resolve_vector(mod.get("m_vRandomPositionMin"), [0.0, 0.0, 0.0])
        max_v = ctx.resolve_vector(mod.get("m_vRandomPositionMax"), [0.0, 0.0, 0.0])
        rand_pos = [0.0, 0.0, 0.0]
        for i in range(3):
            h = ((eid * 374761393 + inst_idx * 668265263 + i * 964729 + 11) & 0x7FFFFFFF)
            h = ((h ^ (h >> 13)) * 1274126177) & 0x7FFFFFFF
            t = (h ^ (h >> 16)) / float(0x7FFFFFFF)
            rand_pos[i] = min_v[i] + t * (max_v[i] - min_v[i])
        T_rand = translation_matrix(*rand_pos)
        new_local = T_rand @ current_local_matrix
        return new_local, None

    # 9. Transform: RandomRotation
    if cls in ("CSmartPropOperation_RandomRotation", "RandomRotation",
               "CSmartPropPulse_RandomRotation", "Pulse_RandomRotation"):
        min_v = ctx.resolve_vector(mod.get("m_vRandomRotationMin"), [0.0, 0.0, 0.0])
        max_v = ctx.resolve_vector(mod.get("m_vRandomRotationMax"), [0.0, 0.0, 0.0])
        rand_rot = [0.0, 0.0, 0.0]
        for i in range(3):
            h = ((eid * 374761393 + inst_idx * 668265263 + i * 964729 + 101) & 0x7FFFFFFF)
            h = ((h ^ (h >> 13)) * 1274126177) & 0x7FFFFFFF
            t = (h ^ (h >> 16)) / float(0x7FFFFFFF)
            rand_rot[i] = min_v[i] + t * (max_v[i] - min_v[i])
        R_rand = rotation_matrix_euler(*rand_rot)
        new_local = R_rand @ current_local_matrix
        return new_local, None

    # 10. Transform: RandomScale
    if cls in ("CSmartPropOperation_RandomScale", "RandomScale",
               "CSmartPropPulse_RandomScale", "Pulse_RandomScale"):
        min_s = ctx.resolve_scalar(mod.get("m_flRandomScaleMin"), 1.0)
        max_s = ctx.resolve_scalar(mod.get("m_flRandomScaleMax"), 1.0)
        h = ((eid * 374761393 + inst_idx * 668265263 + 202) & 0x7FFFFFFF)
        h = ((h ^ (h >> 13)) * 1274126177) & 0x7FFFFFFF
        t = (h ^ (h >> 16)) / float(0x7FFFFFFF)
        s_factor = min_s + t * (max_s - min_s)
        S_rand = scale_matrix(s_factor, s_factor, s_factor)
        new_local = S_rand @ current_local_matrix
        return new_local, None

    # 11. State: SaveState
    if cls in ("CSmartPropOperation_SaveState", "SaveState",
               "CSmartPropPulse_SaveState", "Pulse_SaveState"):
        if state_map is not None:
            state_name = str(mod.get("m_StateName") or "State")
            state_map[state_name] = current_local_matrix.copy()
        return current_local_matrix, None

    # 12. State: RestoreState
    if cls in ("CSmartPropOperation_RestoreState", "RestoreState",
               "CSmartPropPulse_RestoreState", "Pulse_RestoreState"):
        if state_map is not None:
            state_name = str(mod.get("m_StateName") or "State")
            if state_name in state_map:
                return state_map[state_name].copy(), None
        return current_local_matrix, None

    # 13. Variables: SetVariable / SetVariableFloat / SetVariableInt / SetVariableBool
    if cls in ("CSmartPropOperation_SetVariable", "SetVariable",
               "CSmartPropOperation_SetVariableFloat", "SetVariableFloat",
               "CSmartPropOperation_SetVariableInt", "SetVariableInt",
               "CSmartPropOperation_SetVariableBool", "SetVariableBool"):
        var_info = mod.get("m_VariableValue")
        if isinstance(var_info, dict):
            name = var_info.get("m_TargetName")
            val = var_info.get("m_Value")
            if name:
                ctx.set_override(name, val)
        else:
            name = mod.get("m_VariableName")
            val = mod.get("m_Value")
            if val is None:
                val = mod.get("m_flValue")
            if val is None:
                val = mod.get("m_nValue")
            if val is None:
                val = mod.get("m_bValue")
            if name:
                ctx.set_override(name, val)
        return current_local_matrix, None

    # 14. Widget: CreateSizer
    if cls in ("CSmartPropOperation_CreateSizer", "Operation_CreateSizer",
               "CSmartPropPulse_CreateSizer", "Pulse_CreateSizer", "CreateSizer"):
        current_world = current_local_matrix @ parent_world_matrix
        wpos, wrot, _ = decompose_trs(current_world)

        min_x = ctx.resolve_scalar(mod.get("m_flInitialMinX"), 0.0)
        max_x = ctx.resolve_scalar(mod.get("m_flInitialMaxX"), 0.0)
        min_y = ctx.resolve_scalar(mod.get("m_flInitialMinY"), 0.0)
        max_y = ctx.resolve_scalar(mod.get("m_flInitialMaxY"), 0.0)
        min_z = ctx.resolve_scalar(mod.get("m_flInitialMinZ"), 0.0)
        max_z = ctx.resolve_scalar(mod.get("m_flInitialMaxZ"), 0.0)

        out_min_x = str(mod.get("m_OutputVariableMinX") or "")
        out_max_x = str(mod.get("m_OutputVariableMaxX") or "")
        out_min_y = str(mod.get("m_OutputVariableMinY") or "")
        out_max_y = str(mod.get("m_OutputVariableMaxY") or "")
        out_min_z = str(mod.get("m_OutputVariableMinZ") or "")
        out_max_z = str(mod.get("m_OutputVariableMaxZ") or "")

        has_x = bool(out_min_x or out_max_x or min_x != 0.0 or max_x != 0.0)
        has_y = bool(out_min_y or out_max_y or min_y != 0.0 or max_y != 0.0)
        has_z = bool(out_min_z or out_max_z or min_z != 0.0 or max_z != 0.0)

        mod_eid = int(mod.get("m_nElementID") or eid)
        widget_spec = None
        if has_x or has_y or has_z:
            widget_spec = {
                "type": "sizer",
                "element_id": mod_eid,
                "world_matrix": np.array(current_world, dtype=np.float32),
                "position": [float(wpos[0]), float(wpos[1]), float(wpos[2])],
                "rotation": [float(wrot[0]), float(wrot[1]), float(wrot[2])],
                "min_bounds": [min_x, min_y, min_z],
                "max_bounds": [max_x, max_y, max_z],
                "handles": {
                    "min_x": bool(out_min_x), "max_x": bool(out_max_x),
                    "min_y": bool(out_min_y), "max_y": bool(out_max_y),
                    "min_z": bool(out_min_z), "max_z": bool(out_max_z),
                },
                "active_axes": {
                    "x": has_x,
                    "y": has_y,
                    "z": has_z,
                },
                "name": str(mod.get("m_Name") or ""),
            }
        return current_local_matrix, widget_spec

    # 15. Widget: CreateLocator
    if cls in ("CSmartPropOperation_CreateLocator", "Operation_CreateLocator",
               "CSmartPropPulse_CreateLocator", "Pulse_CreateLocator", "CreateLocator"):
        current_world = current_local_matrix @ parent_world_matrix
        _, wrot, _ = decompose_trs(current_world)
        mod_eid = int(mod.get("m_nElementID") or eid)

        offset = ctx.resolve_vector(mod.get("m_vOffset"), [0.0, 0.0, 0.0])
        p = np.array([offset[0], offset[1], offset[2], 1.0], dtype=np.float32)
        world_offset = (p @ current_world)[:3]

        widget_spec = {
            "type": "locator",
            "element_id": mod_eid,
            "offset": offset,
            "world_matrix": np.array(current_world, dtype=np.float32),
            "position": [float(world_offset[0]), float(world_offset[1]), float(world_offset[2])],
            "rotation": [float(wrot[0]), float(wrot[1]), float(wrot[2])],
            "scale": max(0.01, ctx.resolve_scalar(mod.get("m_flDisplayScale"), 1.0)),
            "name": str(mod.get("m_LocatorName") or ""),
        }
        return current_local_matrix, widget_spec

    # 16. Widget: CreateRotator
    if cls in ("CSmartPropOperation_CreateRotator", "Operation_CreateRotator",
               "CSmartPropPulse_CreateRotator", "Pulse_CreateRotator", "CreateRotator"):
        current_world = current_local_matrix @ parent_world_matrix
        _, wrot, _ = decompose_trs(current_world)
        mod_eid = int(mod.get("m_nElementID") or eid)

        offset = ctx.resolve_vector(mod.get("m_vOffset"), [0.0, 0.0, 0.0])
        axis = ctx.resolve_vector(mod.get("m_vRotationAxis"), [0.0, 0.0, 1.0])
        coord_space = str(mod.get("m_CoordinateSpace") or "WORLD").upper()
        if coord_space in ("ELEMENT", "OBJECT"):
            rot_axis = (np.array(axis, dtype=np.float32) @ current_world[:3, :3])
            axis_len = np.linalg.norm(rot_axis)
            if axis_len > 1e-6:
                axis = (rot_axis / axis_len).tolist()

        p = np.array([offset[0], offset[1], offset[2], 1.0], dtype=np.float32)
        world_offset = (p @ current_world)[:3]

        widget_spec = {
            "type": "rotator",
            "element_id": mod_eid,
            "offset": offset,
            "world_matrix": np.array(current_world, dtype=np.float32),
            "position": [float(world_offset[0]), float(world_offset[1]), float(world_offset[2])],
            "rotation": [float(wrot[0]), float(wrot[1]), float(wrot[2])],
            "axis": axis,
            "radius": max(1.0, ctx.resolve_scalar(mod.get("m_flDisplayRadius"), 16.0)),
            "angle": ctx.resolve_scalar(mod.get("m_flInitialAngle"), 0.0),
            "color": resolve_color(mod.get("m_DisplayColor"), ctx, [0.72, 0.74, 0.48]),
            "name": str(mod.get("m_Name") or ""),
        }
        return current_local_matrix, widget_spec

    return current_local_matrix, None


def evaluate_element_modifiers(data, ctx, parent_world_matrix=None, state_map=None):
    """Sequentially evaluate all modifiers for an element and collect its widgets.

    Args:
        data: element dictionary
        ctx: EvalContext
        parent_world_matrix: 4x4 matrix of parent element (or identity)
        state_map: optional dict for named states (SaveState/RestoreState)

    Returns:
        tuple: (local_matrix, world_matrix, model_world_matrix, widgets_list)
            - local_matrix: 4x4 local transform after all modifiers
            - world_matrix: 4x4 world transform for child elements (local @ parent)
            - model_world_matrix: 4x4 world transform including model-level scale
            - widgets_list: list of resolved widget spec dicts positioned in world space
    """
    if parent_world_matrix is None:
        parent_world_matrix = np.eye(4, dtype=np.float32)
    else:
        parent_world_matrix = np.asarray(parent_world_matrix, dtype=np.float32)

    if not isinstance(data, dict):
        return np.eye(4, dtype=np.float32), parent_world_matrix, parent_world_matrix, []

    eid = int(data.get("m_nElementID", 0) or 0)
    inst_idx = getattr(ctx, "instance_index", 0) or 0
    element_class = data.get("_class", "")

    local_matrix = np.eye(4, dtype=np.float32)
    widgets = []

    # 1. PickOne Element Handle (defined at element level)
    if element_class == "CSmartPropElement_PickOne":
        handle_offset = data.get("m_vHandleOfffset")
        if handle_offset is None:
            handle_offset = data.get("m_vHandleOffset")
        offset = ctx.resolve_vector(handle_offset, [0.0, 0.0, 0.0])
        p = np.array([offset[0], offset[1], offset[2], 1.0], dtype=np.float32)
        world_offset = (p @ parent_world_matrix)[:3]
        wpos, wrot, _ = decompose_trs(parent_world_matrix)

        widgets.append({
            "type": "pickone",
            "element_id": eid,
            "offset": offset,
            "position": [float(world_offset[0]), float(world_offset[1]), float(world_offset[2])],
            "rotation": [float(wrot[0]), float(wrot[1]), float(wrot[2])],
            "size": max(1.0, ctx.resolve_scalar(data.get("m_HandleSize"), 8.0)),
            "color": resolve_color(data.get("m_HandleColor"), ctx, [0.6, 0.6, 0.6]),
            "shape": str(data.get("m_HandleShape") or "SQUARE").upper(),
            "name": str(data.get("m_OutputChoiceVariableName") or ""),
        })

    # 2. Sequential evaluation of m_Modifiers
    modifiers = data.get("m_Modifiers")
    if isinstance(modifiers, list):
        for mod in modifiers:
            if not isinstance(mod, dict):
                continue
            local_matrix, widget_spec = evaluate_single_modifier(
                mod, local_matrix, parent_world_matrix, ctx,
                state_map=state_map, eid=eid, inst_idx=inst_idx
            )
            if widget_spec is not None:
                widgets.append(widget_spec)

    # 3. Compute final world matrix for children
    world_matrix = local_matrix @ parent_world_matrix

    # 4. Model-level scale (applies to model instance geometry only)
    model_scale = [1.0, 1.0, 1.0]
    if element_class in ("CSmartPropElement_Model",
                         "CSmartPropElement_ModelEntity",
                         "CSmartPropElement_PropPhysics",
                         "CSmartPropElement_PropDynamic"):
        if data.get("m_vModelScale"):
            model_scale = ctx.resolve_vector(data["m_vModelScale"], [1.0, 1.0, 1.0])
        elif data.get("m_flUniformModelScale") is not None:
            s = ctx.resolve_scalar(data["m_flUniformModelScale"], 1.0)
            model_scale = [s, s, s]

    model_scale_mat = scale_matrix(model_scale[0], model_scale[1], model_scale[2])
    model_world_matrix = model_scale_mat @ world_matrix

    return local_matrix, world_matrix, model_world_matrix, widgets

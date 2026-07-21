"""
Shared Unreal Engine -> Source 2 coordinate / unit transform.

This is the single source of truth for converting spatial data (positions,
rotations, scales) out of Unreal Engine space into Source 2 (Hammer) space.
Everything that migrates content (map actors -> vmap entities, blueprint
component trees -> vsmart, mesh pivots -> vmdl) MUST route through here so the
conversion stays consistent across the whole tool.

Coordinate systems
-------------------
Unreal Engine:  left-handed,  Z-up.  +X forward, +Y right, +Z up.
                1 world unit = 1 cm.
                Rotation = FRotator(Pitch about Y, Yaw about Z, Roll about X), degrees.

Source 2:       right-handed, Z-up.  +X forward, +Y left,  +Z up.
                1 world unit = 1 inch = 2.54 cm.
                Rotation = QAngle(Pitch about Y, Yaw about Z, Roll about X), degrees.

Both are Z-up, so the handedness flip is a single-axis mirror: negate Y.
    C = diag(1, -1, 1)          (C is its own inverse)

    position_src = scale * C @ position_ue
    R_src        = C @ R_ue @ C     (basis conjugation preserves the rotation)

The rotation is built from Unreal's exact FRotationMatrix, conjugated into
Source space, then read back out with Source's MatrixAngles algorithm, so the
result drops straight into a vmap/vsmart angle field.

Unit scale
----------
UE centimetres do not equal Source inches. `UnitScale` exposes the common
choices; the default is `ONE_TO_ONE` (1 uu -> 1 su) because most migration
work keeps the modelled unit count and lets the artist rescale, but
`CM_TO_INCH` (physically correct, 1/2.54) is available when true real-world
size matters.

Pure-python (no numpy) so it is safe to call from worker threads and trivial
to unit-test. See dev/test_ue_transform.py.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Sequence, Tuple

Vec3 = Tuple[float, float, float]
Mat3 = List[List[float]]

# ---------------------------------------------------------------------------
# Unit scale presets (multiply UE units to get Source units)
# ---------------------------------------------------------------------------

class UnitScale:
    ONE_TO_ONE = 1.0          # keep unit count (default for content migration)
    CM_TO_INCH = 1.0 / 2.54   # physically correct cm -> inch (~0.393701)
    INCH_TO_CM = 2.54         # inverse, if a project authored in inches

# Basis change matrix: UE (LH, Z-up) -> Source (RH, Z-up) is an X mirror.
_C: Mat3 = [
    [-1.0, 0.0, 0.0],
    [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
]


# ---------------------------------------------------------------------------
# Small matrix / vector helpers (column-vector convention: v' = M @ v)
# ---------------------------------------------------------------------------

def _matmul(a: Mat3, b: Mat3) -> Mat3:
    return [
        [sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)]
        for i in range(3)
    ]


def _matvec(m: Mat3, v: Sequence[float]) -> Vec3:
    return (
        m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
        m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
        m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2],
    )


# ---------------------------------------------------------------------------
# Unreal FRotator -> rotation matrix (column-vector convention)
# ---------------------------------------------------------------------------

def ue_rotation_matrix(pitch: float, yaw: float, roll: float) -> Mat3:
    """
    Build the column-vector rotation matrix for an Unreal FRotator.

    Uses Unreal's FRotationMatrix basis (rows are the rotated world axes) and
    returns its transpose so that ``v_world = M @ v_local`` holds.
    """
    p = math.radians(pitch)
    y = math.radians(yaw)
    r = math.radians(roll)
    sp, cp = math.sin(p), math.cos(p)
    sy, cy = math.sin(y), math.cos(y)
    sr, cr = math.sin(r), math.cos(r)

    # Rows = Unreal object axes in world space (FRotationMatrix).
    fwd = (cp * cy, cp * sy, sp)                                    # +X
    right = (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp)  # +Y
    up = (-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp)   # +Z

    # Column convention: put the axes into the columns (transpose of the rows).
    return [
        [fwd[0], right[0], up[0]],
        [fwd[1], right[1], up[1]],
        [fwd[2], right[2], up[2]],
    ]


# ---------------------------------------------------------------------------
# Source rotation matrix -> QAngle (Source engine MatrixAngles)
# ---------------------------------------------------------------------------

def source_matrix_angles(m: Mat3) -> Vec3:
    """
    Extract (pitch, yaw, roll) in degrees from a Source-space rotation matrix,
    replicating Source's MatrixAngles(). Column 0 is forward, 1 is left,
    2 is up.
    """
    forward = (m[0][0], m[1][0], m[2][0])
    left = (m[0][1], m[1][1], m[2][1])
    up = (m[0][2], m[1][2], m[2][2])

    xy_dist = math.hypot(forward[0], forward[1])
    if xy_dist > 1e-4:
        yaw = math.degrees(math.atan2(forward[1], forward[0]))
        pitch = math.degrees(math.atan2(-forward[2], xy_dist))
        roll = math.degrees(math.atan2(left[2], up[2]))
    else:
        # Gimbal: looking straight up/down, roll is indeterminate -> 0.
        yaw = math.degrees(math.atan2(-left[0], left[1]))
        pitch = math.degrees(math.atan2(-forward[2], xy_dist))
        roll = 0.0
    return (pitch, yaw, roll)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def convert_position(pos_ue: Sequence[float], scale: float = UnitScale.ONE_TO_ONE) -> Vec3:
    """UE location (X, Y, Z) -> Source position, with unit scaling."""
    x, y, z = _matvec(_C, pos_ue)
    return (x * scale, y * scale, z * scale)


def convert_rotation(pitch: float, yaw: float, roll: float) -> Vec3:
    """
    UE FRotator (pitch, yaw, roll) -> Source QAngle (pitch, yaw, roll), degrees.

    Applies R_src = C @ R_ue @ C then reads Source Euler angles back out.
    In practice (verified in dev/test_ue_transform.py) this yields:
    pitch -> -pitch, yaw -> -yaw, roll -> roll, for the faithful UE and Source
    angle conventions.
    """
    r_ue = ue_rotation_matrix(pitch, yaw, roll)
    r_src = _matmul(_matmul(_C, r_ue), _C)
    return source_matrix_angles(r_src)


def convert_scale(scale_ue: Sequence[float]) -> Vec3:
    """
    UE component scale (X, Y, Z) -> Source scale.

    Scale is dimensionless; the Y mirror does not change a magnitude, so the
    three axes pass through unchanged (kept as a function so callers route all
    transform concerns through this module).
    """
    return (float(scale_ue[0]), float(scale_ue[1]), float(scale_ue[2]))


@dataclass
class UETransform:
    """A single UE actor/component transform in UE space."""
    location: Vec3 = (0.0, 0.0, 0.0)          # cm, UE axes
    rotation: Vec3 = (0.0, 0.0, 0.0)          # FRotator (pitch, yaw, roll)
    scale: Vec3 = (1.0, 1.0, 1.0)


@dataclass
class SourceTransform:
    """The same transform expressed in Source 2 space, ready for vmap/vsmart."""
    origin: Vec3 = (0.0, 0.0, 0.0)            # Source units
    angles: Vec3 = (0.0, 0.0, 0.0)            # QAngle (pitch, yaw, roll)
    scales: Vec3 = (1.0, 1.0, 1.0)


def convert_transform(t: UETransform, unit_scale: float = UnitScale.ONE_TO_ONE) -> SourceTransform:
    """Convert a whole UE transform into Source space in one call."""
    return SourceTransform(
        origin=convert_position(t.location, unit_scale),
        angles=convert_rotation(*t.rotation),
        scales=convert_scale(t.scale),
    )

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
to unit-test. Run the self-check with:

    python -m src.forms.unreal_porter.transform
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Sequence, Tuple

Vec3 = Tuple[float, float, float]
Mat3 = List[List[float]]

# Unit scale presets (multiply UE units to get Source units)

class UnitScale:
    ONE_TO_ONE = 1.0          # keep unit count (default for content migration)
    CM_TO_INCH = 1.0 / 2.54   # physically correct cm -> inch (~0.393701)
    INCH_TO_CM = 2.54         # inverse, if a project authored in inches

# Basis change matrix: UE (LH, Z-up) -> Source (RH, Z-up) is a Y mirror.
#
# The axis is not a free choice. UE's own FBX exporter converts mesh vertices
# with FFbxDataConverter::ConvertToFbxPos, which emits (x, -y, z) and declares
# the scene right-handed, so the geometry has already been mirrored on Y before
# it reaches Source. Positions and rotations must use the same C or actors land
# in a different space than the meshes they place. See demo() for the proof that
# only this axis feeds source_matrix_angles a valid left-vector column.
_C: Mat3 = [
    [1.0, 0.0, 0.0],
    [0.0, -1.0, 0.0],
    [0.0, 0.0, 1.0],
]


# Small matrix / vector helpers (column-vector convention: v' = M @ v)

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


# Unreal FRotator -> rotation matrix (column-vector convention)

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


# Source rotation matrix -> QAngle (Source engine MatrixAngles)

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


def source_rotation_matrix(pitch: float, yaw: float, roll: float) -> Mat3:
    """Source QAngle -> rotation matrix (Source's AngleMatrix).

    The exact inverse of source_matrix_angles, so a matrix can be built from
    stored angles, composed with another rotation, and read back out.
    """
    p = math.radians(pitch)
    y = math.radians(yaw)
    r = math.radians(roll)
    sp, cp = math.sin(p), math.cos(p)
    sy, cy = math.sin(y), math.cos(y)
    sr, cr = math.sin(r), math.cos(r)

    return [
        [cp * cy, sr * sp * cy - cr * sy, cr * sp * cy + sr * sy],
        [cp * sy, sr * sp * sy + cr * cy, cr * sp * sy - sr * cy],
        [-sp,     sr * cp,                cr * cp],
    ]


# Public API

def convert_position(pos_ue: Sequence[float], scale: float = UnitScale.ONE_TO_ONE) -> Vec3:
    """UE location (X, Y, Z) -> Source position, with unit scaling."""
    x, y, z = _matvec(_C, pos_ue)
    return (x * scale, y * scale, z * scale)


def convert_rotation(pitch: float, yaw: float, roll: float) -> Vec3:
    """
    UE FRotator (pitch, yaw, roll) -> Source QAngle (pitch, yaw, roll), degrees.

    Applies R_src = C @ R_ue @ C then reads Source Euler angles back out.
    Exactly equivalent to (-pitch, -yaw, +roll) away from the gimbal poles —
    swept and asserted in demo() rather than special-cased here, because the
    matrix path stays correct at pitch = +-90 where the closed form does not.
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


def is_mirrored(scales: Sequence[float]) -> bool:
    """Does this scale flip handedness (an odd number of negative axes)?

    Source 2 renders a negatively scaled prop inside-out — the winding is never
    flipped to match — so this is the test for "needs a mirrored copy of the
    model" rather than a plain placement.
    """
    return (float(scales[0]) * float(scales[1]) * float(scales[2])) < 0.0


def mirror_placement(angles: Sequence[float], scales: Sequence[float]):
    """Re-express a mirrored placement as a *mirrored model* at positive scale.

    Returns (angles, scales, mirror_axes) where mirror_axes is a per-axis
    (x, y, z) tuple of bools for ModelDoc's ModelModifier_ScaleAndMirror. When
    the scale does not flip handedness nothing is mirrored, mirror_axes is all
    False, and the inputs come back untouched.

    Mirroring *exactly the negative axes* is what makes this free: every matrix
    here is diagonal, so it commutes, and

        R @ diag(s) == R @ diag(|s|) @ M      with   M = mirror(negative axes)

    falls straight out — the entity keeps the angles it already had and only
    drops the signs off its scale. Mirroring some other axis would work too but
    would leave a 180 degree rotation to fold back into those angles.

    Note the even case is deliberately not mirrored: two negative axes are a
    proper rotation, winding is preserved, and Source 2 renders it correctly as
    an ordinary negatively scaled placement.
    """
    if not is_mirrored(scales):
        return (tuple(float(a) for a in angles),
                tuple(float(s) for s in scales),
                (False, False, False))

    return (tuple(float(a) for a in angles),
            tuple(abs(float(s)) for s in scales),
            tuple(float(s) < 0.0 for s in scales))


def _wrap(a: float) -> float:
    """Angle wrapped to (-180, 180] so sign-flipped forms compare equal."""
    return round((a + 180.0) % 360.0 - 180.0, 6) + 0.0


def demo():
    # The mirror axis is the whole ballgame: pick the wrong one and yaw still
    # looks right (both axes give -yaw), so this is checked structurally rather
    # than by eyeballing a placement.
    #
    # source_matrix_angles reads column 1 as Source's LEFT vector, but UE's
    # column 1 is its RIGHT vector. Only the Y mirror makes column 1 of C@R@C
    # come out as the mirrored UE left vector; the X mirror yields mirrored
    # RIGHT, i.e. every extracted roll/pitch is negated.
    r = ue_rotation_matrix(20, 60, 30)
    ue_right = (r[0][1], r[1][1], r[2][1])
    s = _matmul(_matmul(_C, r), _C)
    col1 = (s[0][1], s[1][1], s[2][1])
    want_left = tuple(-v for v in _matvec(_C, ue_right))
    assert all(abs(a - b) < 1e-9 for a, b in zip(col1, want_left)), (col1, want_left)

    # Y mirror, not X — UE's FBX exporter already mirrored the meshes on Y.
    assert _C == [[1.0, 0, 0], [0, -1.0, 0], [0, 0, 1.0]], _C
    assert convert_position((100, 200, 50)) == (100, -200, 50)
    assert abs(convert_position((100, 200, 50), UnitScale.CM_TO_INCH)[0] - 100 / 2.54) < 1e-9
    assert convert_scale((1, 2, 3)) == (1.0, 2.0, 3.0), "a mirror does not change magnitudes"

    # (pitch, yaw, roll) -> (-pitch, -yaw, +roll), away from the gimbal poles.
    for pitch in range(-80, 81, 10):
        for yaw in range(-180, 180, 15):
            for roll in range(-180, 180, 15):
                got = convert_rotation(pitch, yaw, roll)
                want = (-pitch, -yaw, roll)
                assert tuple(map(_wrap, got)) == tuple(map(_wrap, want)), (pitch, yaw, roll, got)

    # Straight up/down: roll is indeterminate, so only pitch is pinned. The
    # matrix path must still produce a finite angle rather than blowing up.
    for yaw in (0, 90, -90, 180):
        p, _y, _r = convert_rotation(90, yaw, 0)
        assert _wrap(p) == -90.0, (yaw, p)

    st = convert_transform(UETransform((10, 20, 30), (0, 90, 0), (1, 1, 2)))
    assert st.origin == (10, -20, 30), st.origin
    assert tuple(map(_wrap, st.angles)) == (0.0, -90.0, 0.0), st.angles
    assert st.scales == (1.0, 1.0, 2.0), st.scales

    # source_rotation_matrix must invert source_matrix_angles exactly, or the
    # mirror below composes its 180 degree turn onto the wrong basis.
    for pitch in (-80, -30, 0, 25, 70):
        for yaw in (-170, -90, 0, 45, 135):
            for roll in (-150, 0, 60, 179):
                back = source_matrix_angles(source_rotation_matrix(pitch, yaw, roll))
                assert tuple(map(_wrap, back)) == (pitch, yaw, roll), (pitch, yaw, roll, back)

    # An even number of negative axes is still a proper rotation — nothing to
    # mirror, and a copy of the model would be wasted.
    assert not is_mirrored((1, 1, 1)) and not is_mirrored((-1, -1, 1))
    assert is_mirrored((-1, 1, 1)) and is_mirrored((-1, -1, -1))
    a, s, m = mirror_placement((10, 20, 30), (1, 2, 3))
    assert (a, s, m) == ((10.0, 20.0, 30.0), (1.0, 2.0, 3.0), (False, False, False))

    # Two negative axes are a proper rotation — winding survives, so mirroring
    # would cost a duplicated model for nothing.
    assert mirror_placement((0, 0, 0), (-1, -1, 1))[2] == (False, False, False)

    # The whole claim of mirror_placement: the returned angles and positive
    # scales, applied to a model mirrored on the returned axes, are the SAME
    # linear map as the original angles at the original negative scales.
    # Checked on every sign pattern that flips handedness.
    for sign in ((-1, 1, 1), (1, -1, 1), (1, 1, -1), (-1, -1, -1)):
        for base_angles in ((0, 0, 0), (0, 90, 0), (15, -40, 65), (-70, 160, -25)):
            scales = tuple(sg * v for sg, v in zip(sign, (1.5, 2.0, 3.0)))
            new_angles, new_scales, axes = mirror_placement(base_angles, scales)
            assert all(v > 0 for v in new_scales), (sign, new_scales)
            # Exactly the negative axes get mirrored, which is what keeps the
            # angles untouched.
            assert axes == tuple(v < 0 for v in sign), (sign, axes)
            assert new_angles == tuple(float(v) for v in base_angles), (sign, new_angles)

            want = _matmul(source_rotation_matrix(*base_angles),
                           [[scales[0], 0, 0], [0, scales[1], 0], [0, 0, scales[2]]])
            # ModelModifier_ScaleAndMirror bakes M into the compiled model, so
            # it sits to the right of the placement's own scale.
            mirror: Mat3 = [[0.0] * 3 for _ in range(3)]
            for i in range(3):
                mirror[i][i] = -1.0 if axes[i] else 1.0
            got = _matmul(_matmul(source_rotation_matrix(*new_angles),
                                  [[new_scales[0], 0, 0], [0, new_scales[1], 0], [0, 0, new_scales[2]]]),
                          mirror)
            assert all(abs(want[i][j] - got[i][j]) < 1e-9 for i in range(3) for j in range(3)), \
                (sign, base_angles, want, got)
    print("ok")


if __name__ == "__main__":
    demo()

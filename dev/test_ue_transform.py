"""
Sanity checks for the UE -> Source 2 coordinate/unit transform prototype.
Run:  python dev/test_ue_transform.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.forms.unreal_converter.transform import (
    UnitScale, UETransform, _C, _matmul,
    ue_rotation_matrix, source_matrix_angles,
    convert_position, convert_rotation, convert_transform,
)

EPS = 1e-4


def source_angle_matrix(pitch, yaw, roll):
    """Source engine AngleMatrix (the inverse of source_matrix_angles)."""
    p, y, r = math.radians(pitch), math.radians(yaw), math.radians(roll)
    sp, cp = math.sin(p), math.cos(p)
    sy, cy = math.sin(y), math.cos(y)
    sr, cr = math.sin(r), math.cos(r)
    return [
        [cp * cy, sr * sp * cy - cr * sy, cr * sp * cy + sr * sy],
        [cp * sy, sr * sp * sy + cr * cy, cr * sp * sy - sr * cy],
        [-sp,     sr * cp,                cr * cp],
    ]


def approx(a, b, eps=EPS):
    return all(abs(x - y) <= eps for x, y in zip(a, b))


def check(name, got, want):
    ok = approx(got, want)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: got={tuple(round(v, 4) for v in got)} want={want}")
    assert ok, f"{name} mismatch"


# --- Position: X mirror + scale --------------------------------------------
check("pos identity",       convert_position((0, 0, 0)),                 (0, 0, 0))
check("pos X mirror",       convert_position((100, 200, 300)),           (-100, 200, 300))
check("pos cm->inch",       convert_position((254, 0, 0), UnitScale.CM_TO_INCH), (-100, 0, 0))

# --- Rotation: handedness flip negates yaw & roll; Source flips pitch too --
check("rot identity",       convert_rotation(0, 0, 0),                   (0, 0, 0))

# --- Rigorous: extracted Source angles must rebuild the conjugated matrix --
def conj(pitch, yaw, roll):
    r_ue = ue_rotation_matrix(pitch, yaw, roll)
    return _matmul(_matmul(_C, r_ue), _C)

for (p, y, r) in [(0, 0, 0), (30, 0, 0), (0, 90, 0), (0, 0, 90),
                  (15, 90, 0), (-40, 33, 77), (89, -120, 12), (10, 200, -95)]:
    r_src = conj(p, y, r)
    ang = source_matrix_angles(r_src)
    rebuilt = source_angle_matrix(*ang)
    ok = all(abs(r_src[i][j] - rebuilt[i][j]) <= EPS for i in range(3) for j in range(3))
    print(f"[{'PASS' if ok else 'FAIL'}] roundtrip UE({p},{y},{r}) -> Source{tuple(round(a,2) for a in ang)}")
    assert ok, f"roundtrip failed for {(p, y, r)}"

# --- Round-trip a full transform -------------------------------------------
st = convert_transform(
    UETransform(location=(500, -250, 128), rotation=(15, 90, 0), scale=(2, 2, 2)),
    unit_scale=UnitScale.ONE_TO_ONE,
)
check("xform origin",       st.origin,  (-500, -250, 128))
check("xform scales",       st.scales,  (2, 2, 2))

print("\nAll transform checks passed.")

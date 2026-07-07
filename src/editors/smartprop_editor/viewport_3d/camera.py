"""
Camera module for the 3D viewport.
Provides an orbit camera with numpy-based matrix math.
"""
import math
import numpy as np


def _normalize(v):
    """Normalize a vector, returning zero vector if length is zero."""
    n = np.linalg.norm(v)
    return v / n if n > 1e-10 else v


def look_at(eye, target, up):
    """Build a 4x4 view matrix (column-major for OpenGL)."""
    f = _normalize(target - eye)
    s = _normalize(np.cross(f, up))
    u = np.cross(s, f)

    m = np.eye(4, dtype=np.float32)
    m[0, 0], m[1, 0], m[2, 0] = s[0], s[1], s[2]
    m[0, 1], m[1, 1], m[2, 1] = u[0], u[1], u[2]
    m[0, 2], m[1, 2], m[2, 2] = -f[0], -f[1], -f[2]
    m[3, 0] = -np.dot(s, eye)
    m[3, 1] = -np.dot(u, eye)
    m[3, 2] = np.dot(f, eye)
    return m


def perspective(fov_deg, aspect, near, far):
    """Build a 4x4 perspective projection matrix (column-major for OpenGL)."""
    f = 1.0 / math.tan(math.radians(fov_deg) / 2.0)
    m = np.zeros((4, 4), dtype=np.float32)
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = -1.0
    m[3, 2] = (2.0 * far * near) / (near - far)
    return m


def ortho(left, right, bottom, top, near, far):
    """Build a 4x4 orthographic projection matrix."""
    m = np.zeros((4, 4), dtype=np.float32)
    m[0, 0] = 2.0 / (right - left)
    m[1, 1] = 2.0 / (top - bottom)
    m[2, 2] = -2.0 / (far - near)
    m[3, 0] = -(right + left) / (right - left)
    m[3, 1] = -(top + bottom) / (top - bottom)
    m[3, 2] = -(far + near) / (far - near)
    m[3, 3] = 1.0
    return m


def translation_matrix(tx, ty, tz):
    """Build a 4x4 translation matrix."""
    m = np.eye(4, dtype=np.float32)
    m[3, 0] = tx
    m[3, 1] = ty
    m[3, 2] = tz
    return m


def scale_matrix(sx, sy, sz):
    """Build a 4x4 scale matrix."""
    m = np.eye(4, dtype=np.float32)
    m[0, 0] = sx
    m[1, 1] = sy
    m[2, 2] = sz
    return m


def rotation_matrix_euler(pitch_deg, yaw_deg, roll_deg):
    """Build a 4x4 rotation matrix from Euler angles (Source 2 convention: pitch=X, yaw=Y, roll=Z)."""
    p = math.radians(pitch_deg)
    y = math.radians(yaw_deg)
    r = math.radians(roll_deg)

    cp, sp = math.cos(p), math.sin(p)
    cy, sy = math.cos(y), math.sin(y)
    cr, sr = math.cos(r), math.sin(r)

    # Rotation order: yaw (Z) * pitch (X) * roll (Y)  — Source 2 convention
    m = np.eye(4, dtype=np.float32)
    m[0, 0] = cy * cr + sy * sp * sr
    m[0, 1] = cp * sr
    m[0, 2] = -sy * cr + cy * sp * sr
    m[1, 0] = -cy * sr + sy * sp * cr
    m[1, 1] = cp * cr
    m[1, 2] = sy * sr + cy * sp * cr
    m[2, 0] = sy * cp
    m[2, 1] = -sp
    m[2, 2] = cy * cp
    return m


# Source 2 uses Z-up. glTF (and our viewport) uses Y-up.
# This matrix converts Source 2 coordinates → OpenGL Y-up:
#   GL_X =  S2_X
#   GL_Y =  S2_Z
#   GL_Z = -S2_Y
SOURCE2_TO_GL = np.array([
    [1,  0,  0, 0],
    [0,  0,  1, 0],
    [0, -1,  0, 0],
    [0,  0,  0, 1],
], dtype=np.float32)


class Camera:
    """Orbit camera for the 3D viewport."""

    def __init__(self):
        self.yaw = 30.0       # degrees, horizontal orbit
        self.pitch = 25.0     # degrees, vertical orbit
        self.distance = 500.0 # distance from target
        self.target = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.fov = 45.0
        self.near = 1.0
        self.far = 50000.0
        self.aspect = 1.0
        self._pan_speed = 1.0

    @property
    def position(self):
        """Camera world position computed from orbit parameters."""
        yaw_r = math.radians(self.yaw)
        pitch_r = math.radians(self.pitch)
        x = self.distance * math.cos(pitch_r) * math.sin(yaw_r)
        y = self.distance * math.sin(pitch_r)
        z = self.distance * math.cos(pitch_r) * math.cos(yaw_r)
        return self.target + np.array([x, y, z], dtype=np.float32)

    @property
    def view_matrix(self):
        return look_at(self.position, self.target, np.array([0, 1, 0], dtype=np.float32))

    @property
    def projection_matrix(self):
        return perspective(self.fov, self.aspect, self.near, self.far)

    @property
    def right_vector(self):
        """Camera right direction in world space."""
        yaw_r = math.radians(self.yaw)
        return np.array([math.cos(yaw_r), 0, -math.sin(yaw_r)], dtype=np.float32)

    @property
    def up_vector(self):
        """Camera up direction in world space."""
        yaw_r = math.radians(self.yaw)
        pitch_r = math.radians(self.pitch)
        return np.array([
            -math.sin(pitch_r) * math.sin(yaw_r),
            math.cos(pitch_r),
            -math.sin(pitch_r) * math.cos(yaw_r),
        ], dtype=np.float32)

    def orbit(self, dx, dy):
        """Orbit around the target. dx/dy are screen-space pixel deltas."""
        self.yaw -= dx * 0.3
        self.pitch -= dy * 0.3
        self.pitch = max(-89.9, min(89.9, self.pitch))

    def pan(self, dx, dy):
        """Pan the camera (move target). dx/dy are screen-space pixel deltas."""
        speed = self.distance * 0.002 * self._pan_speed
        right = self.right_vector
        up = self.up_vector
        self.target -= right * dx * speed
        self.target += up * dy * speed

    def zoom(self, delta):
        """Zoom via scroll wheel delta (positive = zoom in)."""
        factor = 1.15 if delta > 0 else 1.0 / 1.15
        self.distance = max(1.0, min(50000.0, self.distance / factor))

    def fit_to_bounds(self, bbox_min, bbox_max):
        """Adjust camera to fit the given bounding box in view."""
        center = (bbox_min + bbox_max) * 0.5
        extent = np.linalg.norm(bbox_max - bbox_min)
        if extent < 1.0:
            extent = 100.0
        self.target = center.astype(np.float32)
        self.distance = extent * 1.5

    def set_preset(self, name):
        """Set camera to a named view preset."""
        presets = {
            "Perspective":  (30.0,  25.0),
            "Top (XY)":     (0.0,   89.9),
            "Front (XZ)":   (0.0,    0.0),
            "Side (YZ)":    (90.0,   0.0),
        }
        if name in presets:
            self.yaw, self.pitch = presets[name]

    def screen_to_ray(self, sx, sy, viewport_w, viewport_h):
        """Convert screen coordinates to a world-space ray (origin, direction)."""
        # NDC
        ndc_x = (2.0 * sx / viewport_w) - 1.0
        ndc_y = 1.0 - (2.0 * sy / viewport_h)

        # Inverse projection
        proj = self.projection_matrix
        view = self.view_matrix

        inv_proj = np.linalg.inv(proj)
        inv_view = np.linalg.inv(view)

        # Clip space → view space
        clip = np.array([ndc_x, ndc_y, -1.0, 1.0], dtype=np.float32)
        eye_pos = inv_proj @ clip
        eye_pos = np.array([eye_pos[0], eye_pos[1], -1.0, 0.0], dtype=np.float32)

        # View space → world space
        world_dir = inv_view @ eye_pos
        direction = _normalize(world_dir[:3])

        return self.position.copy(), direction

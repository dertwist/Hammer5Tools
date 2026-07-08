"""
GLSL shader source code for the 3D viewport.
All shaders target OpenGL 3.3 core profile.
"""

# ---------------------------------------------------------------------------
# Model shader — Phong lighting with optional texture
# ---------------------------------------------------------------------------

MODEL_VERTEX_SHADER = """
#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aTexCoord;

uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProjection;
uniform mat3 uNormalMatrix;

out vec3 vWorldPos;
out vec3 vNormal;
out vec2 vTexCoord;

void main() {
    vec4 worldPos = uModel * vec4(aPos, 1.0);
    vWorldPos = worldPos.xyz;
    vNormal = normalize(uNormalMatrix * aNormal);
    vTexCoord = aTexCoord;
    gl_Position = uProjection * uView * worldPos;
}
"""

MODEL_FRAGMENT_SHADER = """
#version 330 core
in vec3 vWorldPos;
in vec3 vNormal;
in vec2 vTexCoord;

uniform vec3 uCameraPos;
uniform vec3 uBaseColor;
uniform float uHighlight;
uniform int uHasTexture;
uniform sampler2D uTexture;

out vec4 FragColor;

float pow2(float x) { return x * x; }
vec3 pow2(vec3 x) { return x * x; }
float saturate(float x) { return clamp(x, 0.0, 1.0); }
vec3 saturate(vec3 x) { return clamp(x, 0.0, 1.0); }

vec3 SrgbGammaToLinear(vec3 color)
{
    vec3 vLinearSegment = color / vec3(12.92);
    vec3 vExpSegment = pow((color / vec3(1.055)) + vec3(0.0521327), vec3(2.4));

    const float cap = 0.04045;
    float select = color.r > cap ? vExpSegment.r : vLinearSegment.r;
    float select1 = color.g > cap ? vExpSegment.g : vLinearSegment.g;
    float select2 = color.b > cap ? vExpSegment.b : vLinearSegment.b;

    return vec3(select, select1, select2);
}

vec3 SrgbLinearToGamma(vec3 vLinearColor)
{
    vec3 vLinearSegment = vLinearColor * 12.92;
    vec3 vExpSegment = (1.055 * pow(vLinearColor, vec3(1.0 / 2.4))) - 0.055;

    vec3 vGammaColor = vec3((vLinearColor.r <= 0.0031308) ? vLinearSegment.r : vExpSegment.r,
                            (vLinearColor.g <= 0.0031308) ? vLinearSegment.g : vExpSegment.g,
                            (vLinearColor.b <= 0.0031308) ? vLinearSegment.b : vExpSegment.b);
    return vGammaColor;
}

vec3 CalculateFullbrightLighting(vec3 albedo, vec3 normal, vec3 viewVector)
{
    float flFakeDiffuseLighting = saturate(dot(normal, viewVector)) * 0.7 + 0.3;

    vec3 vReflectionDirWs = reflect(-viewVector, normal);

    float flFakeSpecularLighting = pow2(pow2(saturate(dot(viewVector, vReflectionDirWs)))) * 0.05;

    // Weights converted from Source 2 space (Z-up) to OpenGL space (Y-up)
    //   Source Z-up (1.0/0.2) -> OpenGL Y-up (1.0/0.2)
    //   Source X-forward (0.6) -> OpenGL X-right (0.6)
    //   Source Y-left (0.4) -> OpenGL Z-forward/backward (0.4)
    float XtraLight1 = dot(vec3(0.6, 1.0, 0.4), pow2(saturate(normal)));
    float XtraLight2 = dot(vec3(0.6, 0.2, 0.4), pow2(saturate(-normal)));
    float xtraLight = XtraLight1 + XtraLight2;

    return xtraLight * albedo * flFakeDiffuseLighting + flFakeSpecularLighting;
}

void main() {
    vec3 baseColor = uBaseColor;
    if (uHasTexture == 1) {
        baseColor = SrgbGammaToLinear(texture(uTexture, vTexCoord).rgb);
    }

    vec3 norm = normalize(vNormal);
    vec3 viewDir = normalize(uCameraPos - vWorldPos);

    vec3 color = CalculateFullbrightLighting(baseColor, norm, viewDir);

    // Highlight tint for selection
    if (uHighlight > 0.5) {
        color = mix(color, vec3(0.0, 0.85, 0.85), 0.25);
    }

    FragColor = vec4(SrgbLinearToGamma(color), 1.0);
}
"""

# ---------------------------------------------------------------------------
# Picking shader — renders each object with a unique flat color for ID lookup
# ---------------------------------------------------------------------------

PICKING_VERTEX_SHADER = """
#version 330 core
layout(location = 0) in vec3 aPos;

uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProjection;

void main() {
    gl_Position = uProjection * uView * uModel * vec4(aPos, 1.0);
}
"""

PICKING_FRAGMENT_SHADER = """
#version 330 core
uniform vec3 uPickColor;
out vec4 FragColor;

void main() {
    FragColor = vec4(uPickColor, 1.0);
}
"""

# ---------------------------------------------------------------------------
# Grid shader — procedural infinite grid on the XZ plane (Y=0)
# ---------------------------------------------------------------------------

GRID_VERTEX_SHADER = """
#version 330 core
layout(location = 0) in vec3 aPos;

uniform mat4 uView;
uniform mat4 uProjection;

out vec3 vWorldPos;

void main() {
    vWorldPos = aPos;
    gl_Position = uProjection * uView * vec4(aPos, 1.0);
}
"""

GRID_FRAGMENT_SHADER = """
#version 330 core
in vec3 vWorldPos;
out vec4 FragColor;

uniform float uGridStep;

void main() {
    // Minor cell size follows the toolbar's Grid Step value so the floor
    // visually matches the snapping increment. Guard against a zero step.
    float gridSize = max(uGridStep, 0.001);
    float majorEvery = 5.0;

    vec2 coord = vWorldPos.xz / gridSize;
    vec2 grid = abs(fract(coord - 0.5) - 0.5) / fwidth(coord);
    float line = min(grid.x, grid.y);

    // Major grid lines
    vec2 majorCoord = vWorldPos.xz / (gridSize * majorEvery);
    vec2 majorGrid = abs(fract(majorCoord - 0.5) - 0.5) / fwidth(majorCoord);
    float majorLine = min(majorGrid.x, majorGrid.y);

    // Distance fade
    float dist = length(vWorldPos.xz);
    float fade = 1.0 - smoothstep(800.0, 2500.0, dist);

    float minorAlpha = (1.0 - min(line, 1.0)) * 0.15 * fade;
    float majorAlpha = (1.0 - min(majorLine, 1.0)) * 0.35 * fade;

    float alpha = max(minorAlpha, majorAlpha);
    vec3 color = vec3(0.5);

    // Infinite ground-plane axes, Blender-style — full-length lines that fade
    // with distance exactly like the grid cells (no vertical Z-up axis here).
    //   Source X (red)   runs along GL +X  -> the line where GL z = 0
    //   Source Y (green) runs along GL -Z  -> the line where GL x = 0
    float axisX = abs(vWorldPos.z) / fwidth(vWorldPos.z);  // proximity to X axis
    float axisY = abs(vWorldPos.x) / fwidth(vWorldPos.x);  // proximity to Y axis

    if (axisX < 1.0) {
        color = vec3(0.80, 0.25, 0.25);
        alpha = max(alpha, (1.0 - axisX) * 0.75 * fade);
    }
    if (axisY < 1.0) {
        color = vec3(0.30, 0.75, 0.35);
        alpha = max(alpha, (1.0 - axisY) * 0.75 * fade);
    }

    FragColor = vec4(color, alpha);
}
"""

# ---------------------------------------------------------------------------
# Gizmo shader — unlit solid color, always on top
# ---------------------------------------------------------------------------

GIZMO_VERTEX_SHADER = """
#version 330 core
layout(location = 0) in vec3 aPos;

uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProjection;

void main() {
    gl_Position = uProjection * uView * uModel * vec4(aPos, 1.0);
}
"""

GIZMO_FRAGMENT_SHADER = """
#version 330 core
uniform vec3 uColor;
uniform float uAlpha;
out vec4 FragColor;

void main() {
    FragColor = vec4(uColor, uAlpha);
}
"""

# ---------------------------------------------------------------------------
# Wireframe / fallback box shader — simple unlit wireframe
# ---------------------------------------------------------------------------

WIREFRAME_VERTEX_SHADER = """
#version 330 core
layout(location = 0) in vec3 aPos;

uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProjection;

void main() {
    gl_Position = uProjection * uView * uModel * vec4(aPos, 1.0);
}
"""

WIREFRAME_FRAGMENT_SHADER = """
#version 330 core
uniform vec3 uColor;
out vec4 FragColor;

void main() {
    FragColor = vec4(uColor, 1.0);
}
"""

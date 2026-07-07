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

void main() {
    // Light direction (from upper-right, following camera roughly)
    vec3 lightDir = normalize(vec3(0.3, 0.8, 0.5));
    vec3 lightColor = vec3(1.0, 0.98, 0.95);
    vec3 ambientColor = vec3(0.15, 0.16, 0.18);

    vec3 baseColor = uBaseColor;
    if (uHasTexture == 1) {
        baseColor = texture(uTexture, vTexCoord).rgb;
    }

    // Diffuse
    vec3 norm = normalize(vNormal);
    float diff = max(dot(norm, lightDir), 0.0);

    // Specular (Blinn-Phong)
    vec3 viewDir = normalize(uCameraPos - vWorldPos);
    vec3 halfDir = normalize(lightDir + viewDir);
    float spec = pow(max(dot(norm, halfDir), 0.0), 32.0);

    // Fill light from below-left
    vec3 fillDir = normalize(vec3(-0.5, -0.3, -0.4));
    float fillDiff = max(dot(norm, fillDir), 0.0) * 0.15;

    vec3 color = ambientColor * baseColor
               + diff * lightColor * baseColor
               + fillDiff * vec3(0.4, 0.5, 0.7) * baseColor
               + spec * vec3(0.3);

    // Highlight tint for selection
    if (uHighlight > 0.5) {
        color = mix(color, vec3(0.0, 0.85, 0.85), 0.25);
    }

    FragColor = vec4(color, 1.0);
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

void main() {
    float gridSize = 50.0;
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

    // X axis (red) and Z axis (blue)
    if (abs(vWorldPos.z) < gridSize * 0.4) {
        float xAxis = abs(vWorldPos.x) / fwidth(vWorldPos.x);
        if (xAxis < 1.0) {
            FragColor = vec4(0.85, 0.2, 0.2, (1.0 - xAxis) * 0.6 * fade);
            return;
        }
    }
    if (abs(vWorldPos.x) < gridSize * 0.4) {
        float zAxis = abs(vWorldPos.z) / fwidth(vWorldPos.z);
        if (zAxis < 1.0) {
            FragColor = vec4(0.2, 0.4, 0.85, (1.0 - zAxis) * 0.6 * fade);
            return;
        }
    }

    FragColor = vec4(vec3(0.5), alpha);
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

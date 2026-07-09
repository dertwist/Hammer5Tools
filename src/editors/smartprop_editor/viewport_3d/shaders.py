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
uniform vec3 uBaseColor;      // flat fallback colour (solid mode / untextured)
uniform float uHighlight;     // >0.5 = draw the legacy fill highlight (path editor)

// PBR material inputs (glTF metallic-roughness model, as written by VRF).
uniform vec4 uBaseColorFactor;
uniform int  uHasBaseTex;
uniform sampler2D uBaseTex;   // unit 0 — sRGB albedo (+ alpha)
uniform int  uHasNormalTex;
uniform sampler2D uNormalTex; // unit 1 — tangent-space normal
uniform int  uHasMRTex;
uniform sampler2D uMRTex;     // unit 2 — G=roughness, B=metalness
uniform float uRoughness;
uniform float uMetallic;
uniform int  uHasAO;
uniform sampler2D uAOTex;     // unit 3 — R=occlusion
uniform int  uHasEmissive;
uniform sampler2D uEmissiveTex; // unit 4 — sRGB emissive
uniform vec3 uEmissiveFactor;

// 0 = OPAQUE, 1 = MASK (alpha test), 2 = BLEND (translucent)
uniform int  uAlphaMode;
uniform float uAlphaCutoff;

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

// Per-pixel tangent frame from screen-space derivatives (Christian Schüler).
// Lets us apply tangent-space normal maps without a vertex tangent attribute,
// and stays correct through the viewport's Source<->GL coordinate remap.
mat3 CotangentFrame(vec3 N, vec3 p, vec2 uv)
{
    vec3 dp1 = dFdx(p);
    vec3 dp2 = dFdy(p);
    vec2 duv1 = dFdx(uv);
    vec2 duv2 = dFdy(uv);

    vec3 dp2perp = cross(dp2, N);
    vec3 dp1perp = cross(N, dp1);
    vec3 T = dp2perp * duv1.x + dp1perp * duv2.x;
    vec3 B = dp2perp * duv1.y + dp1perp * duv2.y;

    float invmax = inversesqrt(max(dot(T, T), dot(B, B)));
    return mat3(T * invmax, B * invmax, N);
}

// Stylised "fullbright" lighting matched to Source 2 Viewer, extended with
// roughness (specular sharpness) and metalness (specular tint + diffuse loss).
// ``specOut`` returns the scalar specular intensity so the translucent path can
// keep highlights readable on otherwise see-through glass.
vec3 CalculateLighting(vec3 albedo, vec3 normal, vec3 viewVector, float roughness, float metalness, float ao, out float specOut)
{
    float flFakeDiffuseLighting = saturate(dot(normal, viewVector)) * 0.7 + 0.3;

    vec3 vReflectionDirWs = reflect(-viewVector, normal);
    float specAngle = saturate(dot(viewVector, vReflectionDirWs));
    // Rougher surfaces spread the highlight and dim it.
    float specPower = mix(4.0, 80.0, 1.0 - roughness);
    float flFakeSpecularLighting = pow(specAngle, specPower) * (1.0 - roughness) * 0.35;
    specOut = flFakeSpecularLighting;

    // Hemispheric ambient (weights from Source Z-up mapped to GL Y-up).
    float XtraLight1 = dot(vec3(0.6, 1.0, 0.4), pow2(saturate(normal)));
    float XtraLight2 = dot(vec3(0.6, 0.2, 0.4), pow2(saturate(-normal)));
    float xtraLight = XtraLight1 + XtraLight2;

    vec3 diffuse = xtraLight * albedo * flFakeDiffuseLighting * ao;
    // Metals lose diffuse and tint their highlight with the albedo.
    diffuse *= (1.0 - metalness * 0.75);
    vec3 specColor = mix(vec3(1.0), albedo, metalness);

    return diffuse + flFakeSpecularLighting * specColor;
}

void main() {
    // ---- Base colour + alpha -------------------------------------------------
    vec4 base = uBaseColorFactor;
    base.rgb *= uBaseColor;
    if (uHasBaseTex == 1) {
        vec4 tex = texture(uBaseTex, vTexCoord);
        base.rgb = SrgbGammaToLinear(tex.rgb) * uBaseColorFactor.rgb;
        base.a *= tex.a;
    }

    float alpha = base.a;
    if (uAlphaMode == 1 && alpha < uAlphaCutoff) {
        discard;                 // MASK / alpha-tested cutout
    }

    // ---- Normal --------------------------------------------------------------
    vec3 norm = normalize(vNormal);
    // Two-sided shading: flip the normal on back faces so translucent surfaces
    // (drawn from both sides) and open meshes light correctly instead of going
    // dark/inverted where a back face points away from the camera.
    if (!gl_FrontFacing) norm = -norm;
    vec3 viewDir = normalize(uCameraPos - vWorldPos);
    if (uHasNormalTex == 1) {
        vec3 mapN = texture(uNormalTex, vTexCoord).xyz * 2.0 - 1.0;
        mat3 TBN = CotangentFrame(norm, vWorldPos, vTexCoord);
        norm = normalize(TBN * mapN);
    }

    // ---- Roughness / metalness / occlusion ----------------------------------
    float roughness = clamp(uRoughness, 0.04, 1.0);
    float metalness = saturate(uMetallic);
    if (uHasMRTex == 1) {
        vec3 mr = texture(uMRTex, vTexCoord).rgb;   // R=ao(unused), G=rough, B=metal
        roughness = clamp(roughness * mr.g, 0.04, 1.0);
        metalness = saturate(metalness * mr.b);
    }
    float ao = 1.0;
    if (uHasAO == 1) {
        ao = texture(uAOTex, vTexCoord).r;
    }

    // ---- Shade ---------------------------------------------------------------
    float specTerm = 0.0;
    vec3 color = CalculateLighting(base.rgb, norm, viewDir, roughness, metalness, ao, specTerm);

    if (uHasEmissive == 1) {
        color += SrgbGammaToLinear(texture(uEmissiveTex, vTexCoord).rgb) * uEmissiveFactor;
    } else {
        color += uEmissiveFactor;
    }

    // Legacy fill highlight: a cyan Fresnel rim plus a faint body tint.  The
    // SmartProp viewport no longer uses this (it draws a post-process silhouette
    // outline instead — see the OUTLINE_* shaders and
    // SmartProp3DRenderArea._render_selection_outline, and leaves uHighlight at 0),
    // but the Path editor still relies on it, so the shared shader keeps it.
    if (uHighlight > 0.5) {
        vec3 selColor = vec3(0.15, 0.95, 1.0);
        float rim = pow(1.0 - saturate(dot(norm, viewDir)), 2.5);
        color = mix(color, selColor, 0.12);
        color += selColor * rim * 1.35;
    }

    // ---- Output alpha --------------------------------------------------------
    float outAlpha = 1.0;
    if (uAlphaMode == 2) {
        // Glass/translucent: a Fresnel term makes grazing angles more opaque, and
        // the specular highlight boosts alpha so reflections read on top of the
        // background instead of fading out with the body.
        float fres = pow(1.0 - saturate(dot(norm, viewDir)), 4.0);
        outAlpha = mix(saturate(alpha), 1.0, fres * 0.8);
        outAlpha = saturate(outAlpha + specTerm * 2.0);
    }
    FragColor = vec4(SrgbLinearToGamma(color), outAlpha);
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

# ---------------------------------------------------------------------------
# Outline shader — post-process silhouette outline for the selected element
# ---------------------------------------------------------------------------
# The selected element is first rendered as a solid white-on-black, depth-culled
# silhouette into an offscreen "mask" texture (via the picking shader).  This
# fullscreen pass then dilates that mask and paints the ring that lies just
# outside the silhouette, producing a crisp constant-width outline that works on
# any mesh — unlike an inverted-hull shell, it never splits at the hard edges /
# split normals common in game props.

OUTLINE_VERTEX_SHADER = """
#version 330 core
out vec2 vUV;

void main() {
    // Gpu-generated fullscreen triangle (no VBO): IDs 0,1,2 -> UV 0,0 / 2,0 / 0,2.
    vec2 uv = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    vUV = uv;
    gl_Position = vec4(uv * 2.0 - 1.0, 0.0, 1.0);
}
"""

OUTLINE_FRAGMENT_SHADER = """
#version 330 core
in vec2 vUV;
out vec4 FragColor;

uniform sampler2D uMask;       // R = 1 inside the selected silhouette, 0 outside
uniform vec2  uTexel;          // 1/width, 1/height of the mask (device pixels)
uniform float uThickness;      // outline width, in device pixels
uniform vec3  uOutlineColor;

const int TAPS = 24;

void main() {
    float center = texture(uMask, vUV).r;

    // Ring-sample the mask at the outline radius.  ``coverage`` is how strongly a
    // neighbour falls inside the silhouette; linear filtering on the mask makes
    // it fractional across the 1-texel boundary, softening the outline edge.
    float coverage = 0.0;
    for (int i = 0; i < TAPS; ++i) {
        float a = 6.28318530718 * float(i) / float(TAPS);
        vec2 off = vec2(cos(a), sin(a)) * uTexel * uThickness;
        coverage = max(coverage, texture(uMask, vUV + off).r);
    }

    // Draw only the band that is outside the object (center ~0) but close enough
    // to it that a neighbour is inside — so the outline hugs the silhouette
    // without ever tinting the object's own surface.
    float edge = coverage * (1.0 - center);
    if (edge <= 0.003) discard;
    FragColor = vec4(uOutlineColor, clamp(edge, 0.0, 1.0));
}
"""

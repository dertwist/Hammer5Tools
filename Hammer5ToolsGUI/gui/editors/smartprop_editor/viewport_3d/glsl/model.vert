#version 430 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aTexCoord;

uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProjection;
uniform mat3 uNormalMatrix;

uniform vec2 uUvScale;
uniform vec2 uUvOffset;
uniform vec2 uUvCenter;
uniform float uUvRotation;

out vec3 vWorldPos;
out vec3 vNormal;
out vec2 vTexCoord;

void main() {
    vec4 worldPos = uModel * vec4(aPos, 1.0);
    vWorldPos = worldPos.xyz;
    vNormal = normalize(uNormalMatrix * aNormal);

    vec2 uv = aTexCoord - uUvCenter;
    if (uUvRotation != 0.0) {
        float rad = radians(uUvRotation);
        float c = cos(rad);
        float s = sin(rad);
        uv = vec2(uv.x * c - uv.y * s, uv.x * s + uv.y * c);
    }
    uv = uv * uUvScale + uUvCenter + uUvOffset;
    // No V-flip: _decode_texture() returns textures in the orientation Source 2
    // authored them (GenerateBitmap row 0 = image top), and glTexImage2D uploads
    // that row at GL t=0.  Raw UV lands on the correct row, matching VRF's
    // renderer (which does no flip anywhere -- raw VBIB UVs, raw shader UV).
    vTexCoord = uv;
    gl_Position = uProjection * uView * worldPos;
}

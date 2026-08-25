#version 430 core
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

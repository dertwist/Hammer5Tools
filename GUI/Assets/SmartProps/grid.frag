#version 430 core
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

#version 430 core
out vec2 vUV;

void main() {
    // Gpu-generated fullscreen triangle (no VBO): IDs 0,1,2 -> UV 0,0 / 2,0 / 0,2.
    vec2 uv = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    vUV = uv;
    gl_Position = vec4(uv * 2.0 - 1.0, 0.0, 1.0);
}

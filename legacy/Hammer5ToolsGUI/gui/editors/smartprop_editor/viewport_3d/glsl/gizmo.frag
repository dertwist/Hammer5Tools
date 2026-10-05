#version 430 core
uniform vec3 uColor;
uniform float uAlpha;
out vec4 FragColor;

void main() {
    FragColor = vec4(uColor, uAlpha);
}

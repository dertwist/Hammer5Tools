#version 430 core
uniform vec3 uPickColor;
out vec4 FragColor;

void main() {
    FragColor = vec4(uPickColor, 1.0);
}

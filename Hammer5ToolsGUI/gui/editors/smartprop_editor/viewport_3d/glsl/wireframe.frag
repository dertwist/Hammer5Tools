#version 430 core
uniform vec3 uColor;
out vec4 FragColor;

void main() {
    FragColor = vec4(uColor, 1.0);
}

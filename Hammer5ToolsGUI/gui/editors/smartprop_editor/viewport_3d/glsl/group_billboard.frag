#version 430 core

in vec2 vTexCoord;

uniform sampler2D uIcon;
uniform bool uPicking;
uniform vec3 uPickColor;

out vec4 FragColor;

void main()
{
    vec4 icon = texture(uIcon, vTexCoord);
    if (icon.a < 0.1)
        discard;

    FragColor = uPicking ? vec4(uPickColor, 1.0) : icon;
}

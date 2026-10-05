#version 430 core

layout(location = 0) in vec2 aPosition;
layout(location = 1) in vec2 aTexCoord;

uniform mat4 uView;
uniform mat4 uProjection;
uniform vec3 uCenter;
uniform vec3 uCameraRight;
uniform vec3 uCameraUp;
uniform float uSize;

out vec2 vTexCoord;

void main()
{
    vec3 worldPosition = uCenter
        + uCameraRight * aPosition.x * uSize
        + uCameraUp * aPosition.y * uSize;
    gl_Position = uProjection * uView * vec4(worldPosition, 1.0);
    vTexCoord = aTexCoord;
}

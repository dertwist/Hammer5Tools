SPRITE_VERTEX_SHADER = """#version 330 core
layout(location=0) in vec3 aPosition;
layout(location=1) in vec4 aColor;
layout(location=2) in float aRadius;
out VS_OUT { vec4 color; float radius; } vs;
void main() { gl_Position = vec4(aPosition, 1.0); vs.color = aColor; vs.radius = aRadius; }
"""

SPRITE_GEOMETRY_SHADER = """#version 330 core
layout(points) in;
layout(triangle_strip, max_vertices=4) out;
in VS_OUT { vec4 color; float radius; } gsIn[];
out vec2 uv;
out vec4 particleColor;
uniform mat4 view;
uniform mat4 projection;
uniform vec3 cameraRight;
uniform vec3 cameraUp;
void corner(vec2 p) {
    vec3 world = gl_in[0].gl_Position.xyz
        + cameraRight * p.x * gsIn[0].radius
        + cameraUp * p.y * gsIn[0].radius;
    gl_Position = projection * view * vec4(world, 1.0);
    uv = p;
    particleColor = gsIn[0].color;
    EmitVertex();
}
void main() {
    corner(vec2(-1,-1)); corner(vec2(1,-1)); corner(vec2(-1,1)); corner(vec2(1,1));
    EndPrimitive();
}
"""

SPRITE_FRAGMENT_SHADER = """#version 330 core
in vec2 uv;
in vec4 particleColor;
out vec4 fragColor;
void main() {
    float distanceFromCenter = length(uv);
    if (distanceFromCenter > 1.0) discard;
    float edge = 1.0 - smoothstep(0.82, 1.0, distanceFromCenter);
    fragColor = vec4(particleColor.rgb, particleColor.a * edge);
}
"""

COLOR_VERTEX_SHADER = """#version 330 core
layout(location=0) in vec3 aPosition;
layout(location=1) in vec4 aColor;
out vec4 color;
uniform mat4 view;
uniform mat4 projection;
void main() { gl_Position = projection * view * vec4(aPosition, 1.0); color = aColor; }
"""

COLOR_FRAGMENT_SHADER = """#version 330 core
in vec4 color;
out vec4 fragColor;
void main() { fragColor = color; }
"""


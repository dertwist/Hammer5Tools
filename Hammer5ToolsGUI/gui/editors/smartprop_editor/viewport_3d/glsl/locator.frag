#version 430 core
in vec3 vNormal;
in vec3 vColor;
in vec3 vWorldPos;

uniform vec3 uCameraPos;
uniform float uAlpha;

out vec4 FragColor;

void main() {
    vec3 N = normalize(vNormal);
    if (!gl_FrontFacing) N = -N;

    // Multi-directional lighting for crisp 3D facet rendering matching Hammer 5
    vec3 lightDir1 = normalize(vec3(0.5, 0.8, 0.6));
    vec3 lightDir2 = normalize(vec3(-0.4, -0.6, -0.5));

    float diff1 = max(dot(N, lightDir1), 0.0);
    float diff2 = max(dot(N, lightDir2), 0.0) * 0.25;
    float ambient = 0.45;

    float lighting = clamp(ambient + diff1 * 0.55 + diff2, 0.0, 1.0);

    // Subtle specular highlight for metallic/faceted feel
    vec3 viewDir = normalize(uCameraPos - vWorldPos);
    vec3 halfDir = normalize(lightDir1 + viewDir);
    float spec = pow(max(dot(N, halfDir), 0.0), 16.0) * 0.15;

    vec3 finalColor = vColor * lighting + vec3(spec);
    FragColor = vec4(finalColor, uAlpha);
}

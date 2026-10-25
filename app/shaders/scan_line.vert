#version 440
// One segment of a scan pattern's line, drawn as a quad across it (edi ADR-0041). The segment's two points have x in
// item pixels and v, the intensity, in [0, 1]; each pattern's baseline, the height v = 1 rises to and its colour come
// from the uniforms by the pattern's place in its group, so a new offset, height or colour changes no vertex.

layout(location = 0) in vec4 segment;  // x0, v0, x1, v1
layout(location = 1) in vec3 corner;   // which end (0 or 1), which side (-1 or 1), the pattern's place in the group

layout(location = 0) out float across;  // distance from the line's centre, in pixels
layout(location = 1) out vec4 tint;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    vec4 placement[64];  // base, lift
    vec4 colour[64];     // premultiplied
    float qt_Opacity;
    float halfWidth;
};

void main() {
    int pattern = int(corner.z + 0.5);
    float base = placement[pattern].x;
    float lift = placement[pattern].y;
    vec2 a = vec2(segment.x, base - segment.y * lift);
    vec2 b = vec2(segment.z, base - segment.w * lift);
    vec2 d = b - a;
    float len = length(d);
    vec2 along = len > 0.0 ? d / len : vec2(1.0, 0.0);
    vec2 normal = vec2(-along.y, along.x);
    // One pixel past the edge, for the antialiased fringe.
    across = corner.y * (halfWidth + 1.0);
    tint = colour[pattern] * qt_Opacity;
    gl_Position = qt_Matrix * vec4(mix(a, b, corner.x) + normal * across, 0.0, 1.0);
}

#version 440
// One segment of a scan pattern's line, drawn as a quad around it (edi ADR-0041). The segment's two points have x in
// item pixels and v, the intensity, in [0, 1]; each pattern's baseline, the height v = 1 rises to and its colour come
// from the uniforms by the pattern's place in its group, so a new offset, height or colour changes no vertex. The
// fragment shader reads the pattern's other points from a texture, to give each pixel to the nearest segment only.

layout(location = 0) in vec4 segment;  // x0, v0, x1, v1
layout(location = 1) in vec4 walk;     // this segment's first point in the points texture, the pattern's first and
                                       // last points there, and its largest |v|, negative if x falls along it
layout(location = 2) in vec2 corner;   // end * 2 + (side > 0), the pattern's place in its group * 4

layout(location = 0) out vec2 position;  // in item pixels
layout(location = 1) flat out vec4 steps;  // as `walk`
layout(location = 2) flat out vec2 placing;  // the pattern's base and lift
layout(location = 3) out vec4 tint;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    vec4 placement[64];  // base, lift
    vec4 colour[64];     // premultiplied
    float qt_Opacity;
    float halfWidth;
    float pixel;  // one device pixel, in item pixels
};

void main() {
    int pattern = int((corner.y + 0.5) / 4.0);
    float base = placement[pattern].x;
    float lift = placement[pattern].y;
    vec2 a = vec2(segment.x, base - segment.y * lift);
    vec2 b = vec2(segment.z, base - segment.w * lift);
    vec2 d = b - a;
    float len = length(d);
    vec2 along = len > 0.0 ? d / len : vec2(1.0, 0.0);
    vec2 normal = vec2(-along.y, along.x);
    float end = corner.x >= 1.5 ? 1.0 : 0.0;
    float side = mod(corner.x + 0.5, 2.0) >= 1.0 ? 1.0 : -1.0;
    // Half the width and a device pixel of fringe beyond it, past both ends too for the round joins.
    float reach = halfWidth + pixel;
    position = mix(a, b, end) + along * (2.0 * end - 1.0) * reach + normal * side * reach;
    steps = walk;
    placing = vec2(base, lift);
    tint = colour[pattern] * qt_Opacity;
    gl_Position = qt_Matrix * vec4(position, 0.0, 1.0);
}

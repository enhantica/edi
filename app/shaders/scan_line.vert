#version 440
// One segment of a scan pattern's line, drawn as a quad around it (edi ADR-0041). The segment's two points have x in
// item pixels and v, the intensity, in [0, 1]; each pattern's baseline, the height v = 1 rises to and its colour come
// from the uniforms by the pattern's place in its group, so a new offset, height or colour changes no vertex. The points
// before and after the segment come too: the fragment shader gives a pixel to the nearest of the three segments only,
// so neighbours neither overlap nor leave a notch at their join.

layout(location = 0) in vec4 segment;  // x0, v0, x1, v1
layout(location = 1) in vec4 around;   // the point before (x, v) and the point after, each equal to its end if none
layout(location = 2) in vec2 corner;   // end * 2 + (side > 0), pattern * 4 + (a point before) + 2 * (a point after)

layout(location = 0) out vec2 position;  // in item pixels
layout(location = 1) out vec4 ends;      // the segment's two points, in item pixels
layout(location = 2) out vec4 neighbours;  // the points before and after, in item pixels
layout(location = 3) out vec2 present;   // whether there is a point before, and after
layout(location = 4) out vec4 tint;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    vec4 placement[64];  // base, lift
    vec4 colour[64];     // premultiplied
    float qt_Opacity;
    float halfWidth;
    float pixel;  // one device pixel, in item pixels
};

void main() {
    float code = corner.y + 0.5;
    int pattern = int(code / 4.0);
    float flags = floor(mod(code, 4.0));
    float base = placement[pattern].x;
    float lift = placement[pattern].y;
    vec2 a = vec2(segment.x, base - segment.y * lift);
    vec2 b = vec2(segment.z, base - segment.w * lift);
    vec2 before = vec2(around.x, base - around.y * lift);
    vec2 after = vec2(around.z, base - around.w * lift);
    vec2 d = b - a;
    float len = length(d);
    vec2 along = len > 0.0 ? d / len : vec2(1.0, 0.0);
    vec2 normal = vec2(-along.y, along.x);
    float end = corner.x >= 1.5 ? 1.0 : 0.0;
    float side = mod(corner.x + 0.5, 2.0) >= 1.0 ? 1.0 : -1.0;
    // Half the width and a device pixel of fringe beyond it, past both ends too for the round joins.
    float reach = halfWidth + pixel;
    position = mix(a, b, end) + along * (2.0 * end - 1.0) * reach + normal * side * reach;
    ends = vec4(a, b);
    neighbours = vec4(before, after);
    present = vec2(mod(flags, 2.0), floor(flags / 2.0));
    tint = colour[pattern] * qt_Opacity;
    gl_Position = qt_Matrix * vec4(position, 0.0, 1.0);
}

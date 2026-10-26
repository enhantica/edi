#version 440
// A scan pattern's line: full colour within half its width of the line and fading out over the next device pixel. A
// pixel nearer the segment before or after this one is theirs to draw (ties go to the earlier), so each pixel is drawn
// once along the line, with round joins and no doubled colour where segments meet.

layout(location = 0) in vec2 position;
layout(location = 1) in vec4 ends;
layout(location = 2) in vec4 neighbours;
layout(location = 3) in vec2 present;
layout(location = 4) in vec4 tint;

layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    vec4 placement[64];
    vec4 colour[64];
    float qt_Opacity;
    float halfWidth;
    float pixel;
};

float distanceTo(vec2 p, vec2 a, vec2 b) {
    vec2 d = b - a;
    float l = dot(d, d);
    float t = l > 0.0 ? clamp(dot(p - a, d) / l, 0.0, 1.0) : 0.0;
    return length(p - a - t * d);
}

void main() {
    float own = distanceTo(position, ends.xy, ends.zw);
    if (present.x > 0.5 && distanceTo(position, neighbours.xy, ends.xy) <= own) {
        discard;
    }
    if (present.y > 0.5 && distanceTo(position, ends.zw, neighbours.zw) < own) {
        discard;
    }
    float coverage = clamp((halfWidth - own) / pixel + 0.5, 0.0, 1.0);
    if (coverage <= 0.0) {
        discard;
    }
    fragColor = tint * coverage;
}

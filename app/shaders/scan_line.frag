#version 440
// A scan pattern's line: full colour within half its width of the line and fading out over the next device pixel. A
// pixel is drawn only by the pattern's segment nearest to it (ties go to the earlier), so each pixel of the line is
// drawn once, however many short segments meet near it at a sharp peak, with round joins and no hole.

layout(location = 0) in vec2 position;
layout(location = 1) flat in vec4 steps;
layout(location = 2) flat in vec2 placing;
layout(location = 3) in vec4 tint;

layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    vec4 placement[64];
    vec4 colour[64];
    float qt_Opacity;
    float halfWidth;
    float pixel;
};

// Each pattern's points in order, two texels to a point (its x, then its v as a share of the pattern's largest |v|),
// each a 24-bit number in the red, green and blue bytes; a break's point is all zero (app/src/scan_lines.cpp).
layout(binding = 1) uniform sampler2D points;

const int kRow = 2048;   // texels to a row of `points`
const int kSteps = 256;  // the most segments looked at on each side

float fixed24(int texel) {
    vec3 c = floor(texelFetch(points, ivec2(texel % kRow, texel / kRow), 0).rgb * 255.0 + 0.5);
    return c.r * 65536.0 + c.g * 256.0 + c.b;
}

// The point in item pixels, or x below -32767 for a break.
vec2 pointAt(int i) {
    float x = fixed24(2 * i) / 256.0 - 32768.0;
    float v = (fixed24(2 * i + 1) / 8388608.0 - 1.0) * abs(steps.w);
    return vec2(x, placing.x - v * placing.y);
}

bool isBreak(vec2 p) {
    return p.x < -32767.0;
}

float distanceTo(vec2 p, vec2 a, vec2 b) {
    vec2 d = b - a;
    float l = dot(d, d);
    float t = l > 0.0 ? clamp(dot(p - a, d) / l, 0.0, 1.0) : 0.0;
    return length(p - a - t * d);
}

void main() {
    int k = int(steps.x + 0.5);
    // This segment as the texture holds it, so every segment compared is read the same way and a tie has one winner.
    float own = distanceTo(position, pointAt(k), pointAt(k + 1));
    float coverage = clamp((halfWidth - own) / pixel + 0.5, 0.0, 1.0);
    if (coverage <= 0.0) {
        discard;
    }
    int first = int(steps.y + 0.5);
    int last = int(steps.z + 0.5);
    float rising = sign(steps.w);
    float here = rising * position.x;
    // The segments before this one, back until one lies farther along x than this pixel is from this segment: x runs
    // one way along a pattern, so every earlier one is farther still. A tie goes to the earlier segment.
    for (int j = k - 1, n = 0; j >= first && n < kSteps; --j, ++n) {
        vec2 a = pointAt(j);
        vec2 b = pointAt(j + 1);
        if (isBreak(a) || isBreak(b)) {
            continue;
        }
        if (here - max(rising * a.x, rising * b.x) > own) {
            break;
        }
        if (distanceTo(position, a, b) <= own) {
            discard;
        }
    }
    // The segments after it, forward in the same way; a later one takes the pixel only when it is nearer.
    for (int j = k + 1, n = 0; j < last && n < kSteps; ++j, ++n) {
        vec2 a = pointAt(j);
        vec2 b = pointAt(j + 1);
        if (isBreak(a) || isBreak(b)) {
            continue;
        }
        if (min(rising * a.x, rising * b.x) - here > own) {
            break;
        }
        if (distanceTo(position, a, b) < own) {
            discard;
        }
    }
    fragColor = tint * coverage;
}

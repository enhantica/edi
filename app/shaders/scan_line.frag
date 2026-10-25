#version 440
// A scan pattern's line, full colour within half its width of the centre and fading out over the next pixel.

layout(location = 0) in float across;
layout(location = 1) in vec4 tint;

layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    vec4 placement[64];
    vec4 colour[64];
    float qt_Opacity;
    float halfWidth;
};

void main() {
    fragColor = tint * clamp(halfWidth + 0.5 - abs(across), 0.0, 1.0);
}

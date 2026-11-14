"""CIEDE2000, Sharma, Wu and Dalal (2005), equations 2-22.

https://hajim.rochester.edu/ece/sites/gsharma/ciede2000/ciede2000noteCRNA.pdf
"""

import math


def delta(first, second):  # noqa: PLR0914 - the published equation's scalar intermediates
    l1, a1, b1 = first
    l2, a2, b2 = second
    mean = (math.hypot(a1, b1) + math.hypot(a2, b2)) / 2
    gain = 0.5 * (1 - math.sqrt(mean**7 / (mean**7 + 25**7)))
    a1, a2 = (1 + gain) * a1, (1 + gain) * a2
    c1, c2 = math.hypot(a1, b1), math.hypot(a2, b2)
    h1, h2 = math.degrees(math.atan2(b1, a1)) % 360, math.degrees(math.atan2(b2, a2)) % 360
    dh = 0 if c1 * c2 == 0 else (h2 - h1 + 180) % 360 - 180
    dl, dc = l2 - l1, c2 - c1
    dh = 2 * math.sqrt(c1 * c2) * math.sin(math.radians(dh / 2))
    light, chroma = (l1 + l2) / 2, (c1 + c2) / 2
    if c1 * c2 == 0:
        hue = h1 + h2
    elif abs(h1 - h2) <= 180:
        hue = (h1 + h2) / 2
    else:
        hue = (h1 + h2 + (360 if h1 + h2 < 360 else -360)) / 2

    def cos(degrees):
        return math.cos(math.radians(degrees))

    weight = (
        1
        - 0.17 * cos(hue - 30)
        + 0.24 * cos(2 * hue)
        + 0.32 * cos(3 * hue + 6)
        - 0.20 * cos(4 * hue - 63)
    )
    angle = 30 * math.exp(-(((hue - 275) / 25) ** 2))
    rotation = -2 * math.sqrt(chroma**7 / (chroma**7 + 25**7)) * math.sin(math.radians(2 * angle))
    dl /= 1 + 0.015 * (light - 50) ** 2 / math.sqrt(20 + (light - 50) ** 2)
    dc /= 1 + 0.045 * chroma
    dh /= 1 + 0.015 * chroma * weight
    return math.sqrt(dl * dl + dc * dc + dh * dh + rotation * dc * dh)


def srgb_lab(value):
    values = [int(value[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in values]
    xyz = [
        sum(a * b for a, b in zip(row, linear, strict=True)) / white
        for row, white in zip(
            [
                (0.4124564, 0.3575761, 0.1804375),
                (0.2126729, 0.7151522, 0.0721750),
                (0.0193339, 0.1191920, 0.9503041),
            ],
            (0.95047, 1, 1.08883),
            strict=True,
        )
    ]
    x, y, z = [
        v ** (1 / 3) if v > (6 / 29) ** 3 else v / (3 * (6 / 29) ** 2) + 4 / 29 for v in xyz
    ]
    return 116 * y - 16, 500 * (x - y), 200 * (y - z)

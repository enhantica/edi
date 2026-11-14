"""edi's colour maps for the concept figures: stops mixed in Oklab, as the app mixes its maps."""

import numpy as np
from matplotlib.colors import ListedColormap


def srgb2lin(c) -> np.ndarray:
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin2srgb(c) -> np.ndarray:
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.clip(c, 0, None) ** (1 / 2.4) - 0.055)


M1 = np.array([
    [0.4122214708, 0.5363325363, 0.0514459929],
    [0.2119034982, 0.6806995451, 0.1073969566],
    [0.0883024619, 0.2817188376, 0.6299787005],
])
M2 = np.array([
    [0.2104542553, 0.7936177850, -0.0040720468],
    [1.9779984951, -2.4285922050, 0.4505937099],
    [0.0259040371, 0.7827717662, -0.8086757660],
])


def to_ok(h) -> np.ndarray:
    c = np.array([int(h[i : i + 2], 16) / 255 for i in (1, 3, 5)])
    return M2 @ np.cbrt(M1 @ srgb2lin(c))


def from_ok(lab) -> np.ndarray:
    lms = np.linalg.solve(M2, lab) ** 3
    return np.clip(lin2srgb(np.linalg.solve(M1, lms)), 0, 1)


def cmap(stops, n=256) -> ListedColormap:
    pts = [to_ok(s) for s in stops]
    out = []
    for t in np.linspace(0, 1, n):
        x = t * (len(pts) - 1)
        i = min(int(x), len(pts) - 2)
        f = x - i
        out.append(from_ok(pts[i] * (1 - f) + pts[i + 1] * f))
    return ListedColormap(out)


# edi's measured blue (palette figure 0) to edi's calculated red (total_calculation), from a dark
# navy floor
EDI = cmap(['#101826', '#618EC8', '#E5533D'])

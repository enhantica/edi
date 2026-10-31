"""Independent stroke area coverage and comparisons on physical pixel grids."""

import math
import struct
import zlib
from operator import itemgetter
from pathlib import Path

import numpy as np


def _png_payload(path):
    data = Path(path).read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('A quality capture must be an actual PNG raster')
    position, compressed = 8, bytearray()
    while position < len(data):
        size = struct.unpack('>I', data[position : position + 4])[0]
        kind = data[position + 4 : position + 8]
        block = data[position + 8 : position + 8 + size]
        if kind == b'IHDR':
            width, height, depth, colour, _, _, interlace = struct.unpack('>IIBBBBB', block)
            if depth != 8 or colour not in {2, 6} or interlace:
                raise ValueError('The Qt quality PNG must have uninterlaced eight-bit RGB pixels')
            channels = 3 if colour == 2 else 4
        elif kind == b'IDAT':
            compressed.extend(block)
        position += size + 12
    return zlib.decompress(compressed), width, height, channels


def _predictor(mode, left, up, corner):
    if mode == 0:
        return 0
    if mode == 1:
        return left
    if mode == 2:
        return up
    if mode == 3:
        return (left + up) // 2
    if mode == 4:
        p = left + up - corner
        distances = [abs(p - left), abs(p - up), abs(p - corner)]
        return [left, up, corner][distances.index(min(distances))]
    raise ValueError('The Qt PNG uses an invalid scanline filter')


def read_png(path):
    raw, width, height, channels = _png_payload(path)
    stride = width * channels
    result = np.zeros((height, stride), dtype=np.uint8)
    for y in range(height):
        mode = raw[y * (stride + 1)]
        row = bytearray(raw[y * (stride + 1) + 1 : (y + 1) * (stride + 1)])
        for x in range(stride):
            left = row[x - channels] if x >= channels else 0
            up = int(result[y - 1, x]) if y else 0
            corner = int(result[y - 1, x - channels]) if y and x >= channels else 0
            row[x] = (row[x] + _predictor(mode, left, up, corner)) & 255
        result[y] = np.frombuffer(row, dtype=np.uint8)
    return result.reshape(height, width, channels)[..., :3]


def coverage(rgb, colour):
    ink = np.array([int(colour[i : i + 2], 16) for i in (1, 3, 5)], dtype=float)
    direction = 255 - ink
    return np.clip(((255 - rgb.astype(float)) @ direction) / (direction @ direction), 0, 1)


def physical_points(receipt):
    """Map the fixture's hand-written knots to its observed physical plot rectangle."""
    dpr = receipt['dpr']
    h, w = round(receipt['height'] * dpr), round(receipt['width'] * dpr)
    x0, x1 = receipt['x_range']
    y0, y1 = receipt['y_range']
    if dpr not in {1, 2} or w <= 0 or h <= 0 or x1 <= x0 or y1 <= y0:
        raise ValueError('The stroke reference requires a valid physical grid and plot ranges')
    points = np.asarray(receipt['points'], dtype=float)
    if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] != 2:
        raise ValueError('The independent stroke requires at least two planar points')
    if not np.isfinite(points).all() or np.any(np.all(np.diff(points, axis=0) == 0, axis=1)):
        raise ValueError('The independent stroke requires finite distinct consecutive points')
    return np.column_stack((
        (points[:, 0] - x0) / (x1 - x0) * w,
        (y1 - points[:, 1]) / (y1 - y0) * h,
    ))


def _stroke_cells(points, size, radius):
    cells = []
    for a, b in zip(points[:-1], points[1:], strict=True):
        delta = b - a
        axis = int(abs(delta[1]) > abs(delta[0]))
        sweep = np.arange(
            max(0, math.floor(min(a[axis], b[axis]) - radius)),
            min(size[axis], math.ceil(max(a[axis], b[axis]) + radius)),
        )
        centre = (
            a[1 - axis] + np.clip((sweep + 0.5 - a[axis]) / delta[axis], 0, 1) * delta[1 - axis]
        )
        for offset in range(
            -math.ceil(radius * math.sqrt(2) + 1), math.ceil(radius * math.sqrt(2) + 1) + 1
        ):
            across = np.floor(centre).astype(int) + offset
            xy = (sweep, across) if axis == 0 else (across, sweep)
            valid = (xy[0] >= 0) & (xy[0] < size[0]) & (xy[1] >= 0) & (xy[1] < size[1])
            cells.extend((xy[1][valid] * size[0] + xy[0][valid]).tolist())
    return np.unique(cells)


def _stroke_area(points, size, radius, samples):
    coordinates = np.divmod(_stroke_cells(points, size, radius), size[0])
    offsets = np.meshgrid(
        (np.arange(samples) + 0.5) / samples, (np.arange(samples) + 0.5) / samples
    )
    grid = (
        coordinates[1][:, None] + offsets[0].ravel(),
        coordinates[0][:, None] + offsets[1].ravel(),
    )
    inside = np.zeros(grid[0].shape, dtype=bool)
    for a, b in zip(points[:-1], points[1:], strict=True):
        delta = b - a
        projection = np.clip(
            ((grid[0] - a[0]) * delta[0] + (grid[1] - a[1]) * delta[1]) / np.dot(delta, delta),
            0,
            1,
        )
        inside |= (grid[0] - a[0] - projection * delta[0]) ** 2 + (
            grid[1] - a[1] - projection * delta[1]
        ) ** 2 <= radius * radius
    return coordinates, inside.mean(axis=1)


def stroke_reference(receipt, samples=16):
    """Box-filter a round stroke's geometric union, never blending its joins twice.

    Distance to a finite segment defines its round-ended stroke. Uniform midpoint
    integration measures the union inside each physical pixel square; it does not
    use Qt or either production renderer. Only the narrow segment corridors need
    integration. Closed-form area/flat-profile and convergence controls bound it.
    """
    points = physical_points(receipt)
    dpr = receipt['dpr']
    opacity, width = receipt['reference_opacity'], receipt['stroke_width']
    if not 0 < opacity <= 1 or not math.isfinite(width) or width <= 0 or samples < 2:
        raise ValueError('The independent stroke needs a positive width, opacity and sample grid')
    coordinates, area = _stroke_area(
        points,
        (round(receipt['width'] * dpr), round(receipt['height'] * dpr)),
        width * dpr / 2,
        samples,
    )
    canvas = np.zeros((round(384 * dpr), round(512 * dpr)))
    canvas[coordinates] = area * opacity
    colour = np.array([int(receipt['colour'][i : i + 2], 16) for i in (1, 3, 5)])
    return np.round(255 - (255 - colour) * canvas[..., None]).astype(np.uint8)


def smooth(values):
    for axis in (0, 1):
        pad = [(0, 0), (0, 0)]
        pad[axis] = (1, 1)
        padded = np.pad(values, pad)
        values = (
            np.take(padded, range(values.shape[axis]), axis=axis)
            + 2 * np.take(padded, range(1, values.shape[axis] + 1), axis=axis)
            + np.take(padded, range(2, values.shape[axis] + 2), axis=axis)
        ) / 4
    return values


def local_width_error(reference, candidate, vertex_x, dpr):
    errors = []
    for share in (0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875):
        x = round(share * reference.shape[1])
        if abs(x - vertex_x) <= 5 * dpr:
            continue
        expected = reference[:, x - 1 : x + 2].sum()
        if expected > 0:
            errors.append(abs(candidate[:, x - 1 : x + 2].sum() / expected - 1))
    return float(max(errors))


def metrics(reference, candidate, receipt):
    if reference.shape != candidate.shape:
        raise ValueError('Paired Pattern and Stacked rasters must have identical physical grids')
    dpr = receipt['dpr']
    if reference.shape[:2] != (round(384 * dpr), round(512 * dpr)):
        raise ValueError('The native quality capture must use the requested physical DPR')
    h, w = round(receipt['height'] * dpr), round(receipt['width'] * dpr)
    opacity = receipt['reference_opacity']
    if not 0 < opacity <= 1:
        raise ValueError('Raster comparison requires the independently declared positive opacity')
    ref = coverage(reference[:h, :w], receipt['colour']) / opacity
    got = coverage(candidate[:h, :w], receipt['colour']) / opacity
    # The independently declared viewport maps 0..255 inside -25.5..280.5.
    vertex = min(physical_points(receipt), key=itemgetter(1))
    yy, xx = np.ogrid[:h, :w]
    join = (xx - vertex[0]) ** 2 + (yy - vertex[1]) ** 2 <= (5 * dpr) ** 2
    nearby = np.maximum.reduce([
        np.roll(np.roll(got, dy, axis=0), dx, axis=1) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
    ])
    ink = ref > 0.04
    if not ink.any() or ref.sum() <= 0 or got.sum() <= 0:
        raise ValueError('Both paired production paths must contribute nonempty actual line ink')
    # A half-physical-pixel blur permits different antialiasing kernels, never a DPR rescale.
    blurred_ref, blurred_got = smooth(ref), smooth(got)
    return {
        'width_ratio': float(got.sum() / ref.sum()),
        'local_width_error': local_width_error(ref, got, vertex[0], dpr),
        'coverage_error': float(np.abs(blurred_got - blurred_ref).sum() / ref.sum()),
        'missing_core_pixels': int(np.count_nonzero((ref > 0.24) & (nearby < 0.04))),
        'missing_join_pixels': int(np.count_nonzero(join & (ref > 0.16) & (nearby < 0.04))),
        'join_excess_alpha': float(max(0, np.max(got[join]) - np.max(ref[join])) * opacity),
    }


def violations(result):
    return [
        name
        for name, valid in {
            'width': 0.85 <= result['width_ratio'] <= 1.15 and result['local_width_error'] <= 0.15,
            'antialiasing_or_device_pixel_reduction': result['coverage_error'] <= 0.12,
            'gaps': result['missing_core_pixels'] == 0,
            'vertex_notches': result['missing_join_pixels'] == 0,
            'double_alpha_join': result['join_excess_alpha'] <= 0.08,
        }.items()
        if not valid
    ]

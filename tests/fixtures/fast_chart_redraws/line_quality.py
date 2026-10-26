"""Compare paired Qt rasters without resampling their physical pixel grids."""

import struct
import zlib
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
    ref = coverage(reference[:h, :w], receipt['colour'])
    got = coverage(candidate[:h, :w], receipt['colour'])
    # The independently declared viewport maps 0..255 inside -25.5..280.5.
    peak_x = receipt['points'][1 if receipt['shape'] == 'peak' else 2][0]
    px = (peak_x - 10) / 70 * w
    py = (280.5 - 255) / 306 * h
    yy, xx = np.ogrid[:h, :w]
    join = (xx - px) ** 2 + (yy - py) ** 2 <= (5 * dpr) ** 2
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
        'local_width_error': local_width_error(ref, got, px, dpr),
        'coverage_error': float(np.abs(blurred_got - blurred_ref).sum() / ref.sum()),
        'missing_core_pixels': int(np.count_nonzero((ref > 0.24) & (nearby < 0.04))),
        'missing_join_pixels': int(np.count_nonzero(join & (ref > 0.16) & (nearby < 0.04))),
        'join_excess_alpha': float(max(0, np.max(got[join]) - np.max(ref[join]))),
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

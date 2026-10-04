"""Exercise the production Qt image comparator against independent SSIM boundaries."""

from __future__ import annotations

import os
import struct
import subprocess
import zlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def write_png(path, pixels, width=100, height=100):
    def chunk(kind, data):
        return (
            struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
        )

    raw = b''.join(b'\0' + pixels[i * width * 4 : (i + 1) * width * 4] for i in range(height))
    path.write_bytes(
        b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
        + chunk(b'IDAT', zlib.compress(raw))
        + chunk(b'IEND', b'')
    )


def comparator():
    override = os.environ.get('EDI_APP_UI_COMPARE')
    candidates = (
        [Path(override)]
        if override
        else [ROOT / 'build/app/app/edi_app_ui_compare', ROOT / 'build/app/edi_app_ui_compare']
    )
    binary = next((p for p in candidates if p.is_file()), None)
    assert binary is not None, (
        'gate 7: build the production edi_app_ui_compare executable before running acceptance'
    )
    return binary


@pytest.mark.parametrize(
    ('case', 'passes'),
    [
        ('identical', True),
        ('small-luminance-change', True),
        ('whole-image-threshold', False),
        ('tile-threshold', False),
        ('missing-expected', False),
        ('different-size', False),
    ],
)
def test_production_comparator_similarity_and_missing_escape(tmp_path, case, passes):
    # Accepted owner-amendment plan §5b: SSIM, min tile .90 and mean .98.
    # Constant fields have SSIM=(2*x*y+C1)/(x*x+y*y+C1), C1=(.01*255)^2.
    # 128->129 is >.999; 128->160 is .9756 (above tile, below mean).
    # A single black 32px tile in a 320px square is <.90 locally while
    # the other 99 tiles are identical: whole-image average remains >.98.
    actual, expected, diff = (tmp_path / name for name in ('actual', 'expected', 'diff'))
    for directory in (actual, expected, diff):
        directory.mkdir()
    width = 320
    normal = bytearray([128, 128, 128, 255] * width * width)
    modified = bytearray(normal)
    if case in {'small-luminance-change', 'whole-image-threshold'}:
        value = 129 if case == 'small-luminance-change' else 160
        modified = bytearray([value, value, value, 255] * width * width)
    elif case == 'tile-threshold':
        for y in range(32):
            for x in range(32):
                offset = (y * width + x) * 4
                modified[offset : offset + 3] = bytes(3)
    write_png(actual / '01-home.png', normal, width, width)
    if case != 'missing-expected':
        size = width - 1 if case == 'different-size' else width
        write_png(expected / '01-home.png', modified[: size * size * 4], size, size)
    run = subprocess.run(
        [
            str(comparator()),
            '--actual',
            str(actual),
            '--expected',
            str(expected),
            '--diff',
            str(diff),
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert (run.returncode == 0) == passes, (
        f'gate 7: SSIM comparator must honor the boundary ({case}): {run.stdout}{run.stderr}'
    )
    if not passes:
        assert '01-home' in run.stdout + run.stderr, (
            'gate 7: comparator failure names the affected demo state'
        )
        if case in {'whole-image-threshold', 'tile-threshold'}:
            assert list(diff.glob('*.png')), 'gate 7: SSIM refusal emits a similarity map'


def test_retired_calculation_identity_rows_and_adjacent_text_are_compared(tmp_path):
    actual, expected, diff = (tmp_path / name for name in ('actual', 'expected', 'diff'))
    for directory in (actual, expected, diff):
        directory.mkdir()
    width, height = 1280, 768
    normal = bytes([128, 128, 128, 255]) * width * height
    names = (
        '23-experiment-text.png',
        't2-05-report-text.png',
        't2-09-system-dark-report.png',
        't2-10-system-light-report.png',
    )
    for name in names:
        modified = bytearray(normal)
        top = 248 if name.startswith('23-') else 440
        for y in range(top, top + 32):
            for x in range(904, 936):
                modified[(y * width + x) * 4 : (y * width + x) * 4 + 3] = bytes(3)
        write_png(actual / name, modified, width, height)
        write_png(expected / name, normal, width, height)

    command = [
        str(comparator()),
        '--actual',
        str(actual),
        '--expected',
        str(expected),
        '--diff',
        str(diff),
    ]
    former_mask = subprocess.run(command, capture_output=True, text=True, timeout=15, check=False)
    all_named = all(name in former_mask.stdout for name in names)
    assert former_mask.returncode != 0 and all_named, (
        ' unit 0: retired calculation-identity rows must be compared '
        'in all four text views: ' + former_mask.stdout + former_mask.stderr
    )

    for name in names[1:]:
        (actual / name).unlink()
        (expected / name).unlink()
    # Keep the neighbouring-tile control; alter decoded pixels, not PNG bytes.
    outside = bytearray(normal)
    for y in range(248, 280):
        for x in range(832, 864):
            outside[(y * width + x) * 4 : (y * width + x) * 4 + 3] = bytes(3)
    write_png(actual / names[0], outside, width, height)
    unmasked = subprocess.run(command, capture_output=True, text=True, timeout=15, check=False)
    assert unmasked.returncode != 0 and names[0] in unmasked.stdout, (
        ' unit 0: an adjacent Experiment Text tile must still be compared: '
        + unmasked.stdout
        + unmasked.stderr
    )

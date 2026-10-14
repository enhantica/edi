"""Write independent PDF image/transform witnesses; no report writer is imported."""

import json
import zlib
from pathlib import Path

CASES = {
    'translated': ('200 0 0 100 72 600 cm /Im0 Do', [72, 142, 272, 242], [200, 100]),
    'nested': (
        '0.5 0 0 0.5 30 45 cm q 200 0 0 100 72 600 cm /Im0 Do Q',
        [66, 447, 166, 497],
        [100, 50],
    ),
    'rotated': ('0 150 -75 0 360 220 cm /Im0 Do', [285, 472, 360, 622], [150, 75]),
    'clipped': (
        '72 600 100 100 re W n 200 0 0 100 72 600 cm /Im0 Do',
        [72, 142, 272, 242],
        [200, 100],
    ),
}


def pdf(content):
    pixels = zlib.compress(bytes([171, 205, 239]) * 200 * 100)
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        (
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] '
            b'/Resources 5 0 R /Contents 6 0 R >>'
        ),
        b'<< /Type /XObject /Subtype /Image /Width 200 /Height 100 '
        b'/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode /Length '
        + str(len(pixels)).encode()
        + b' >>\nstream\n'
        + pixels
        + b'\nendstream',
        b'<< /XObject << /Im0 4 0 R >> >>',
        b'<< /Length ' + str(len(content)).encode() + b' >>\nstream\n' + content + b'\nendstream',
    ]
    output, offsets = bytearray(b'%PDF-1.4\n'), [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(str(index).encode() + b' 0 obj\n' + obj + b'\nendobj\n')
    xref = len(output)
    output.extend(b'xref\n0 7\n0000000000 65535 f \n')
    for offset in offsets[1:]:
        output.extend(f'{offset:010d} 00000 n \n'.encode())
    output.extend(
        b'trailer\n<< /Size 7 /Root 1 0 R >>\nstartxref\n' + str(xref).encode() + b'\n%%EOF\n'
    )
    return bytes(output)


def main():
    root = Path(__file__).parent
    expected = {}
    for name, (content, bounds, edges) in CASES.items():
        (root / (name + '.pdf')).write_bytes(pdf(('q ' + content + ' Q').encode()))
        expected[name] = {
            'bounds': bounds,
            'edges': edges,
            'pixels': [200, 100],
            'clip': [72, 142, 172, 242] if name == 'clipped' else [0, 0, 595, 842],
        }
    (root / 'reference.json').write_text(
        json.dumps(
            {
                'reference': 'Independent PDF unit-square image mapping and affine composition',
                'cases': expected,
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()

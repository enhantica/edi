"""Qualify the PDF image observer with independently authored image streams."""

import hashlib
import runpy
import zlib
from pathlib import Path


def test_pdf_image_identity_reaches_bytes_dimensions_and_alpha(tmp_path):
    inspect = runpy.run_path(str(Path(__file__).resolve().parents[2] / 'unit/app/ReportPdf.py'))[
        'inspect'
    ]

    def observed(colour, alpha, width):
        content = b'/Im0 Do'
        picture = zlib.compress(colour)
        mask = zlib.compress(alpha)
        document = b'%PDF-1.4\n'
        for number, body in enumerate(
            [
                b'<< /Type /Page /MediaBox [0 0 595 842] /Resources 2 0 R /Contents 3 0 R >>',
                b'<< /XObject << /Im0 4 0 R >> >>',
                b'<< >>\nstream\n' + content + b'\nendstream',
                (
                    b'<< /Subtype /Image /Width %d /Height 1 /Filter /FlateDecode '
                    b'/SMask 5 0 R >>\nstream\n' % width
                )
                + picture
                + b'\nendstream',
                b'<< /Filter /FlateDecode >>\nstream\n' + mask + b'\nendstream',
            ],
            start=1,
        ):
            document += str(number).encode() + b' 0 obj\n' + body + b'\nendobj\n'
        path = tmp_path / 'independent.pdf'
        path.write_bytes(document)
        return inspect(path)['pages'][0]['image_draws'][0]

    initial = observed(b'\x12\x34\x56', b'\xff', 1)
    assert initial['sha256'] == hashlib.sha256(b'\x12\x34\x56\xff').hexdigest(), (
        'The observer fingerprints the independent decoded image and alpha bytes'
    )
    assert observed(b'\x12\x34\x57', b'\xff', 1)['sha256'] != initial['sha256'], (
        'A stale image with the same size must differ by its actual content'
    )
    assert observed(b'\x12\x34\x56', b'\x80', 1)['sha256'] != initial['sha256'], (
        'Different transparency must not masquerade as the same PDF figure'
    )
    assert observed(b'\x12\x34\x56', b'\xff', 2)['pixels'] != initial['pixels'], (
        'The identity comparison also reaches independently declared image dimensions'
    )

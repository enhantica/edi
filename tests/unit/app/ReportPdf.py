"""Read Qt's PDF objects, fonts and text operators using only the Python standard library.

This observer is qualified against a separate Qt-written multipage witness. It refuses
unsupported text/font structures instead of silently accepting an unextractable report.
"""

import hashlib
import json
import math
import os
import re
import sys
import zlib
from operator import itemgetter
from pathlib import Path


def inspect(path):  # noqa: PLR0912, PLR0914, PLR0915 - explicit PDF grammar boundaries
    data = Path(path).read_bytes()
    if not data.startswith(b'%PDF-'):
        raise ValueError('PDF output must have the actual PDF header')
    objects = {
        int(m[1]): m[2] for m in re.finditer(rb'(\d+)\s+0\s+obj\b(.*?)endobj', data, re.DOTALL)
    }

    def stream(number):
        obj = objects[number]
        match = re.search(rb'stream\r?\n(.*?)\r?\nendstream', obj, re.DOTALL)
        if not match:
            return b''
        content = match[1]
        return zlib.decompress(content) if b'/FlateDecode' in obj[: match.start()] else content

    def glyph_map(font):
        reference = re.search(rb'/ToUnicode\s+(\d+)\s+0\s+R', objects[font])
        if not reference:
            raise ValueError('PDF text font must expose an extractable ToUnicode map')
        cmap = stream(int(reference[1]))
        result = {}
        for block in re.findall(rb'beginbfchar(.*?)endbfchar', cmap, re.DOTALL):
            for src, dst in re.findall(rb'<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>', block):
                result[int(src, 16)] = bytes.fromhex(dst.decode()).decode('utf-16-be')
        for block in re.findall(rb'beginbfrange(.*?)endbfrange', cmap, re.DOTALL):
            for lo, hi, dst in re.findall(
                rb'<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>', block
            ):
                for code in range(int(lo, 16), int(hi, 16) + 1):
                    result[code] = chr(int(dst, 16) + code - int(lo, 16))
            for lo, hi, values in re.findall(
                rb'<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>\s*\[(.*?)\]', block, re.DOTALL
            ):
                for code, dst in zip(
                    range(int(lo, 16), int(hi, 16) + 1),
                    re.findall(rb'<([0-9a-fA-F]+)>', values),
                    strict=True,
                ):
                    result[code] = bytes.fromhex(dst.decode()).decode('utf-16-be')
        if not result:
            raise ValueError('PDF font map must contain actual glyph mappings')
        return result

    def multiply(a, b):
        return (
            a[0] * b[0] + a[2] * b[1],
            a[1] * b[0] + a[3] * b[1],
            a[0] * b[2] + a[2] * b[3],
            a[1] * b[2] + a[3] * b[3],
            a[0] * b[4] + a[2] * b[5] + a[4],
            a[1] * b[4] + a[3] * b[5] + a[5],
        )

    pages = []
    colours = set()
    for obj in objects.values():  # noqa: PLR1702 - nested page/font/text grammar
        if not re.search(rb'/Type\s*/Page\b', obj):
            continue
        box = re.search(rb'/MediaBox\s*\[([^]]+)\]', obj)
        if not box:
            raise ValueError('Every PDF page must expose its MediaBox')
        resources = re.search(rb'/Resources\s+(\d+)\s+0\s+R', obj)
        resource = objects[int(resources[1])] if resources else obj
        fonts = {
            name.decode(): glyph_map(int(font))
            for name, font in re.findall(rb'/((?:F|f)\w*)\s+(\d+)\s+0\s+R', resource)
        }
        images = {}
        for name, reference in re.findall(rb'/(\w+)\s+(\d+)\s+0\s+R', resource):
            image = objects[int(reference)]
            if re.search(rb'/Subtype\s*/Image\b', image):
                width = re.search(rb'/Width\s+(\d+)', image)
                height = re.search(rb'/Height\s+(\d+)', image)
                if not width or not height:
                    raise ValueError('Every drawn PDF image must declare its pixel dimensions')
                mask = re.search(rb'/SMask\s+(\d+)\s+0\s+R', image)
                pixels = stream(int(reference))
                if mask:
                    pixels += stream(int(mask[1]))
                images[name.decode()] = {
                    'pixels': (int(width[1]), int(height[1])),
                    'sha256': hashlib.sha256(pixels).hexdigest(),
                }
        contents = re.search(rb'/Contents\s+(\d+)\s+0\s+R', obj)
        if not contents:
            raise ValueError('Every PDF page must expose an actual content stream')
        content = stream(int(contents[1])).decode('latin1')
        number_pattern = r'([-+]?\d+(?:\.\d+)?)'
        for rgb in re.findall(
            number_pattern
            + r'\s+'
            + number_pattern
            + r'\s+'
            + number_pattern
            + r'\s+(?:rg|scn)\b',
            content,
        ):
            channels = [round(float(value) * 255) for value in rgb]
            if all(0 <= value <= 255 for value in channels):
                colours.add('#' + ''.join(f'{value:02x}' for value in channels))
        token = re.compile(r'<[0-9a-fA-F\s]*>|/\w+|[-+]?\d+(?:\.\d+)?|\b[A-Za-z]+\b|[\[\]]')
        operands, stack, fragments, image_draws = [], [], [], []
        ctm = (1, 0, 0, 1, 0, 0)
        page_box = list(map(float, box[1].split()))
        clip = page_box.copy()
        rectangle = None
        path_points = []
        tm = ctm
        font, size = None, 0
        array = False
        for word in token.findall(content):
            if word == '[':
                array = True
            elif word == ']':
                array = False
            elif word.startswith(('/', '<')) or re.fullmatch(r'[-+]?\d+(?:\.\d+)?', word):
                operands.append(word)
            elif array:
                raise ValueError('Unsupported token inside a PDF text array')
            else:
                if word == 'q':
                    stack.append((ctm, font, size, clip.copy()))
                elif word == 'Q':
                    ctm, font, size, clip = stack.pop()
                elif word == 'cm':
                    ctm = multiply(ctm, tuple(map(float, operands[-6:])))
                elif word in {'m', 'l'}:
                    if word == 'm':
                        path_points = []
                        rectangle = None
                    point = multiply(ctm, (1, 0, 0, 1, *map(float, operands[-2:])))[4:]
                    path_points.append(point)
                elif word == 'h':
                    xs = {point[0] for point in path_points}
                    ys = {point[1] for point in path_points}
                    if len(xs) == len(ys) == 2 and set(path_points) == {
                        (x, y) for x in xs for y in ys
                    }:
                        rectangle = [min(xs), min(ys), max(xs), max(ys)]
                elif word == 're':
                    x, y, width, height = map(float, operands[-4:])
                    corners = [
                        multiply(ctm, (1, 0, 0, 1, px, py))[4:]
                        for px, py in (
                            (x, y),
                            (x + width, y),
                            (x, y + height),
                            (x + width, y + height),
                        )
                    ]
                    rectangle = [
                        min(p[0] for p in corners),
                        min(p[1] for p in corners),
                        max(p[0] for p in corners),
                        max(p[1] for p in corners),
                    ]
                elif word == 'W':
                    if rectangle is None:
                        raise ValueError('The PDF image observer requires rectangular clip paths')
                    clip = [
                        max(clip[0], rectangle[0]),
                        max(clip[1], rectangle[1]),
                        min(clip[2], rectangle[2]),
                        min(clip[3], rectangle[3]),
                    ]
                elif word == 'Do':
                    name = operands[-1][1:]
                    if name not in images:
                        raise ValueError('Every PDF figure must resolve an actual image XObject')
                    corners = [
                        multiply(ctm, (1, 0, 0, 1, x, y))[4:]
                        for x, y in ((0, 0), (1, 0), (0, 1), (1, 1))
                    ]
                    bounds = [
                        min(p[0] for p in corners),
                        min(p[1] for p in corners),
                        max(p[0] for p in corners),
                        max(p[1] for p in corners),
                    ]
                    image_draws.append({
                        'name': name,
                        'pixels': list(images[name]['pixels']),
                        'sha256': images[name]['sha256'],
                        'bounds': [
                            bounds[0],
                            page_box[3] - bounds[3],
                            bounds[2],
                            page_box[3] - bounds[1],
                        ],
                        'clip': [clip[0], page_box[3] - clip[3], clip[2], page_box[3] - clip[1]],
                        'edge_width': math.hypot(ctm[0], ctm[1]),
                        'edge_height': math.hypot(ctm[2], ctm[3]),
                    })
                elif word == 'Tm':
                    tm = tuple(map(float, operands[-6:]))
                elif word == 'Td':
                    tm = multiply(tm, (1, 0, 0, 1, *map(float, operands[-2:])))
                elif word == 'BT':
                    tm = (1, 0, 0, 1, 0, 0)
                elif word == 'Tf':
                    font, size = operands[-2][1:], float(operands[-1])
                elif word in {'Tj', 'TJ'}:
                    if font not in fonts:
                        raise ValueError('PDF text must use a mapped page font')
                    text = ''
                    for operand in operands:
                        if not operand.startswith('<'):
                            continue
                        encoded = re.sub(r'\s+', '', operand[1:-1])
                        if len(encoded) % 4:
                            raise ValueError(
                                'Qt PDF glyph strings must have complete two-byte codes'
                            )
                        for at in range(0, len(encoded), 4):
                            code = int(encoded[at : at + 4], 16)
                            if code not in fonts[font]:
                                raise ValueError(
                                    'Every visible PDF glyph must be extractable as Unicode'
                                )
                            text += fonts[font][code]
                    transform = multiply(ctm, tm)
                    fragments.append({
                        'text': text,
                        'x': transform[4],
                        'y': float(box[1].split()[3]) - transform[5],
                        'size': size * math.hypot(transform[0], transform[1]),
                    })
                operands = []
        lines = {}
        for f in fragments:
            lines.setdefault(round(f['y'], 3), []).append(f)
        line_facts = [
            {
                'text': ' '.join(
                    ''.join(f['text'] for f in sorted(line, key=itemgetter('x'))).split()
                ),
                'x': min(f['x'] for f in line),
                'y': line[0]['y'],
                'size': line[0]['size'],
            }
            for line in lines.values()
        ]
        pages.append({
            'image_draws': image_draws,
            'lines': line_facts,
            'box': list(map(float, box[1].split())),
            'fragments': fragments,
            'text': '\n'.join(line['text'] for line in line_facts),
        })
    if not pages:
        raise ValueError('PDF output must contain a page')
    return {
        'colours': sorted(colours),
        'pages': pages,
        'text': '\n'.join(p['text'] for p in pages),
        'images': sum(bool(re.search(rb'/Subtype\s*/Image\b', obj)) for obj in objects.values()),
    }


def main():
    result = inspect(sys.argv[1])
    if os.environ.get('EDI_PDF_PROOF_DIR'):
        directory = Path(os.environ['EDI_PDF_PROOF_DIR'])
        directory.mkdir(parents=True, exist_ok=True)
        document = Path(sys.argv[1]).read_bytes()
        name = hashlib.sha256(document).hexdigest()
        (directory / (name + '.pdf')).write_bytes(document)
        (directory / (name + '.json')).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, IndexError, zlib.error) as error:
        print(json.dumps({'error': str(error)}))
        sys.exit(1)

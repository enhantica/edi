# SPDX-License-Identifier: BSD-3-Clause
"""Fully decode fresh captures with libpng's public simplified-read interface."""

import argparse
import ctypes
import ctypes.util
import json
import os
import sys
from pathlib import Path


# png.h: PNG_IMAGE_VERSION=1, PNG_FORMAT_RGBA=3 and the public png_image layout.
class PngImage(ctypes.Structure):
    _fields_ = [
        ('opaque', ctypes.c_void_p),
        *[
            (name, ctypes.c_uint32)
            for name in (
                'version',
                'width',
                'height',
                'format',
                'flags',
                'colormap_entries',
                'warning_or_error',
            )
        ],
        ('message', ctypes.c_char * 64),
    ]


def library():
    root = Path(__file__).resolve().parents[3] / '.pixi/envs/app'
    candidates = [
        os.environ.get('EDI_DOCS_PNG_LIBRARY'),
        str(root / 'lib/libpng16.so.16'),
        str(root / 'lib/libpng16.dylib'),
        str(root / 'Library/bin/libpng16.dll'),
        str(root / 'bin/libpng16.dll'),
        ctypes.util.find_library('png16'),
    ]
    decoder = None
    for candidate in filter(None, candidates):
        try:
            decoder = ctypes.CDLL(candidate)
            break
        except OSError:
            continue
    if decoder is None:
        raise RuntimeError('Provision the public libpng decoder before capture qualification')
    image_pointer = ctypes.POINTER(PngImage)
    decoder.png_image_begin_read_from_file.argtypes = [image_pointer, ctypes.c_char_p]
    decoder.png_image_begin_read_from_file.restype = ctypes.c_int
    decoder.png_image_finish_read.argtypes = [
        image_pointer,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_int32,
        ctypes.c_void_p,
    ]
    decoder.png_image_finish_read.restype = ctypes.c_int
    decoder.png_image_free.argtypes = [image_pointer]
    decoder.png_image_free.restype = None
    return decoder


def decode(decoder, path):
    image = PngImage()
    image.version = 1
    loaded = False
    try:
        if decoder.png_image_begin_read_from_file(ctypes.byref(image), os.fsencode(path)):
            image.format = 3
            size = image.width * image.height * 4
            # Fixture resource bound, well above the declared app-capture viewport.
            if 0 < size <= 256 * 1024 * 1024:
                pixels = ctypes.create_string_buffer(size)
                loaded = bool(
                    decoder.png_image_finish_read(ctypes.byref(image), None, pixels, 0, None)
                )
        return {
            'loaded': loaded,
            'width': image.width,
            'height': image.height,
            'message': bytes(image.message).decode('utf-8', errors='replace'),
        }
    finally:
        decoder.png_image_free(ctypes.byref(image))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    paths = [
        Path(path).resolve(strict=True)
        for path in json.loads(args.inputs.read_text(encoding='utf-8'))
    ]
    decoder = library() if any(path.suffix != '.webp' for path in paths) else None
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from tests.fixtures.tutorial_cases.screenshots import webp_info  # noqa: PLC0415

    rows = [webp_info(path) if path.suffix == '.webp' else decode(decoder, path) for path in paths]
    args.output.write_text(json.dumps(rows), encoding='utf-8')


if __name__ == '__main__':
    main()

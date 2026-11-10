"""Freeze independent Unicode cmaps from the fonts, using FreeType (no app checker).

Reference: https://freetype.org/freetype2/docs/reference/ft2-character_mapping.html
FT_Get_First_Char/FT_Get_Next_Char enumerate only nonzero glyph mappings.
Run after app configuration fetched the hash-verified gui-components archive.
"""

import argparse
import ctypes as ct
import ctypes.util
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'build/app/_deps/gui_components-src/src/EasyApplication/Gui/Resources/Fonts'
FACES = {
    'PT Sans': [('base', 'PT_Sans/PTSans-Regular.ttf'), ('base', 'PT_Sans/PTSans-Bold.ttf')],
    'PT Mono': [('base', 'PT_Mono/PTMono-Regular.ttf')],
    'Noto Sans': [('owned', 'Noto_Sans/NotoSans-Regular.ttf')],
    'Noto Sans Light': [('owned', 'Noto_Sans/NotoSans-Light.ttf')],
    'Noto Sans Mono': [('owned', 'Noto_Sans_Mono/NotoSansMono-Regular.ttf')],
    'Font Awesome': [('base', 'FontAwesome/Font Awesome 5 Free-Solid-900.otf')],
    'Baloo 2': [('owned', 'Baloo_2/Baloo2-Regular.ttf'), ('owned', 'Baloo_2/Baloo2-SemiBold.ttf')],
    'Encode Sans': [('base', 'Encode_Sans/EncodeSans-Regular.ttf')],
}


def face_weight(data):
    # The OpenType OS/2 table stores usWeightClass at byte offset 4.
    for index in range(int.from_bytes(data[4:6], 'big')):
        record = data[12 + index * 16 : 28 + index * 16]
        if record[:4] == b'OS/2':
            offset = int.from_bytes(record[8:12], 'big')
            return int.from_bytes(data[offset + 4 : offset + 6], 'big')
    raise RuntimeError('Bundled face has no OS/2 weight class')


def read_face(ft, library, path, origin, filename):
    face = ct.c_void_p()
    if ft.FT_New_Face(library, str(path).encode(), 0, ct.byref(face)):
        raise RuntimeError(f'Cannot read bundled face {path}')
    try:
        if ft.FT_Select_Charmap(face, int.from_bytes(b'unic', 'big')):
            raise RuntimeError(f'No Unicode cmap in {path}')
        glyph = ct.c_uint()
        code = ft.FT_Get_First_Char(face, ct.byref(glyph))
        ranges = []
        while glyph.value:
            if ranges and ranges[-1][1] + 1 == code:
                ranges[-1][1] = code
            else:
                ranges.append([code, code])
            code = ft.FT_Get_Next_Char(face, code, ct.byref(glyph))
        return {
            'origin': origin,
            'path': filename,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'weight': face_weight(path.read_bytes()),
            'ranges': ranges,
        }
    finally:
        ft.FT_Done_Face(face)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-fonts', type=Path, default=BASE)
    args = parser.parse_args()
    ft = ct.CDLL(ctypes.util.find_library('freetype'))
    ft.FT_Init_FreeType.argtypes = [ct.POINTER(ct.c_void_p)]
    ft.FT_New_Face.argtypes = [ct.c_void_p, ct.c_char_p, ct.c_long, ct.POINTER(ct.c_void_p)]
    ft.FT_Select_Charmap.argtypes = [ct.c_void_p, ct.c_uint]
    ft.FT_Get_First_Char.argtypes = [ct.c_void_p, ct.POINTER(ct.c_uint)]
    ft.FT_Get_First_Char.restype = ct.c_ulong
    ft.FT_Get_Next_Char.argtypes = [ct.c_void_p, ct.c_ulong, ct.POINTER(ct.c_uint)]
    ft.FT_Get_Next_Char.restype = ct.c_ulong
    ft.FT_Done_Face.argtypes = [ct.c_void_p]
    ft.FT_Done_FreeType.argtypes = [ct.c_void_p]
    library = ct.c_void_p()
    if ft.FT_Init_FreeType(ct.byref(library)):
        raise RuntimeError('FreeType initialization failed')
    rows = {}
    try:
        for family, faces in FACES.items():
            rows[family] = []
            for origin, filename in faces:
                path = (
                    args.base_fonts if origin == 'base' else ROOT / 'app/resources/fonts'
                ) / filename
                rows[family].append(read_face(ft, library, path, origin, filename))
    finally:
        ft.FT_Done_FreeType(library)
    cmake = (ROOT / 'cmake/EdiGuiBase.cmake').read_text()
    pin = re.search(r'set\(EDI_GUI_COMPONENTS_ARCHIVE_SHA256 (\w+)\)', cmake).group(1)
    target = Path(__file__).with_name('cmaps.json')
    target.write_text(json.dumps({'archive_sha256': pin, 'fonts': rows}, indent=2) + '\n')


if __name__ == '__main__':
    main()

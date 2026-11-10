"""WebP witnesses use libwebp's public decode/encode headers, independently of the site writer."""

import ctypes
import ctypes.util
import json
from functools import cache, lru_cache
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

PNG = b'\x89PNG\r\n\x1a\n'


@cache
def webp_library():
    app = Path(__file__).resolve().parents[3] / '.pixi/envs/app'
    candidates = [
        ctypes.util.find_library('webp'),
        str(app / 'lib/libwebp.so.7'),
        str(app / 'lib/libwebp.dylib'),
        str(app / 'Library/bin/libwebp.dll'),
    ]
    for name in filter(None, candidates):
        try:
            library = ctypes.CDLL(name)
            break
        except OSError:
            continue
    else:
        raise RuntimeError('Provision the public libwebp decoder for screenshot checks')
    library.WebPGetInfo.argtypes = [
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    library.WebPGetInfo.restype = ctypes.c_int
    library.WebPDecodeRGBAInto.argtypes = [
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_int,
    ]
    library.WebPDecodeRGBAInto.restype = ctypes.c_void_p
    return library


def webp_info(path):
    return dict(_webp_pixels(path.read_bytes()))


@lru_cache(maxsize=128)
def _webp_pixels(content):
    result = {'loaded': False, 'width': 0, 'height': 0, 'message': 'Invalid WebP pixels'}
    if content[:4] != b'RIFF' or content[8:12] != b'WEBP':
        return result
    library = webp_library()
    width, height = ctypes.c_int(), ctypes.c_int()
    if not library.WebPGetInfo(content, len(content), ctypes.byref(width), ctypes.byref(height)):
        return result
    result.update(width=width.value, height=height.value)
    size = width.value * height.value * 4
    if 0 < size <= 256 * 1024 * 1024:
        pixels = ctypes.create_string_buffer(size)
        result['loaded'] = bool(
            library.WebPDecodeRGBAInto(content, len(content), pixels, size, width.value * 4)
        )
    if result['loaded']:
        result['message'] = ''
    return result


def control_webp():
    """An authored transparent format control; not an app image or scientific reference."""
    library = webp_library()
    library.WebPEncodeRGBA.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_float,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    library.WebPEncodeRGBA.restype = ctypes.c_size_t
    library.WebPFree.argtypes = [ctypes.c_void_p]
    library.WebPFree.restype = None
    output = ctypes.c_void_p()
    pixels = bytes([35, 70, 120, 255, 120, 70, 35, 80] * 6)
    size = library.WebPEncodeRGBA(pixels, 4, 3, 16, 85, ctypes.byref(output))
    assert size and output, 'The independent libwebp encoder must produce the format control'
    try:
        return ctypes.string_at(output, size)
    finally:
        library.WebPFree(output)


def tutorial_folders(docs):
    gui = docs / 'assets/gui'
    folders = {gui / 'cases', gui / 'assistant'}
    for manifest in gui.rglob('manifest.json'):
        if json.loads(manifest.read_text()).get('workflow') == 'tutorial':
            folders.add(manifest.parent)
    return sorted(folders)


def assert_no_tutorial_png(docs):
    wrong = set()
    for folder in tutorial_folders(docs):
        for path in folder.rglob('*'):
            if path.is_file():
                with path.open('rb') as stream:
                    is_png = stream.read(8) == PNG
                if path.suffix.casefold() == '.png' or is_png:
                    wrong.add(path.relative_to(docs).as_posix())
    assert not wrong, 'Gate 4: tutorial screenshot folders contain no PNG files: ' + repr(
        sorted(wrong)[:12]
    )


def assert_webp_asset(address, page, root):
    parsed = urlparse(urljoin(page.as_uri(), address))
    assert parsed.scheme == 'file' and not parsed.netloc, (
        'Gate 4: tutorial images resolve to local published WebP files'
    )
    path = Path(unquote(parsed.path))
    assert path.resolve().is_relative_to(root.resolve()) and path.is_file(), (
        'Gate 4: every tutorial image resolves inside the actual publication: ' + address
    )
    assert path.suffix == '.webp' and webp_info(path)['loaded'], (
        'Gate 4: tutorial images are fully decodable .webp files: ' + address
    )
    return path


def assert_page_webp(page, root):
    from bs4 import BeautifulSoup  # noqa: PLC0415 - decoder subprocess needs only the stdlib

    soup = BeautifulSoup(page.read_text(), 'html.parser')
    main = soup.select_one('main') or soup
    for node in main.select('img, svg image, picture source, a.gui-image-link'):
        addresses = [node[attr] for attr in ['src', 'href', 'xlink:href'] if node.get(attr)]
        if node.get('srcset'):
            addresses += [item.strip().split()[0] for item in node['srcset'].split(',')]
        assert addresses or (node.name == 'img' and node.find_parent('picture')), (
            'Gate 4: every declared tutorial image has a resolvable source'
        )
        for address in addresses:
            path = assert_webp_asset(address, page, root)
            if node.get('data-gui-dark'):
                assert_webp_asset((path.parent / 'dark' / path.name).as_uri(), page, root)

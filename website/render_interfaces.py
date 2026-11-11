#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Render shared interface previews and release download controls."""

from __future__ import annotations

import hashlib
import html
import json
import re
import struct
from importlib.metadata import distribution
from pathlib import Path

import yaml
from defusedxml import ElementTree

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / 'surfaces/docs'


def screenshot_radius(width: int) -> float:
    match = re.search(
        r'--ed-screenshot-radius:\s*(\d+(?:\.\d+)?)%;',
        (DOCS / 'assets/site-components.css').read_text(),
    )
    if not match:
        raise ValueError('Screenshot radius must be a percentage of image width')
    return width * float(match[1]) / 100


def webp_size(data: bytes, filename: str) -> tuple[int, int]:
    """A WebP image's width and height from its first chunk: lossy, lossless or extended."""
    chunk = data[12:16]
    if chunk == b'VP8X':
        return 1 + int.from_bytes(data[24:27], 'little'), 1 + int.from_bytes(data[27:30], 'little')
    if chunk == b'VP8 ':
        width = int.from_bytes(data[26:28], 'little') & 0x3FFF
        return width, int.from_bytes(data[28:30], 'little') & 0x3FFF
    if chunk == b'VP8L':
        bits = int.from_bytes(data[21:25], 'little')
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    raise ValueError(f'Unreadable WebP preview: {filename}')


def preview(filename: str, description: str, crop_top: int = 0) -> str:
    source = DOCS / 'assets' / filename
    data = source.read_bytes()
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        width, height = struct.unpack('!II', data[16:24])
    elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        width, height = webp_size(data, filename)
    elif source.suffix == '.svg':
        root = ElementTree.fromstring(data)
        if root.tag != '{http://www.w3.org/2000/svg}svg':
            raise ValueError(f'Invalid generated SVG: {filename}')
        width, height = int(root.attrib['width']), int(root.attrib['height'])
    else:
        raise ValueError(f'Preview must be PNG, WebP or generated SVG: {filename}')
    if width <= 0 or height <= 0:
        raise ValueError(f'Invalid preview size: {filename}')
    if not 0 <= crop_top < height:
        raise ValueError(f'Invalid preview crop: {filename}')
    shown_height = height - crop_top
    image = html.escape('../assets/' + filename + '?v=' + hashlib.sha256(data).hexdigest()[:12])
    # An app capture's dark twin sits in dark/ beside it; the page script swaps to it in dark.
    twin = source.parent / 'dark' / source.name
    dark = (
        f' data-gui-dark="{hashlib.sha256(twin.read_bytes()).hexdigest()[:12]}"'
        if twin.is_file()
        else ''
    )
    title = html.escape(description, quote=True)
    clip = 'interface-' + source.stem
    frame = (
        f'y="{crop_top}" width="{width}" height="{shown_height}" rx="{screenshot_radius(width):g}"'
    )
    return (
        '<figure class="ed-interface-preview" data-interface-hero>\n'
        f'<a class="gui-image-link" href="{image}"{dark} data-gui-open aria-haspopup="dialog" '
        f'aria-label="Enlarge screenshot: {title}">'
        f'<svg class="gui-capture" viewBox="0 {crop_top} {width} {shown_height}" '
        f'width="{width}" height="{shown_height}" role="img" aria-label="{title}">'
        f'<title>{title}</title><defs><clipPath id="{clip}"><rect {frame} /></clipPath></defs>'
        f'<image href="{image}"{dark} width="{width}" height="{height}" '
        f'clip-path="url(#{clip})" />'
        f'<rect class="gui-image-frame" {frame} />'
        '</svg></a>\n</figure>'
    )


def replace_marker(source: Path, kind: str, key: str, content: str) -> None:
    start, end = f'<!-- {kind}:{key} -->', f'<!-- /{kind} -->'
    text, count = re.subn(
        re.escape(start) + '.*?' + re.escape(end),
        lambda _: start + '\n' + content + '\n' + end,
        source.read_text(encoding='utf-8'),
        flags=re.DOTALL,
    )
    if count != 1:
        raise ValueError(f'Expected one {kind} marker in {source}')
    source.write_text(text, encoding='utf-8')


def platform_icon(name: str) -> str:
    if name not in {'apple', 'windows', 'linux'}:
        raise ValueError(f'Unknown download platform icon: {name}')
    relative = f'zensical/templates/.icons/fontawesome/brands/{name}.svg'
    source = distribution('zensical').locate_file(relative)
    root = ElementTree.fromstring(source.read_bytes())
    paths = ''.join(
        '<path d="' + html.escape(path.attrib['d'], quote=True) + '"/>'
        for path in root
        if path.tag.endswith('path')
    )
    view_box = html.escape(root.attrib['viewBox'], quote=True)
    return f'<svg viewBox="{view_box}" aria-hidden="true" focusable="false">{paths}</svg>'


def render_interface_links() -> None:
    config = yaml.load((ROOT / 'surfaces/mkdocs.yml').read_text(), Loader=yaml.BaseLoader)
    icons = config['extra']['interface_icons']
    for path in DOCS.rglob('*.md'):

        def decorate(match):
            label, url, attributes = match.groups()
            label = re.sub(r'^<span class="ed-interface-icons"[^>]*>.*?</span>\s*', '', label)
            label = re.sub(r':[a-z][a-z0-9-]+:(?:\{[^}]*\})?\s*', '', label)
            label = re.sub(r'^<span class="ed-icon-text">(.*?)</span>$', r'\1', label)
            name = label.removeprefix('the ')
            if name not in icons:
                return match[0]
            symbols = ' '.join(':' + name.replace('/', '-') + ':' for name in icons[name])
            attributes = attributes or ''
            if '.ed-icon-label' not in attributes:
                attributes = (
                    attributes.rstrip().removesuffix('}').rstrip() + ' .ed-icon-label }'
                    if attributes
                    else '{ .ed-icon-label }'
                )
            if '.ed-interface-link' not in attributes:
                attributes = (
                    attributes.rstrip().removesuffix('}').rstrip() + ' .ed-interface-link }'
                    if attributes
                    else '{ .ed-interface-link }'
                )
            return (
                '[<span class="ed-interface-icons" aria-hidden="true">'
                + symbols
                + '</span> <span class="ed-icon-text">'
                + label
                + '</span>]('
                + url
                + ')'
                + attributes
            )

        # Code examples keep literal names. Only named interface links get icons.
        parts = re.split(
            r'(^```[^\n]*\n.*?^```[^\n]*(?:\n|$))',
            path.read_text(),
            flags=re.MULTILINE | re.DOTALL,
        )
        for index in range(0, len(parts), 2):
            parts[index] = re.sub(
                r'(?<!!)\[([^\]\n]+)\]\(([^)\n]+)\)([ \t]*\{[^}\n]*\})?',
                decorate,
                parts[index],
            )
        path.write_text(''.join(parts))


def download_buttons(family: str, entries: list[dict]) -> list[str]:
    """The download buttons of a distribution family, disabled until a release links them.

    The desktop installers come online and offline, a row each, one button per platform; a
    button's third line names its kind and, once a release is read, its size (render_downloads).
    The command line has one kind.
    """
    kinds = ('online', 'offline') if family == 'desktop' else (None,)
    buttons = []
    for kind in kinds:
        for entry in entries:
            label = html.escape(entry['platform'], quote=True)
            requirements = html.escape(entry['requirements'], quote=True)
            platform = html.escape(entry['artifact_platform'], quote=True)
            kind_attr = f' data-download-kind="{kind}"' if kind else ''
            kind_line = (
                f'<small data-download-size="{platform}-{kind}">{kind.capitalize()}</small>'
                if kind
                else ''
            )
            named = f', {kind}' if kind else ''
            buttons.append(
                f'<a class="md-button" data-download-platform="{platform}"{kind_attr} '
                'aria-disabled="true" '
                f'aria-label="Download for {label}, {requirements}{named}">'
                f'{platform_icon(entry["icon"])}'
                f'<span class="ed-download-label">{label}<small>{requirements}</small>'
                f'{kind_line}</span></a>'
            )
    return buttons


def render() -> None:
    capture = DOCS / 'assets/interfaces/capture.json'
    if capture.exists():
        metadata = json.loads(capture.read_text())
        example = metadata['example']
        fixture = json.loads((DOCS / 'assets/gui/y2o3/manifest.json').read_text())['example']
        if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', example) or example != fixture:
            raise ValueError('Interface screenshots must use the selected GUI example')
    for name, image, title, crop in [
        (
            'application',
            'gui/y2o3/13-analysis-basic.webp',
            'EasyDiffraction graphical application',
            0,
        ),
        ('python', 'interfaces/python-notebook.png', 'EasyDiffraction in a Jupyter notebook', 0),
        ('cli', 'interfaces/command-line.png', 'EasyDiffraction command-line session', 0),
    ]:
        source = DOCS / name / 'index.md'
        if f'<!-- interface-preview:{name} -->' in source.read_text():
            replace_marker(source, 'interface-preview', name, preview(image, title, crop))
    # The User guide's How you want to work table shows each interface's screenshot under its row.
    guide = DOCS / 'user-guide/index.md'
    for name, image, title in [
        (
            'application',
            'gui/y2o3/13-analysis-basic.webp',
            'EasyDiffraction graphical application',
        ),
        ('python', 'interfaces/python-notebook.png', 'EasyDiffraction in a Jupyter notebook'),
        ('cli', 'interfaces/command-line.png', 'EasyDiffraction command-line session'),
    ]:
        if f'<!-- interface-preview:guide-{name} -->' in guide.read_text():
            replace_marker(guide, 'interface-preview', f'guide-{name}', preview(image, title))
    releases = json.loads((ROOT / 'distributions.json').read_text())
    for family, filename in [
        ('desktop', 'application/desktop.md'),
        ('command-line', 'cli/standalone.md'),
    ]:
        source = DOCS / filename
        if not source.exists():
            continue
        buttons = download_buttons(family, releases['desktop'])
        rows = ' ed-downloads--kinds' if family == 'desktop' else ''
        replace_marker(
            source,
            'distribution',
            family,
            f'<div class="ed-downloads{rows}">' + '\n'.join(buttons) + '</div>',
        )
    render_interface_links()


if __name__ == '__main__':
    render()

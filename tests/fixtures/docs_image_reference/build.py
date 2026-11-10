# SPDX-License-Identifier: BSD-3-Clause
"""Author tiny built pages and executable capture producers without reading product outputs."""

import json
import struct
import sys
import zlib


def png(colour, *, incomplete_pixels=False):
    def chunk(kind, content):
        return (
            struct.pack('!I', len(content))
            + kind
            + content
            + struct.pack('!I', zlib.crc32(kind + content))
        )

    return (
        b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', struct.pack('!IIBBBBB', 2, 1, 8, 2, 0, 0, 0))
        + chunk(b'IDAT', zlib.compress(b'\0' if incomplete_pixels else b'\0' + bytes(colour) * 2))
        + chunk(b'IEND', b'')
    )


def build(root, fault=None):
    site, project = root / 'site', root / 'project'
    images = []
    for theme, colour in [('light', (137, 53, 19)), ('dark', (21, 79, 149))]:
        for name in ('ordinary.png', 'diagram.png'):
            relative = 'assets/gui/' + ('' if theme == 'light' else 'dark/') + name
            content = png(colour)
            if fault == 'undecodable-svg' and name == 'diagram.png':
                content = (theme + ' invalid image bytes').encode()
            for base in (site, project / 'website/surfaces/docs', project / 'inputs'):
                target = base / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                payload = content
                if base == project / 'inputs':
                    if fault == 'capture-broken-output':
                        payload = content[:24]
                    elif fault == 'capture-incomplete-pixels':
                        payload = png(colour, incomplete_pixels=True)
                target.write_bytes(payload)
            images.append({'theme': theme, 'path': relative})
    hidden = 'figure.ed-landing__preview {display:none}' if fault == 'hidden-slot' else ''
    html = (
        """<html><head><link rel="canonical" href="https://example.invalid/"></head>
<body data-md-color-scheme="default"><style>
body {background:#fff} body[data-md-color-scheme=slate] {background:#202020}
img {width:100px;height:50px;border:1px solid #eee}
body[data-md-color-scheme=slate] img {border-color:#282828}
.gui-image-frame {fill:none;stroke:#eee;stroke-width:1px}
body[data-md-color-scheme=slate] .gui-image-frame {stroke:#282828}
body[data-md-color-scheme=default] [data-theme=dark],
body[data-md-color-scheme=slate] [data-theme=light] {display:none}
"""
        + hidden
        + """</style>
<input type="radio" data-md-color-scheme="default"
 onclick="document.body.dataset.mdColorScheme='default'">
<input type="radio" data-md-color-scheme="slate"
 onclick="document.body.dataset.mdColorScheme='slate'">
<main><article><figure class="ed-landing__preview">
<img data-theme="light" src="assets/gui/ordinary.png" alt="Application preview">
<img data-theme="dark" src="assets/gui/dark/ordinary.png" alt="Application preview">
</figure><figure><svg width="102" height="52">
<image data-theme="light" href="assets/gui/diagram.png" width="100" height="50"/>
<image data-theme="dark" href="assets/gui/dark/diagram.png" width="100" height="50"/>
<rect class="gui-image-frame" width="101" height="51"/>
</svg></figure></article></main></body></html>"""
    )
    (site / 'index.html').write_text(html, encoding='utf-8')
    producer = """import json, pathlib, shutil, sys
root=pathlib.Path.cwd()
output=pathlib.Path(sys.argv[1]); output.mkdir()
plan=json.loads((root/'plan.json').read_text())
for item in plan:
    destination=root/'website/surfaces/docs'/item['path']
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(root/'inputs'/item['path'],destination)
"""
    (project / 'capture.py').write_text(producer, encoding='utf-8')
    plan = images[:-1] if fault == 'capture-omits-output' else images
    (project / 'plan.json').write_text(json.dumps(plan), encoding='utf-8')
    command = [sys.executable, 'capture.py', 'OUTPUT']
    if fault == 'capture-missing-command':
        command = ['nonexistent-image-capture-command', 'OUTPUT']
    elif fault == 'capture-fails':
        command = [sys.executable, '-c', 'raise SystemExit(17)', 'OUTPUT']
    manifest = {'command': command, 'images': images}
    (site / 'assets/capture-manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    return site, project, manifest

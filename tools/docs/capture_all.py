#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Capture every app image of the docs site in both themes, import them and write a manifest.

    pixi run -e app python tools/docs/capture_all.py OUTPUT   # capture, import, write the manifest
    pixi run python tools/docs/capture_all.py --check           # what is missing or stale

The plan is what is already committed: each capture set's executed walkthrough
(`website/surfaces/docs/assets/gui/<set>/walkthrough.js`), run once as committed in the light
theme and once in the dark theme. Every run goes through `tools/docs/capture-gui.sh`, the native
capture route (an isolated OpenGL display on Linux, since offscreen rendering skips shader
effects). The manifest, `assets/capture-manifest.json`, lists every image the command produces
with its theme; captures are not byte-reproducible, so the check compares presence and pixel
size, never bytes.
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / 'website/surfaces/docs'
GUI = DOCS / 'assets/gui'
MANIFEST = DOCS / 'assets/capture-manifest.json'
SETS = ('y2o3', 'scan', 'joint', 'sc', 'magnetic')  # the importer's capture sets, in its order
THEMES = ('light', 'dark')
# Content images that are not app captures. Each one's dark twin sits in `dark/` beside it when
# it has one; the concept figures are published illustrations and stay one image in both schemes.
STATIC = ('interfaces', 'learning', 'concepts')
COMMAND = ['pixi', 'run', '-e', 'app', 'python', 'tools/docs/capture_all.py', 'OUTPUT']
LOCK = os.environ.get('EDI_LOCAL_BUILD_LOCK', str(Path.home() / 'runs/.local-build.lock'))


def walkthrough(folder: str, theme: str) -> str:
    """A set's committed walkthrough, switched to `theme`."""
    script = (GUI / folder / 'walkthrough.js').read_text(encoding='utf-8')
    if theme == 'light':
        return script
    if '"theme:light"' not in script:
        raise SystemExit(
            f'{folder}: its walkthrough never selects the light theme, so it cannot be switched'
        )
    return script.replace('"theme:light"', '"theme:dark"')


def capture(output: Path) -> dict[str, Path]:
    """Run every set in both themes; answer each run's bundle folder by `<set>-<theme>`."""
    scripts = output / 'scripts'
    scripts.mkdir(parents=True, exist_ok=True)
    bundles = {}
    for folder in SETS:
        for theme in THEMES:
            name = f'{folder}-{theme}'
            script = scripts / f'{name}.js'
            script.write_text(walkthrough(folder, theme), encoding='utf-8')
            bundle = output / name
            print(f'capture: {name}', flush=True)
            # One heavy local job at a time on this machine; the lock is shared with builds.
            subprocess.run(
                [
                    'flock',
                    LOCK,
                    'bash',
                    'tools/docs/capture-gui.sh',
                    str(bundle),
                    '--docs-script',
                    str(script),
                ],
                cwd=ROOT,
                check=True,
            )
            bundles[name] = bundle
    return bundles


def import_bundles(bundles: dict[str, Path]) -> None:
    command = [
        sys.executable,
        'website/import_gui_captures.py',
        str(bundles['y2o3-light']),
        '--reference-bundle',
        str(bundles['scan-light']),
        '--joint-bundle',
        str(bundles['joint-light']),
        '--group-bundle',
        f'sc={bundles["sc-light"]}',
        '--group-bundle',
        f'magnetic={bundles["magnetic-light"]}',
    ]
    for folder in SETS:
        command += ['--dark-bundle', f'{folder}={bundles[folder + "-dark"]}']
    subprocess.run(command, cwd=ROOT, check=True)


def image_size(path: Path) -> tuple[int, int] | None:
    """A PNG's or a WebP's pixel size, read from its header; None for anything else."""
    data = path.read_bytes()[:30] if path.is_file() else b''
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return struct.unpack('!II', data[16:24])
    if data[:4] != b'RIFF' or data[8:12] != b'WEBP':
        return None
    chunk = data[12:16]
    if chunk == b'VP8X':
        return 1 + int.from_bytes(data[24:27], 'little'), 1 + int.from_bytes(data[27:30], 'little')
    if chunk == b'VP8 ':
        width, height = struct.unpack('<HH', data[26:30])
        return width & 0x3FFF, height & 0x3FFF
    if chunk == b'VP8L':
        bits = int.from_bytes(data[21:25], 'little')
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    return None


def expected() -> list[dict]:
    """Every image the command produces: each set's scenes in both themes, at its logical size."""
    rows = []
    for folder in SETS:
        manifest = json.loads((GUI / folder / 'manifest.json').read_text(encoding='utf-8'))
        size = tuple(manifest['logical_size'])
        for scene in (scene for scene in manifest['scenes'] if scene.get('image')):
            for theme in THEMES:
                place = (
                    f'assets/gui/{folder}/'
                    + ('' if theme == 'light' else 'dark/')
                    + scene['image']
                )
                rows.append({'theme': theme, 'path': place, 'size': list(size)})
    return rows


def static_images() -> list[dict]:
    """The static content images, with the file shown in each theme."""
    rows = []
    for folder in STATIC:
        for image in sorted((DOCS / 'assets' / folder).rglob('*')):
            if (
                image.suffix not in {'.png', '.jpg', '.svg', '.webp'}
                or 'dark' in image.relative_to(DOCS).parts
            ):
                continue
            light = image.relative_to(DOCS).as_posix()
            twin = image.parent / 'dark' / image.name
            dark = twin.relative_to(DOCS).as_posix() if twin.is_file() else light
            rows += [{'theme': 'light', 'path': light}, {'theme': 'dark', 'path': dark}]
    return rows


def write_manifest() -> None:
    images = [{'theme': row['theme'], 'path': row['path']} for row in expected()]
    images += static_images()
    MANIFEST.write_text(
        json.dumps({'command': COMMAND, 'images': images}, indent=1) + '\n', encoding='utf-8'
    )
    print(f'manifest: {len(images)} images in {MANIFEST.relative_to(ROOT)}')


def check() -> int:
    """Report images missing or stale by pixel size, and a manifest out of step with the sets."""
    problems = []
    for row in expected():
        size = image_size(DOCS / row['path'])
        if size is None:
            problems.append(f'missing: {row["path"]}')
        elif list(size) != row['size']:
            problems.append(
                f'stale: {row["path"]} is {size[0]}x{size[1]}, '
                f'not {row["size"][0]}x{row["size"][1]}'
            )
    listed = (
        json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.is_file() else {'images': []}
    )
    wanted = {(row['theme'], row['path']) for row in expected() + static_images()}
    have = {(row['theme'], row['path']) for row in listed['images']}
    problems += [f'not in the manifest: {theme} {path}' for theme, path in sorted(wanted - have)]
    problems += [
        f'in the manifest but not captured: {theme} {path}'
        for theme, path in sorted(have - wanted)
    ]
    for problem in problems:
        print(problem)
    print(f'capture check: {len(wanted)} images, {len(problems)} problems')
    return 1 if problems else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        'output', nargs='?', type=Path, help='a new folder for the capture bundles'
    )
    parser.add_argument('--check', action='store_true', help='report missing or stale images only')
    args = parser.parse_args()
    if args.check:
        return check()
    if args.output is None:
        parser.error('give an OUTPUT folder, or --check')
    if args.output.exists() and any(args.output.iterdir()):
        parser.error(f'{args.output} must be new or empty')
    import_bundles(capture(args.output.resolve()))
    write_manifest()
    return check()


if __name__ == '__main__':
    sys.exit(main())

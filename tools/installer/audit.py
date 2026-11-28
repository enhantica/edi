# SPDX-License-Identifier: BSD-3-Clause
"""Inventory a deployed native bundle and reject unrelated Qt component families."""

import argparse
import json
import re
from operator import itemgetter
from pathlib import Path

# Qt Multimedia itself records voice input (ADR-0107); its QML and widget parts are not used.
UNUSED_QT = re.compile(
    r'^(?:lib)?Qt6?(?:WebEngine|Charts|Multimedia(?:Quick|Widgets)|QuickTest|Test)(?:[^a-z]|$)'
)
# Qt Multimedia's FFmpeg plugin and FFmpeg itself, which build.py leaves out (ADR-0107).
FFMPEG = re.compile(
    r'^(?:lib)?(?:ffmpegmediaplugin|av(?:codec|device|filter|format|util)|postproc'
    r'|sw(?:resample|scale))[-.]'
)


def audit_bundle(stage: Path) -> dict:
    """Measure regular files without double-counting aliases or permitting unused Qt modules."""
    stage = stage.resolve()
    files = []
    qt_modules = set()
    for path in stage.rglob('*'):
        if path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(stage).as_posix()
        with path.open('rb') as stream:
            magic = stream.read(4)
        native = magic.startswith((b'\x7fELF', b'MZ')) or magic in {
            b'\xfe\xed\xfa\xce',
            b'\xfe\xed\xfa\xcf',
            b'\xce\xfa\xed\xfe',
            b'\xcf\xfa\xed\xfe',
            b'\xca\xfe\xba\xbe',
            b'\xbe\xba\xfe\xca',
            b'\xca\xfe\xba\xbf',
            b'\xbf\xba\xfe\xca',
        }
        if native and UNUSED_QT.match(path.name):
            raise RuntimeError(f'Unused Qt component was deployed: {relative}')
        if native and FFMPEG.match(path.name.lower()):
            raise RuntimeError(f'FFmpeg was deployed: {relative}')
        if native and re.match(r'^(?:lib)?Qt6?[A-Z]', path.name):
            qt_modules.add(path.name)
        files.append({'path': relative, 'bytes': path.stat().st_size})
    if not files:
        raise RuntimeError('Cannot audit an empty application bundle')
    assistant = [item for item in files if '/libexec/edi/codex/' in '/' + item['path']]
    voice = [item for item in files if '/share/edi/voice/' in '/' + item['path']]
    return {
        'schema': 'edi.bundle-audit/1',
        'regular_file_bytes': sum(item['bytes'] for item in files),
        'assistant_bytes': sum(item['bytes'] for item in assistant),
        'voice_bytes': sum(item['bytes'] for item in voice),
        'qt_modules': sorted(qt_modules),
        'largest_files': sorted(files, key=itemgetter('bytes'), reverse=True)[:15],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(audit_bundle(args.stage), indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()

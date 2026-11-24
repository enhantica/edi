# SPDX-License-Identifier: BSD-3-Clause
"""Check that the app holds nothing of the assistant demo.

The demo (app/tools/assistant_demo.cpp, the target edi_app_assistant_demo) attaches files,
signs in and sends without a person, so it must never be part of the app. Its names are
looked for in the app's sources and in its built program, as UTF-8 and as UTF-16.

    python tools/checks/assistant_demo_absent.py [program ...]

Without arguments the programs are those a build of this tree has made; a program named on
the command line must exist.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEMO = Path('app/tools/assistant_demo.cpp')
# What only the demo says: its name, its switches, its peer, its request and its notes.
NAMES = (
    'assistant-tools',
    'AssistantDemo',
    'EDI_ASSISTANT_PEER_DIR',
    'EDI_ASSISTANT_SHOW',
    'EDI_ASSISTANT_PROJECT',
    'EDI_ASSISTANT_FILES',
    'EDI_ASSISTANT_INACTIVE',
    'assistant_peer.py',
    'local-peer',
    'Call every tool',
    'presses.tsv',
    'demo.cover',
)
# Names it had, or has outside its source.
FORMER = ('demo_assistant', 'start_assistant_demo', 'assistant_demo')
SOURCES = {'.cpp', '.hpp', '.mm', '.qml', '.js', '.in'}
# What the app is linked from.
TARGETS = {'edi_app', 'edi_app_module', 'edi_app_moduleplugin'}
PROGRAMS = (
    'build/app/app/edi_app',
    'build/app/app/edi_app.exe',
    'build/app/app/EasyDiffraction',
    'build/app/app/EasyDiffraction.exe',
    'build/app/app/EasyDiffraction.app/Contents/MacOS/EasyDiffraction',
)


def stale_names(demo: str) -> list[str]:
    """Names this check looks for that the demo no longer has."""
    return [f'{DEMO} has no {name!r} any more' for name in NAMES if name not in demo]


def source_errors(root: Path) -> list[str]:
    errors = []
    paths = [root / 'app/main.cpp']
    paths += [path for path in (root / 'app/src').rglob('*') if path.suffix in SOURCES]
    paths += [path for path in (root / 'app/qml').rglob('*') if path.suffix in SOURCES]
    for path in sorted(paths):
        text = path.read_text(encoding='utf-8')
        errors += [
            f'{path.relative_to(root)}: {name!r}' for name in NAMES + FORMER if name in text
        ]
    return errors


def build_errors(cmake: str) -> list[str]:
    """The demo's source is in one command only, the target of its own."""
    errors = []
    text = re.sub(r'#[^\n]*', '', cmake)
    for command in re.finditer(r'\b(\w+)\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)', text):
        words = command.group(2).split()
        if not words or words[0] == 'edi_app_assistant_demo':
            continue
        if words[0] in TARGETS and any('assistant_demo' in word for word in words):
            errors.append(f'app/CMakeLists.txt: {command.group(1)} adds the demo to {words[0]}')
    used = text.count('tools/assistant_demo.cpp')
    own = re.search(
        r'qt_add_executable\(\s*edi_app_assistant_demo\s+EXCLUDE_FROM_ALL\s+tools/assistant_demo\.cpp',
        text,
    )
    if used != 1 or own is None:
        errors.append(
            'app/CMakeLists.txt: the demo is not the source of edi_app_assistant_demo alone'
        )
    if re.search(r'install\s*\([^)]*edi_app_assistant_demo', text):
        errors.append('app/CMakeLists.txt: the demo is installed')
    return errors


def program_errors(program: Path) -> list[str]:
    data = program.read_bytes()
    return [
        f'{program}: {name!r} ({encoding})'
        for name in NAMES + FORMER
        for encoding in ('utf-8', 'utf-16-le')
        if name.encode(encoding) in data
    ]


def main() -> int:
    named = [Path(argument) for argument in sys.argv[1:]]
    missing = [f'{program}: no such program' for program in named if not program.is_file()]
    programs = named or [ROOT / program for program in PROGRAMS if (ROOT / program).is_file()]
    errors = [*missing, *stale_names((ROOT / DEMO).read_text(encoding='utf-8'))]
    errors += source_errors(ROOT)
    errors += build_errors((ROOT / 'app/CMakeLists.txt').read_text(encoding='utf-8'))
    for program in programs:
        if program.is_file():
            errors += program_errors(program)
    for error in errors:
        print(error)
    where = ', '.join(str(program) for program in programs) or 'no program built yet'
    print(f'assistant demo: {len(errors)} problem(s) in the sources and {where}')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())

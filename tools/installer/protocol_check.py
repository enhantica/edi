# SPDX-License-Identifier: BSD-3-Clause
"""Exercise real IFW install/update transport with tiny local marker components."""

import argparse
import json
import os
from itertools import combinations
from pathlib import Path
from unittest.mock import patch

from package import (
    ASSISTANT_COMPONENT,
    ASSISTANT_RUNTIME,
    SUFFIX,
    SYSTEM,
    clean_environment,
    installer_from_download,
    package_app,
    run,
    verify_installed_maintenance_tool,
)

ASSISTANT_MARKERS = {
    ASSISTANT_COMPONENT: ASSISTANT_RUNTIME / 'chatgpt.txt',
    'org.easydiffraction.app.claude': Path('libexec/edi/claude/claude.txt'),
    'org.easydiffraction.app.copilot': Path('libexec/edi/copilot/copilot.txt'),
}


def installer_command(path: Path) -> Path:
    """Locate the framework entry point inside a platform installer."""
    if SYSTEM == 'macos':
        return next((path / 'Contents/MacOS').iterdir())
    return path


def check(tools: Path, output: Path) -> None:
    """Check offline install, local repository update, online install and removal."""
    output = output.resolve()
    output.mkdir(parents=True)
    stage = output / 'marker-stage'
    marker = stage / (
        'EasyDiffraction.app/Contents/MacOS/EasyDiffraction'
        if SYSTEM == 'macos'
        else 'bin/EasyDiffraction' + SUFFIX
    )
    marker.parent.mkdir(parents=True)
    marker.write_text('first marker\n')
    for component, relative in ASSISTANT_MARKERS.items():
        assistant_marker = stage / relative
        assistant_marker.parent.mkdir(parents=True)
        assistant_marker.write_text(component + '\n', encoding='utf-8')
    repository = (output / 'online/repository').as_uri() + '/'
    # Substitute only the endpoint; install and maintenance use the real embedded configuration.
    with patch('package.repository_urls', return_value=(repository,)):
        offline = package_app(stage, tools, output / 'offline', '2026.11.0')
    marker.write_text('second marker\n')
    online = package_app(stage, tools, output / 'online', '2026.11.1', repository)
    (output / 'isolated home').mkdir()
    for kind, bootstrap in [('offline', offline), ('online', online)]:
        exercise(kind, bootstrap, output, marker.relative_to(stage))
    (output / 'passed.json').write_text(
        json.dumps({'passed': True, 'transport': 'file', 'application_test': False}) + '\n'
    )


def check_assistants(target: Path, expected: set[str]) -> None:
    """Read the installed marker for each provider after an operation."""
    for component, relative in ASSISTANT_MARKERS.items():
        installed = target / relative
        if component in expected:
            if (
                not installed.is_file()
                or installed.read_text(encoding='utf-8') != component + '\n'
            ):
                raise RuntimeError(f'Installer did not preserve the selected {component} payload')
        elif installed.exists():
            raise RuntimeError(f'Installer installed the unselected {component} payload')


def check_offline_subsets(executable, maintenance, target, installed, options) -> None:
    install = [
        executable,
        '--root',
        target,
        '--accept-licenses',
        '--default-answer',
        '--confirm-command',
        'install',
    ]
    for count in range(1, len(ASSISTANT_MARKERS) + 1):
        for subset in combinations(ASSISTANT_MARKERS, count):
            run([*install, *subset], **options)
            try:
                if installed.read_text() != 'first marker\n':
                    raise RuntimeError('Selecting assistants must retain the application')
                check_assistants(target, set(subset))
            finally:
                run([maintenance, '--default-answer', '--confirm-command', 'purge'], **options)


def exercise(kind: str, bootstrap: Path, output: Path, marker: Path) -> None:
    env = clean_environment(output / 'isolated home' / kind)
    metadata = json.loads((bootstrap.parent / 'installer.json').read_text())
    executable = installer_command(
        installer_from_download(
            bootstrap.parent / metadata['download'], output / kind / 'unpacked'
        )
    )
    target = output / (kind + ' installed app')
    maintenance = target / (
        'MaintenanceTool.app/Contents/MacOS/MaintenanceTool'
        if SYSTEM == 'macos'
        else 'MaintenanceTool' + SUFFIX
    )
    with (output / (kind + '.log')).open('w') as log:
        options = {'env': env, 'stdout': log, 'stderr': -2, 'timeout': 60}
        run(
            [
                executable,
                '--root',
                target,
                '--accept-licenses',
                '--default-answer',
                '--confirm-command',
                'install',
            ],
            **options,
        )
        installed = target / marker
        try:
            verify_installed_maintenance_tool(target, metadata)
            expected = 'first marker\n' if kind == 'offline' else 'second marker\n'
            if installed.read_text() != expected:
                raise RuntimeError('Installer did not install the expected component')
            check_assistants(target, set())
            if kind == 'offline':
                user_file = target / 'user-project.edi'
                user_file.write_text('keep the project\n')
                run(
                    [maintenance, 'check-updates'],
                    **options,
                )
                run(
                    [
                        maintenance,
                        '--accept-licenses',
                        '--default-answer',
                        '--confirm-command',
                        'update',
                    ],
                    **options,
                )
                if installed.read_text() != 'second marker\n':
                    raise RuntimeError('Maintenance tool did not apply the component update')
                if user_file.read_text() != 'keep the project\n':
                    raise RuntimeError('In-place update changed an unrelated user file')
            maintenance_args = [
                maintenance,
                '--accept-licenses',
                '--default-answer',
                '--confirm-command',
            ]
            selected = set()
            for component in ASSISTANT_MARKERS:
                run([*maintenance_args, 'install', component], **options)
                selected.add(component)
                check_assistants(target, selected)
            for component in ASSISTANT_MARKERS:
                run([*maintenance_args, 'remove', component], **options)
                selected.remove(component)
                check_assistants(target, selected)
            if installed.read_text() != 'second marker\n':
                raise RuntimeError('Removing the assistant changed the required application')
        finally:
            run([maintenance, '--default-answer', '--confirm-command', 'purge'], **options)
        if installed.exists():
            raise RuntimeError('Maintenance tool left the component installed')
        if kind == 'offline':
            check_offline_subsets(executable, maintenance, target, installed, options)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tools', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # The marker installers are never signed, release runs included (edi ADR-0091).
    os.environ.pop('EDI_CODESIGN', None)
    check(args.tools.resolve(), args.output)


if __name__ == '__main__':
    main()

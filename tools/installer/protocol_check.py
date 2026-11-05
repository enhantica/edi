# SPDX-License-Identifier: BSD-3-Clause
"""Exercise real IFW install/update transport with tiny local marker components."""

import argparse
import json
from pathlib import Path

from package import (
    ASSISTANT_COMPONENT,
    ASSISTANT_RUNTIME,
    SUFFIX,
    SYSTEM,
    clean_environment,
    package_app,
    run,
    unpack_installer,
)


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
        else 'bin/edi_app' + SUFFIX
    )
    marker.parent.mkdir(parents=True)
    marker.write_text('first marker\n')
    assistant_marker = stage / ASSISTANT_RUNTIME / 'assistant.txt'
    assistant_marker.parent.mkdir(parents=True)
    assistant_marker.write_text('optional assistant marker\n')
    offline = package_app(stage, tools, output / 'offline', '2026.11.0')
    marker.write_text('second marker\n')
    repository = (output / 'online/repository').as_uri() + '/'
    online = package_app(stage, tools, output / 'online', '2026.11.1', repository)
    (output / 'isolated home').mkdir()
    for kind, bootstrap in [('offline', offline), ('online', online)]:
        exercise(
            kind, bootstrap, output, marker.relative_to(stage), assistant_marker.relative_to(stage)
        )
    (output / 'passed.json').write_text(
        json.dumps({'passed': True, 'transport': 'file', 'application_test': False}) + '\n'
    )


def exercise(
    kind: str, bootstrap: Path, output: Path, marker: Path, assistant_marker: Path
) -> None:
    repository = (output / 'online/repository').as_uri() + '/'
    env = clean_environment(output / 'isolated home' / kind)
    executable = installer_command(
        unpack_installer(bootstrap.with_suffix('.zip'), output / kind / 'unzipped')
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
            expected = 'first marker\n' if kind == 'offline' else 'second marker\n'
            if installed.read_text() != expected:
                raise RuntimeError('Installer did not install the expected component')
            installed_assistant = target / assistant_marker
            if installed_assistant.exists():
                raise RuntimeError('Default installation selected the optional component')
            if kind == 'offline':
                user_file = target / 'user-project.edi'
                user_file.write_text('keep the project\n')
                run(
                    [maintenance, '--set-temp-repository', repository, 'check-updates'],
                    **options,
                )
                run(
                    [
                        maintenance,
                        '--set-temp-repository',
                        repository,
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
                '--set-temp-repository',
                repository,
                '--accept-licenses',
                '--default-answer',
                '--confirm-command',
            ]
            run([*maintenance_args, 'install', ASSISTANT_COMPONENT], **options)
            if installed_assistant.read_text() != 'optional assistant marker\n':
                raise RuntimeError('Maintenance tool did not install the assistant')
            run([*maintenance_args, 'remove', ASSISTANT_COMPONENT], **options)
            if installed_assistant.exists() or installed.read_text() != 'second marker\n':
                raise RuntimeError('Removing the assistant changed the required application')
        finally:
            run([maintenance, '--default-answer', '--confirm-command', 'purge'], **options)
        if installed.exists():
            raise RuntimeError('Maintenance tool left the component installed')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tools', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    check(args.tools.resolve(), args.output)


if __name__ == '__main__':
    main()

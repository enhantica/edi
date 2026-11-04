# SPDX-License-Identifier: BSD-3-Clause
"""Exercise real IFW install/update transport with tiny local marker components."""

import argparse
import json
from pathlib import Path

from package import SUFFIX, SYSTEM, clean_environment, package_app, run, unpack_installer


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
    offline = package_app(stage, tools, output / 'offline', '2026.11.0')
    marker.write_text('second marker\n')
    repository = (output / 'online/repository').as_uri() + '/'
    online = package_app(stage, tools, output / 'online', '2026.11.1', repository)
    home = output / 'isolated home'
    home.mkdir()
    env = clean_environment(home)
    for kind, bootstrap in [('offline', offline), ('online', online)]:
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
            installed = target / marker.relative_to(stage)
            try:
                expected = 'first marker\n' if kind == 'offline' else 'second marker\n'
                if installed.read_text() != expected:
                    raise RuntimeError('Installer did not install the expected component')
                if kind == 'offline':
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
            finally:
                run([maintenance, '--default-answer', '--confirm-command', 'purge'], **options)
            if installed.exists():
                raise RuntimeError('Maintenance tool left the component installed')
    (output / 'passed.json').write_text(
        json.dumps({'passed': True, 'transport': 'file', 'application_test': False}) + '\n'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tools', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    check(args.tools.resolve(), args.output)


if __name__ == '__main__':
    main()

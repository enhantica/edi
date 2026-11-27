# SPDX-License-Identifier: BSD-3-Clause
"""Exercise real IFW install/update transport with tiny local marker components."""

import argparse
import json
import os
import re
import subprocess
import time
from itertools import combinations
from pathlib import Path
from unittest.mock import patch

from package import (
    ASSISTANT_COMPONENT,
    ASSISTANT_RUNTIME,
    CLAUDE_COMPONENT,
    COPILOT_COMPONENT,
    SUFFIX,
    SYSTEM,
    build_maintenance_tool,
    clean_environment,
    distributed_assistants,
    installer_from_download,
    package_app,
    run,
    sha256,
    verify_installed_maintenance_tool,
)

ASSISTANT_MARKERS = {
    ASSISTANT_COMPONENT: ASSISTANT_RUNTIME / 'chatgpt.txt',
    CLAUDE_COMPONENT: Path('libexec/edi/claude/claude.txt'),
    COPILOT_COMPONENT: Path('libexec/edi/copilot/copilot.txt'),
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
    # The update goes from the last old-form version to the first YY.N, which sorts lower by its
    # numbers: the repository offers it by content checksum (edi ADR-0106).
    # The marker installers are internal builds, so they exercise Claude before its distribution is
    # public; a public build of the same stage carries only the distributed assistants.
    with patch('package.repository_urls', return_value=(repository,)):
        offline = package_app(stage, tools, output / 'offline', '2026.11.31', internal=True)
        public = package_app(stage, tools, output / 'public', '2026.11.31')
    public_metadata = json.loads((public.parent / 'installer.json').read_text())
    public_offer = offered(
        installer_command(
            installer_from_download(
                public.parent / public_metadata['download'], output / 'public/unpacked'
            )
        ),
        clean_environment(output / 'public/home'),
    )
    if public_metadata['internal'] or public_offer & set(ASSISTANT_MARKERS) != set(
        distributed_assistants()
    ):
        raise RuntimeError('A public installer carries an assistant that is not distributed')
    marker.write_text('second marker\n')
    # The new release's tool gets other bytes, so the update has a tool to replace. On Linux the
    # update leaves the tool alone (edi ADR-0091), so only macOS and Windows build one.
    new_tool = (
        build_maintenance_tool(tools, output / 'online tool', '1')
        if SYSTEM in {'macos', 'windows'}
        else None
    )
    online = package_app(
        stage, tools, output / 'online', '26.17', repository, (), new_tool, internal=True
    )
    (output / 'isolated home').mkdir()
    for kind, bootstrap in [('offline', offline), ('online', online)]:
        exercise(kind, bootstrap, output, marker.relative_to(stage))
    (output / 'passed.json').write_text(
        json.dumps({'passed': True, 'transport': 'file', 'application_test': False}) + '\n'
    )


def offered(executable: Path, env: dict) -> set[str]:
    """The components an installer offers, as its search command lists them."""
    result = subprocess.run(
        [executable, 'search'], env=env, capture_output=True, text=True, timeout=60, check=True
    )
    return set(re.findall(r'<package name="([^"]+)"', result.stdout + result.stderr))


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
                new_metadata = json.loads((output / 'online/installer.json').read_text())
                if SYSTEM in {'macos', 'windows'}:
                    old_tool = sha256(maintenance)
                    if old_tool == new_metadata['maintenance_tool_sha256']:
                        raise RuntimeError('Old and new maintenance tools are the same file')
                run(
                    [maintenance, 'check-updates'],
                    **options,
                )
                run(
                    [
                        maintenance,
                        '--verbose',  # the log says whether the tool component was updated
                        '--accept-licenses',
                        '--default-answer',
                        '--confirm-command',
                        'update',
                    ],
                    **options,
                )
                if installed.read_text() != 'second marker\n':
                    raise RuntimeError('Maintenance tool did not apply the component update')
                # The update brings the newer release's signed tool along (edi ADR-0106). The
                # Framework may swap the tool only once the updating process has ended, so the
                # check waits for it a while, and says what it found if it never comes.
                tool_replaced(target, new_metadata)
                # Nothing is left to offer after the update.
                nothing_offered(maintenance, env)
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


def nothing_offered(maintenance: Path, env: dict) -> None:
    """Require a successful update query with no update in it.

    A query that failed to fetch the repository ends with an error status and proves nothing.
    """
    again = subprocess.run(
        [maintenance, 'check-updates'],
        env=env, capture_output=True, text=True, timeout=60, check=False,
    )  # fmt: skip
    print(again.stdout + again.stderr, flush=True)
    if again.returncode != 0:
        raise RuntimeError('The second update query failed')
    if '<update ' in again.stdout:
        raise RuntimeError('The maintenance tool still offers an update')


def tool_replaced(target: Path, metadata: dict, wait: float = 60) -> None:
    deadline = time.monotonic() + wait
    while True:
        try:
            verify_installed_maintenance_tool(target, metadata)
        # The signature probe fails with CalledProcessError while the bundle is being swapped.
        except (RuntimeError, subprocess.CalledProcessError):
            if time.monotonic() > deadline:
                found = sorted(path.name for path in target.iterdir())
                print(f'protocol check: after the update the folder holds {found}', flush=True)
                raise
            time.sleep(2)
        else:
            return


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

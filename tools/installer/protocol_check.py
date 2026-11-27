# SPDX-License-Identifier: BSD-3-Clause
"""Exercise real IFW install/update transport with tiny local marker components."""

import argparse
import json
import os
import subprocess
import time
import xml.etree.ElementTree as ET  # noqa: S405 - binarycreator's own XML only
from pathlib import Path
from unittest.mock import patch

from maintenance_resource import RESOURCE_NAME, dat_resources, read_rcc
from package import (
    ASSISTANT_COMPONENT,
    ASSISTANT_RUNTIME,
    SUFFIX,
    SYSTEM,
    build_maintenance_tool,
    clean_environment,
    installer_from_download,
    package_app,
    run,
    sha256,
    verify_installed_maintenance_tool,
    write_controller,
)

# Ends the first release's control script, so the check can tell its pages from the new ones.
FIRST_RELEASE_MARKER = '// edi protocol check: the interface of the first release'


def installer_command(path: Path) -> Path:
    """Locate the framework entry point inside a platform installer."""
    if SYSTEM == 'macos':
        return next((path / 'Contents/MacOS').iterdir())
    return path


def first_release_controller(config: Path, tool_bytes: int = 0) -> None:
    """Write the controller and mark it as the first release's."""
    write_controller(config, tool_bytes)
    with (config / 'Installer.qs').open('a', encoding='utf-8') as controller:
        controller.write('\n' + FIRST_RELEASE_MARKER + '\n')


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
    assistant_marker = stage / ASSISTANT_RUNTIME / 'assistant.txt'
    assistant_marker.parent.mkdir(parents=True)
    assistant_marker.write_text('optional assistant marker\n')
    repository = (output / 'online/repository').as_uri() + '/'
    # Substitute only the endpoint; install and maintenance use the real embedded configuration.
    # The update goes from the last old-form version to the first YY.N, which sorts lower by its
    # numbers: the repository offers it by content checksum (edi ADR-0106). The first release
    # stands for 2026.11: its pages are marked and it ships no replacement for the tool's default
    # resource, so only the update can bring the new pages.
    with (
        patch('package.repository_urls', return_value=(repository,)),
        patch('package.write_controller', first_release_controller),
    ):
        offline = package_app(stage, tools, output / 'offline', '2026.11.31')
    if list((output / 'offline/source/packages').glob('*/data/**/' + RESOURCE_NAME)):
        raise RuntimeError(f'The first release ships {RESOURCE_NAME}, which 2026.11 did not')
    marker.write_text('second marker\n')
    # The new release's tool gets other bytes, so the update has a tool to replace. On Linux the
    # update leaves the tool alone (edi ADR-0091), so only macOS and Windows build one.
    new_tool = (
        build_maintenance_tool(tools, output / 'online tool', '1')
        if SYSTEM in {'macos', 'windows'}
        else None
    )
    online = package_app(stage, tools, output / 'online', '26.17', repository, (), new_tool)
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
            installed_assistant = target / assistant_marker
            if installed_assistant.exists():
                raise RuntimeError('Default installation selected the optional component')
            # The offline install shows the first release's pages, which proves the check below
            # can tell them apart; the online install shows the new ones.
            maintenance_pages(target, output / kind / 'source', first_release=kind == 'offline')
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
                # The new tool must show the new release's pages, not the ones the old .dat held.
                maintenance_pages(target, output / 'online/source', first_release=False)
                if user_file.read_text() != 'keep the project\n':
                    raise RuntimeError('In-place update changed an unrelated user file')
            maintenance_args = [
                maintenance,
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


def maintenance_pages(target: Path, source: Path, *, first_release: bool) -> None:
    """Require the installed tool's pages to be the ones the installer `source` was built with.

    The tool reads its configuration, control script and style sheet from the default resource,
    the first segment of MaintenanceTool.dat, and an update replaces that segment only with the
    MaintenanceTool.rcc the app component brings, which the Framework deletes once written. A
    2026.11 .dat holds no -r resources, so after an update the replacement must carry them too.
    """
    if (target / RESOURCE_NAME).exists():
        raise RuntimeError(f'The Framework left {RESOURCE_NAME} in the installation')
    dat = target / 'MaintenanceTool.dat'
    if not dat.is_file():
        raise RuntimeError('The installation has no MaintenanceTool.dat')
    files = read_rcc(dat_resources(dat)[0])
    if 'installer-config/config.xml' not in files:
        raise RuntimeError('The default resource of MaintenanceTool.dat has no config.xml')
    config = ET.fromstring(files['installer-config/config.xml'])  # noqa: S314 - from binarycreator
    control_script = b''
    for element, built in [('ControlScript', 'Installer.qs'), ('StyleSheet', 'Installer.qss')]:
        named = config.findtext(element)
        if not named:
            raise RuntimeError(f'The config.xml in MaintenanceTool.dat names no {element}')
        # binarycreator renames the file it copies under installer-config/ and names it there.
        name = named.removeprefix(':/metadata/').removeprefix('installer-config/')
        path = 'installer-config/' + name
        if path not in files:
            raise RuntimeError(f'MaintenanceTool.dat has no {path}, the {element} it names')
        if files[path] != (source / 'config' / built).read_bytes():
            raise RuntimeError(
                f'The {element} in MaintenanceTool.dat is not the {built} of {source.parent.name}'
            )
        if element == 'ControlScript':
            control_script = files[path]
    if (FIRST_RELEASE_MARKER.encode() in control_script) != first_release:
        raise RuntimeError(
            'The first release does not show its marked control script'
            if first_release
            else "The maintenance tool still shows the first release's control script"
        )
    if first_release:
        return  # binarycreator keeps the -r resources in a segment of their own
    for required in ('translations/ifw_en.qm', 'edi/CheckMark.png'):
        if required not in files:
            raise RuntimeError(f'The default resource of MaintenanceTool.dat has no {required}')


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

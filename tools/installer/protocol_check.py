# SPDX-License-Identifier: BSD-3-Clause
"""Exercise real IFW install/update transport with tiny local marker components."""

import argparse
import base64
import functools
import json
import os
import subprocess
import time
import xml.etree.ElementTree as ET  # noqa: S405 - binarycreator's and our own XML only
from pathlib import Path
from unittest.mock import patch

from maintenance_resource import RESOURCE_NAME, dat_files, dat_resources, read_rcc
from package import (
    APP_COMPONENT,
    ASSISTANT_COMPONENT,
    ASSISTANT_RUNTIME,
    ROOT,
    SUFFIX,
    SYSTEM,
    add_maintenance_resource,
    build_maintenance_tool,
    check_maintenance_tool,
    clean_environment,
    installer_from_download,
    maintenance_script,
    maintenance_tool_executable,
    maintenance_tool_name,
    package_app,
    run,
    sha256,
    verify_installed_maintenance_tool,
    write_resources,
)

# The release users update from: its control script has no cleanup for the tool the macOS swap
# keeps, and its .dat holds no replacement for the tool's pages.
RELEASED_TAG = 'v2026.11.27'

# Added to one 26.18 build's component script: its update fails once the component's own
# operations have run, so the Framework rolls it back.
FAILING_OPERATION = """
// protocol check: an update with this build fails after the component's own operations.
var ediCreateOperations = Component.prototype.createOperations;
Component.prototype.createOperations = function () {
    ediCreateOperations.call(this);
    if (installer.isUpdater())
        component.addOperation("Execute", %s);
};
"""

UPDATE = ['--verbose', '--accept-licenses', '--default-answer', '--confirm-command', 'update']


def installer_command(path: Path) -> Path:
    """Locate the framework entry point inside a platform installer."""
    if SYSTEM == 'macos':
        return next((path / 'Contents/MacOS').iterdir())
    return path


@functools.cache
def released_file(path: str) -> bytes:
    """A file as the released tag holds it. CI checkouts must fetch the tags."""
    result = subprocess.run(
        ['git', '-C', str(ROOT), 'show', f'{RELEASED_TAG}:{path}'],
        capture_output=True, timeout=60, check=False,
    )  # fmt: skip
    if result.returncode != 0:
        raise RuntimeError(
            f'Cannot read {path} at {RELEASED_TAG}; fetch the tags: '
            + result.stderr.decode(errors='replace').strip()
        )
    return result.stdout


def released_text(path: str) -> str:
    """A released text file with universal newlines, as the released code read it."""
    return released_file(path).decode('utf-8').replace('\r\n', '\n')


@functools.cache
def released_controller_text() -> str:
    """The released control script, its wordmarks filled in as its write_controller did."""
    controller = released_text('tools/installer/Installer.qs')
    wordmarks = (('@WORDMARK@', 'InstallerLogo.png'), ('@DARK_WORDMARK@', 'InstallerLogoDark.png'))
    for marker, name in wordmarks:
        if marker not in controller:
            raise RuntimeError(f'The control script at {RELEASED_TAG} has no {marker}')
        image = base64.b64encode(released_file('tools/installer/' + name)).decode('ascii')
        controller = controller.replace(marker, image)
    return controller


def released_controller(config: Path, _tool_bytes: int = 0) -> None:
    """Write the stylesheet and the controller as the released write_controller wrote them."""
    stylesheet = released_text('tools/installer/Installer.qss')
    if '@STEP_LIST_INSET@' not in stylesheet:
        raise RuntimeError(f'The stylesheet at {RELEASED_TAG} has no @STEP_LIST_INSET@')
    (config / 'Installer.qss').write_text(
        stylesheet.replace('@STEP_LIST_INSET@', '23' if SYSTEM == 'macos' else '9'),
        encoding='utf-8',
    )
    (config / 'Installer.qs').write_text(released_controller_text(), encoding='utf-8')


def first_release_resources(config: Path, configuration: ET.ElementTree) -> Path:
    """Write the resources with another tick image, so the update must bring the new one."""
    listed = write_resources(config, configuration)
    (config / 'resources/CheckMark.png').write_bytes(
        (ROOT / 'tools/installer/icons/finish.png').read_bytes()
    )
    return listed


def failing_operation() -> str:
    """The component script text that makes an update with it fail."""
    command = ['cmd.exe', '/c', 'exit 1'] if SYSTEM == 'windows' else ['/bin/sh', '-c', 'exit 1']
    return FAILING_OPERATION % ', '.join(json.dumps(part) for part in command)


def failing_tool_script() -> str:
    """The tool component's script with the failing operation after the macOS swap."""
    return maintenance_script() + failing_operation()


def failing_app_resource(source: Path, tools: Path, environment: dict | None) -> None:
    """Linux has no tool component, so the app component's update fails instead."""
    add_maintenance_resource(source, tools, environment)
    with (source / 'packages' / APP_COMPONENT / 'meta/installscript.qs').open(
        'a', encoding='utf-8'
    ) as script:
        script.write(failing_operation())


def check(tools: Path, output: Path) -> None:
    """Check offline install, two updates (one interrupted), online install and removal."""
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
    # numbers: the repository offers it by content checksum (edi ADR-0106). The first release has
    # the released controller and stylesheet, another tick image, and no replacement for the
    # tool's default resource, so only the update can bring the new pages.
    with (
        patch('package.repository_urls', return_value=(repository,)),
        patch('package.write_controller', released_controller),
        patch('package.write_resources', first_release_resources),
    ):
        offline = package_app(stage, tools, output / 'offline', '2026.11.31')
    if list((output / 'offline/source/packages').glob('*/data/**/' + RESOURCE_NAME)):
        raise RuntimeError(f'The first release ships {RESOURCE_NAME}, which 2026.11 did not')
    marker.write_text('second marker\n')
    # The new release's tool gets other bytes, so the update has a tool to replace. On Linux the
    # update leaves the tool alone (edi ADR-0091), so only macOS and Windows build one.
    tool_builds = SYSTEM in {'macos', 'windows'}
    new_tool = build_maintenance_tool(tools, output / 'online tool', '1') if tool_builds else None
    online = package_app(stage, tools, output / 'online', '26.17', repository, (), new_tool)
    for name in ('Installer.qs', 'resources/CheckMark.png'):
        first, new = (output / kind / 'source/config' / name for kind in ('offline', 'online'))
        if first.read_bytes() == new.read_bytes():
            raise RuntimeError(f'The first release and 26.17 have the same {name}')
    # 26.18 changes the app and the tool again. One build of it fails its update and the other
    # succeeds, each from a repository of its own.
    marker.write_text('third marker\n')
    third_tool = build_maintenance_tool(tools, output / 'tool 26.18', '2') if tool_builds else None
    with (
        patch('package.maintenance_script', failing_tool_script)
        if tool_builds
        else patch('package.add_maintenance_resource', failing_app_resource)
    ):
        failing = output / 'failing-26.18'
        package_app(
            stage, tools, failing, '26.18', (failing / 'repository').as_uri() + '/', (), third_tool
        )
    update = output / 'update-26.18'
    package_app(
        stage, tools, update, '26.18', (update / 'repository').as_uri() + '/', (), third_tool
    )
    (output / 'isolated home').mkdir()
    # The interrupted update leaves an installation the Framework can no longer update, so the
    # successful second update starts from an installation of its own.
    for kind, bootstrap in [('offline', offline), ('interrupted', offline), ('online', online)]:
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
    first_release = kind != 'online'
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
            expected = 'first marker\n' if first_release else 'second marker\n'
            if installed.read_text() != expected:
                raise RuntimeError('Installer did not install the expected component')
            installed_assistant = target / assistant_marker
            if installed_assistant.exists():
                raise RuntimeError('Default installation selected the optional component')
            # The first release's install shows its pages, which proves the check below can tell
            # them apart; the online install shows the new ones.
            maintenance_pages(
                target, output / bootstrap.parent.name / 'source', first_release=first_release
            )
            if first_release:
                first_update(target, maintenance, installed, output, options)
            if kind == 'interrupted':
                interrupted_update(target, maintenance, installed, output, options)
            else:
                if kind == 'offline':
                    second_update(target, maintenance, installed, output, options)
                assistant(maintenance, installed, installed_assistant, kind, options)
        finally:
            run([maintenance, '--default-answer', '--confirm-command', 'purge'], **options)
        if installed.exists():
            raise RuntimeError('Maintenance tool left the component installed')


def assistant(
    maintenance: Path, installed: Path, installed_assistant: Path, kind: str, options: dict
) -> None:
    """Install and remove the optional assistant, leaving the application as it was."""
    final = 'third marker\n' if kind == 'offline' else 'second marker\n'
    maintenance_args = [maintenance, '--accept-licenses', '--default-answer', '--confirm-command']
    run([*maintenance_args, 'install', ASSISTANT_COMPONENT], **options)
    if installed_assistant.read_text(encoding='utf-8') != 'optional assistant marker\n':
        raise RuntimeError('Maintenance tool did not install the assistant')
    run([*maintenance_args, 'remove', ASSISTANT_COMPONENT], **options)
    if installed_assistant.exists() or installed.read_text(encoding='utf-8') != final:
        raise RuntimeError('Removing the assistant changed the required application')


def first_update(
    target: Path, maintenance: Path, installed: Path, output: Path, options: dict
) -> None:
    """Update the first release, run by the released controller, to 26.17."""
    user_file = target / 'user-project.edi'
    user_file.write_text('keep the project\n')
    new_metadata = json.loads((output / 'online/installer.json').read_text())
    if SYSTEM in {'macos', 'windows'}:
        old_tool = sha256(maintenance)
        if old_tool == new_metadata['maintenance_tool_sha256']:
            raise RuntimeError('Old and new maintenance tools are the same file')
    run([maintenance, 'check-updates'], **options)
    # --verbose: the log says whether the tool component was updated.
    run([maintenance, *UPDATE], **options)
    if installed.read_text(encoding='utf-8') != 'second marker\n':
        raise RuntimeError('Maintenance tool did not apply the component update')
    # The update brings the newer release's signed tool along (edi ADR-0106). The Framework may
    # swap the tool only once the updating process has ended, so the check waits for it a while,
    # and says what it found if it never comes. The released controller ran this update and has
    # no cleanup for the tool the macOS swap kept, and the new controller loads only in the next
    # process, so the backup stays until the next update's swap removes it.
    tool_replaced(target, new_metadata, old_left=SYSTEM == 'macos')
    # Nothing is left to offer after the update.
    nothing_offered(maintenance, options['env'])
    # The new tool must show the new release's pages, not the ones the old .dat held.
    maintenance_pages(target, output / 'online/source', first_release=False)
    old_tick = (output / 'offline/source/config/resources/CheckMark.png').read_bytes()
    if default_resource(target).get('edi/CheckMark.png') == old_tick:
        raise RuntimeError("The maintenance tool still shows the first release's tick image")
    if user_file.read_text() != 'keep the project\n':
        raise RuntimeError('In-place update changed an unrelated user file')


def second_update(
    target: Path, maintenance: Path, installed: Path, output: Path, options: dict
) -> None:
    """Update 26.17, which the released controller installed, to 26.18: app and tool change."""
    third = json.loads((output / 'update-26.18/installer.json').read_text())
    run([maintenance, '--set-temp-repository', third['repository_url'], *UPDATE], **options)
    if installed.read_text(encoding='utf-8') != 'third marker\n':
        raise RuntimeError('Maintenance tool did not apply the second component update')
    # 26.17's controller ran this update, so the macOS backup goes once it has succeeded.
    tool_replaced(target, third)
    if (target / 'MaintenanceTool.app.old-token').exists():
        raise RuntimeError('The second update left the mark of the replaced maintenance tool')
    maintenance_pages(target, output / 'update-26.18/source', first_release=False)
    # The tool keeps asking the repositories it was installed with (its own settings), and here
    # each release has a repository of its own: ask 26.18's, as a release replaces the one.
    nothing_offered(maintenance, options['env'], third['repository_url'])
    if (target / 'user-project.edi').read_text() != 'keep the project\n':
        raise RuntimeError('The second update changed an unrelated user file')


def interrupted_update(
    target: Path, maintenance: Path, installed: Path, output: Path, options: dict
) -> None:
    """Require a failed update to 26.18 to leave 26.17's tool and pages, and no 26.18 files.

    The update first undoes the operations 26.17's update saved, the macOS swap's included, then
    unpacks and swaps in the new tool before its failing operation, so the rollback has the swap
    to undo. On Linux the app component fails instead, there being no tool component. The
    Framework's rollback undoes only what this update did: the app files the saved operations
    removed stay removed and the app is no longer listed as installed (measured with IFW 4.11 on
    Linux), so the tool answers but has nothing left to update.
    """
    metadata = json.loads((output / 'online/installer.json').read_text())
    failing = json.loads((output / 'failing-26.18/installer.json').read_text())
    command = [maintenance, '--set-temp-repository', failing['repository_url'], *UPDATE]
    print('+', ' '.join(map(str, command)), '(expected to fail)', flush=True)
    result = subprocess.run(list(map(str, command)), check=False, **options)
    if result.returncode == 0:
        raise RuntimeError('The update meant to fail succeeded')
    left = installed.read_text(encoding='utf-8') if installed.is_file() else None
    print(f'protocol check: after the failed update the app marker is {left!r}', flush=True)
    if left not in {None, 'second marker\n'}:
        raise RuntimeError('The failed update left files of the 26.18 application')
    if SYSTEM in {'macos', 'windows'}:
        bundle = target / maintenance_tool_name()
        if not maintenance_tool_executable(bundle).is_file():
            raise RuntimeError('The failed update left no maintenance tool in place')
        if sha256(maintenance_tool_executable(bundle)) != metadata['maintenance_tool_sha256']:
            raise RuntimeError("The failed update did not leave 26.17's maintenance tool")
    if SYSTEM == 'macos' and (target / 'MaintenanceTool.app.new').exists():
        raise RuntimeError('The failed update left MaintenanceTool.app.new behind')
    # Signed, and on macOS no staged tool or backup left.
    verify_installed_maintenance_tool(target, metadata)
    maintenance_pages(target, output / 'online/source', first_release=False)
    nothing_offered(maintenance, options['env'])


def default_resource(target: Path) -> dict[str, bytes]:
    """The files of MaintenanceTool.dat's first segment, where the tool reads its pages."""
    dat = target / 'MaintenanceTool.dat'
    if not dat.is_file():
        raise RuntimeError('The installation has no MaintenanceTool.dat')
    return read_rcc(dat_resources(dat)[0])


def maintenance_pages(target: Path, source: Path, *, first_release: bool) -> None:
    """Require the installed tool's pages to be the ones the installer `source` was built with.

    The tool reads its configuration, control script and style sheet from the default resource,
    the first segment of MaintenanceTool.dat, and an update replaces that segment only with the
    MaintenanceTool.rcc the app component brings, which the Framework deletes once written. A
    2026.11 .dat holds no -r resources, so after an update the replacement must carry them too.
    """
    if (target / RESOURCE_NAME).exists():
        raise RuntimeError(f'The Framework left {RESOURCE_NAME} in the installation')
    files = default_resource(target)
    if 'installer-config/config.xml' not in files:
        raise RuntimeError('The default resource of MaintenanceTool.dat has no config.xml')
    config = ET.fromstring(files['installer-config/config.xml'])  # noqa: S314 - from binarycreator
    # The version tells two builds with the same controller apart.
    version = ET.parse(source / 'config/config.xml').getroot().findtext('Version')  # noqa: S314
    if config.findtext('Version') != version:
        raise RuntimeError(
            f'MaintenanceTool.dat holds the pages of {config.findtext("Version")}, not {version}'
        )
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
    released = control_script.decode('utf-8').replace('\r\n', '\n') == released_controller_text()
    if released != first_release:
        raise RuntimeError(
            f'The first release does not show the control script of {RELEASED_TAG}'
            if first_release
            else f'The maintenance tool still shows the control script of {RELEASED_TAG}'
        )
    if first_release:
        # binarycreator keeps the -r resources in a segment of their own, after the default one.
        resource_files(dat_files(target / 'MaintenanceTool.dat'), source, 'MaintenanceTool.dat')
        return
    resource_files(files, source, 'the default resource of MaintenanceTool.dat')


def resource_files(files: dict[str, bytes], source: Path, where: str) -> None:
    """Require the build's -r resources byte for byte in `files`, and no edi image besides."""
    resources = source / 'config/resources'
    translation = 'translations/ifw_en.qm'
    if files.get(translation) != (resources / translation).read_bytes():
        raise RuntimeError(f'The {translation} in {where} is not the one {source.parent.name} has')
    listed = set()
    for element in ET.parse(resources / 'resources.qrc').iter('file'):  # noqa: S314 - package.py
        name = element.get('alias', element.text)
        listed.add(name)
        if name not in files:
            raise RuntimeError(f'{where} has no {name}')
        if files[name] != (resources / element.text).read_bytes():
            raise RuntimeError(f'The {name} in {where} is not the one {source.parent.name} has')
    unlisted = sorted(name for name in files if name.startswith('edi/') and name not in listed)
    if unlisted:
        raise RuntimeError(f'{where} holds images {source.parent.name} does not list: {unlisted}')


def nothing_offered(maintenance: Path, env: dict, repository: str | None = None) -> None:
    """Require a successful update query with no update in it, from `repository` if given.

    A query that failed to fetch the repository ends with an error status and proves nothing.
    """
    temporary = ['--set-temp-repository', repository] if repository else []
    again = subprocess.run(
        [maintenance, *temporary, 'check-updates'],
        env=env, capture_output=True, text=True, timeout=60, check=False,
    )  # fmt: skip
    print(again.stdout + again.stderr, flush=True)
    if again.returncode != 0:
        raise RuntimeError('The second update query failed')
    if '<update ' in again.stdout:
        raise RuntimeError('The maintenance tool still offers an update')


def tool_beside_backup(target: Path, metadata: dict) -> None:
    """Require the update's tool in place with the macOS backup the released controller keeps."""
    bundle = target / maintenance_tool_name()
    check_maintenance_tool(bundle)
    if sha256(maintenance_tool_executable(bundle)) != metadata['maintenance_tool_sha256']:
        raise RuntimeError('The update did not put its maintenance tool in place')
    if (target / 'maintenancetool').exists():
        raise RuntimeError('The update left the shipped maintenance tool staged')
    if not (target / 'MaintenanceTool.app.old').is_dir():
        raise RuntimeError('The released controller leaves MaintenanceTool.app.old; none is there')
    if not (target / 'MaintenanceTool.app.old-token').is_file():
        raise RuntimeError('The kept MaintenanceTool.app.old has no mark beside it')


def tool_replaced(
    target: Path, metadata: dict, wait: float = 60, *, old_left: bool = False
) -> None:
    """Wait for the update's tool; `old_left` expects the macOS backup still beside it."""
    verify = tool_beside_backup if old_left else verify_installed_maintenance_tool
    deadline = time.monotonic() + wait
    while True:
        try:
            verify(target, metadata)
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

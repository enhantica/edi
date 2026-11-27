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
    VOICE_COMPONENT,
    VOICE_MODEL,
    add_maintenance_resource,
    build_maintenance_tool,
    clean_environment,
    installer_from_download,
    maintenance_item,
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
# The speech model's stand-in, in the voice component.
VOICE_MARKER = VOICE_MODEL / 'voice.txt'

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

# Run by that operation with the installation folder, the evidence file and the app marker's path
# in it: the top-level names, which of the marker and the macOS swap's files exist, the marker's
# text and the swap's mark, so the check can see the state the update failed in.
FAILURE_EVIDENCE = """cd "$1" || exit 1
{
    ls -A | sed 's/^/name /'
    for f in "$3" MaintenanceTool.app.old-token MaintenanceTool.app.new; do
        if [ -e "$f" ]; then printf 'exists %s\\n' "$f"; fi
    done
    if [ -f "$3" ]; then printf 'marker %s\\n' "$(cat "$3")"; fi
    if [ -f MaintenanceTool.app.old-token ]; then
        printf 'token %s\\n' "$(cat MaintenanceTool.app.old-token)"
    fi
} > "$2"
exit 1
"""

# Where that operation writes, in the protocol output folder.
FAILURE_EVIDENCE_NAME = 'failed update evidence.txt'

# The folder the tool component unpacks into, the Linux tool's runtime and the lock every writer
# of the tool's files takes (edi ADR-0108).
STAGING = 'maintenancetool'
RUNTIME = 'installer-runtime'
LOCK_NAME = '.MaintenanceTool.lock'

# IFW prints this once it has rolled a failed update back.
ROLLBACK_TEXT = 'update aborted!'

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


def failing_operation(evidence: Path, marker: Path) -> str:
    """The component script text that makes an update with it fail.

    Before failing, the operation writes what it finds in the installation to `evidence`, outside
    it, so the check can tell the update failed where intended and what the rollback undid.
    """
    if SYSTEM == 'windows':
        # Separate words: the tool quotes only the ones with spaces, and cmd.exe keeps a command
        # line that starts unquoted as it is. cd accepts the target's forward slashes.
        command = [
            'cmd.exe', '/c', 'cd', '/d', '@TargetDir@', '&&', 'dir', '/b', '/s',
            '>', str(evidence), '&', 'exit', '1',
        ]  # fmt: skip
    else:
        command = ['/bin/sh', '-c', FAILURE_EVIDENCE, 'sh', '@TargetDir@', str(evidence)]
        command.append(marker.as_posix())
    return FAILING_OPERATION % ', '.join(json.dumps(part) for part in command)


def failing_tool_script(evidence: Path, marker: Path) -> str:
    """The tool component's script with the failing operation after the macOS swap."""
    return maintenance_script() + failing_operation(evidence, marker)


def failing_app_resource(
    evidence: Path, marker: Path, source: Path, tools: Path, environment: dict | None
) -> None:
    """On Linux the app component's update fails: undoing it used to take the tool's runtime."""
    add_maintenance_resource(source, tools, environment)
    with (source / 'packages' / APP_COMPONENT / 'meta/installscript.qs').open(
        'a', encoding='utf-8'
    ) as script:
        script.write(failing_operation(evidence, marker))


def failure_evidence(path: Path, target: Path) -> dict:
    """Read what the failing operation found: paths below `target`, the marker and the mark.

    POSIX writes tagged lines; Windows writes the full paths dir /s lists, made relative here.
    """
    found = {'paths': set(), 'marker': None, 'token': None}
    prefix = str(target).replace('\\', '/').casefold() + '/'
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        tag, _, value = line.partition(' ')
        if tag in {'marker', 'token'}:
            found[tag] = value
        elif tag in {'name', 'exists'}:
            found['paths'].add(value)
        elif line.strip():
            entry = line.strip().replace('\\', '/')
            if entry.casefold().startswith(prefix):
                entry = entry[len(prefix) :]
            found['paths'].add(entry)
    return found


def found_path(found: dict, relative: str) -> bool:
    """Whether the failing operation saw `relative`, matched by its end if a path stayed full."""
    return any(path == relative or path.endswith('/' + relative) for path in found['paths'])


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
    # The marker stands in for the speech model, so every release below checks it against its own
    # pin.
    with patch('package.release_voice_pin', return_value=write_voice_marker(stage)):
        with (
            patch('package.repository_urls', return_value=(repository,)),
            patch('package.write_controller', released_controller),
            patch('package.write_resources', first_release_resources),
        ):
            offline = package_app(stage, tools, output / 'offline', '2026.11.31')
        if list((output / 'offline/source/packages').glob('*/data/**/' + RESOURCE_NAME)):
            raise RuntimeError(f'The first release ships {RESOURCE_NAME}, which 2026.11 did not')
        marker.write_text('second marker\n')
        # The new release's tool gets other bytes, so the update has a tool to replace. The Linux
        # tool component carries only the runtime and the Framework writes the tool from its
        # template (edi ADR-0091), so only macOS and Windows build one.
        tool_builds = SYSTEM in {'macos', 'windows'}
        new_tool = (
            build_maintenance_tool(tools, output / 'online tool', '1') if tool_builds else None
        )
        online = package_app(stage, tools, output / 'online', '26.17', repository, (), new_tool)
        for name in ('Installer.qs', 'resources/CheckMark.png'):
            first, new = (output / kind / 'source/config' / name for kind in ('offline', 'online'))
            if first.read_bytes() == new.read_bytes():
                raise RuntimeError(f'The first release and 26.17 have the same {name}')
        # 26.18 changes the app and the tool again. One build of it fails its update and the other
        # succeeds, each from a repository of its own.
        marker.write_text('third marker\n')
        third_tool = (
            build_maintenance_tool(tools, output / 'tool 26.18', '2') if tool_builds else None
        )
        failure = (output / FAILURE_EVIDENCE_NAME, marker.relative_to(stage))
        with (
            patch('package.maintenance_script', functools.partial(failing_tool_script, *failure))
            if tool_builds
            else patch(
                'package.add_maintenance_resource',
                functools.partial(failing_app_resource, *failure),
            )
        ):
            failing = output / 'failing-26.18'
            package_app(
                stage,
                tools,
                failing,
                '26.18',
                (failing / 'repository').as_uri() + '/',
                (),
                third_tool,
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
            kind,
            bootstrap,
            output,
            marker.relative_to(stage),
            assistant_marker.relative_to(stage),
        )
    (output / 'passed.json').write_text(
        json.dumps({'passed': True, 'transport': 'file', 'application_test': False}) + '\n'
    )


def write_voice_marker(stage: Path) -> dict:
    """Stage a small stand-in for the speech model and return its pin."""
    model = stage / VOICE_MARKER
    model.parent.mkdir(parents=True)
    model.write_text('optional voice marker\n', encoding='utf-8')
    return {'file': model.name, 'bytes': model.stat().st_size, 'sha256': sha256(model)}


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
            installed_voice = target / VOICE_MARKER
            if installed_assistant.exists() or installed_voice.exists():
                raise RuntimeError('Default installation selected an optional component')
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
                optional = [
                    (ASSISTANT_COMPONENT, installed_assistant, 'optional assistant marker\n'),
                    (VOICE_COMPONENT, installed_voice, 'optional voice marker\n'),
                ]
                for component, path, text in optional:
                    add_and_remove(maintenance, installed, component, path, text, kind, options)
        finally:
            run([maintenance, '--default-answer', '--confirm-command', 'purge'], **options)
        purged(target, installed)


def purged(target: Path, installed: Path) -> None:
    """Require the purge to take the app, the lock and the Linux runtime nothing else owns."""
    if installed.exists():
        raise RuntimeError('Maintenance tool left the component installed')
    for name in (LOCK_NAME, RUNTIME):
        if (target / name).exists():
            raise RuntimeError(f'The purge left {name} in the installation')


def add_and_remove(
    maintenance: Path,
    installed: Path,
    component: str,
    optional: Path,
    text: str,
    kind: str,
    options: dict,
) -> None:
    """Install and remove an optional component, leaving the application as it was."""
    final = 'third marker\n' if kind == 'offline' else 'second marker\n'
    maintenance_args = [maintenance, '--accept-licenses', '--default-answer', '--confirm-command']
    run([*maintenance_args, 'install', component], **options)
    if not optional.is_file() or optional.read_text(encoding='utf-8') != text:
        raise RuntimeError(f'Maintenance tool did not install {component}')
    run([*maintenance_args, 'remove', component], **options)
    if optional.exists() or installed.read_text(encoding='utf-8') != final:
        raise RuntimeError(f'Removing {component} changed the required application')


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
    if SYSTEM == 'macos':
        # What Finder leaves in a folder it showed; the owner's update kept the folder for it.
        staging = target / STAGING
        staging.mkdir(exist_ok=True)
        (staging / '.DS_Store').write_bytes(b'')
    # --verbose: the log says whether the tool component was updated.
    run([maintenance, *UPDATE], **options)
    if installed.read_text(encoding='utf-8') != 'second marker\n':
        raise RuntimeError('Maintenance tool did not apply the component update')
    # The update brings the newer release's signed tool along (edi ADR-0106). The Framework may
    # write the tool only once the updating process has ended, so the check waits for it a while,
    # and says what it found if it never comes. The released controller ran this update and has
    # no cleanup of its own: the new tool component's scripts must leave no backup and no staging
    # folder (edi ADR-0108).
    tool_replaced(target, new_metadata)
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
    tool_replaced(target, third)
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

    The update first undoes the operations 26.17's update saved, then unpacks the new files before
    its failing operation. On macOS and Windows the tool component fails, after the macOS swap, so
    the rollback has the swap to undo. On Linux the app component fails: undoing it used to take
    the tool's runtime. The Framework's rollback undoes only what this update did: the app files
    the saved operations removed stay removed and the app is no longer listed as installed
    (measured with IFW 4.11 on Linux), so the tool answers but has nothing left to update.
    """
    metadata = json.loads((output / 'online/installer.json').read_text())
    found = failed_update(target, maintenance, output, options)
    left = installed.read_text(encoding='utf-8') if installed.is_file() else None
    print(f'protocol check: after the failed update the app marker is {left!r}', flush=True)
    if left not in {None, 'second marker\n'}:
        raise RuntimeError('The failed update left files of the 26.18 application')
    rolled_back(target, found, output)
    if SYSTEM in {'macos', 'windows'}:
        bundle = target / maintenance_tool_name()
        if not maintenance_tool_executable(bundle).is_file():
            raise RuntimeError('The failed update left no maintenance tool in place')
        if sha256(maintenance_tool_executable(bundle)) != metadata['maintenance_tool_sha256']:
            raise RuntimeError("The failed update did not leave 26.17's maintenance tool")
    # Signed as shipped; on Linux the tool and every library of its runtime.
    verify_installed_maintenance_tool(target, metadata)
    maintenance_pages(target, output / 'online/source', first_release=False)
    nothing_offered(maintenance, options['env'])


def failed_update(target: Path, maintenance: Path, output: Path, options: dict) -> dict:
    """Run the update meant to fail; require IFW's rollback and return the failure evidence."""
    failing = json.loads((output / 'failing-26.18/installer.json').read_text())
    evidence = output / FAILURE_EVIDENCE_NAME
    if evidence.exists():
        raise RuntimeError(f'{evidence.name} exists before the update meant to fail')
    command = [maintenance, '--set-temp-repository', failing['repository_url'], *UPDATE]
    print('+', ' '.join(map(str, command)), '(expected to fail)', flush=True)
    result = subprocess.run(
        list(map(str, command)),
        env=options['env'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        errors='replace', timeout=options['timeout'], check=False,
    )  # fmt: skip
    # Kept in the installation's log with the rest of its output.
    options['stdout'].write(result.stdout)
    options['stdout'].flush()
    if result.returncode == 0:
        raise RuntimeError('The update meant to fail succeeded')
    if ROLLBACK_TEXT not in result.stdout.casefold():
        raise RuntimeError(f'The failed update never printed {ROLLBACK_TEXT!r}: no rollback ran')
    # Written by the failing operation only: the update failed there, after unpacking.
    if not evidence.is_file():
        raise RuntimeError('The update failed before its failing operation ran')
    found = failure_evidence(evidence, target)
    print(f'protocol check: the failing operation found {sorted(found["paths"])}', flush=True)
    return found


def rolled_back(target: Path, found: dict, output: Path) -> None:
    """Require the failing operation to have seen 26.18's files, and the rollback to undo them.

    The caller has already required the 26.18 app marker gone from the installation. The first
    update left no backup, mark or staging folder, so whatever the failing operation saw of them
    is this update's.
    """
    if SYSTEM == 'macos':
        # The swap ran before the failure: it marks the backup it keeps with its own token.
        if not found_path(found, 'MaintenanceTool.app.old-token') or found['token'] is None:
            raise RuntimeError('The update failed before the macOS swap kept the installed tool')
    elif SYSTEM == 'windows':
        # The tool component, which fails, comes after the app it depends on.
        if not found_path(found, STAGING + '/MaintenanceTool.exe'):
            raise RuntimeError('The update failed before it unpacked the 26.18 maintenance tool')
        windows_staging_rolled_back(target, output)
        return
    else:
        if found['marker'] != 'third marker':
            raise RuntimeError(f'The failing operation saw the app marker {found["marker"]!r}')
        # The runtime ships in the tool component, so undoing the app leaves it (edi ADR-0108);
        # the caller requires it complete.
        if RUNTIME not in found['paths']:
            raise RuntimeError(f'The failing operation saw no {RUNTIME}')
    # Without the swap's undo the 26.18 tool would be in place and 26.17's kept as .old.
    tool_files_settled(target)


def windows_staging_rolled_back(target: Path, output: Path) -> None:
    """Require the rollback to take the 26.18 tool it staged, and say whose tool is left if any.

    The Framework's undo of an unpack puts back a file it overwrote, so an earlier release's staged
    tool may come back; 26.18's must not stay.
    """
    releases = [('offline', 'the first release'), ('online', '26.17'), ('failing-26.18', '26.18')]
    owners = {
        json.loads((output / kind / 'installer.json').read_text())['maintenance_tool_sha256']: name
        for kind, name in releases
    }
    staging = target / STAGING
    staged = staging / 'MaintenanceTool.exe'
    owner = owners.get(sha256(staged), 'no release') if staged.is_file() else None
    print(
        f'protocol check: after the rollback {STAGING}/ holds '
        + (held(staging) if staging.is_dir() else 'nothing: it is absent')
        + (f", {owner}'s tool" if owner else ''),
        flush=True,
    )
    others = []
    if staging.is_dir():
        others = [path.name for path in staging.iterdir() if path != staged]
    if others:
        raise RuntimeError(f'The failed update left {others} in {STAGING}/')
    if owner == '26.18':
        raise RuntimeError(f'The failed update left the 26.18 maintenance tool in {STAGING}/')


def held(folder: Path) -> str:
    """Name what a leftover folder holds, with each tool's or file's hash, to say whose it is."""
    names = []
    for path in sorted(folder.iterdir()):
        is_tool = path.name == maintenance_tool_name()
        file = maintenance_tool_executable(path) if is_tool else path
        names.append(f'{path.name} (sha256 {sha256(file)})' if file.is_file() else path.name)
    return ', '.join(names) or 'nothing'


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


def tool_files_settled(target: Path) -> None:
    """Require no staging folder and no backup of the tool's swapped files (edi ADR-0108).

    Windows writes the installed tool from the staged one after the update ends, so its staging
    folder stays until the app's next start; verify_installed_maintenance_tool checks it there.
    """
    staging = target / STAGING
    if SYSTEM != 'windows' and staging.is_dir():
        raise RuntimeError(f'{STAGING}/ is left in the installation, holding {held(staging)}')
    if SYSTEM != 'windows' and staging.exists():
        raise RuntimeError(f'{STAGING} is left in the installation')
    item = maintenance_item()
    for suffix in ('.old', '.old-token', '.new') if item else ():
        if (target / (item + suffix)).exists():
            raise RuntimeError(f'{item}{suffix} is left in the installation')


def tool_replaced(target: Path, metadata: dict, wait: float = 60) -> None:
    """Wait for the update's tool in place, with no staging folder and no backup left."""
    deadline = time.monotonic() + wait
    while True:
        try:
            tool_files_settled(target)
            verify_installed_maintenance_tool(target, metadata, updated=True)
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

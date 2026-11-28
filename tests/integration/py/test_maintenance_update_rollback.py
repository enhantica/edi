# SPDX-License-Identifier: BSD-3-Clause
"""Maintenance tool rollback with independent release bytes and local payloads."""

import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools.installer import package

ROOT = Path(__file__).resolve().parents[3]
RELEASES = {
    'offline': b'original maintenance executable',
    'online': b'installed maintenance executable',
    'failing-26.18': b'new maintenance executable from the failed update',
}
APP = Path('bin/EasyDiffraction')
RUNTIME = Path('installer-runtime')
LIBRARY = RUNTIME / 'lib/libQt6Core.so.6'
REGISTER_OPERATIONS = """
const fs = require('node:fs');
const vm = require('node:vm');
const operations = [];
const installer = {
    isInstaller: () => true,
    isUpdater: () => false,
    installationFinished: {connect() {}}
};
const component = {createOperations() {}, addOperation: (...args) => operations.push(args)};
const scope = {installer, component, systemInfo: {kernelType: 'linux'}};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), scope);
new scope.Component().createOperations();
process.stdout.write(JSON.stringify(operations));
"""

# QtIFW 4.11.0 packagemanagercore_p.cpp, runPackageUpdater: installationStarted,
# beginInstallation, undo old Extract, unpack all new archives, rollback, installationFinished.
LEGACY_UPDATE = """
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {spawnSync} = require('node:child_process');
const [target, oldApp, packages, appMarker, appId, toolId] = process.argv.slice(1);
function signal() {
    const listeners = [];
    return {
        connect(owner, slot) {
            listeners.push(slot ? slot.bind(owner) : owner);
        },
        emit() { for (const slot of listeners) slot(); }
    };
}
const QInstaller = {Success: 0, Failure: 1, Running: 2, Canceled: 3};
const components = {};
const installer = {
    status: QInstaller.Running,
    installationStarted: signal(),
    installationFinished: signal(),
    isUpdater: () => true,
    isInstaller: () => false,
    isPackageManager: () => false,
    isMaintainer: () => true,
    value: key => ({TargetDir: target, os: 'x11'})[key] ?? '',
    componentByName: name => components[name],
    fileExists: file => fs.existsSync(file),
    interrupt() { this.status = QInstaller.Canceled; },
    execute(program, args) {
        const expand = value => value.replaceAll('@TargetDir@', target);
        const ran = spawnSync(expand(program), args.map(expand), {
            stdio: ['ignore', 'pipe', 'pipe'], encoding: 'utf8'
        });
        if (ran.error)
            throw new Error(`Could not launch ${program}: ${ran.error.code}`);
        if (ran.status !== 0)
            process.stderr.write(ran.stderr);
        return [ran.stdout, ran.status];
    }
};
function loadComponent(id, name) {
    const folder = path.join(packages, id);
    const script = path.join(folder, 'meta', name);
    if (!fs.existsSync(script))
        return null;
    const installed = id === appId;
    const component = {
        installed,
        isInstalled: () => installed,
        updateRequested: () => installed,
        installationRequested: () => !installed,
        installedVersion: installed ? '2026.11.27' : '',
        beginInstallation() {}
    };
    components[id] = component;
    const scope = {installer, component, QInstaller, systemInfo: {kernelType: 'linux'}};
    vm.runInNewContext(fs.readFileSync(script, 'utf8'), scope);
    return {callbacks: new scope.Component(), payload: path.join(folder, 'data')};
}
function undoExtract(source, destination) {
    for (const entry of fs.readdirSync(source, {withFileTypes: true})) {
        const from = path.join(source, entry.name);
        const to = path.join(destination, entry.name);
        if (!entry.isDirectory()) {
            fs.rmSync(to, {force: true});
            continue;
        }
        undoExtract(from, to);
        try { fs.rmdirSync(to); }
        catch (error) { if (!['ENOENT', 'ENOTEMPTY'].includes(error.code)) throw error; }
    }
}
const selected = [
    loadComponent(appId, 'installscript.qs'),
    loadComponent(toolId, 'maintenancescript.qs')
].filter(Boolean);
installer.installationStarted.emit();
for (const {callbacks} of selected)
    callbacks.beginInstallation?.();
if (installer.status !== QInstaller.Running)
    throw new Error('The update stopped before the injected failure');
const library = 'lib/libQt6Core.so.6';
const runtime = path.join(target, 'installer-runtime', library);
const backup = path.join(target, 'installer-runtime.old', library);
if (!fs.existsSync(backup) || !fs.readFileSync(backup).equals(fs.readFileSync(runtime))
    || !fs.existsSync(path.join(target, 'installer-runtime.old-token')))
    throw new Error('The updater must keep the released runtime before undoing its extraction');
if (!fs.existsSync(path.join(target, 'maintenance-update', '.claim')))
    throw new Error('The updater must claim staging before unpacking');
undoExtract(oldApp, target);
for (const {payload} of selected)
    fs.cpSync(payload, target, {recursive: true});
const extracted = fs.readFileSync(path.join(target, appMarker), 'utf8');
if (fs.existsSync(runtime))
    throw new Error('The released extraction must have removed the runtime before the failure');
for (const {payload} of [...selected].reverse())
    undoExtract(payload, target);
installer.status = QInstaller.Failure;
installer.installationFinished.emit();
process.stdout.write(extracted);
"""


@pytest.fixture
def windows_protocol(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'tools/installer'))
    protocol = importlib.import_module('protocol_check')
    monkeypatch.setattr(protocol, 'SYSTEM', 'windows')
    monkeypatch.setattr(importlib.import_module('package'), 'SYSTEM', 'windows')
    monkeypatch.delenv('EDI_CODESIGN', raising=False)
    monkeypatch.setattr(protocol, 'maintenance_pages', lambda *_args, **_kwargs: None)
    monkeypatch.setattr(protocol, 'nothing_offered', lambda *_args: None)
    return protocol


@pytest.mark.parametrize(
    ('observed_tool', 'staged_before', 'staged_after', 'error'),
    [
        (True, None, None, None),
        (True, 'online', 'online', None),
        (False, None, None, 'before it unpacked'),
        (True, None, 'failing-26.18', r'left .*26\.18.*MaintenanceTool\.update\.exe'),
    ],
    ids=['removed', 'previous-restored', 'failed-before-staging', 'new-tool-left-behind'],
)
def test_windows_rollback_requires_the_observed_new_tool_to_be_undone(
    windows_protocol, tmp_path, monkeypatch, observed_tool, staged_before, staged_after, error
):
    target = tmp_path / 'Program Files' / 'EasyDiffraction'
    target.mkdir(parents=True)
    tool = target / 'MaintenanceTool.exe'
    tool.write_bytes(RELEASES['online'])
    staged = target / 'MaintenanceTool.update.exe'
    if staged_before:
        staged.write_bytes(RELEASES[staged_before])
    before = hashlib.sha256(staged.read_bytes()).hexdigest() if staged.is_file() else None
    for release, content in RELEASES.items():
        (tmp_path / release).mkdir()
        (tmp_path / release / 'installer.json').write_text(
            json.dumps({'maintenance_tool_sha256': hashlib.sha256(content).hexdigest()}),
            encoding='utf-8',
        )

    evidence = tmp_path / 'failed-operation.txt'
    app = target / 'bin/EasyDiffraction.exe'
    unpacked = staged if observed_tool else target / 'maintenancetool' / tool.name
    unpacked.parent.mkdir(exist_ok=True)
    unpacked.write_bytes(RELEASES['failing-26.18' if observed_tool else 'online'])
    evidence.write_text(
        '\n'.join(str(path).replace('/', '\\') for path in (app, unpacked)) + '\n',
        encoding='utf-8',
    )
    found = windows_protocol.failure_evidence(evidence, target)
    found['staged_before'] = before
    if staged_after:
        staged.write_bytes(RELEASES[staged_after])
    else:
        staged.unlink(missing_ok=True)
    monkeypatch.setattr(windows_protocol, 'failed_update', lambda *_args: found)
    args = (target, tool, app, tmp_path, {'env': {}})
    if error:
        with pytest.raises(RuntimeError, match=error):
            windows_protocol.interrupted_update(*args)
    else:
        windows_protocol.interrupted_update(*args)
        assert tool.read_bytes() == RELEASES['online'], (
            'Rollback preserves the previously installed Windows Maintenance Tool bytes'
        )


def write_runtime(root, runtime_bytes):
    library = root / LIBRARY
    library.parent.mkdir(parents=True)
    library.write_bytes(runtime_bytes)
    (root / RUNTIME / 'dependencies.json').write_text(
        json.dumps({library.name: hashlib.sha256(runtime_bytes).hexdigest()}), encoding='utf-8'
    )


def packaged_source(tmp_path, version, runtime_bytes, monkeypatch):
    work = tmp_path / version
    stage = work / 'stage'
    (stage / APP).parent.mkdir(parents=True)
    (stage / APP).write_text(version, encoding='utf-8')
    assistant = stage / package.ASSISTANT_RUNTIME / 'assistant.txt'
    assistant.parent.mkdir(parents=True)
    assistant.write_bytes(b'independent assistant payload')
    write_runtime(work, runtime_bytes)

    monkeypatch.setattr(
        package,
        'linux_installer_runtime',
        lambda *_args: (work / 'installerbase', work / RUNTIME, {}),
    )
    output = work / 'package'
    package.package_app(stage, work / 'tools', output, version)
    return output / 'source/packages'


def install_linux_tool_runtime(packages, target):
    tool_component = packages / 'org.easydiffraction.app.maintenancetool'
    if not tool_component.is_dir():
        return
    shutil.copytree(tool_component / 'data', target, dirs_exist_ok=True)
    script = tool_component / 'meta/maintenancescript.qs'
    result = subprocess.run(
        ['node', '-e', REGISTER_OPERATIONS, script],
        capture_output=True,
        text=True,
        timeout=4,
        check=False,
    )
    assert result.returncode == 0, 'The shipped Linux component registers its install operations'
    operations = json.loads(result.stdout)
    assert len(operations) == 1 and operations[0][0] == 'Execute', (
        'Installing the tool component runs the emitted operation to put its runtime in place'
    )
    operation = operations[0]
    command = [arg.replace('@TargetDir@', str(target)) for arg in operation[1:]]
    installed = subprocess.run(command[: command.index('UNDOEXECUTE')], timeout=4, check=False)
    assert installed.returncode == 0, (
        'The emitted install operation puts the tool runtime in place'
    )


def remove_extracted_files(payload, target):
    """An Extract undo removes the files that operation put in the installation."""
    for entry in payload.rglob('*'):
        if entry.is_file():
            (target / entry.relative_to(payload)).unlink(missing_ok=True)


@pytest.fixture
def linux_packaging(tmp_path, monkeypatch):
    monkeypatch.setattr(package, 'SYSTEM', 'linux')
    monkeypatch.setattr(package, 'SUFFIX', '')
    monkeypatch.setattr(package, 'write_resources', lambda *_args: None)
    monkeypatch.setattr(package, 'run', lambda *_args, **_kwargs: None)
    download = tmp_path / 'installer-download'
    download.write_bytes(b'local installer transport marker')
    monkeypatch.setattr(package, 'deliver_installer', lambda *_args: download)


def maintenance_probe(target):
    tool = target / 'MaintenanceTool'
    tool.write_bytes(b'#!/bin/sh\nexec /bin/cat "${0%/*}/installer-runtime/lib/libQt6Core.so.6"\n')
    tool.chmod(0o755)
    return tool


@pytest.mark.skipif(
    sys.platform == 'win32', reason='Exercises the Linux POSIX installer operation'
)
@pytest.mark.usefixtures('linux_packaging')
def test_linux_tool_starts_with_its_original_runtime_after_the_app_update_is_undone(
    tmp_path, monkeypatch
):
    installed_runtime = b'runtime of the installed maintenance tool\n'
    installed_pkg = packaged_source(tmp_path, '26.17', installed_runtime, monkeypatch)
    incoming_pkg = packaged_source(tmp_path, '26.18', b'runtime from the update\n', monkeypatch)
    old_app = installed_pkg / package.APP_COMPONENT / 'data'
    new_app = incoming_pkg / package.APP_COMPONENT / 'data'
    target = tmp_path / 'installed app'
    shutil.copytree(old_app, target)
    install_linux_tool_runtime(installed_pkg, target)

    tool = maintenance_probe(target)
    tool_bytes = tool.read_bytes()
    before = subprocess.run([tool], capture_output=True, timeout=4, check=False)
    assert (before.returncode, before.stdout) == (0, installed_runtime), (
        'The starting Linux Maintenance Tool can load the original bundled runtime'
    )

    # IFW first undoes the installed app's saved extraction, then undoes the failed app update.
    # Only the app component ran at the point of failure in the Linux protocol. The original
    # runtime must survive both actions if its component, rather than the app, owns it.
    remove_extracted_files(old_app, target)
    shutil.copytree(new_app, target, dirs_exist_ok=True)
    assert (target / APP).read_text(encoding='utf-8') == '26.18', (
        'The new app was unpacked before the failure that triggers rollback'
    )
    remove_extracted_files(new_app, target)
    assert not (target / APP).exists(), 'The failed update rolls back the new app payload'
    assert tool.read_bytes() == tool_bytes and os.access(tool, os.X_OK), (
        'Rollback keeps the original Linux Maintenance Tool executable'
    )
    after = subprocess.run([tool], capture_output=True, timeout=4, check=False)
    assert (after.returncode, after.stdout) == (0, installed_runtime), (
        'After app rollback the Linux Maintenance Tool starts with its original bundled Qt runtime'
    )
    package.verify_installed_maintenance_tool(target, {})


@pytest.mark.skipif(
    sys.platform == 'win32', reason='Exercises the Linux POSIX installer operation'
)
@pytest.mark.usefixtures('linux_packaging')
def test_failed_first_linux_update_preserves_the_released_tools_runtime(tmp_path, monkeypatch):
    # v2026.11.27's package.py put installer-runtime in the app component's Extract.
    released_app = tmp_path / 'released app payload'
    (released_app / APP).parent.mkdir(parents=True)
    (released_app / APP).write_text('2026.11.27', encoding='utf-8')
    original_runtime = b'runtime of the released maintenance tool\n'
    write_runtime(released_app, original_runtime)

    incoming = packaged_source(tmp_path, '26.18', b'runtime from the update\n', monkeypatch)
    target = tmp_path / 'installed app'
    shutil.copytree(released_app, target)
    tool = maintenance_probe(target)
    tool_bytes = tool.read_bytes()
    before = subprocess.run([tool], capture_output=True, timeout=4, check=False)
    assert (before.returncode, before.stdout) == (0, original_runtime), (
        'The released Maintenance Tool starts before its first update'
    )

    result = subprocess.run(
        [
            'node', '-e', LEGACY_UPDATE, target, released_app, incoming,
            APP.as_posix(), package.APP_COMPONENT, 'org.easydiffraction.app.maintenancetool',
        ],
        capture_output=True,
        timeout=4,
        check=False,
    )  # fmt: skip
    assert (result.returncode, result.stdout) == (0, b'26.18'), (
        'The first update reaches the injected failure after extracting the new app'
        + result.stderr.decode(errors='replace')
    )
    assert (
        not (target / APP).exists()
        and tool.read_bytes() == tool_bytes
        and os.access(tool, os.X_OK)
    ), 'First-update rollback removes the new app and preserves the released executable and mode'
    after = subprocess.run([tool], capture_output=True, timeout=4, check=False)
    assert (after.returncode, after.stdout) == (0, original_runtime), (
        'A failed first update off 2026.11 leaves its tool able to load its original Qt runtime'
    )
    assert not any(
        (target / name).exists()
        for name in ('installer-runtime.old', 'installer-runtime.old-token', 'maintenance-update')
    ), 'Rollback consumes the runtime backup and releases the failed update staging'

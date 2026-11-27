# SPDX-License-Identifier: BSD-3-Clause
"""Desktop runtime payload boundaries from the installer contract."""

import importlib.util
import itertools
import shutil
from pathlib import Path
from xml.etree import ElementTree as ET  # noqa: S405 - installer-generated XML only

import pytest

ROOT = Path(__file__).resolve().parents[3]
INSTALLER = ROOT / 'tools/installer'
APP_COMPONENT = 'org.easydiffraction.app'
PROVIDERS = {'codex': 'ChatGPT', 'claude': 'Claude', 'copilot': 'GitHub Copilot'}


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, INSTALLER / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def put_payload(root, relative, content):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def runtime_path(provider, suffix=''):
    return Path('libexec/edi') / provider / f'{provider}{suffix}'


def test_each_provider_is_an_independent_installer_payload(tmp_path, monkeypatch):
    package = load_tool('package')
    monkeypatch.setattr(package, 'SYSTEM', 'windows')
    monkeypatch.setattr(package, 'write_resources', lambda *_args: None)
    stage = tmp_path / 'stage'
    payloads = {runtime_path(provider, '.exe'): provider.encode() for provider in PROVIDERS}
    app = Path('bin/EasyDiffraction.exe')
    put_payload(stage, app, b'application')
    for path, contents in payloads.items():
        put_payload(stage, path, contents)

    source, *_ = package.prepare_installer_source(
        stage, tmp_path, tmp_path / 'installer', '2026.11.27', tmp_path.as_uri(), (), 'preview'
    )
    packages = source / 'packages'
    app_payload = packages / APP_COMPONENT / 'data'
    assert (app_payload / app).read_bytes() == b'application', (
        'The desktop executable belongs to the required application component'
    )
    assert not any((app_payload / path).exists() for path in payloads), (
        'An unselected assistant runtime must never arrive in the required app payload'
    )

    owners = {}
    for path, contents in payloads.items():
        matches = [folder for folder in packages.iterdir() if (folder / 'data' / path).is_file()]
        assert len(matches) == 1, 'Each provider binary belongs to one installer component'
        (component,) = matches
        owners[path] = component.name
        assert (component / 'data' / path).read_bytes() == contents, (
            'Installer packaging must preserve the staged runtime bytes'
        )
        metadata = ET.parse(component / 'meta/package.xml')  # noqa: S314 - generated XML
        provider = path.parent.name
        assert PROVIDERS[provider] in (metadata.findtext('DisplayName') or ''), (
            'The component identifies its provider in the Maintenance Tool'
        )
        dependencies = (metadata.findtext('Dependencies') or '').split(',')
        assert [name.strip() for name in dependencies if name.strip()] == [APP_COMPONENT], (
            'An optional assistant can require the app, with no dependency on another assistant'
        )
        assert metadata.findtext('ForcedInstallation', 'false') == 'false', (
            'Each assistant component can be left unchecked'
        )
    assert len(set(owners.values())) == len(payloads), (
        'ChatGPT, Claude and GitHub Copilot have independently selectable components'
    )

    for count in range(len(payloads) + 1):
        for selection in itertools.combinations(payloads, count):
            install = tmp_path / ('install-' + '-'.join(path.stem for path in selection))
            shutil.copytree(app_payload, install)
            for path in selection:
                shutil.copytree(packages / owners[path] / 'data', install, dirs_exist_ok=True)
            assert {path for path in payloads if (install / path).exists()} == set(selection), (
                'Every installer selection delivers exactly the selected assistant runtimes'
            )


@pytest.mark.parametrize(
    ('system', 'suffix', 'magic'),
    [('windows', '.exe', b'MZ\0\0'), ('macos', '', b'\xcf\xfa\xed\xfe')],
)
def test_release_signing_preserves_vendor_binary_bytes(
    tmp_path, monkeypatch, system, suffix, magic
):
    monkeypatch.syspath_prepend(str(INSTALLER))
    build = load_tool('build')
    monkeypatch.setattr(build, 'SYSTEM', system)
    monkeypatch.setattr(build, 'macos_signing', lambda: system == 'macos')
    monkeypatch.setattr(build, 'windows_signing', lambda: system == 'windows')
    monkeypatch.setattr(build, 'macos_signing_args', lambda: ['--sign', 'test identity'])
    stage = tmp_path / 'stage'
    codex = put_payload(stage, runtime_path('codex', suffix), magic + b'codex')
    vendors = {
        put_payload(stage, runtime_path(provider, suffix), magic + provider.encode()): (
            magic + provider.encode()
        )
        for provider in ('claude', 'copilot')
    }

    def sign(path):
        path.write_bytes(path.read_bytes() + b'new signature')

    def codesign(command):
        if command[0] == 'codesign' and '--force' in command:
            sign(Path(command[-1]))

    monkeypatch.setattr(build, 'sign_windows', sign)
    monkeypatch.setattr(build, 'run', codesign)
    build.sign_release_executables(stage)

    assert codex.read_bytes() == magic + b'codexnew signature', (
        'The release signing path still reaches the existing Codex executable'
    )
    assert {path: path.read_bytes() for path in vendors} == vendors, (
        'Release signing must preserve the exact downloaded Claude and Copilot bytes'
    )

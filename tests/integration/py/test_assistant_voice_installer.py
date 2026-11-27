# SPDX-License-Identifier: BSD-3-Clause
"""Offline checks at the generated installer component boundary."""

import re
from pathlib import Path

import pytest
from defusedxml import ElementTree

from tools.installer import package

ROOT = Path(__file__).resolve().parents[3]
MODEL = Path('share/edi/voice/ggml-small-q5_1.bin')
VOICE_COMPONENT = 'org.easydiffraction.app.voice'
MODEL_BYTES = b'fixture bytes for the separately selectable model'
VOICE = re.compile(r'voice|speech|microphone', re.IGNORECASE)
ASSISTANT = re.compile(r'assistant|chatgpt|claude|copilot', re.IGNORECASE)


@pytest.fixture
def installer_source(tmp_path, monkeypatch):
    stage = tmp_path / 'stage'
    marker = stage / 'bin/EasyDiffraction'
    marker.parent.mkdir(parents=True)
    marker.write_bytes(b'base application')
    runtime = stage / package.ASSISTANT_RUNTIME
    runtime.mkdir(parents=True)
    (runtime / 'assistant.txt').write_bytes(b'assistant payload')
    bootstrap = tmp_path / 'installer-runtime'
    bootstrap.mkdir()
    monkeypatch.setattr(package, 'write_resources', lambda *_args: None)
    monkeypatch.setattr(
        package, 'linux_installer_runtime', lambda *_args: ('installerbase', bootstrap, None)
    )
    monkeypatch.setattr(package, 'macos_installer_template', lambda *_args: 'installerbase')

    def prepare(system, *, with_voice):
        monkeypatch.setattr(package, 'SYSTEM', system)
        if with_voice:
            source = stage / MODEL
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(MODEL_BYTES)
        prepared, *_ = package.prepare_installer_source(
            stage, tmp_path / 'tools', tmp_path / 'output', '26.18', None, (), 'testing'
        )
        return prepared / 'packages'

    return prepare


def component_metadata(packages):
    return {
        path.parents[1].name: ElementTree.parse(path).getroot()
        for path in packages.glob('*/meta/package.xml')
    }


@pytest.mark.parametrize('system', ['linux', 'macos', 'windows'])
def test_core_installer_prepares_without_a_voice_model(installer_source, system):
    packages = installer_source(system, with_voice=False)
    metadata = component_metadata(packages)
    assert package.APP_COMPONENT in metadata and package.ASSISTANT_COMPONENT in metadata, (
        'Without voice weights the base app and assistant remain installable'
    )
    assert not any(VOICE.search(item.findtext('DisplayName', '')) for item in metadata.values()), (
        'A build without voice weights cannot offer an empty voice component'
    )
    assert not list(packages.glob('*/data/**/ggml-*.bin')), (
        'A build without voice weights leaves no model in the installer payloads'
    )


@pytest.mark.parametrize('system', ['linux', 'macos', 'windows'])
def test_model_is_installed_only_with_the_opt_in_voice_component(installer_source, system):
    packages = installer_source(system, with_voice=True)
    metadata = component_metadata(packages)
    assert VOICE_COMPONENT in metadata, (
        'The model is offered as an independently selectable voice component'
    )
    item = metadata[VOICE_COMPONENT]
    assert item.findtext('Default', '').lower() == 'false', (
        'The voice component is unselected on a fresh installation'
    )
    assert item.findtext('ForcedInstallation', 'false').lower() == 'false', (
        'The Maintenance Tool can remove the optional voice component'
    )
    description = item.findtext('Description', '').strip()
    assert description and len(description.splitlines()) == 1, (
        'The voice component presents a one-line description'
    )
    model = packages / VOICE_COMPONENT / 'data' / MODEL
    assert list(packages.glob(f'*/data/**/{MODEL.name}')) == [model], (
        'Only the voice component carries the model at its installed path'
    )
    assert model.read_bytes() == MODEL_BYTES, (
        'The installer preserves the model bytes at the optional component boundary'
    )


def test_voice_choice_follows_all_assistant_choices():
    form = ROOT / 'tools/installer/AssistantForm.ui'
    tree = ElementTree.parse(form)
    boxes = tree.findall(".//widget[@class='QCheckBox']")
    choices = [
        ' '.join([box.get('name', ''), box.findtext("property[@name='text']/string", '')])
        for box in boxes
    ]
    voice = [index for index, label in enumerate(choices) if VOICE.search(label)]
    assistants = [
        index
        for index, label in enumerate(choices)
        if index not in voice and ASSISTANT.search(label)
    ]
    assert len(voice) == 1, 'The installer choices include one voice input checkbox'
    assert assistants and max(assistants) < voice[0], (
        'Voice input follows every AI assistant checkbox in the choices shown to the user'
    )
    checkbox = boxes[voice[0]]
    assert checkbox.findtext("property[@name='checked']/bool", 'false') == 'false', (
        'The voice checkbox starts unchecked on a fresh install'
    )
    row = next(
        (
            layout
            for layout in tree.findall('.//layout')
            if checkbox in layout.findall('item/widget')
        ),
        None,
    )
    assert row is not None and any(
        'size' in label.get('name', '').casefold()
        for label in row.findall("item/widget[@class='QLabel']")
    ), 'The voice checkbox shares its row with a component-size label'


def test_desktop_composer_registers_voice_controls_for_native_input():
    composer = (ROOT / 'app/qml/Components/AssistantComposer.qml').read_text(encoding='utf-8')
    controls = set(re.findall(r'objectName:\s*"([^"]+)"', composer))
    assert {'assistant.voice', 'assistant.voiceCancel'} <= controls, (
        'The native composer exposes microphone and recording cancellation controls'
    )

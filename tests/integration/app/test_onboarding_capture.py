"""Run the native documentation producer against the independent site consumer."""

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.onboarding.preview_consumer import (
    POPUP_FILL,
    WAVELENGTH,
    WAVELENGTH_SCENE,
    validate_bundle,
    validate_wavelength_commit,
)

ROOT = Path(__file__).resolve().parents[3]


def test_native_capture_is_accepted_by_the_preview_consumer():
    binary = Path(os.environ.get('EDI_DOCS_APP', ROOT / 'build/app/app/edi_app'))
    assert binary.is_file(), (
        'Capture compatibility requires the current native application artifact'
    )
    launcher = ROOT / 'tools/docs/capture-gui.sh'
    assert launcher.is_file(), (
        'Capture compatibility executes the source-tree documentation launcher'
    )
    bundle = Path(
        os.environ.get('EDI_ONBOARDING_CAPTURE_BUNDLE', ROOT / 'build/onboarding-capture')
    )
    assert (bundle / 'manifest.json').is_file(), (
        'The native capture prerequisite must produce a complete bundle through capture-gui.sh'
    )
    manifest, scenes = validate_bundle(bundle)
    ancestry = subprocess.run(
        ['git', 'merge-base', '--is-ancestor', manifest['source_revision'], 'HEAD'],
        cwd=ROOT,
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert ancestry.returncode == 0, (
        'The captured native source belongs to the current main-based implementation lineage'
    )
    for arguments in [
        [
            'git',
            'diff',
            '--quiet',
            manifest['source_revision'],
            'HEAD',
            '--',
            'app',
            'core',
            'tools/docs',
        ],
        ['git', 'diff', '--quiet', 'HEAD', '--', 'app', 'core', 'tools/docs'],
    ]:
        unchanged = subprocess.run(
            arguments, cwd=ROOT, capture_output=True, check=False, timeout=5
        )
        assert unchanged.returncode == 0, (
            'Native producer source must remain unchanged since the captured clean revision'
        )
    script = ROOT / 'app/docs/y2o3-spodi.js'
    assert manifest['script_sha256'] == hashlib.sha256(script.read_bytes()).hexdigest(), (
        'The captured walkthrough script matches the native plan from the checked source'
    )
    assert manifest['binary_sha256'] == hashlib.sha256(binary.read_bytes()).hexdigest(), (
        'The accepted capture belongs to the actual native application artifact under test'
    )
    assert manifest['status'] == 'complete' and scenes, (
        'The independently maintained preview consumer accepts the actual native exports'
    )
    assert any(
        item.get('options')
        for scene in scenes
        for item in scene['layout'].get('items', {}).values()
    ), 'The capture exports native selector choices used by the documentation reference'
    assert any(
        item.get('fontIcon') or item.get('icon') or item.get('keyIcon')
        for scene in scenes
        for item in scene['layout'].get('items', {}).values()
    ), 'The capture exports real control icons used by the documentation reference'


def test_published_onboarding_bundle_records_the_native_popup_commit():
    bundle = ROOT / 'website/surfaces/docs/assets/gui/y2o3'
    manifest, scenes = validate_bundle(bundle)
    assert (
        manifest['script_sha256']
        == hashlib.sha256((ROOT / 'app/docs/y2o3-spodi.js').read_bytes()).hexdigest()
    ), 'The published bundle must use the same walkthrough plan as the app'
    assert any(scene['id'] == WAVELENGTH_SCENE for scene in scenes), (
        'The published walkthrough includes the witnessed wavelength commit'
    )


@pytest.mark.parametrize(
    ('damage', 'message'),
    [
        ('missing-open', 'open the popup'),
        ('inline', 'open the popup'),
        ('wrong-order', 'open the popup'),
        ('missing-return', 'press Return'),
        ('prefixed-value', 'replace the value'),
        ('unchanged-field', 'display the committed replacement'),
        ('unsaved-value', 'persist the committed wavelength'),
    ],
)
def test_popup_commit_refuses_wrong_order_and_uncommitted_values(tmp_path, damage, message):
    value = '1.34791'
    tag = '_instrument.setup_wavelength'
    experiment = tmp_path / 'inputs/experiment.edi'
    checkpoint = tmp_path / 'checkpoints/starting/experiments/experiment.edi'
    for path in (experiment, checkpoint):
        path.parent.mkdir(parents=True)
        path.write_text(f'data_sample\n{tag} {value}\n', encoding='utf-8')

    def observed(actions):
        return {
            'inputs': {'experiment': {'file': experiment.relative_to(tmp_path).as_posix()}},
            'actions': [{'action': action, 'scene': WAVELENGTH_SCENE} for action in actions],
        }

    actions = [WAVELENGTH, POPUP_FILL + value, 'key:Return']
    field = {'label': value}
    scenes = [{'id': WAVELENGTH_SCENE, 'layout': {'items': {WAVELENGTH: field}}}]
    validate_wavelength_commit(tmp_path, observed(actions), scenes)
    if damage == 'missing-open':
        actions.pop(0)
    elif damage == 'inline':
        actions[1] = f'fill:{WAVELENGTH}={value}'
    elif damage == 'wrong-order':
        actions[1], actions[2] = actions[2], actions[1]
    elif damage == 'missing-return':
        actions.pop()
    elif damage == 'prefixed-value':
        actions[1] = POPUP_FILL + '1' + value
    elif damage == 'unchanged-field':
        field['label'] = '1'
    else:
        checkpoint.write_text(f'data_sample\n{tag} 1\n', encoding='utf-8')
    with pytest.raises(ValueError, match=message):
        validate_wavelength_commit(tmp_path, observed(actions), scenes)

"""Run the native documentation producer against the independent site consumer."""

import hashlib
import os
import subprocess
from pathlib import Path

from tests.fixtures.onboarding.preview_consumer import validate_bundle

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

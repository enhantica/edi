# SPDX-License-Identifier: BSD-3-Clause
"""The release run prepares the SmartScreen submission last, never failing the release."""

import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('smartscreen', ROOT / 'tools/release/smartscreen.py')
SMARTSCREEN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SMARTSCREEN)


def test_the_publish_job_ends_with_the_submission_and_cannot_fail_on_it():
    yaml = pytest.importorskip('yaml')
    workflow = yaml.safe_load((ROOT / '.github/workflows/release-publish.yml').read_text())
    steps = workflow['jobs']['publish']['steps']
    prepare, keep = steps[-2], steps[-1]
    assert prepare['name'] == 'Prepare the SmartScreen submission'
    assert 'tools/release/smartscreen.py' in prepare['run'] and '::warning::' in prepare['run']
    assert keep['uses'].startswith('actions/upload-artifact@')
    assert keep['with']['name'] == 'smartscreen-submission'
    assert prepare['continue-on-error'] is True and keep['continue-on-error'] is True


def publication(tmp_path, *, zipped):
    folder = tmp_path / 'publication'
    assets = folder / 'assets'
    assets.mkdir(parents=True)
    (folder / 'release.json').write_text(json.dumps({'version': '2026.11.23'}))
    name = 'EasyDiffraction-2026.11.23-windows-x86_64-online'
    if zipped:
        with zipfile.ZipFile(assets / f'{name}.zip', 'w') as archive:
            archive.writestr(f'{name}.exe', b'MZ installer')
            archive.writestr('BRANDING-LICENSE.txt', 'licence')
    else:
        (assets / f'{name}.exe').write_bytes(b'MZ installer')
    return folder


@pytest.mark.parametrize('zipped', [False, True])
def test_the_online_installer_and_the_steps_are_prepared(tmp_path, monkeypatch, zipped):
    summary = tmp_path / 'summary.md'
    monkeypatch.setenv('GITHUB_STEP_SUMMARY', str(summary))
    output = tmp_path / 'out'
    folder = publication(tmp_path, zipped=zipped)
    arguments = ['--publication', str(folder), '--repo', 'enhantica/edi', '--output', str(output)]
    monkeypatch.setattr('sys.argv', ['smartscreen.py', *arguments])
    SMARTSCREEN.main()
    installer = output / 'EasyDiffraction-2026.11.23-windows-x86_64-online.exe'
    assert installer.read_bytes() == b'MZ installer'
    text = (output / 'additional-information.txt').read_text()
    assert 'European Spallation Source ERIC (Lund, Sweden)' in text
    assert 'releases/tag/v2026.11.23' in text
    assert 'Copenhagen' not in text and 'Denmark' not in text
    steps = summary.read_text()
    for expected in (
        'https://www.microsoft.com/en-us/wdsi/filesubmission',
        'Microsoft Defender Smartscreen',
        'European Spallation Source ERIC',
        'Incorrectly detected as malware/malicious',
        'SmartScreen: unrecognized app',
        'only while a fresh download',
        text.strip(),
    ):
        assert expected in steps


def test_a_release_without_the_installer_is_refused_by_name(tmp_path):
    folder = tmp_path / 'publication'
    (folder / 'assets').mkdir(parents=True)
    with pytest.raises(RuntimeError, match='windows-x86_64-online'):
        SMARTSCREEN.find_installer(folder / 'assets', '2026.11.23', tmp_path / 'out')

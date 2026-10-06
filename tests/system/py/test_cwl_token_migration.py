"""The migration sweep must also reject newly introduced retired spellings."""

import shutil
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.cwl_family import profiles

ROOT = Path(__file__).resolve().parents[3]


def test_no_tracked_file_keeps_a_retired_cw_token():
    result = subprocess.run(
        [shutil.which('git'), 'ls-files', '-z'], cwd=ROOT, capture_output=True, check=True
    )
    paths = [ROOT / name.decode() for name in result.stdout.split(b'\0') if name]
    hits = profiles.migration_hits(paths, ROOT)
    assert not hits, (
        'Every tracked file outside the exact sealed pre-change capture '
        'must migrate retired CW tokens'
    )


def test_retired_token_scan_detects_each_planted_spelling(tmp_path):
    for index, token in enumerate(profiles.RETIRED):
        path = tmp_path / f'planted-{index}.edi'
        path.write_text(f'_peak.type {token}\n')
        assert profiles.retired_hits([path]) == [str(path)], (
            'The migration scan must fail when either retired token is planted in a new file'
        )


@pytest.mark.parametrize('escape', ['changed-input', 'extra-token', 'copied-path'])
def test_retained_capture_exception_requires_exact_bytes_and_location(tmp_path, escape):
    fixture = tmp_path / 'tests/fixtures/cwl_family'
    shutil.copytree(ROOT / 'tests/fixtures/cwl_family/rename_inputs', fixture / 'rename_inputs')
    shutil.copyfile(
        ROOT / 'tests/fixtures/cwl_family/rename-input-sha256.json',
        fixture / 'rename-input-sha256.json',
    )
    historical = fixture / 'rename_inputs/fcj/experiments/bank.edi'
    assert not profiles.migration_hits([historical], tmp_path), (
        'Only the exact retained historical FCJ input is exempt from the token migration'
    )
    if escape == 'changed-input':
        historical.write_text(historical.read_text().replace('.023', '.024', 1))
    elif escape == 'extra-token':
        historical.write_text(historical.read_text() + '\n' + profiles.RETIRED[1] + '\n')
    else:
        copied = fixture / 'rename_inputs/another.edi'
        shutil.copyfile(historical, copied)
        historical = copied
    assert profiles.migration_hits([historical], tmp_path) == [str(historical)], (
        'A changed vehicle, extra retired token or copied path '
        'cannot borrow the historical exemption'
    )

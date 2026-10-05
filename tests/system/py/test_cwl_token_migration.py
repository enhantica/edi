"""The migration sweep must also reject newly introduced retired spellings."""

import shutil
import subprocess
from pathlib import Path

from tests.fixtures.cwl_family import profiles

ROOT = Path(__file__).resolve().parents[3]


def test_no_tracked_file_keeps_a_retired_cw_token():
    result = subprocess.run(
        [shutil.which('git'), 'ls-files', '-z'], cwd=ROOT, capture_output=True, check=True
    )
    paths = [ROOT / name.decode() for name in result.stdout.split(b'\0') if name]
    hits = profiles.retired_hits(paths)
    assert not hits, (
        'Every tracked code, fixture, project and document must migrate retired CW tokens'
    )


def test_retired_token_scan_detects_each_planted_spelling(tmp_path):
    for index, token in enumerate(profiles.RETIRED):
        path = tmp_path / f'planted-{index}.edi'
        path.write_text(f'_peak.type {token}\n')
        assert profiles.retired_hits([path]) == [str(path)], (
            'The migration scan must fail when either retired token is planted in a new file'
        )

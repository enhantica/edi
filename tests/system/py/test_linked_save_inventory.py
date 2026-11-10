"""Linked file and scan inputs share the owner count, byte and preference rules."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.system.py import test_save_policy_continuations as policy

ROOT = Path(__file__).resolve().parents[3]
tutorial_observer = policy.tutorial_observer
REPRESENTATIONS = (
    'separate-powder',
    'separate-single-crystal-cwl',
    'separate-single-crystal-tof',
    'scan',
    'mixed',
)
BOUNDARIES = ('count-20', 'count-21', 'bytes-below', 'bytes-exact', 'bytes-above')


@pytest.mark.parametrize('representation', REPRESENTATIONS)
@pytest.mark.parametrize('boundary', BOUNDARIES)
@pytest.mark.parametrize('preference', ['unset', 'all', 'linked', 'ask'])
@pytest.mark.parametrize('location', ['existing', 'unsaved'])
def test_one_linked_inventory_controls_save_default_and_plan(
    tutorial_observer, tmp_path, representation, boundary, preference, location
):
    corpus = Path(
        os.environ.get('EDI_CRYSTA_CORPUS_ROOT', ROOT / 'build/crysta-src/tests/fitting')
    )
    source = (
        corpus / 'cosio-d20-scan-3f/project'
        if representation in {'scan', 'mixed'}
        else ROOT / 'tests/fixtures/loop_parameter_ids/line-segment'
    )
    form = (
        representation.removeprefix('separate-')
        if representation.startswith('separate-single-crystal')
        else 'powder-cwl'
    )
    result = subprocess.run(
        [
            tutorial_observer,
            str(source),
            f'linked-inventory/{representation}/{boundary}/{preference}/{location}/{form}',
        ],
        text=True,
        capture_output=True,
        timeout=25,
        check=False,
        env={
            **os.environ,
            'TMPDIR': str(tmp_path),
            'QT_QPA_PLATFORM': 'offscreen',
            'QT_QUICK_BACKEND': 'software',
            'EDI_ONLINE_SOURCES': f'cod={tmp_path.as_uri()};easydiffraction={tmp_path.as_uri()}',
        },
    )
    (tmp_path / 'observation.log').write_text(result.stdout + result.stderr)
    assert result.returncode == 0, (
        'The physical linked-inventory witness reaches its actual project model: ' + result.stderr
    )
    rows = json.loads(result.stdout.splitlines()[-1])
    assert len(rows) == 1, (
        'One complete linked inventory belongs to its declared project and preference'
    )
    row = rows[0]
    assert row['admitted'], (
        'Every declared separate or combined linked inventory opens and imports normally'
    )
    expected_count = 20 if boundary == 'count-20' else 21 if boundary == 'count-21' else 2
    assert row['files'] == expected_count, (
        'The independently authored source inventory reaches the declared file-count neighbor'
    )
    if boundary.startswith('bytes-'):
        offset = -1 if boundary == 'bytes-below' else 1 if boundary == 'bytes-above' else 0
        assert row['bytes'] == 50 * 1024 * 1024 + offset, (
            'The actual physical input bytes reach the exact owner size boundary and each neighbor'
        )
    plan = row['plan']
    assert plan['linked'], (
        'Linked inventory classification includes experiment files, scans and their combination'
    )
    assert plan['linkedFiles'] == expected_count, (
        'The common inventory counts every physical linked scan and experiment input exactly once'
    )
    assert plan['linkedBytes'] == row['bytes'], (
        'Save planning and default policy use the same independently counted physical bytes'
    )
    default = 'all' if expected_count <= 20 and row['bytes'] <= 50 * 1024 * 1024 else 'linked'
    expected = default if preference == 'unset' else preference
    assert row['mode'] == expected, (
        'An explicit per-project preference wins; an unset one uses the shared '
        'twenty-file and fifty-MiB rule'
    )
    assert plan['mode'] == expected, (
        'The actual staged-writer plan retains the same resolved project save policy'
    )

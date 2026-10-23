"""The published comparison keeps the same observations for every compared program.

The synthetic observations are all ten; only the final included point has calculated zero.
Consequently Rwp is 100/sqrt(N) percent and chi-square is 100/N. No engine produces this oracle.
"""

import math
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.fit_quality.inputs import comparison_case, matching_case

ROOT = Path(__file__).resolve().parents[3]


def command(root, *arguments):
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / 'tools/comparison/fit_quality.py'),
            '--root',
            str(root),
            *arguments,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )


def program_row(page, program):
    return next(line.split('|')[1:-1] for line in page.splitlines() if f'| {program} |' in line)


@pytest.mark.parametrize('banks', [['bank'], ['bank-a', 'bank-b']])
@pytest.mark.parametrize('missing', [0, 1, 3])
def test_published_comparison_never_silently_drops_a_required_observation(
    tmp_path, banks, missing
):
    case, count = comparison_case(tmp_path, banks, missing)
    result = command(tmp_path)
    page = (tmp_path / 'docs/user/guides/fit-quality.md').read_text()
    if result.returncode:
        assert 'FullProf' in result.stderr and 'Traceback' not in result.stderr, (
            'Missing reference observations must be refused with a FullProf diagnostic'
        )
        return
    edi = [value.strip() for value in program_row(page, 'edi')]
    dl = [value.strip() for value in program_row(page, 'diffraction-lib')]
    assert edi[2] == dl[2] == str(count), (
        'Reference gaps must never shrink the measured observation set of other programs'
    )
    assert edi[5] == dl[5] == f'{100 / math.sqrt(count):.2f}', (
        'The published weighted residual must retain the deliberately missed final observation'
    )
    assert 'not compared' in '|'.join(program_row(page, 'FullProf')), (
        'A FullProf profile missing an included observation must be marked as not compared'
    )
    assert (
        case in page
        and banks[-1] in page
        and any(word in page for word in ['missing', 'lacks', 'incomplete', 'matching'])
    ), 'A missing-reference mark must identify the affected case and bank'
    assert command(tmp_path, '--check').returncode == 0, (
        'The marked comparison must reproduce through the public check command'
    )


@pytest.mark.parametrize('control', ['rounded-complete', 'excluded-gap'])
def test_complete_or_excluded_reference_points_remain_comparable(tmp_path, control):
    excluded = control == 'excluded-gap'
    _, count = comparison_case(
        tmp_path, ['bank'], 3 if excluded else None, excluded=excluded, rounded=not excluded
    )
    result = command(tmp_path)
    assert result.returncode == 0, (
        'A complete rounded profile or excluded gap is a valid comparison'
    )
    page = (tmp_path / 'docs/user/guides/fit-quality.md').read_text()
    for program in ['edi', 'FullProf', 'diffraction-lib']:
        row = [value.strip() for value in program_row(page, program)]
        assert row[2] == str(count), 'Every compared program must use every included observation'
        expected = 0 if excluded else 100 / math.sqrt(count)
        assert row[5] == f'{expected:.2f}', (
            'Excluded observations and harmless coordinate rounding must preserve closed-form Rwp'
        )


@pytest.mark.parametrize('layout', ['single', 'joint-first', 'joint-last'])
@pytest.mark.parametrize(
    'scenario',
    [
        'dense-lower',
        'dense-middle',
        'dense-upper',
        'irregular-middle',
        'singleton-far',
        'duplicate-reference',
        'rounded-collision',
    ],
)
def test_ambiguous_reference_rows_cannot_manufacture_observation_coverage(
    tmp_path, layout, scenario
):
    case, count, bank = matching_case(tmp_path, layout, scenario)
    result = command(tmp_path)
    if result.returncode:
        assert 'fullprof' in result.stderr.lower() and 'Traceback' not in result.stderr, (
            'An ambiguous or absent reference observation needs a normal FullProf diagnostic'
        )
        return
    page = (tmp_path / 'docs/user/guides/fit-quality.md').read_text()
    for program in ['edi', 'diffraction-lib']:
        row = [value.strip() for value in program_row(page, program)]
        assert row[2] == str(count) and row[5] == f'{100 / math.sqrt(count):.2f}', (
            'Ambiguous reference coordinates cannot change the independent observation population'
        )
    assert 'not compared' in '|'.join(program_row(page, 'FullProf')), (
        'Each included observation needs an unambiguous unique FullProf row before comparison'
    )
    assert case in page and bank in page, (
        'A not-compared diagnostic must identify the case and affected bank'
    )
    assert command(tmp_path, '--check').returncode == 0, (
        'A marked ambiguous comparison must reproduce through the public check command'
    )


@pytest.mark.parametrize('layout', ['single', 'joint-first', 'joint-last'])
@pytest.mark.parametrize(
    'scenario',
    [
        'dense-exact',
        'rounded-complete',
        'singleton-rounded',
        'excluded-dense-gap',
        'excluded-claim',
    ],
)
def test_unique_rounded_or_excluded_observations_keep_their_closed_form_comparison(
    tmp_path, layout, scenario
):
    _, count, _ = matching_case(tmp_path, layout, scenario)
    result = command(tmp_path)
    assert result.returncode == 0, (
        'Complete distinguishable rounded grids and missing excluded rows remain comparable'
    )
    page = (tmp_path / 'docs/user/guides/fit-quality.md').read_text()
    for program in ['edi', 'FullProf', 'diffraction-lib']:
        row = [value.strip() for value in program_row(page, program)]
        assert row[2] == str(count) and row[5] == f'{100 / math.sqrt(count):.2f}', (
            'Unique reference associations must retain every included observation and its value'
        )
    assert command(tmp_path, '--check').returncode == 0, (
        'A complete comparison must reproduce through the public check command'
    )

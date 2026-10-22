"""The published comparison keeps the same observations for every compared program.

The synthetic observations are all ten; only the final included point has calculated zero.
Consequently Rwp is 100/sqrt(N) percent and chi-square is 100/N. No engine produces this oracle.
"""

import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BEGIN = '<!-- fit-quality tables: written by tools/comparison/fit_quality.py -->'
END = '<!-- end of the fit-quality tables -->'


def write(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def record(root, relative, value):
    write(root, relative, json.dumps(value))


def comparison_case(root, banks, missing, *, excluded=False, rounded=False):
    case = 'pd-neut-tof_coverage_scan' if len(banks) == 1 else 'pd-neut-tof_coverage_joint'
    write(
        root, 'docs/user/cli/projects.yml', f'projects:\n  - id: {case}\n    user-facing: true\n'
    )
    write(root, f'docs/user/cli/{case}/project/project.edi', '_metadata.purpose fitting\n')
    write(root, 'docs/user/guides/fit-quality.md', BEGIN + '\n' + END + '\n')
    comparison = f'knowledge/comparison/{case}'
    reference = f'knowledge/fitting/fullprof/{case}'
    metadata = {'banks': banks, 'n_free': 0, 'cells': {}}
    record(root, f'{comparison}/edi/reference.json', metadata)
    record(
        root, f'{comparison}/diffraction-lib/reference.json', metadata | {'model_compatible': True}
    )
    record(root, f'{reference}/reference.json', metadata)
    write(root, f'{reference}/fit.new', '')
    n_points = 0
    for bank_index, bank in enumerate(banks):
        rows = ['x,observed,calculated,sigma,included']
        fp = ['BEGIN']
        for index, x in enumerate([1.0, 2.0, 3.0, 4.0]):
            included = not (excluded and index == 3 and bank_index == len(banks) - 1)
            calculated = 0 if bank_index == len(banks) - 1 and index == 3 else 10
            rows.append(f'{x},10,{calculated},1,{int(included)}')
            n_points += included
            if bank_index == len(banks) - 1 and index == missing:
                continue
            fp.append(f'{x + (0.001 if rounded else 0):.3f} 10 {calculated} 0')
        for program in ['edi', 'diffraction-lib']:
            write(root, f'{comparison}/{program}/{bank}.csv', '\n'.join(rows) + '\n')
        name = 'fit.prf' if len(banks) == 1 else f'fit_{bank_index + 1}.prf'
        write(root, f'{reference}/{name}', '\n'.join([*fp, 'END']) + '\n')
    return case, n_points


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
    assert case in page and banks[-1] in page and 'lacks included points' in page, (
        'A missing-reference mark must identify the affected case and bank'
    )
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

"""/F6: independent named-bank records at the public persistence boundary."""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import edi
import pytest

from tests.integration.py.test_e05_t1_fit_result import projection
from tests.system.py.test_e05_t1_cli_fit_save import check_banks

ROOT = Path(__file__).resolve().parents[3]
CASE = next(
    row
    for row in json.loads((ROOT / 'tests/fixtures/e05_t1/cli.json').read_text())['cases']
    if row['id'] == 'pd-neut-tof_ncaf-wish-3bank_start-5'
)
REFERENCE = CASE['record']
TAGS = [
    '_fit_result_bank.experiment_id',
    '_fit_result_bank.n_data_points',
    '_fit_result_bank.prof_wr_factor',
    '_fit_result_bank.chi_square',
]


def bank_rows():
    names = sorted(
        key[5:-4] for key in REFERENCE if key.startswith('bank.') and key.endswith('.rwp')
    )
    return [
        [
            name,
            REFERENCE['bank.' + name + '.n_points'],
            REFERENCE['bank.' + name + '.rwp'],
            REFERENCE['bank.' + name + '.chi_square'],
        ]
        for name in names
    ]


def bank_text(rows, tags=TAGS):
    return '\nloop_\n' + '\n'.join(tags) + '\n' + ''.join(' '.join(row) + '\n' for row in rows)


def planted(tmp_path, rows):
    source = tmp_path / 'source'
    shutil.copytree(ROOT / CASE['path'], source)
    analysis = source / 'analysis/analysis.edi'
    scalar = ''.join(
        '_fit_result.' + name + ' ' + shlex.quote(value) + '\n'
        for name, value in projection(CASE).items()
    )
    analysis.write_text(analysis.read_text() + '\n' + scalar + bank_text(rows))
    return source


def test_independent_named_bank_loop_survives_public_load_save(tmp_path):
    source = planted(tmp_path, bank_rows())
    check_banks(source / 'analysis/analysis.edi', REFERENCE)
    result = subprocess.run(
        [sys.executable, '-m', 'edi', 'calc', str(source), '--dry'],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, ' gate 8 valid distinct banks pass the public CLI load surface'
    first = tmp_path / 'first'
    edi.Project.load(source).save_as(first)
    check_banks(first / 'analysis/analysis.edi', REFERENCE)
    second = tmp_path / 'second'
    edi.Project.load(first).save_as(second)
    check_banks(second / 'analysis/analysis.edi', REFERENCE)


@pytest.mark.parametrize(
    'mutation',
    [
        'swapped-metrics',
        'renamed-rwp',
        'renamed-chi',
        'wrong-identity',
        'duplicate-identity',
        'extra-bank',
        'missing-bank',
        'wrong-points',
    ],
)
def test_named_bank_oracle_refuses_field_identity_escapes(mutation, tmp_path):
    rows = bank_rows()
    tags = TAGS.copy()
    if mutation == 'swapped-metrics':
        for row in rows:
            row[2], row[3] = row[3], row[2]
    elif mutation == 'renamed-rwp':
        tags[2] = '_fit_result_bank.rwp'
    elif mutation == 'renamed-chi':
        tags[3] = '_fit_result_bank.reduced_chi_square'
    elif mutation == 'wrong-identity':
        rows[0][0] = 'wrong-bank'
    elif mutation == 'duplicate-identity':
        rows[1][0] = rows[0][0]
    elif mutation == 'extra-bank':
        rows.append(['extra-bank', *rows[0][1:]])
    elif mutation == 'missing-bank':
        rows.pop()
    else:
        rows[0][1] = str(int(rows[0][1]) + 1)
    path = tmp_path / 'analysis.edi'
    path.write_text(bank_text(rows, tags))
    with pytest.raises(AssertionError, match=' gate 8'):
        check_banks(path, REFERENCE)


@pytest.mark.parametrize('duplicate', ['identical', 'conflicting'])
@pytest.mark.parametrize('surface', ['python', 'cli'])
def test_duplicate_bank_identity_refused_without_rewriting(duplicate, surface, tmp_path):
    rows = bank_rows()
    repeated = rows[0].copy()
    if duplicate == 'conflicting':
        repeated[2], repeated[3] = '0.731', '987.125'
    rows.append(repeated)
    source = planted(tmp_path, rows)
    before = {
        path.relative_to(source): path.read_bytes() for path in source.rglob('*') if path.is_file()
    }
    if surface == 'python':
        with pytest.raises(
            (ValueError, RuntimeError), match=r'(?i)(duplicate|repeated|unique|identity)'
        ):
            edi.Project.load(source).save_as(tmp_path / 'saved')
        assert not (tmp_path / 'saved').exists(), (
            ' gate 8 ambiguous bank load never creates a normalized save'
        )
    else:
        result = subprocess.run(
            [sys.executable, '-m', 'edi', 'calc', str(source), '--dry'],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        assert result.returncode != 0, (
            ' gate 8 identical and conflicting duplicate banks refuse CLI load'
        )
        assert 'fit_result_bank' in result.stderr, ' gate 8 refusal names the result-bank category'
        assert any(
            word in result.stderr.lower()
            for word in ('duplicate', 'repeated', 'unique', 'identity')
        ), ' gate 8 public refusal names the ambiguous result-bank identity'
    assert {
        path.relative_to(source): path.read_bytes() for path in source.rglob('*') if path.is_file()
    } == before, ' gate 8 refusing duplicate identities leaves every original project byte intact'

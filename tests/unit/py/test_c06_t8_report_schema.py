"""ADR-0057's version projection preserves captured quantities and closed readers."""

from __future__ import annotations

import ast
import hashlib
import json
from itertools import pairwise
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
UNKNOWN = 'stopping_rule=none\nstopping_value=nan\nlast_shift_su=nan\n'


def _restore_capture(text):
    assert text.startswith('schema=9\n'), 'Current fixture projections must declare schema nine'
    if text.splitlines()[1] == 'record=fit':
        assert text.count(UNKNOWN) == 1, 'Unobserved stop metadata must be explicit once'
        rows = text.splitlines()
        index = next(i for i, line in enumerate(rows) if line.startswith('rwp='))
        assert rows[index + 1 : index + 4] == UNKNOWN.splitlines(), (
            'ADR-0057 places the three new rows directly after Rwp'
        )
        text = text.replace(UNKNOWN, '')
    return text.replace('schema=9\n', 'schema=8\n', 1)


def test_c06_t8_report_projection_preserves_all_captured_bytes():
    receipt = json.loads((ROOT / 'tests/fixtures/c06_t8/schema9-projection.json').read_text())
    assert receipt['authority'] == '01fd45799', 'Stop metadata must name its committed authority'
    paths = set((ROOT / 'tests/fixtures/e05_t1').glob('*.record'))
    paths.update((ROOT / 'tests/fixtures/e04_t11_wasm').rglob('*native-report.txt'))
    paths.update((ROOT / 'tests/fixtures/web_parallel').glob('*native-report.txt'))
    paths.add(ROOT / 'tests/fixtures/c11_t35_descent_selector/default-record-no-elapsed.txt')
    paths.update(ROOT / f'tests/fixtures/e05_t1/cli.{suffix}' for suffix in ('json', 'hpp'))
    paths.update(ROOT / f'tests/fixtures/e05_t1/{name}.json' for name in ('stops', 'refusal'))
    assert set(receipt['records']) == {p.relative_to(ROOT).as_posix() for p in paths}, (
        'The version projection must cover every current native and CLI capture exactly'
    )
    for name, hashes in receipt['records'].items():
        actual = (ROOT / name).read_bytes()
        assert hashlib.sha256(actual).hexdigest() == hashes['after_sha256'], (
            'The format projection must retain its exact reviewed output bytes'
        )
        text = actual.decode()
        if name.endswith('.json'):
            manifest = json.loads(text)
            mappings = (
                [case['record'] for case in manifest['cases']]
                if 'cases' in manifest
                else [manifest['record']]
            )
            for mapping in mappings:
                record = ''.join(k + '=' + v + '\n' for k, v in mapping.items())
                restored_record = dict(
                    line.split('=', 1) for line in _restore_capture(record).splitlines()
                )
                mapping.clear()
                mapping.update(restored_record)
            restored = json.dumps(manifest, indent=2) + '\n'
        elif name.endswith('.hpp'):
            unknown = ',{"stopping_rule","none"},{"stopping_value","nan"},{"last_shift_su","nan"}'
            assert '{"schema","8"}' not in text, 'Generated C++ fixtures must share schema nine'
            restored = text.replace(unknown, '').replace('{"schema","9"}', '{"schema","8"}')
        else:
            restored = _restore_capture(text)
        assert hashlib.sha256(restored.encode()).hexdigest() == hashes['before_sha256'], (
            'Removing only the version projection must recover every original captured byte'
        )


def _reader(path, names):
    tree = ast.parse((ROOT / path).read_text())
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {f.name for f in functions} == set(names), (
        'Every selected live reader must be exercised'
    )
    namespace = {'pairwise': pairwise}
    # Exercise the repository-owned readers without importing an unrelated native SDK.
    exec(compile(ast.Module(body=functions, type_ignores=[]), path, 'exec'), namespace)  # noqa: S102
    return namespace


@pytest.mark.parametrize(
    'filename', ['test_c09_t9_output_contract_and_cli.py', 'test_c09_t10_streamed_progress.py']
)
def test_c06_t8_current_readers_accept_nine_and_refuse_eight(filename):
    names = ['_parse_record']
    if filename == 'test_c09_t10_streamed_progress.py':
        names.append('_split_records')
    reader = _reader('tests/system/py/' + filename, names)
    wire = (
        'schema=9\nrecord=progress\niter=1\nrwp=0.125\nreduced_chi_square=2.5\nelapsed_ms=1.000\n'
    )
    _, values = reader['_parse_record'](wire)
    assert values['schema'] == '9', 'The live record reader must accept the new contract version'
    with pytest.raises(AssertionError):
        reader['_parse_record'](wire.replace('schema=9', 'schema=8'))
    if '_split_records' in reader:
        assert reader['_split_records'](wire + wire) == [wire, wire], (
            'The stream boundary must follow the current version without dropping records'
        )

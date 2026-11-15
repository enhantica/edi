"""Capture exact selector parity pins without replacing the historical records."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from tests.conftest import calculator_load_warning, corpus_case_dir, crysta_reference_prefix

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent


def fields(raw):
    return dict(line.split('=', 1) for line in raw.splitlines())


def ladder_history(current):
    old = (
        ROOT / 'tests/fixtures/c11_t35_descent_selector/default-record-no-elapsed.txt'
    ).read_text()
    before, after = fields(old), fields(current)
    changes = {key: [before[key], after[key]] for key in before if before[key] != after[key]}
    assert before.keys() == after.keys(), (
        'The historical ladder retains every report field and its order'
    )
    assert set(changes) <= {
        'stopping_rule',
        'last_shift_su',
        'unevaluable_trials',
        'terminal_unevaluable_trials',
    }, (
        'Only truthful terminal metadata and the damping-restart trial counters may differ in '
        'the retained ladder record'
    )
    return {
        'historical_sha256': hashlib.sha256(old.encode()).hexdigest(),
        'changes': changes,
    }


def quantity_changes(current, expected, prefix, args, selected):
    changes = {}
    engine = subprocess.run(
        [str(prefix / 'bin/crysta'), *args], text=True, capture_output=True, check=True
    )
    actual = fields(current)
    independent = fields(engine.stdout)
    variant = 'multistart-prune' if selected == 'fast_descent_and_ladder' else 'fast-descent'
    for key, spec in expected[variant]['quantities'].items():
        value = float(actual[key])
        assert value == float(independent[key]), (
            'Current edi numerical pins must equal the matching independent engine CLI exactly'
        )
        bound = max(spec['tol_abs'] or 0, (spec['tol_rel'] or 0) * abs(spec['value']))
        assert abs(value - spec['value']) <= bound, (
            'The capture must stay inside every unchanged engine corpus reference or regression '
            'bound'
        )
        if value != spec['value']:
            assert spec['kind'] == 'regression-pin', (
                'An independent correctness reference cannot be re-pinned'
            )
            changes[key] = [spec['value'], value]
    return changes


def main():
    source = corpus_case_dir('cosio-d20-s1')
    expected_bytes = (source / 'expected.json').read_bytes()
    expected = json.loads(expected_bytes)['variants']
    prefix = crysta_reference_prefix()
    receipt = {
        'claim': 'Current exact CLI parity regression pins; original engine corpus and '
        'historical record remain immutable',
        'engine_sha': (prefix / '.crysta-sha').read_text().strip(),
        'engine_cli_sha256': hashlib.sha256((prefix / 'bin/crysta').read_bytes()).hexdigest(),
        'corpus_expected_sha256': hashlib.sha256(expected_bytes).hexdigest(),
        'records': {},
    }
    with tempfile.TemporaryDirectory(
        prefix='selector-records-', dir=os.environ.get('TMPDIR')
    ) as work:
        for selected in ('ladder', 'fast_descent', 'fast_descent_and_ladder'):
            project = Path(work) / selected
            shutil.copytree(source / 'project', project)
            analysis = project / 'analysis/analysis.edi'
            text = re.sub(r'(?m)^_minimizer\.descent[^\n]*\n?', '', analysis.read_text())
            analysis.write_text(text + '\n_minimizer.descent ' + selected + '\n')
            args = ['fit', str(project), '--dry', '--verbosity', 'compact']
            edi = subprocess.run(
                [sys.executable, '-m', 'edi', *args, '--report', 'machine'],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            )
            assert edi.stderr == calculator_load_warning(project), (
                'The capture permits only the declared unsupported-calculator warning'
            )
            lines = edi.stdout.splitlines()
            assert sum(line.startswith('elapsed_ms=') for line in lines) == 1, (
                'The real CLI capture must contain exactly one wall-time row'
            )
            current = (
                '\n'.join(
                    line
                    for line in lines
                    if not line.startswith(('elapsed_ms=', 'x-edi.correlations='))
                )
                + '\n'
            )
            row = {'record': current, 'quantity_changes': {}}
            if selected == 'ladder':
                row.update(ladder_history(current))
            else:
                row['quantity_changes'] = quantity_changes(
                    current, expected, prefix, args, selected
                )
            receipt['records'][selected] = row
    (HERE / 'selector-current.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()

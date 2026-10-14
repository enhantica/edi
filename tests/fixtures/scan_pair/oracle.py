"""Validate matched inputs and independent Start-to-reset measurements."""

import math
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

BASELINE = {'edi': '2e04556f', 'crysta': 'fb153aeb'}
BOUND = 1.05
PAIRS = 5
SPREAD = 0.03


def measurement(run, count=162):
    receipt = run['receipt']
    assert receipt['kind'] == 'normal-app', 'Performance must observe the normal delivered app'
    assert all(len(receipt[k]) == 64 for k in ('binary_sha256', 'observer_sha256')), (
        'The executed binary and shared DemoDriver instrumentation must have build digests'
    )
    assert run['scenario'] == 'perf-162f' and run['command'] == [
        '--demo',
        '--demo-only',
        'perf-162f',
    ], 'Timing must execute the shared complete adaptive scan and Reset scenario'
    assert run['returncode'] == 0, 'The real driver must accept all fitted files and settled Reset'
    assert len(run['files']) == count and len(set(run['files'])) == count, (
        'The timing subject must retain the independently counted 162-file input'
    )
    rows = [line.split('\t') for line in run['timings_tsv'].splitlines()]
    assert len(rows) == 2 and all(len(row) == 3 for row in rows), (
        'Shared output must contain exactly fit and Reset, with no empty or partial evidence'
    )
    assert [(row[0], row[1]) for row in rows] == [('perf-162f', 'fit'), ('perf-162f', 'reset')], (
        'Both actual Start-to-finished and Reset intervals must be captured in order'
    )
    milliseconds = [float(row[2]) for row in rows]
    assert (
        all(math.isfinite(value) and value >= 0 for value in milliseconds) and milliseconds[0] > 0
    ), 'Both recorded intervals must be finite and fit must actually take positive time'
    start, finish = run['process_started_ns'], run['process_finished_ns']
    assert type(start) is int and type(finish) is int and 0 <= start < finish, (
        'Caller monotonic process boundaries must establish actual back-to-back execution'
    )
    assert sum(milliseconds) * 1000000 <= finish - start, (
        'Fit and Reset intervals must fit inside the independently observed process lifetime'
    )
    return sum(milliseconds) / 1000


def paired(document, expected_context):
    assert document['schema'] == 1, 'Paired timing evidence must use the declared schema'
    assert document['context'] == expected_context, (
        'A timing verdict must bind the current CI run, attempt and source head'
    )
    runs = document['pairs']
    assert len(runs) == PAIRS, 'The performance verdict requires all five fresh back-to-back pairs'
    baseline, candidate = [], []
    for index, pair in enumerate(runs):
        expected_order = ['baseline', 'candidate'] if index % 2 == 0 else ['candidate', 'baseline']
        assert pair['order'] == expected_order, 'Pair order must alternate to expose host drift'
        left, right = pair['baseline'], pair['candidate']
        assert left['host'] == right['host'] == document['host'], (
            'Both apps in every pair must run on the same actual host'
        )
        assert left['environment'] == right['environment'] == document['environment'], (
            'Paired apps must have identical worker settings and runtime environment'
        )
        assert left['input_sha256'] == right['input_sha256'] == document['input_sha256'], (
            'Paired apps must fit identical input bytes, not their different example copies'
        )
        assert left['files'] == right['files'] == document['files'], (
            'Every pair must fit the same independently enumerated file list'
        )
        for product, prefix in BASELINE.items():
            assert left['receipt'][product + '_commit'].startswith(prefix), (
                'The reference must be the declared merge, never the slower later main build'
            )
        assert right['receipt']['edi_commit'] == expected_context['head'], (
            'The measured candidate must be compiled from the current source head'
        )
        assert left['receipt']['observer_sha256'] == right['receipt']['observer_sha256'], (
            'Both apps must use identical timing instrumentation'
        )
        assert left['receipt']['binary_sha256'] != right['receipt']['binary_sha256'], (
            'A reference binary must not be reused as the candidate measurement'
        )
        first, second = (pair[name] for name in expected_order)
        assert first['process_finished_ns'] < second['process_started_ns'], (
            'A back-to-back pair must never run its apps concurrently'
        )
        b, c = measurement(left), measurement(right)
        baseline.append(b)
        candidate.append(c)
    for values in (baseline, candidate):
        assert (max(values) - min(values)) / statistics.median(values) <= SPREAD, (
            'Noisy paired timing is inconclusive and cannot produce a green 5% verdict'
        )
    # Reuse the shared comparison algorithm after proving completeness.
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'total.tsv'
        path.write_text(
            ''.join(
                f'{name}\tfit-and-reset\t{seconds}\n'
                for name, values in (('base', baseline), ('fixed', candidate))
                for seconds in values
            )
        )
        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name('compare.py')), str(path), str(BOUND)],
            capture_output=True,
            text=True,
            check=False,
        )
    assert result.returncode == 0, (
        'Adaptive 162-file Start-through-Reset time must be within 5% of the reference: '
        + result.stdout
    )
    return statistics.median(candidate) / statistics.median(baseline)

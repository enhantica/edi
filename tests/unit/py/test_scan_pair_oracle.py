"""Logical timing controls exercise identity, completeness, reset and the unchanged bound."""

import copy

import pytest

from tests.fixtures.scan_pair.oracle import paired

CONTEXT = {'head': 'c' * 40, 'run_id': '123', 'attempt': '1'}


def sample_run(name, start, seconds):
    files = [f'{index}.dat' for index in range(162)]
    receipt = {
        'kind': 'normal-app',
        'binary_sha256': ('a' if name == 'baseline' else 'b') * 64,
        'observer_sha256': 'd' * 64,
        'edi_commit': '2e04556f' + '0' * 32 if name == 'baseline' else CONTEXT['head'],
        'crysta_commit': 'fb153aeb' + '0' * 32,
    }
    return {
        'receipt': receipt,
        'files': files,
        'host': {'node': 'same-host'},
        'environment': {'OMP_NUM_THREADS': '1'},
        'input_sha256': 'e' * 64,
        'process_started_ns': start,
        'process_finished_ns': start + int((seconds + 0.1) * 1e9),
        'scenario': 'perf-162f',
        'command': ['--demo', '--demo-only', 'perf-162f'],
        'returncode': 0,
        'timings_tsv': f'perf-162f\tfit\t{seconds * 1000 - 10}\nperf-162f\treset\t10\n',
    }


def document(ratio=1.04):
    pairs = []
    for index in range(5):
        order = ['baseline', 'candidate'] if index % 2 == 0 else ['candidate', 'baseline']
        pair = {'order': order}
        start = (index + 1) * 10000000000
        for name in order:
            pair[name] = sample_run(name, start, 1 if name == 'baseline' else ratio)
            start = pair[name]['process_finished_ns'] + 1
        pairs.append(pair)
    return {
        'schema': 1,
        'context': CONTEXT,
        'host': {'node': 'same-host'},
        'environment': {'OMP_NUM_THREADS': '1'},
        'input_sha256': 'e' * 64,
        'files': pairs[0]['baseline']['files'],
        'pairs': pairs,
    }


@pytest.mark.parametrize('ratio', [1.0, 1.05])
def test_paired_scan_bound_accepts_only_complete_matching_evidence_at_the_boundary(ratio):
    assert paired(document(ratio), CONTEXT) == pytest.approx(ratio), (
        'The independent paired comparator must retain the inclusive unchanged 1.05 boundary'
    )


@pytest.mark.parametrize(
    'escape',
    [
        'slower',
        'wrong-baseline',
        'wrong-head',
        'wrong-run',
        'wrong-host',
        'wrong-input',
        'missing-pair',
        'missing-file',
        'no-reset',
        'refused-work',
        'empty-evidence',
        'nonfinite',
        'concurrent',
        'unbound-clock',
        'different-observer',
        'noisy',
        'wrong-command',
    ],
)
def test_paired_scan_oracle_refuses_each_ordinary_measurement_escape(escape):
    value = copy.deepcopy(document())
    pair = value['pairs'][0]
    candidate = pair['candidate']
    if escape == 'slower':
        value = document(1.050001)
    elif escape == 'wrong-baseline':
        pair['baseline']['receipt']['edi_commit'] = 'b' * 40
    elif escape == 'wrong-head':
        candidate['receipt']['edi_commit'] = 'a' * 40
    elif escape == 'wrong-run':
        value['context'] = dict(CONTEXT, run_id='122')
    elif escape == 'missing-pair':
        value['pairs'].pop()
    else:
        mutate_candidate(candidate, pair['baseline'], escape)
    with pytest.raises(AssertionError):
        paired(value, CONTEXT)


def mutate_candidate(candidate, baseline, escape):
    if escape == 'wrong-host':
        candidate['host'] = {'node': 'other-host'}
    elif escape == 'wrong-input':
        candidate['input_sha256'] = 'f' * 64
    elif escape == 'missing-file':
        candidate['files'] = candidate['files'][:-1]
    elif escape == 'no-reset':
        candidate['timings_tsv'] = candidate['timings_tsv'].splitlines()[0] + '\n'
    elif escape == 'refused-work':
        candidate['returncode'] = 1
    elif escape == 'empty-evidence':
        candidate['timings_tsv'] = ''
    elif escape == 'nonfinite':
        candidate['timings_tsv'] = 'perf-162f\tfit\tnan\nperf-162f\treset\t10\n'
    elif escape == 'concurrent':
        candidate['process_started_ns'] = baseline['process_started_ns']
    elif escape == 'unbound-clock':
        candidate['process_finished_ns'] = candidate['process_started_ns'] + 1
    elif escape == 'different-observer':
        candidate['receipt']['observer_sha256'] = 'f' * 64
    elif escape == 'noisy':
        candidate['timings_tsv'] = 'perf-162f\tfit\t1070\nperf-162f\treset\t10\n'
    else:
        candidate['command'] = ['--demo', '--demo-only', 'perf-control-partial']

"""I24: elapsed engine time, alternating repetitions and unchanged inputs."""

import copy
import json
import sys
from decimal import Decimal

import pytest

from tests.fixtures.c34_t28_performance import generate_project, measure


def record(elapsed):
    return measure.read_record(
        'record=fit\nstatus=done\nconverged=true\niterations=9\nn_free=193\nn_points_fitted=18973\n'
        'reduced_chi_square=9.497530558\nelapsed_ms=' + str(elapsed)
    )


def rows():
    return [
        {'repetition': rep, 'repo': repo, 'record': record(elapsed)}
        for rep, left, right in ((1, 4000, 5200), (2, 3000, 3900), (3, 5000, 6500))
        for repo, elapsed in (('crysta', left), ('edi', right))
    ]


def test_performance_bound_uses_the_engine_medians_and_includes_its_endpoint():
    result = measure.compare(rows())
    assert result['median_engine_ms'] == {'crysta': 4000, 'edi': 5200}, (
        ' I24 compare three engine observations, not process wall time or the best run'
    )
    assert result['within_bound'], ' I24 the stated 1.3x bound includes its endpoint'
    slower = rows()
    for row in slower:
        if row['repo'] == 'edi':
            row['record']['elapsed_ms'] = str(float(row['record']['elapsed_ms']) + 1)
    assert not measure.compare(slower)['within_bound'], (
        ' I24 a median even just above the bound cannot count as green'
    )


@pytest.mark.parametrize('damage', ['order', 'missing', 'duplicate', 'work', 'objective'])
def test_timing_comparison_refuses_unmatched_or_non_alternating_work(damage):
    sample = copy.deepcopy(rows())
    if damage == 'order':
        sample[1], sample[2] = sample[2], sample[1]
    elif damage == 'missing':
        sample.pop()
    elif damage == 'duplicate':
        sample[-1] = sample[1]
    elif damage == 'work':
        sample[3]['record']['n_free'] = '192'
    else:
        sample[3]['record']['reduced_chi_square'] = '12.5'
    with pytest.raises(ValueError, match=r'alternating|different fit'):
        measure.compare(sample)


@pytest.mark.parametrize('value', ['nan', 'inf', '-1', '0'])
def test_invalid_engine_time_cannot_be_a_fast_result(value):
    with pytest.raises(ValueError, match='engine metric'):
        record(value)


def test_repeated_machine_time_refuses_instead_of_selecting_a_favorable_value():
    with pytest.raises(ValueError, match='duplicate'):
        measure.read_record('elapsed_ms=100\nelapsed_ms=1')


def test_project_bytes_and_three_sigma_transform_have_independent_provenance():
    data = json.loads((measure.HERE / 'project-provenance.json').read_text())
    assert measure.hashes(measure.HERE / 'project') == data['project_sha256'], (
        ' I24 all alternating executions must consume the same committed project bytes'
    )
    assert (
        len([name for name in data['shifted_tokens'] if name.startswith('experiments/')]) == 5
    ), ' I24 the independent timing witness retains all five TOF banks'
    token = generate_project.NUMBER.fullmatch('12.34(5)')
    shifted = generate_project.shift(token)
    assert Decimal(shifted.split('(')[0]) - Decimal('12.34') == Decimal('0.15'), (
        ' I24 the visible input perturbation is three uncertainties at decimal scale'
    )
    scientific = generate_project.shift(generate_project.NUMBER.fullmatch('1.25(2)e3'))
    assert scientific == '1.31(2)e3', (
        ' I24 the input transformation preserves a nontrivial exponent and uncertainty'
    )


def timing_commands(tmp_path, damage='none'):
    """Separate processes expose exit status and mutation, not just parsed dictionaries."""
    script = tmp_path / 'engine_control.py'
    trace = tmp_path / 'executions.jsonl'
    script.write_text("""import hashlib, json, pathlib, sys
repo, project, trace, damage = sys.argv[1:]
project, trace = pathlib.Path(project), pathlib.Path(trace)
files = {str(p.relative_to(project)): hashlib.sha256(p.read_bytes()).hexdigest()
         for p in sorted(project.rglob('*')) if p.is_file()}
prior = trace.read_text().splitlines() if trace.exists() else []
repetition = 1 + sum(json.loads(row)['repo'] == repo for row in prior)
with trace.open('a') as stream:
    stream.write(json.dumps({'repo': repo, 'repetition': repetition, 'files': files}) + '\\n')
if repo == 'edi' and repetition == 2:
    if damage == 'exit':
        print('named engine refusal', file=sys.stderr)
        raise SystemExit(17)
    if damage == 'input':
        (project / 'project.edi').write_text('changed by dry fit')
    if damage == 'empty':
        raise SystemExit(0)
elapsed = ([4000, 3000, 5000] if repo == 'crysta' else [5200, 3900, 6500])[repetition-1]
if damage == 'slow' and repo == 'edi': elapsed += 1
print('record=fit\\nstatus=done\\nconverged=true\\niterations=9\\nn_free=193')
print('n_points_fitted=18973\\nreduced_chi_square=9.497530558\\nelapsed_ms=' + str(elapsed))
""")
    return {
        repo: [sys.executable, str(script), repo, '@PROJECT@', str(trace), damage]
        for repo in ('crysta', 'edi')
    }, trace


def test_timing_vehicle_executes_six_alternating_identical_inputs(tmp_path):
    commands, trace = timing_commands(tmp_path)
    output = tmp_path / 'records'
    result = measure.measure(commands, output)
    calls = [json.loads(line) for line in trace.read_text().splitlines()]
    assert [(row['repetition'], row['repo']) for row in calls] == [
        (rep, repo) for rep in (1, 2, 3) for repo in ('crysta', 'edi')
    ], ' I24 actual process launches must alternate on all three repetitions'
    assert all(row['files'] == result['project_sha256'] for row in calls), (
        ' I24 every process must receive all the same committed input bytes'
    )
    assert result['within_bound'] and result['edi_over_crysta'] == 1.3, (
        ' I24 the executable witness uses the same inclusive engine-median bound'
    )
    assert len(list(output.glob('*.stdout'))) == len(list(output.glob('*.stderr'))) == 6, (
        ' I24 every execution retains stdout and stderr, including successful runs'
    )
    assert json.loads((output / 'measurement.json').read_text()) == result, (
        ' I24 the persisted report records the observations actually compared'
    )


@pytest.mark.parametrize('damage', ['exit', 'input', 'empty'])
def test_timing_vehicle_refuses_failed_mutating_and_empty_executions(tmp_path, damage):
    commands, trace = timing_commands(tmp_path, damage)
    output = tmp_path / 'records'
    with pytest.raises((RuntimeError, ValueError), match=r'engine refusal|mutated|completed fit'):
        measure.measure(commands, output)
    assert len(trace.read_text().splitlines()) == 4, (
        ' I24 a bad middle execution cannot be skipped in favor of a later repetition'
    )
    assert not (output / 'measurement.json').exists(), (
        ' I24 failed or incomparable executions cannot leave a green measurement report'
    )
    assert (output / 'edi-2.stderr').exists() and (output / 'edi-2.stdout').exists(), (
        ' I24 a refused execution must retain its raw diagnostic evidence'
    )


def test_timing_vehicle_records_a_slow_complete_execution_as_red(tmp_path):
    commands, _ = timing_commands(tmp_path, 'slow')
    result = measure.measure(commands, tmp_path / 'records')
    assert not result['within_bound'], (
        ' I24 six completed executions above the bound still give a red measurement'
    )

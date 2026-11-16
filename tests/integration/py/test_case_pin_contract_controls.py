"""Gate 2 escape controls use authored numbers and a private Git history; no diffraction fit."""

import copy
import json
import math
import subprocess

import pytest

from tests.fixtures.tutorial_cases.pins import compare_regression_pin, pinned_start

CASE = 'pd-neut-cwl_lbco-hrpt'
QUANTITY = {'value': 1.25, 'kind': 'regression-pin', 'tol_abs': 0.0002, 'tol_rel': None}


def git(root, *arguments):
    run = subprocess.run(
        [
            'git',
            '-C',
            str(root),
            '-c',
            'user.name=Contract control',
            '-c',
            'user.email=control@example.invalid',
            '-c',
            'commit.gpgsign=false',
            *arguments,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, (
        'Gate 2 control: the private authored history must be valid: ' + run.stderr
    )
    return run.stdout.strip()


def write_pin(root, commit, reason):
    path = root / 'docs/user/cli' / CASE / 'expected.json'
    path.write_text(
        json.dumps({
            'source': {'pins': {'commit': commit, 'reason': reason}},
            'quantities': {'authored_control': QUANTITY},
        }),
        newline='\n',
    )


@pytest.fixture
def authored_history(tmp_path):
    directory = tmp_path / 'docs/user/cli' / CASE / 'project'
    directory.mkdir(parents=True)
    (directory / 'project.edi').write_text(
        'data_authored_metadata_control\n_cell.length_a 4.2\n', newline='\n'
    )
    git(tmp_path, 'init', '--quiet')
    git(tmp_path, 'add', '--', 'docs/user/cli/' + CASE + '/project/project.edi')
    git(tmp_path, 'commit', '--quiet', '-m', 'Record an authored metadata control')
    commit = git(tmp_path, 'rev-parse', 'HEAD')
    write_pin(tmp_path, commit, 'Authored metadata-only control; no fitted physics claim')
    git(tmp_path, 'add', '--', 'docs/user/cli/' + CASE + '/expected.json')
    git(tmp_path, 'commit', '--quiet', '-m', 'Record the authored regression-pin metadata')
    return tmp_path, directory, commit


def test_a_changed_start_fails_until_re_pinned_with_a_reason(authored_history):
    root, project, previous = authored_history
    pinned_start(CASE, root)
    path = project / 'project.edi'
    path.write_text(path.read_text().replace('4.2', '4.37'), newline='\n')
    with pytest.raises(AssertionError, match='changing any starting file'):
        pinned_start(CASE, root)
    git(root, 'add', '--', 'docs/user/cli/' + CASE + '/project/project.edi')
    git(root, 'commit', '--quiet', '-m', 'Change the authored starting value')
    current = git(root, 'rev-parse', 'HEAD')
    assert current != previous, (
        'Gate 2 control: the re-pin must identify the changed starting tree'
    )
    write_pin(root, current, '   ')
    with pytest.raises(AssertionError, match='explicit nonblank reason'):
        pinned_start(CASE, root)
    write_pin(root, current, 'Explicitly adopt the changed authored start; metadata control only')
    assert pinned_start(CASE, root)['authored_control'] == QUANTITY, (
        'Gate 2: a new committed start with an explicit re-pin reason restores custody'
    )


@pytest.mark.parametrize('damage', ['missing', 'extra', 'content'])
def test_every_start_tree_change_invalidates_the_old_regression_pin(authored_history, damage):
    root, project, _ = authored_history
    if damage == 'missing':
        (project / 'project.edi').unlink()
    elif damage == 'extra':
        (project / 'unregistered.edi').write_text('data_extra\n', newline='\n')
    else:
        (project / 'project.edi').write_text('data_changed\n', newline='\n')
    with pytest.raises(AssertionError, match='changing any starting file'):
        pinned_start(CASE, root)


@pytest.mark.parametrize('value', [math.nan, math.inf, -math.inf, 1.251])
def test_nonfinite_and_out_of_tolerance_outputs_fail_the_same_gate(value):
    with pytest.raises(AssertionError, match='Gate 2:'):
        compare_regression_pin({'authored_control': value}, {'authored_control': QUANTITY})


@pytest.mark.parametrize(
    'bounds',
    [
        {'tol_abs': 0.0002, 'tol_rel': None},
        {'tol_abs': None, 'tol_rel': 0.0002},
        {'tol_abs': 0, 'tol_rel': 0},
    ],
)
def test_only_the_declared_absolute_or_relative_tolerance_is_used(bounds):
    row = {**QUANTITY, **bounds}
    allowance = max(bounds['tol_abs'] or 0, (bounds['tol_rel'] or 0) * abs(row['value']))
    compare_regression_pin({'authored_control': row['value']}, {'authored_control': row})
    if allowance:
        compare_regression_pin(
            {'authored_control': row['value'] + allowance / 2}, {'authored_control': row}
        )
    outside = row['value'] + max(allowance * 4, math.ulp(row['value']) * 4)
    with pytest.raises(AssertionError, match='within only its stated tolerance'):
        compare_regression_pin({'authored_control': outside}, {'authored_control': row})


@pytest.mark.parametrize(
    'damage',
    [
        'missing-quantity',
        'negative-tolerance',
        'infinite-tolerance',
        'missing-tolerance',
        'boolean-tolerance',
        'boolean-value',
        'nonfinite-value',
        'unlabelled',
    ],
)
def test_malformed_regression_pin_cannot_make_a_false_green(authored_history, damage):
    root, _, _ = authored_history
    path = root / 'docs/user/cli' / CASE / 'expected.json'
    document = json.loads(path.read_text())
    row = document['quantities']['authored_control']
    if damage == 'missing-quantity':
        document['quantities'] = {}
    elif damage in {'boolean-value', 'nonfinite-value'}:
        row['value'] = True if damage == 'boolean-value' else math.nan
    elif damage == 'unlabelled':
        row['kind'] = 'reference'
    else:
        row.update({'tol_abs': None, 'tol_rel': None})
        if damage != 'missing-tolerance':
            row['tol_abs'] = {
                'negative-tolerance': -1,
                'infinite-tolerance': math.inf,
                'boolean-tolerance': True,
            }[damage]
    path.write_text(json.dumps(document), newline='\n')
    with pytest.raises(AssertionError, match='Gate 2:'):
        pinned_start(CASE, root)


def test_missing_observation_does_not_drop_a_pinned_quantity():
    with pytest.raises(AssertionError, match='every pinned quantity must be observed'):
        compare_regression_pin({}, {'authored_control': copy.deepcopy(QUANTITY)})


@pytest.mark.parametrize('state', ['uncommitted', 'committed', 'later-metadata-edit'])
@pytest.mark.parametrize('field', ['value', 'tol_abs'])
def test_changing_a_pin_cannot_reuse_old_source_provenance(authored_history, state, field):
    root, _, _ = authored_history
    path = root / 'docs/user/cli' / CASE / 'expected.json'
    document = json.loads(path.read_text())
    document['quantities']['authored_control'][field] *= 2
    path.write_text(json.dumps(document), newline='\n')
    if state != 'uncommitted':
        git(root, 'add', '--', 'docs/user/cli/' + CASE + '/expected.json')
        git(root, 'commit', '--quiet', '-m', 'Exercise an unexplained authored pin change')
    if state == 'later-metadata-edit':
        document['source']['note'] = 'A later metadata change cannot conceal the unexplained pin'
        path.write_text(json.dumps(document), newline='\n')
        git(root, 'add', '--', 'docs/user/cli/' + CASE + '/expected.json')
        git(root, 'commit', '--quiet', '-m', 'Exercise a later authored metadata change')
    with pytest.raises(AssertionError, match='fresh source provenance and a re-pin reason'):
        pinned_start(CASE, root)

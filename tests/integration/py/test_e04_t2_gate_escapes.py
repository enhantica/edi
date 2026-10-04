"""Review F4/F5 escape controls exercise the same predicates as the live gates."""

from copy import deepcopy

import pytest
import test_e04_t1_app_contract as app_contract
import yaml
from test_e04_t1_app_contract import assert_image_families, assert_numbered_states

from tests.integration.py.ci_runner_contract import RUNNERS, self_hosted_runners


def matrix_job():
    return {
        'runs-on': '${{ matrix.runner }}',
        'strategy': {
            'matrix': {
                'include': [
                    {'platform': platform, 'runner': labels.copy()}
                    for platform, labels in RUNNERS.items()
                ]
            }
        },
    }


def test_resolved_runner_positive_controls():
    for labels in RUNNERS.values():
        assert self_hosted_runners({'runs-on': labels}) == [labels], (
            'F5: legacy literal self-hosted jobs retain their runner meaning'
        )
    assert self_hosted_runners(matrix_job()) == list(RUNNERS.values()), (
        'F5: a valid matrix resolves both actual runner values'
    )


@pytest.mark.parametrize(
    'binding',
    [
        '${{ matrix.os }}',
        '${{ matrix.platform }}',
        '${{ matrix.missing }}',
        'ubuntu-latest',
        ['self-hosted', 'Linux', 'X64'],
    ],
)
def test_wrong_runner_binding_is_rejected(binding):
    job = matrix_job()
    job['runs-on'] = binding
    job['strategy']['matrix']['include'][0]['os'] = 'ubuntu-latest'
    job['strategy']['matrix']['include'][1]['os'] = 'macos-latest'
    with pytest.raises(AssertionError, match='E01:'):
        self_hosted_runners(job)


@pytest.mark.parametrize(
    'runner',
    [
        'ubuntu-latest',
        ['Linux', 'X64'],
        ['self-hosted', 'Linux', 'ARM64'],
        ['self-hosted', 'macOS', 'ARM64'],
        None,
    ],
)
def test_wrong_runner_row_is_rejected(runner):
    job = matrix_job()
    job['strategy']['matrix']['include'][0]['runner'] = runner
    with pytest.raises(AssertionError, match='E01:'):
        self_hosted_runners(job)


@pytest.mark.parametrize('damage', ['duplicate', 'missing', 'extra', 'replacement'])
def test_numbered_state_inventory_rejects_damage(damage):
    names = [f'{number:02d}-state.png' for number in range(1, 29)]
    assert_numbered_states(names)
    if damage == 'duplicate':
        names.append('01-other.png')
    elif damage == 'missing':
        names.pop()
    elif damage == 'extra':
        names.append('29-extra.png')
    else:
        names[-1] = '01-other.png'
    with pytest.raises(AssertionError, match='exactly one expected image'):
        assert_numbered_states(names)


@pytest.mark.parametrize(
    'damage',
    [
        'example-missing',
        'example-extra',
        'capture-missing',
        'capture-unmapped',
        'unrelated',
        'duplicate-state',
    ],
)
def test_image_family_inventory_rejects_damage(damage):
    names = [f'{number:02d}-state.png' for number in range(1, 29)]
    examples = {'ex-example.png'}
    captures = [{'image': 't2-01-state.png'}, {'image': '01-state.png'}]
    names += sorted(examples) + ['t2-01-state.png']
    assert_image_families(names, examples, deepcopy(captures))
    if damage == 'example-missing':
        names.remove('ex-example.png')
    elif damage == 'capture-missing':
        names.remove('t2-01-state.png')
    else:
        names.append(
            {
                'example-extra': 'ex-unknown.png',
                'capture-unmapped': 't2-02-unmapped.png',
                'unrelated': 'unknown.png',
                'duplicate-state': '01-other.png',
            }[damage]
        )
    with pytest.raises(AssertionError, match='gate 7'):
        assert_image_families(names, examples, captures)


@pytest.mark.parametrize(
    'damage', ['duplicate-platform', 'missing-platform', 'wrong-binding', 'wrong-row']
)
def test_live_app_gate_rejects_matrix_damage(tmp_path, monkeypatch, damage):
    workflow = yaml.safe_load((app_contract.ROOT / '.github/workflows/ci.yml').read_text())
    job = workflow['jobs']['app']
    rows = job['strategy']['matrix']['include']
    if damage == 'duplicate-platform':
        rows.append(deepcopy(rows[0]))
    elif damage == 'missing-platform':
        rows.pop()
    elif damage == 'wrong-binding':
        job['runs-on'] = '${{ matrix.platform }}'
    else:
        rows[0]['runner'] = 'ubuntu-latest'
    (tmp_path / '.github/workflows').mkdir(parents=True)
    (tmp_path / '.github/workflows/ci.yml').write_text(yaml.safe_dump(workflow))
    (tmp_path / 'pixi.toml').write_text((app_contract.ROOT / 'pixi.toml').read_text())
    monkeypatch.setattr(app_contract, 'ROOT', tmp_path)
    with pytest.raises(AssertionError, match=r'gate 7:|E01:'):
        app_contract.test_local_and_ci_gates_reach_app_tests()

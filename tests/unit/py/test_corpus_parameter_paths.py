import ast
import shlex
from pathlib import Path

import pytest

RUNNER = Path(__file__).resolve().parents[2] / 'system/py/test_c06_t6_fitting_corpus.py'


def _paths(project):
    tree = ast.parse(RUNNER.read_text())
    functions = {'_input_loops', '_loop_parameter_paths', '_corpus_parameter_paths'}
    module = ast.Module(
        body=[
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name in functions
        ],
        type_ignores=[],
    )
    namespace = {'Path': Path, 'shlex': shlex}
    exec(compile(module, str(RUNNER), 'exec'), namespace)  # noqa: S102
    return namespace['_corpus_parameter_paths'](project)


@pytest.mark.parametrize('field', ['coef', 'intensity'])
def test_corpus_positions_follow_input_ids_and_row_order(field, tmp_path):
    experiments = tmp_path / 'experiments'
    experiments.mkdir()
    bank = experiments / 'bank.edi'
    bank.write_text(f'loop_\n_background.id\n_background.{field}\n"ramp one" 12\nbase 31\n')
    paths = _paths(tmp_path)
    assert (
        paths[f'experiment.background[0].{field}'] == f'experiment.background[ramp one].{field}'
    ), 'The archived position must map to its declared input id, including quoted ids'
    bank.write_text(f'loop_\n_background.id\n_background.{field}\nbase 31\n"ramp one" 12\n')
    assert (
        _paths(tmp_path)[f'experiment.background[0].{field}']
        == f'experiment.background[base].{field}'
    ), 'Reordering input rows must reorder the position mapping without consulting fitted values'


def test_corpus_old_terms_without_ids_use_one_based_input_ordinals(tmp_path):
    experiments = tmp_path / 'experiments'
    experiments.mkdir()
    (experiments / 'bank.edi').write_text(
        'loop_\n_background.order\n_background.coef\n4 12\n0 31\n'
    )
    assert _paths(tmp_path)['experiment.background[0].coef'] == 'experiment.background[1].coef', (
        'An old term without an id gets its one-based row ordinal, '
        'rather than its polynomial order'
    )


@pytest.mark.parametrize('links', ['phase 12\n', 'phase 12\nother 31\n'])
def test_corpus_scale_shortcut_requires_one_declared_link(links, tmp_path):
    experiments = tmp_path / 'experiments'
    experiments.mkdir()
    (experiments / 'bank.edi').write_text(
        f'loop_\n_linked_structure.structure_id\n_linked_structure.scale\n{links}'
    )
    paths = _paths(tmp_path)
    if len(links.splitlines()) == 1:
        assert (
            paths['experiments[bank].linked_structure.scale']
            == 'experiments[bank].linked_structures[phase].scale'
        ), 'A single linked structure must still appear by its structure id'
    else:
        assert 'experiments[bank].linked_structure.scale' not in paths, (
            'A scale shortcut must not choose the first of several declared structures'
        )


def test_corpus_identity_mapping_refuses_incomplete_input_rows(tmp_path):
    experiments = tmp_path / 'experiments'
    experiments.mkdir()
    (experiments / 'bank.edi').write_text('loop_\n_background.id\n_background.coef\nramp\n')
    with pytest.raises(AssertionError, match='complete declared loop rows'):
        _paths(tmp_path)

"""Public cell addresses and compact fit-state IDs have different rename roles."""

import edi
import pytest

from tests.fixtures.constraint_expressions.project import materialize
from tests.fixtures.correlations.rename_history import historical_loop
from tests.fixtures.loop_parameter_ids.historical_fit_ids import _loops  # noqa: PLC2701
from tests.integration.py.test_parameter_correlations import correlations, saved_analysis

CELLS = ['length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma']


def observe(text):
    groups = list(_loops(text.encode()))
    return {
        'aliases': [
            r['_alias.parameter_unique_name']
            for tags, rows in groups
            if '_alias.id' in tags
            for r in rows
        ],
        'ids': [
            r['_fit_parameter.id']
            for tags, rows in groups
            if '_fit_parameter.id' in tags
            for r in rows
        ],
        'pairs': correlations(text),
    }


@pytest.mark.parametrize('multiple', [False, True])
def test_literal_structure_key_keeps_public_cells_and_stable_fit_ids(tmp_path, multiple):
    source = materialize(tmp_path / 'input', second_structure=multiple)
    path = source / 'structures/phase.edi'
    path.write_text(path.read_text().replace('data_phase', 'data_structure', 1))
    bank = source / 'experiments/bank.edi'
    bank.write_text(bank.read_text().replace('phase 1', 'structure 1'))
    names = ['structure.cell.' + field for field in CELLS]
    analysis = source / 'analysis/analysis.edi'
    text = analysis.read_text() + '\nloop_\n_alias.id\n_alias.parameter_unique_name\n'
    text += ''.join(f'cell_{index} {name}\n' for index, name in enumerate(names))
    text += historical_loop(names).replace('phase.cell.', 'structure.cell.')
    analysis.write_text(text)
    project = edi.Project.load(source)
    for field in CELLS:
        parameter = getattr(project.structures['structure'].cell, field)
        parameter.start_value = 4.125 if field.startswith('length') else 89.375
        parameter.start_uncertainty = 0.03125
    before = observe(saved_analysis(project, tmp_path / 'before'))
    assert before['aliases'] == names and len(before['ids']) == 6, (
        'The literal structure witness must reach all six public aliases and compact fit-state IDs'
    )
    original_ids = before['ids']
    current = 'structure'
    for index, name in enumerate(['phase', 'structure', 'phase']):
        project.structures[current].name = name
        current = name
        saved = tmp_path / f'save-{index}'
        result = observe(saved_analysis(project, saved))
        assert result['aliases'] == [name + '.cell.' + field for field in CELLS], (
            'A literal default structure rename follows every public cell alias away and back'
        )
        expected_ids = (
            original_ids
            if not multiple
            else [
                value.replace('structure.structure.', 'structure.' + name + '.')
                for value in original_ids
            ]
        )
        assert result['ids'] == expected_ids, (
            'Compact fit-state IDs retain their storage role independently of public cell names'
        )
        expected_pairs = [
            {
                **row,
                'parameter_unique_name_i': row['parameter_unique_name_i'].replace(
                    'structure.cell.', name + '.cell.'
                ),
                'parameter_unique_name_j': row['parameter_unique_name_j'].replace(
                    'structure.cell.', name + '.cell.'
                ),
            }
            for row in before['pairs']
        ]
        assert result['pairs'] == expected_pairs, (
            'Both endpoints follow the public structure key while other namespaces stay intact'
        )
        project = edi.Project.load(saved)
        assert observe(saved_analysis(project, tmp_path / f'reload-{index}')) == result, (
            'Public names and compact fit-state IDs retain their distinct roles after reload'
        )

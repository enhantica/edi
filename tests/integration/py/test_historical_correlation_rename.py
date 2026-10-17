"""Correlation history follows the block owner after its parameter row disappears."""

import edi
import pytest

from tests.fixtures.correlations.rename_history import (
    CASES,
    address,
    frozen_loop,
    historical_loop,
    owners,
    remove_live_row,
    seed,
)
from tests.fixtures.report_units.iucr_reference import rounded_correlation
from tests.integration.py.test_parameter_correlations import correlations, saved_analysis


def rename_address(name, kind, namespace):
    structure, experiment = owners(namespace)
    structural = any(
        name.startswith(structure + '.' + category + '.')
        for category in ['cell', 'atom_site', 'atom_site_aniso']
    )
    if kind == 'experiment':
        return 'new_bank.' + name.removeprefix(experiment + '.') if not structural else name
    if structural:
        return 'new_phase.' + name.removeprefix(structure + '.')
    for stem in [experiment + '.linked_structure.', experiment + '.preferred_orientation.']:
        if name.startswith(stem + structure + '.'):
            return stem + 'new_phase.' + name.removeprefix(stem + structure + '.')
    compact = experiment + '.' + structure + '.'
    if name.startswith(compact) and len(name.split('.')) == 3:
        return experiment + '.new_phase.' + name.removeprefix(compact)
    return name


@pytest.mark.parametrize(
    ('kind', 'address_role'),
    [
        pytest.param(
            kind,
            role,
            marks=pytest.mark.xfail(
                reason='known gap: historical compact endpoints after a block rename',
                strict=False,
            )
            if role == 'compact'
            else (),
        )
        for kind in CASES
        for role in (
            ['public', 'compact'] if kind in {'link-remove', 'texture-remove'} else ['public']
        )
    ],
)
@pytest.mark.parametrize('owner', ['structure', 'experiment'])
@pytest.mark.parametrize('namespace', ['ordinary', 'shared', 'category'])
def test_removed_rows_keep_both_historical_endpoints_on_block_rename(
    tmp_path, kind, address_role, owner, namespace
):
    source = seed(tmp_path / 'input', kind, namespace)
    names = [
        address(name, namespace)
        for name in CASES[kind]
        if kind not in {'link-remove', 'texture-remove'}
        or (len(name.split('.')) == 3) == (address_role == 'compact')
    ]
    project = edi.Project.load(source)
    before = tmp_path / 'before'
    saved_analysis(project, before)
    analysis = before / 'analysis/analysis.edi'
    if kind.startswith('term'):
        # The saved external covariance belongs to this same independently declared model.
        analysis.write_text(analysis.read_text() + frozen_loop(namespace))
        original = correlations(analysis.read_text())
    else:
        analysis.write_text(analysis.read_text() + historical_loop(names, *owners(namespace)))
        original = correlations(analysis.read_text())
    assert any(
        name in {r['parameter_unique_name_i'], r['parameter_unique_name_j']}
        for name in names
        for r in original
    ), 'The history witness must contain the actual row identities before removal'
    # Before literal coefficient spelling; after only that field follows IUCr rec. 12.
    original = [
        {**row, 'correlation': rounded_correlation(row['correlation'])} for row in original
    ]
    project = edi.Project.load(before)
    remove_live_row(project, kind, owners(namespace)[0])
    removed = tmp_path / 'removed'
    saved_analysis(project, removed)
    project = edi.Project.load(removed)
    assert correlations((removed / 'analysis/analysis.edi').read_text()) == original, (
        'A structural exit preserves correlation history before any block rename'
    )
    expected = [
        {
            **row,
            'parameter_unique_name_i': rename_address(
                row['parameter_unique_name_i'], owner, namespace
            ),
            'parameter_unique_name_j': rename_address(
                row['parameter_unique_name_j'], owner, namespace
            ),
        }
        for row in original
    ]
    blocks = project.structures if owner == 'structure' else project.experiments
    blocks[0].name = 'new_phase' if owner == 'structure' else 'new_bank'
    renamed = tmp_path / 'renamed'
    text = saved_analysis(project, renamed)
    assert correlations(text) == expected, (
        'Renaming a block follows both current and removed historical endpoints by owner role'
    )
    assert (
        correlations(saved_analysis(edi.Project.load(renamed), tmp_path / 'reopened')) == expected
    ), 'Historical endpoint renames survive project reload with coefficients and row IDs intact'

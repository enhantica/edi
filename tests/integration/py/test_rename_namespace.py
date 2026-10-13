"""Renames preserve parameter ownership when datablock names collide across kinds."""

import edi
import pytest

from tests.fixtures.constraint_expressions.project import materialize
from tests.fixtures.loop_parameter_ids.historical_fit_ids import (
    _loops,  # noqa: PLC2701 - shared strict STAR reference parser
)

CASES = [
    (kind, links, surface, mode)
    for kind in [
        'structure',
        'experiment',
        'peak',
        'instrument',
        'absorption',
        'background',
        'linked_structure',
        'preferred_orientation',
        'unequal-structure',
        'unequal-experiment',
    ]
    for links in [False, True]
    for surface in ['aliases', 'correlations']
    for mode in ['single', 'sequential']
]


def references(structure, experiment, *, compact=False):
    names = [
        structure + '.cell.length_a',
        experiment + '.instrument.setup_wavelength',
        experiment + '.peak.broad_gauss_w',
        experiment + '.background.left.intensity',
        experiment + '.absorption.mu_r',
        experiment + '.linked_structure.' + structure + '.scale',
        experiment + '.preferred_orientation.' + structure + '.march_r',
        experiment + '.preferred_orientation.' + structure + '.march_random_fract',
    ]
    if compact:
        names += [
            experiment + '.' + structure + '.' + field
            for field in ('scale', 'march_r', 'march_random_fract')
        ]
    return names


def observe(project, destination, surface):
    project.save_as(destination)
    text = (destination / 'analysis/analysis.edi').read_bytes()
    groups = list(_loops(text))
    if surface == 'aliases':
        return [
            r['_alias.parameter_unique_name']
            for tags, rows in groups
            if '_alias.id' in tags
            for r in rows
        ]
    return [
        (
            r['_fit_parameter_correlation.parameter_unique_name_i'],
            r['_fit_parameter_correlation.parameter_unique_name_j'],
            r['_fit_parameter_correlation.correlation'],
        )
        for tags, rows in groups
        if '_fit_parameter_correlation.id' in tags
        for r in rows
    ]


@pytest.mark.parametrize(('kind', 'multiple', 'surface', 'mode'), CASES)
def test_datablock_rename_preserves_namespace_and_category_tokens(  # noqa: PLR0912,PLR0914,PLR0915 - complete ownership matrix
    kind, multiple, surface, mode, tmp_path
):
    ordinary = kind.startswith('unequal-')
    direction = kind.removeprefix('unequal-') if ordinary else kind
    old_structure = (
        ('phase' if ordinary else 'shared') if direction in {'structure', 'experiment'} else kind
    )
    old_experiment = (
        'bank' if ordinary or direction not in {'structure', 'experiment'} else 'shared'
    )
    source = materialize(tmp_path / 'input', second_structure=multiple)
    for path in (source / 'structures').glob('*.edi'):
        text = path.read_text()
        if path.stem == 'phase':
            path.write_text(text.replace('data_phase', 'data_' + old_structure, 1))
    bank = source / 'experiments/bank.edi'
    text = bank.read_text().replace('data_bank', 'data_' + old_experiment, 1)
    text = text.replace('phase 1', old_structure + ' 1')
    text += (
        '\n_absorption.type cylinder-hewat\n_absorption.mu_r .125\n'
        'loop_\n_preferred_orientation.structure_id\n_preferred_orientation.march_r\n'
        '_preferred_orientation.march_random_fract\n_preferred_orientation.index_h\n'
        '_preferred_orientation.index_k\n_preferred_orientation.index_l\n'
        + old_structure
        + ' .73 .2 0 0 1\n'
    )
    bank.write_text(text)
    is_experiment = direction == 'experiment'
    names = references(old_structure, old_experiment, compact=surface == 'correlations')
    expected_names = references(
        old_structure if is_experiment else 'renamed',
        'renamed' if is_experiment else old_experiment,
        compact=surface == 'correlations',
    )
    analysis = source / 'analysis/analysis.edi'
    text = analysis.read_text().replace('_fitting_mode.type single', '_fitting_mode.type ' + mode)
    if mode == 'sequential':
        scan = source / 'experiments/scan'
        scan.mkdir()
        (scan / '01.xy').write_text('40 5.125 1\n44 6.375 1\n')
        text += (
            '\n_sequential_fit.data_dir experiments/scan\n_sequential_fit.file_pattern *.xy\n'
            '_sequential_fit.template_file 01.xy\n'
        )
    if surface == 'aliases':
        text += '\nloop_\n_alias.id\n_alias.parameter_unique_name\n'
        text += ''.join('ref_' + str(i) + ' ' + name + '\n' for i, name in enumerate(names))
        text += '\nloop_\n_constraint.expression\n"ref_3 = ref_0 + .375"\n'
    else:
        text += (
            '\nloop_\n_fit_parameter_correlation.id\n_fit_parameter_correlation.source_kind\n'
            '_fit_parameter_correlation.parameter_unique_name_i\n'
            '_fit_parameter_correlation.parameter_unique_name_j\n'
            '_fit_parameter_correlation.correlation\n'
        )
        if mode == 'sequential':
            text += '_fit_parameter_correlation.file_path\n'
        for i, name in enumerate(names):
            for endpoint in ('i', 'j'):
                pair = [name, old_structure + '.cell.length_b']
                if endpoint == 'j':
                    pair.reverse()
                text += 'pair' + str(i) + endpoint + ' deterministic ' + ' '.join(pair) + ' -.625'
                text += (' 01.xy' if mode == 'sequential' else '') + '\n'
    analysis.write_text(text)
    project = edi.Project.load(source)
    before = observe(project, tmp_path / 'before', surface)
    if surface == 'aliases':
        assert before == names, 'The namespace witness must begin with every genuine public alias'
        expected = expected_names
    else:
        expected = []
        peer = old_structure + '.cell.length_b' if is_experiment else 'renamed.cell.length_b'
        for name in expected_names:
            expected.extend([(name, peer, '-.625'), (peer, name, '-.625')])
        original = []
        for name in names:
            original.extend([
                (name, old_structure + '.cell.length_b', '-.625'),
                (old_structure + '.cell.length_b', name, '-.625'),
            ])
        assert before == original, (
            'Both correlation endpoint directions must be reached before renaming'
        )
    blocks = project.experiments if is_experiment else project.structures
    blocks[old_experiment if is_experiment else old_structure].name = 'renamed'
    after = observe(project, tmp_path / 'after', surface)
    assert after == expected, (
        'A rename must follow only its owning namespace '
        'and preserve every experimental category token'
    )
    reopened = edi.Project.load(tmp_path / 'after')
    assert observe(reopened, tmp_path / 'reopened', surface) == expected, (
        'Shared-name and category-token renames must save and reload '
        'without mislabelling references'
    )
    if surface == 'aliases':
        assert (
            '"ref_3 = ref_0 + .375"' in (tmp_path / 'after/analysis/analysis.edi').read_text()
        ), 'Reference propagation must retain each constraint alias identity and expression'

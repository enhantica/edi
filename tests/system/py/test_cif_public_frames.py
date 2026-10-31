"""Publication frames and point uncertainties survive the actual public entrances."""

import pytest

from tests.fixtures import cif_import_cases as case
from tests.system.py.test_cif_public_entrances import observe


@pytest.mark.parametrize('route', ['cli', 'app'])
@pytest.mark.parametrize(
    'control',
    [
        'precision',
        'symmetry',
        'rotation',
        'hexagonal',
        'invalid-letter',
        'empty-letter',
        'two-blocks',
    ],
)
def test_public_structure_accounting_uses_the_final_model_frame(tmp_path, route, control):
    if control == 'precision':
        text = case.tensor(scalar='0.0200')
    elif control == 'symmetry':
        text = case.tensor('P m -3 m', scalar='0.0222')
    elif control == 'rotation':
        text = case.tensor('P m -3 m', moved=True)
    elif control == 'hexagonal':
        text = case.tensor('P 3 1 2', moved=True)
    elif control == 'two-blocks':
        text = case.STRUCTURE + case.STRUCTURE.replace('data_witness', 'data_second')
    else:
        letter = 'z' if control == 'invalid-letter' else "''"
        text = case.STRUCTURE.replace('Ba1 Ba a', 'Ba1 Ba ' + letter)
    result = observe(tmp_path, route, 'structure', [case.STRUCTURE, text])[0]
    if control == 'two-blocks':
        assert 'refused' in result, (
            'Every public structure entrance refuses multiple structure blocks'
        )
        assert all(name in result['refused'] for name in ['witness', 'second']), (
            'Public ambiguity reports name both structure blocks'
        )
        return
    assert 'refused' not in result, (
        'The public entrance imports each valid coupled structure witness'
    )
    tags = {
        'precision': ['_atom_site.U_iso_or_equiv'],
        'symmetry': [
            '_atom_site.U_iso_or_equiv',
            '_atom_site_aniso.U_22',
            '_atom_site_aniso.U_33',
        ],
        'rotation': ['_atom_site_aniso.U_13'],
        'invalid-letter': ['_atom_site_Wyckoff_symbol'],
        'empty-letter': ['_atom_site_Wyckoff_symbol'],
    }
    for tag in tags.get(control, []):
        assert any(case.notices(note, tag) for note in result['notes']), (
            'The public warning surface names each declaration changed by final-model settlement'
        )
    if control in {'precision', 'symmetry'}:
        expected = '0.0240' if control == 'precision' else '0.0111'
        assert case.same(result['cells'][case.key('_atom_site.adp_iso')][0], expected), (
            'Public saved-model readback gives the tensor equivalent after site symmetry'
        )
    if control == 'hexagonal':
        assert not any('not used' in note or 'not read' in note for note in result['notes']), (
            'The public entrance reports no false disagreement for the invariant hexagonal tensor'
        )
        for component, expected in zip(
            case.COMPONENTS, [0.02, 0.02, 0.02, 0.01, 0, 0], strict=True
        ):
            assert float(
                result['cells'][case.key('_atom_site_aniso.adp_' + component)][0]
            ) == pytest.approx(expected, abs=1e-10), (
                'The public saved tensor retains every component '
                'of the source-frame isotropic form'
            )


@pytest.mark.parametrize('route', ['cli', 'app'])
@pytest.mark.parametrize('separate', ['35', '34'])
def test_public_measured_brackets_keep_the_point_uncertainty(tmp_path, route, separate):
    text = case.EXPERIMENT.replace('10 21 2', '10 1234(35) ' + separate)
    result = observe(tmp_path, route, 'experiment', [case.EXPERIMENT, text])[0]
    if separate == '34':
        assert 'refused' in result, 'Every public entrance refuses conflicting point uncertainties'
        assert '35' in result['refused'], 'The public refusal states the bracket uncertainty'
        assert '34' in result['refused'], (
            'The public refusal states the conflicting explicit uncertainty'
        )
    else:
        assert 'refused' not in result, (
            'Public entrances consume agreeing measured-point uncertainties'
        )
        assert result['cells'][case.key('_data.intensity_meas')][0] == '1234', (
            'Public saved-model readback retains the measured intensity'
        )
        assert result['cells'][case.key('_data.intensity_meas_su')][0] == '35', (
            'Public saved-model readback retains the measured point uncertainty'
        )

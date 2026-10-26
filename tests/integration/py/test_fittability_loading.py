"""Blocked free marks preserve numbers and report the same physical reason."""

import importlib
import re
import warnings
from pathlib import Path

import pytest

from tests.fixtures.fittability.inputs import CELL_FIELDS, mark_free, materialize
from tests.fixtures.fittability.saved_reference import staged

API = 'edi'
DESCRIPTOR = 'a descriptor, never fitted'
DATA = "this fit's data cannot determine it"
CAPABILITY = 'the fit cannot vary it yet'


@pytest.fixture(scope='module')
def api():
    return importlib.import_module(API)


def load(api, root):
    with warnings.catch_warnings(record=True) as notes:
        warnings.simplefilter('always')
        project = api.Project.load(root)
    return project, [str(note.message) for note in notes]


@pytest.mark.parametrize(
    'sample',
    [
        (
            'radius',
            True,
            'experiments/bank.edi',
            '_extinction.crystal_radius',
            '0.12(1)',
            0.12,
            0.01,
            DESCRIPTOR,
        ),
        (
            'limit',
            False,
            'experiments/bank.edi',
            '_peak.asym_beba_limit',
            '150(2)',
            150,
            2,
            DESCRIPTOR,
        ),
        ('cell', True, 'structures/phase.edi', '_cell.length_a', '5.10(2)', 5.1, 0.02, DATA),
        (
            'wavelength',
            True,
            'experiments/bank.edi',
            '_instrument.setup_wavelength',
            '1.60(3)',
            1.6,
            0.03,
            DATA,
        ),
    ],
)
def test_load_clears_one_blocked_mark_but_keeps_value_and_uncertainty(api, tmp_path, sample):
    case, single, relative, tag, number, value, su, reason = sample
    root = materialize(tmp_path / case, single=single)
    mark_free(root, relative, tag, number)
    project, notes = load(api, root)
    category, field = tag.removeprefix('_').split('.')
    parameter = getattr(
        getattr(project.structure if case == 'cell' else project.experiments['bank'], category),
        field,
    )
    assert not parameter.free, 'Loading a blocked free mark fixes that parameter'
    assert parameter.value == pytest.approx(value), 'Clearing a free mark preserves its value'
    assert parameter.uncertainty == pytest.approx(su), (
        'Clearing a free mark preserves its nonzero input uncertainty'
    )
    selected = [note for note in notes if 'crysta.domain.unfittable_free_ignored' in note]
    assert len(selected) == 1, 'Each ignored free mark emits exactly one coded loader note'
    assert all(token in selected[0] for token in (field, reason, 'loaded fixed')), (
        'The loader note names the parameter, the shared reason and the fixed result'
    )


@pytest.mark.parametrize('field', CELL_FIELDS)
def test_single_crystal_independent_cell_marks_load_fixed(api, tmp_path, field):
    root = materialize(tmp_path / field)
    path = root / 'structures/phase.edi'
    text = path.read_text()
    path.write_text(re.sub(r'(_cell\.' + field + r' [^\n]+)', r'\1()', text))
    project, notes = load(api, root)
    assert not getattr(project.structure.cell, field).free, (
        'Every independent triclinic cell degree needs reflection positions'
    )
    assert any(field in note and DATA in note for note in notes), (
        'Each independent cell refusal identifies the missing position measurements'
    )


@pytest.mark.parametrize('field', CELL_FIELDS)
def test_cubic_cell_reasons_prefer_symmetry_to_missing_positions(api, tmp_path, field):
    root = materialize(tmp_path / field, cubic=True)
    path = root / 'structures/phase.edi'
    path.write_text(re.sub(r'(_cell\.' + field + r' [^\n]+)', r'\1()', path.read_text()))
    project, notes = load(api, root)
    assert not getattr(project.structure.cell, field).free, (
        'A cubic single-crystal cell has no externally free cell parameter after load'
    )
    expected = DATA if field == 'length_a' else 'set by symmetry'
    assert any(field in note and expected in note for note in notes), (
        'The cubic metric takes precedence over data limitations for its five dependents'
    )


@pytest.mark.parametrize('case', ['radius', 'limit'])
def test_descriptor_python_refusal_uses_shared_reason(api, tmp_path, case):
    project, _ = load(api, materialize(tmp_path / case, single=case == 'radius'))
    experiment = project.experiments['bank']
    parameter = (
        experiment.extinction.crystal_radius
        if case == 'radius'
        else experiment.peak.asym_beba_limit
    )
    with pytest.raises(ValueError, match=re.escape(DESCRIPTOR)):
        parameter.free = True
    assert not parameter.free, 'A refused descriptor flag stays false'
    parameter.free = False
    assert not parameter.free, 'Clearing a descriptor flag is always accepted'


def test_nonruntime_background_position_still_refuses_brackets(api, tmp_path):
    root = materialize(tmp_path / 'plain', single=False)
    path = root / 'experiments/bank.edi'
    path.write_text(path.read_text().replace('a 20 3', 'a 20(1) 3'))
    with pytest.raises((ValueError, RuntimeError), match=r'(?i)(background|position|numeric)'):
        api.Project.load(root)


def test_surviving_cell_flag_is_refused_after_powder_is_removed(api, tmp_path):
    project, _ = load(api, materialize(tmp_path / 'mixed', cubic=True, mixed=True))
    parameter = project.structure.cell.length_a
    parameter.free = True
    assert parameter.free, (
        'An enabled powder link supplies position observations to the shared cell'
    )
    project.experiments.remove('powder')
    assert parameter.free, (
        'Changing fit context preserves an existing free choice until explicitly cleared'
    )
    with pytest.raises((ValueError, RuntimeError), match=re.escape(DATA)) as error:
        project.analysis.fit()
    assert 'length_a' in str(error.value), 'Fit-entry refusal names the stale free cell flag'
    parameter.free = False
    assert not parameter.free, 'A stale free flag can always be cleared'


def test_dispersion_load_refuses_only_the_primary_wavelength(api, tmp_path):
    root = materialize(tmp_path / 'dispersion', single=False, xray=True)
    path = root / 'experiments/bank.edi'
    path.write_text(
        path.read_text() + '\n_instrument.setup_wavelength_2 1.65()\n'
        '_instrument.setup_wavelength_2_to_1_ratio .37\n'
    )
    mark_free(root, 'experiments/bank.edi', '_instrument.setup_wavelength', '1.60(3)')
    project, notes = load(api, root)
    instrument = project.experiments['bank'].instrument
    assert not instrument.setup_wavelength.free, (
        'Dispersion-enabled primary wavelength loads fixed under the declared derivative boundary'
    )
    assert instrument.setup_wavelength_2.free, (
        'The second wavelength remains fittable because dispersion uses the first wavelength'
    )
    selected = [note for note in notes if 'crysta.domain.unfittable_free_ignored' in note]
    assert len(selected) == 1, 'Only the unsupported primary wavelength emits a load note'
    assert all(token in selected[0] for token in (CAPABILITY, 'sasaki1989')), (
        'The capability note names the shared reason and the selected dispersion source'
    )
    assert 'declare _scattering_source.xray_dispersion none to fit it' in selected[0], (
        'The wavelength note explains the supported no-dispersion alternative'
    )


@pytest.mark.parametrize('field', ['abscor2', 'calib_d_to_tof_reciprocal'])
def test_tof_capability_load_keeps_value_and_uncertainty(api, tmp_path, field):
    root = Path(__file__).resolve().parents[3]
    relative = (
        'tests/fitting/si-sepd-s2/project'
        if API == 'crysta'
        else 'docs/user/cli/pd-neut-tof_ceo2-pearl/project'
    )
    source = staged(root / relative, tmp_path / 'input', 'iucr_19')
    experiment_file = next((source / 'experiments').glob('*.edi'))
    category = 'absorption' if field == 'abscor2' else 'instrument'
    tag = '_' + category + '.' + field
    text = experiment_file.read_text()
    text = re.sub(r'(?m)^' + re.escape(tag) + r'[^\n]*\n?', '', text)
    if field == 'abscor2':
        text = re.sub(r'(?m)^_absorption.type[^\n]*', '_absorption.type cylinder', text)
        if '_absorption.abscor1' not in text:
            text += '\n_absorption.abscor1 0\n'
    experiment_file.write_text(text + '\n' + tag + ' 0.037(2)\n')
    project, notes = load(api, source)
    parameter = getattr(getattr(project.experiments[0], category), field)
    assert not parameter.free, 'Unsupported TOF derivatives load as fixed parameters'
    assert parameter.value == pytest.approx(0.037), (
        'A capability block preserves the parameter value'
    )
    assert parameter.uncertainty == pytest.approx(0.002), (
        'A capability block preserves the input s.u.'
    )
    selected = [note for note in notes if 'unfittable_free_ignored' in note and field in note]
    assert len(selected) == 1, 'Each ignored TOF free mark emits one named loader note'
    assert all(
        token in selected[0] for token in (CAPABILITY, 'crysta has no derivative for it')
    ), 'Unsupported TOF derivatives use the shared capability reason and detail'
    if API == 'edi':
        with pytest.raises(ValueError, match=re.escape(CAPABILITY)):
            parameter.free = True
    parameter.free = False
    assert not parameter.free, 'Clearing an unsupported derivative flag is always allowed'


def test_wavelength_can_fit_when_dispersion_is_explicitly_none(api, tmp_path):
    root = materialize(tmp_path / 'no-dispersion', single=False, xray=True)
    path = root / 'experiments/bank.edi'
    path.write_text(path.read_text().replace('xray_dispersion sasaki1989', 'xray_dispersion none'))
    project, _ = load(api, root)
    project.experiments['bank'].instrument.setup_wavelength.free = True
    project.analysis.fit()
    assert project.experiments['bank'].instrument.setup_wavelength.free, (
        'With the cell fixed and dispersion disabled, a primary wavelength fit reaches the solver'
    )

"""currentness under 's lazy non-UI read rule."""

import os
from pathlib import Path

import edi
import numpy as np
import pytest
import test_c13_t4_march as march

ROOT = Path(__file__).resolve().parents[3]
CORPUS = Path(os.environ.get('EDI_CRYSTA_CORPUS_ROOT', ROOT / 'build/crysta-src/tests/fitting'))


def write_input(project, route):
    if route == 'parameter':
        project.experiment.linked_structure.scale.value *= 1.25
    elif route == 'cell':
        project.structure.cell.length_a.value *= 1.01
    elif route == 'site':
        project.structure.atom_sites[0].occupancy.value *= 0.875
    elif route in {'measured', 'measured-su'}:
        name = 'intensity_meas' if route == 'measured' else 'intensity_meas_su'
        data = project.experiment.data
        values = list(getattr(data, name))
        values[0] += 0.25
        setattr(data, name, values)
    elif route == 'structure-replacement':
        project.structure = edi.Project.load(CORPUS / 'si-sepd-s2/project').structure
    elif route == 'data-replacement':
        data = project.experiment.data
        project.experiment.data = edi.PdTofData(
            time_of_flight=list(data.axis()),
            intensity_meas=list(data.intensity_meas),
            intensity_meas_su=list(data.intensity_meas_su),
        )
    elif route == 'exclusions':
        project.experiment.excluded_regions = [(2000, 2100)]
    elif route == 'refused-cell':
        # A negative length is refused by the setter; zero reaches the lazy
        # metric calculation and must still refuse before returning old data.
        project.structure.cell.length_a.value = 0
    else:
        raise AssertionError(f' unknown test edit route: {route}')


def column(project, category):
    return (
        project.experiment.data.intensity_calc
        if category == 'data'
        else project.experiment.refln.index_h
    )


def saved_text(project, tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    destination = tmp_path / 'saved'
    project.save_as(destination)
    return next((destination / 'experiments').glob('*.edi')).read_text()


def tag(category):
    return '_data.intensity_calc' if category == 'data' else '_refln.index_h'


@pytest.mark.parametrize('category', ['data', 'refln'])
@pytest.mark.parametrize('route', ['cell', 'refused-cell'])
def test_retained_category_rechecks_its_live_owner(tmp_path, route, category):
    project = edi.Project.load(CORPUS / 'si-sepd-s2/project')
    project.analysis.calculate()
    retained = project.experiment.data if category == 'data' else project.experiment.refln
    assert np.asarray(column(project, category)).size, (
        ' retained-category control starts from a published value'
    )
    write_input(project, route)
    if route == 'refused-cell':
        with pytest.raises((ValueError, RuntimeError), match=r'(?i)cell|calculat|invalid'):
            _ = retained.intensity_calc if category == 'data' else retained.index_h
        return
    observed = retained.intensity_calc if category == 'data' else retained.index_h
    assert np.asarray(observed).size, (
        ' a held edi category must lazily recalculate after a live-owner edit'
    )
    assert tag(category) in saved_text(project, tmp_path), (
        ' a held category read publishes current output savable under its live owner'
    )


def test_mixed_bank_save_precedes_lazy_recalculation(tmp_path):
    # This gate checks bank-local freshness, not NCAF physics. The existing
    # three-point public project keeps both save/read rounds within the tier.
    source = tmp_path / 'two-bank-input'
    march._project(source, None)
    original = (source / 'experiments/experiment.edi').read_text()
    assert original.startswith('data_experiment\n'), (
        'the two-bank control must duplicate the declared three-point bank exactly'
    )
    (source / 'experiments/experiment_copy.edi').write_text(
        original.replace('data_experiment\n', 'data_experiment_copy\n', 1)
    )
    project = edi.Project.load(source)
    assert len(project.experiments) == 2, (
        ' mixed-bank control requires independently editable banks'
    )
    project.analysis.calculate()
    current_bank, edited_bank = project.experiments
    assert (
        np.asarray(current_bank.data.intensity_calc).size
        and np.asarray(edited_bank.data.intensity_calc).size
    ), ' both banks must start calculated'
    edited_bank.linked_structure.scale.value *= 1.25
    destination = tmp_path / 'mixed-bank'
    project.save_as(destination)
    current_file = (destination / 'experiments' / f'{current_bank.name}.edi').read_text()
    edited_file = (destination / 'experiments' / f'{edited_bank.name}.edi').read_text()
    assert '_data.intensity_calc' in current_file and '_refln.index_h' in current_file, (
        ' a bank-local edit leaves the untouched bank savable as current'
    )
    assert '_data.intensity_calc' not in edited_file and '_refln.index_h' not in edited_file, (
        ' a stale bank is omitted if saved before a non-UI read'
    )
    assert np.asarray(edited_bank.data.intensity_calc).size, (
        ' the first edited-bank read recalculates its current model'
    )
    recalculated = tmp_path / 'recalculated'
    project.save_as(recalculated)
    assert (
        '_data.intensity_calc'
        in (recalculated / 'experiments' / f'{edited_bank.name}.edi').read_text()
    ), ' the edited bank becomes savable after its lazy calculation'


@pytest.mark.parametrize('route', ['parameter', 'measured', 'measured-su'])
def test_equal_write_stales_before_read_then_recalculates(tmp_path, route):
    project = edi.Project.load(CORPUS / 'si-sepd-s2/project')
    project.analysis.calculate()
    if route == 'parameter':
        parameter = project.experiment.linked_structure.scale
        parameter.value = parameter.value
    else:
        name = 'intensity_meas' if route == 'measured' else 'intensity_meas_su'
        data = project.experiment.data
        setattr(data, name, list(getattr(data, name)))
    assert '_data.intensity_calc' not in saved_text(project, tmp_path / route), (
        ' an equal write stales a computed unit before any read'
    )
    assert np.asarray(project.experiment.data.intensity_calc).size, (
        ' an equal-write non-UI read recalculates rather than returns empty'
    )


@pytest.mark.parametrize('category', ['data', 'refln'])
@pytest.mark.parametrize(
    'route',
    [
        'parameter',
        'cell',
        'site',
        'measured',
        'measured-su',
        'structure-replacement',
        'data-replacement',
        'exclusions',
        'refused-cell',
    ],
)
def test_edited_category_reads_current_or_raises(tmp_path, route, category):
    project = edi.Project.load(CORPUS / 'si-sepd-s2/project')
    project.analysis.calculate()
    assert np.asarray(column(project, category)).size, (
        ' freshness witness begins with a published computed unit'
    )
    write_input(project, route)
    if route == 'refused-cell':
        with pytest.raises((ValueError, RuntimeError), match=r'(?i)cell|calculat|invalid'):
            _ = column(project, category)
        return
    observed = np.asarray(column(project, category))
    assert observed.size, (
        ' an edited non-UI read computes current rows on this partly included grid'
    )
    assert tag(category) in saved_text(project, tmp_path / route / category), (
        ' a successful non-UI read publishes current output after every edit route'
    )

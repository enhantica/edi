""": a present zero shift must not lose the identity of its saved start state."""

import edi
import pytest
import test_c13_t4_march as march

from conftest import tree_bytes_with_normalized_project_metadata

TERMS = ('calib_sample_displacement', 'calib_sample_transparency')


def _project(tmp_path, probe, banks):
    march._project(tmp_path / 'input', None)
    path = tmp_path / 'input/experiments/experiment.edi'
    text = path.read_text().replace('radiation_probe neutron', f'radiation_probe {probe}')
    if probe == 'xray':
        text = text.replace(
            '_scattering_source.neutron_scattering_length sears1992',
            '_scattering_source.xray_dispersion none',
        )
    path.write_text(text)
    if banks == 2:
        (path.parent / 'second.edi').write_text(text.replace('data_experiment', 'data_second'))
    return edi.Project.load(tmp_path / 'input')


@pytest.mark.parametrize('probe', ['neutron', 'xray'])
@pytest.mark.parametrize('banks', [1, 2])
@pytest.mark.parametrize(
    'terms', [TERMS[:1], TERMS[1:], TERMS], ids=['displacement', 'transparency', 'both']
)
def test_zero_fixed_shift_snapshot_survives_save_load_undo(tmp_path, probe, banks, terms):
    project = _project(tmp_path, probe, banks)
    for bank_index, experiment in enumerate(project.experiments):
        for term_index, name in enumerate(terms):
            parameter = edi.Parameter(0)
            parameter.free = False
            parameter.uncertainty = None
            parameter.start_value = 0.17 + bank_index * 0.1 + term_index * 0.03
            parameter.start_uncertainty = 0.007
            setattr(experiment.instrument, name, parameter)
    project.save_as(tmp_path / 'saved')
    restored = edi.Project.load(tmp_path / 'saved')
    assert len(restored.experiments) == banks, ' all banks must survive shift snapshot persistence'
    for bank_index, experiment in enumerate(restored.experiments):
        for term_index, name in enumerate(terms):
            parameter = getattr(experiment.instrument, name)
            assert parameter is not None, ' a snapshot requires a declared, resolvable shift slot'
            # Edi's fixed-value grammar canonicalizes absent current uncertainty to zero.
            # The nonzero snapshot uncertainty remains a separate persistence requirement.
            assert parameter.value == 0 and not parameter.free and parameter.uncertainty == 0, (
                ' persist zero, fixed status and canonical fixed uncertainty'
            )
            assert parameter.start_value == pytest.approx(
                0.17 + bank_index * 0.1 + term_index * 0.03
            ), ' each bank and shift retains its own prior value'
            assert parameter.start_uncertainty == pytest.approx(0.007), (
                ' prior uncertainty survives loading'
            )
    restored._undo_fit()
    for bank_index, experiment in enumerate(restored.experiments):
        for term_index, name in enumerate(terms):
            parameter = getattr(experiment.instrument, name)
            assert parameter.value == pytest.approx(0.17 + bank_index * 0.1 + term_index * 0.03), (
                ' undo restores each saved shift start value'
            )
            assert parameter.uncertainty == pytest.approx(0.007), (
                ' undo restores the prior uncertainty'
            )
            assert parameter.start_value is None, ' undo consumes the restored snapshot'


@pytest.mark.parametrize('probe', ['neutron', 'xray'])
@pytest.mark.parametrize('banks', [1, 2])
def test_absent_shift_remains_absent_with_stable_saved_bytes(tmp_path, probe, banks):
    project = _project(tmp_path, probe, banks)
    project.save_as(tmp_path / 'first')
    restored = edi.Project.load(tmp_path / 'first')
    for experiment in restored.experiments:
        for name in TERMS:
            assert getattr(experiment.instrument, name) is None, (
                ' an undeclared shift stays absent'
            )
    restored.save_as(tmp_path / 'second')
    assert tree_bytes_with_normalized_project_metadata(
        tmp_path / 'first', 'created', 'last_modified'
    ) == tree_bytes_with_normalized_project_metadata(
        tmp_path / 'second', 'created', 'last_modified'
    ), ' absent shifts preserve saved bytes except wall-clock metadata'

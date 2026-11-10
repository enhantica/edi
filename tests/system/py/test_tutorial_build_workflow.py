"""Stepwise construction follows the published LBCO workflow; fit checks are invariants."""

import importlib
import importlib.util
import math

from conftest import corpus_case_dir


def test_structure_built_step_by_step_fits_without_blank_model_objects():
    module = 'easydiffraction' if importlib.util.find_spec('easydiffraction') else 'edi'
    edi = importlib.import_module(module)
    project = edi.Project(name='lbco_hrpt')
    project.structures.create(name='lbco')
    structure = project.structures['lbco']
    structure.space_group.name_h_m = 'P m -3 m'
    structure.space_group.coord_system_code = '1'
    structure.cell.length_a = 3.88
    for label, xyz, occupancy, letter in [
        ('La', (0, 0, 0), 0.5, 'a'),
        ('Ba', (0, 0, 0), 0.5, 'a'),
        ('Co', (0.5, 0.5, 0.5), 1, 'b'),
        ('O', (0, 0.5, 0.5), 1, 'c'),
    ]:
        structure.atom_sites.create(
            id=label,
            type_symbol=label,
            fract_x=xyz[0],
            fract_y=xyz[1],
            fract_z=xyz[2],
            occupancy=occupancy,
            adp_iso=0.5,
        )
        structure.atom_sites[label].wyckoff_letter = letter
    data_path = corpus_case_dir('lbco-hrpt-s2') / 'fullprof/lbco.dat'
    project.experiments.add_from_data_path(
        name='hrpt',
        data_path=data_path,
        sample_form='powder',
        beam_mode='constant wavelength',
        radiation_probe='neutron',
    )
    experiment = project.experiments['hrpt']
    experiment.instrument.setup_wavelength = 1.494
    experiment.instrument.calib_twotheta_offset = 0.6
    experiment.peak.broad_gauss_u = 0.1
    experiment.peak.broad_gauss_v = -0.1
    experiment.peak.broad_gauss_w = 0.1
    experiment.peak.broad_lorentz_y = 0.1
    assert hasattr(experiment.excluded_regions, 'create'), (
        'A code-built experiment must support app-style excluded regions'
    )
    experiment.excluded_regions.create(id='1', start=0, end=5)
    experiment.excluded_regions.create(id='2', start=165, end=180)
    experiment.background.auto_estimate()
    experiment.linked_structures.create(structure_id='lbco', scale=10.0)
    assert [item.name for item in project.structures] == ['lbco'], (
        'Building one structure must leave no implicit blank structure'
    )
    assert [item.name for item in project.experiments] == ['hrpt'], (
        'Building one experiment must leave no implicit blank experiment'
    )
    assert len(experiment.linked_structures) == 1, (
        'Only the explicitly created structure link may participate in the fit'
    )
    structure.cell.length_a.free = True
    experiment.linked_structures['lbco'].scale.free = True
    project.analysis.calculate()
    data = experiment.data

    def objective():
        return sum(
            ((obs - calc) / su) ** 2
            for obs, calc, su in zip(
                data.intensity_meas, data.intensity_calc, data.intensity_meas_su, strict=True
            )
            if su > 0
        )

    initial = objective()
    result = project.analysis.fit()
    project.analysis.calculate()
    assert math.isfinite(result.reduced_chi_square), (
        'The code-built project must fit with finite statistics'
    )
    assert objective() < initial, (
        'The fit must reduce the measured weighted residual from its non-optimised start'
    )
    assert all(math.isfinite(value) for value in result.values.values()), (
        'The stepwise fit must return finite parameter values'
    )

"""small valid family vehicles, independently declared EDI inputs."""

from pathlib import Path


def family_project(root, family):
    source = Path(__file__).parent / 'isolated.edi'
    structure, experiment = source.read_text().split('data_experiment', 1)
    experiment = 'data_experiment' + experiment
    if family == 'xray-bare':
        experiment = '\n'.join(
            line for line in experiment.splitlines() if not line.startswith('_scattering_source.')
        )
    if family == 'neutron-cw':
        experiment = experiment.replace('radiation_probe xray', 'radiation_probe neutron')
        experiment = '\n'.join(
            line for line in experiment.splitlines() if not line.startswith('_scattering_source.')
        )
    if family == 'tof':
        experiment = """data_experiment
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.radiation_probe neutron
_experiment_type.scattering_type bragg
_experiment_type.beam_mode time-of-flight
_peak.type tof-jorgensen
_peak.cutoff_fwhm 10
_peak.rise_alpha_0 1
_peak.rise_alpha_1 0
_peak.decay_beta_0 1
_peak.decay_beta_1 0
_peak.broad_gauss_sigma_0 10
_peak.broad_gauss_sigma_1 0
_peak.broad_gauss_sigma_2 0
_peak.broad_gauss_size 0
_peak.broad_gauss_strain 0
_peak.broad_lorentz_gamma_0 0
_peak.broad_lorentz_gamma_1 0
_peak.broad_lorentz_gamma_2 0
_peak.broad_lorentz_size 0
_peak.broad_lorentz_strain 0
_instrument.calib_d_to_tof_offset 0
_instrument.calib_d_to_tof_linear 7000
_instrument.calib_d_to_tof_quadratic 0
_instrument.setup_twotheta_bank 90
_absorption.type none
loop_
_linked_structure.structure_id
_linked_structure.scale
structure 1
"""
    axis = 'time_of_flight' if family == 'tof' else 'two_theta'
    grid = (5000, 7000, 9000) if family == 'tof' else (30, 50, 70)
    experiment += f'\nloop_\n_data.{axis}\n_data.intensity_meas\n_data.intensity_meas_su\n'
    experiment += ''.join(f'{x} 1 1\n' for x in grid)
    (root / 'structures').mkdir(parents=True)
    (root / 'experiments').mkdir()
    (root / 'structures/structure.edi').write_text(structure)
    (root / 'experiments/experiment.edi').write_text(experiment)
    return root

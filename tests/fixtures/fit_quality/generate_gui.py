"""Generate independent metric-display inputs and rational scan transitions."""

import shutil
from pathlib import Path

root = Path(__file__).resolve().parent
shutil.copytree(root.parent / 'e04_t1/editable-project', root / 'gui', dirs_exist_ok=True)
experiment = root / 'gui/experiments/hrpt.edi'
(root / 'gui/experiments/aux.edi').write_text(
    experiment.read_text().replace('data_hrpt', 'data_aux')
)
analysis = root / 'gui/analysis/analysis.edi'
analysis.write_text(
    analysis.read_text().replace('_fitting_mode.type single', '_fitting_mode.type joint')
    + """
loop_
_joint_fit.experiment_id
_joint_fit.weight
hrpt 1
aux 1
_fit_result.result_kind deterministic
_fit_result.success true
_fit_result.iterations 17
_fit_result.prof_wr_factor 0.2137
_fit_result.prof_r_factor 0.1876
_fit_result.prof_wr_expected 0.0654
_fit_result.prof_cr_factor 0.2876
_fit_result.prof_cwr_factor 0.3234
_fit_result.reduced_chi_square 5.56
loop_
_fit_result_bank.experiment_id
_fit_result_bank.n_data_points
_fit_result_bank.prof_wr_factor
_fit_result_bank.prof_r_factor
_fit_result_bank.prof_wr_expected
_fit_result_bank.prof_cr_factor
_fit_result_bank.prof_cwr_factor
_fit_result_bank.chi_square
hrpt 123 0.1234 0.0876 0.0654 0.1876 0.2234 3.56
aux 123 0.3123 0.2154 0.0987 0.4156 0.5123 7.89
loop_
_fit_result_phase.experiment_id
_fit_result_phase.structure_id
_fit_result_phase.bragg_r_factor
_fit_result_phase.f_r_factor
hrpt lbco 0.0432 0.0210
aux lbco 0.1432 0.1210
"""
)

source = root.parents[2] / 'build/crysta-src/tests/fitting/constraint-covariance/project'
for mode in ('single', 'sequential', 'independent'):
    destination = root / f'uncertainty-{mode}'
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    if mode != 'single':
        bank = destination / 'experiments/bank.edi'
        bank.write_text(bank.read_text().replace('1 0 4()', '1 0 4.00(15)'))
        settings = destination / 'analysis/analysis.edi'
        settings.write_text(
            settings.read_text().replace('_fitting_mode.type single', f'_fitting_mode.type {mode}')
            + '\n_sequential_fit.data_dir experiments/scan\n_sequential_fit.file_pattern *.dat\n'
        )
        folder = destination / 'experiments/scan'
        folder.mkdir()
        measurements = (
            (destination / 'experiments/bank.edi')
            .read_text()
            .split('_data.intensity_meas_su\n')[1]
        )
        for index in range(2):
            (folder / f'{index}.dat').write_text('XYDATA\n' + measurements)

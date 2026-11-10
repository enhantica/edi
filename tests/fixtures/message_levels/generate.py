"""A closed-form diagnostic witness: Q || M makes M_perp and dI/dMx zero.

The a=5, b=1.2, c=1.3 cell and 54.5..55.5 degree window admit h00 only.
The covariance therefore cannot determine its sole free longitudinal moment.
No fitted number is a correctness oracle or a regression pin in this fixture.
"""

from pathlib import Path

from tests.fixtures.magnetic_pnma import commensurate, reference


def generate(destination):
    structure = (
        commensurate
        .structure(b=1.2, moment='3.125() 0 0')
        .replace('_cell.length_a 4', '_cell.length_a 5')
        .replace('_cell.length_c 6', '_cell.length_c 1.3')
        .replace('A Co a', 'Co1 Co a')
        .replace('A 3.125()', 'Co1 3.125()')
    )
    experiment = (reference.ROOT / 'compound-experiment.edi').read_text()
    experiment = experiment.split('loop_\n_data.two_theta')[0]
    for before, after in [
        ('_instrument.setup_wavelength 1.87', '_instrument.setup_wavelength 1.54'),
        ('_instrument.calib_twotheta_offset 0.29433', '_instrument.calib_twotheta_offset 0'),
        ('_peak.broad_gauss_u 0.273213', '_peak.broad_gauss_u 0'),
        ('_peak.broad_gauss_v -0.587787', '_peak.broad_gauss_v 0'),
        ('_peak.broad_gauss_w 0.410988', '_peak.broad_gauss_w .04'),
    ]:
        experiment = experiment.replace(before, after)
    points = ''.join(
        f'{54.5 + index * 0.05:.8f} {2 + index * 0.01:.8f} 1\n' for index in range(21)
    )
    reference.project(
        destination,
        structure,
        experiment
        + 'loop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
        + points,
    )
    analysis = destination / 'analysis'
    analysis.mkdir()
    (analysis / 'analysis.edi').write_text(
        '_edi.schema_version 3\n_minimizer.type crysta\n_minimizer.max_iterations 4\n'
        '_fitting_mode.type single\n'
    )


if __name__ == '__main__':
    generate(Path(__file__).parent / 'project')

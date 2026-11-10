"""Generate synthetic GUI inputs from the committed  editable project.

Owner ideas 9, 16, 24-26 are the oracle; these values are not app output.
Uniform steps are 0.125; irregular steps are 0.125 and 0.375 degrees.
The out-of-domain grid starts at zero to exercise a calculation refusal.
"""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEST = Path(__file__).resolve().parent
SOURCE = ROOT / 'tests/fixtures/e04_t1/editable-project'


def generate_overflow(destination):
    """Twelve independent unsupported engines plus refused grids exceed the dialog viewport."""
    shutil.copytree(DEST / 'messages', destination, dirs_exist_ok=True)
    source = (destination / 'experiments/hrpt.edi').read_text()
    for index in range(1, 12):
        name = f'overflow_{index:02d}'
        text = source.replace('data_hrpt', 'data_' + name).replace(
            '_calculator.type cryspy', '_calculator.type cryspy_' + str(index)
        )
        (destination / 'experiments' / (name + '.edi')).write_text(text)


def generate():
    for case, axes in {
        'uniform': [12.25, 12.375, 12.5, 12.625],
        'irregular': [12.25, 12.375, 12.75, 12.875],
        'messages': [0, 0.125, 0.5, 0.625],
    }.items():
        target = DEST / case
        shutil.copytree(SOURCE, target, dirs_exist_ok=True)
        (target / 'project.edi').write_text(
            '_edi.schema_version 2\n_metadata.name lbco_hrpt_s2\n'
            '_metadata.title " independent GUI input"\n_metadata.description ?\n'
        )
        experiment = target / 'experiments/hrpt.edi'
        prefix = experiment.read_text().split('loop_\n_data.two_theta')[0]
        grid = 'loop_\n_data.two_theta\n_data.id\n_data.intensity_meas\n_data.intensity_meas_su\n'
        grid += ''.join(f'{x} {i + 1} {180 + i} 13\n' for i, x in enumerate(axes))
        experiment.write_text(prefix + grid)
        if case == 'irregular':
            (target / 'experiments/second.edi').write_text(
                (prefix + grid).replace('data_hrpt', 'data_second')
            )
        if case == 'messages':
            experiment.write_text(experiment.read_text() + '\n_calculator.type cryspy\n')
            analysis = target / 'analysis/analysis.edi'
            analysis.write_text(
                analysis.read_text().replace(
                    '_minimizer.type crysta', '_minimizer.type "bumps (lm)"'
                )
            )


if __name__ == '__main__':
    generate()
    generate_overflow(DEST / 'overflow')

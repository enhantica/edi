"""Regenerate exact serialized inputs shared by pre-change and renamed captures."""

import shutil
from pathlib import Path

from tests.fixtures.cwl_family import profiles

ROOT = Path(__file__).resolve().parent / 'rename_inputs'


def generate():
    for name, token in [('tch', 'cwl-' + 'pseudo-voigt'), ('fcj', profiles.RETIRED[0])]:
        destination = ROOT / name
        if destination.exists():
            shutil.rmtree(destination)
        path = profiles.write_project(
            destination, token, extra='_peak.broad_lorentz_x .023\n_peak.broad_lorentz_y .047\n'
        )
        if name == 'fcj':
            experiment = path / 'experiments/bank.edi'
            experiment.write_text(
                experiment.read_text().replace(
                    '_peak.broad_lorentz_x 0\n_peak.broad_lorentz_y 0\n', ''
                )
            )


if __name__ == '__main__':
    generate()

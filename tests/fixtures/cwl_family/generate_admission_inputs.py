"""Generate declaration-only native vehicles; no engine output or correctness pins."""

import shutil
from pathlib import Path

from tests.fixtures.cwl_family import profiles

ROOT = Path(__file__).resolve().parent


def generate():
    for name, token in [
        ('tch', profiles.TOKENS[4]),
        ('gaussian', profiles.TOKENS[0]),
        ('beba', profiles.TOKENS[3]),
    ]:
        destination = ROOT / 'native' / name
        if destination.exists():
            shutil.rmtree(destination)
        extra = '_peak.asym_beba_limit 160\n_peak.asym_beba_a0 .031\n' if name == 'beba' else ''
        path = profiles.write_project(destination, token, extra=extra)
        file = path / 'experiments/bank.edi'
        text = file.read_text().replace(
            '_peak.broad_lorentz_x 0\n', '_peak.broad_lorentz_x .023\n'
        )
        file.write_text(text.replace('_peak.broad_lorentz_y 0\n', '_peak.broad_lorentz_y .047\n'))


if __name__ == '__main__':
    generate()

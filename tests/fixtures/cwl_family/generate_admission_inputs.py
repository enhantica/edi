"""Generate declaration-only native vehicles; no engine output or correctness pins."""

from pathlib import Path

from tests.fixtures.cwl_family import profiles

ROOT = Path(__file__).resolve().parent

if __name__ == '__main__':
    for name, token in [('tch', profiles.TOKENS[4]), ('gaussian', profiles.TOKENS[0])]:
        path = profiles.write_project(ROOT / 'native' / name, token)
        file = path / 'experiments/bank.edi'
        text = file.read_text().replace(
            '_peak.broad_lorentz_x 0\n', '_peak.broad_lorentz_x .023\n'
        )
        file.write_text(text.replace('_peak.broad_lorentz_y 0\n', '_peak.broad_lorentz_y .047\n'))

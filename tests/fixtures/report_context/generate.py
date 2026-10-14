"""Two distinct banks and a long scan declare the report context witnesses."""

import shutil
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[2]
for name, original in [
    ('joint', 'report_options/pairs'),
    ('long-scan', 'report_evolution/project'),
]:
    target = HERE / name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(ROOT / 'tests/fixtures' / original, target)
joint = HERE / 'joint'
first = (joint / 'experiments/bank.edi').read_text()
(joint / 'experiments/other.edi').write_text(first.replace('data_bank', 'data_other'))
analysis = joint / 'analysis/analysis.edi'
text = analysis.read_text().replace('_fitting_mode.type single', '_fitting_mode.type joint')
lines = [line for line in text.splitlines() if ' deterministic bank.background.' in line]
for line in lines:
    tokens = line.split()
    tokens[0] = str(int(tokens[0]) + 100)
    tokens[2] = tokens[2].replace('bank.', 'other.')
    tokens[3] = tokens[3].replace('bank.', 'other.')
    tokens[4] = '0.81' if float(tokens[4]) > 0.8 else '0.2'
    text += '\n' + ' '.join(tokens)
analysis.write_text(text + '\n')
scan = HERE / 'long-scan'
for file in (scan / 'scan').glob('*.dat'):
    file.unlink()
for index in range(20):
    (scan / 'scan' / f'point{index:02}.dat').write_text(
        f'TEMP {293.15 + index * 2}\n40 5 1\n44 6 1\n48 7 1\n52 8 1\n56 9 1\n'
        '60 10 1\n64 11 1\n68 12 1\n72 13 1\n'
    )
analysis = scan / 'analysis/analysis.edi'
analysis.write_text(
    analysis.read_text().replace('template_file point1.dat', 'template_file point12.dat')
)
results = scan / 'analysis/results.csv'
text = (
    results
    .read_text()
    .replace('point1.dat', 'point00.dat')
    .replace('point2.dat', 'point12.dat')
    .replace('point3.dat', 'point19.dat')
)
results.write_text(text)

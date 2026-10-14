"""Stage a short, genuine scan from the retained three-temperature reference."""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'tests/fixtures/scan_template/project'


def prepare(destination, count):
    destination = Path(destination)
    shutil.copytree(SOURCE, destination)
    data = destination / 'experiments/d20_scan'
    names = sorted(path.name for path in data.glob('*.dat'))
    if count not in {2, 3} or len(names) != 3:
        raise ValueError('The lifecycle vehicle must retain its declared measured scan files')
    for name in names[count:]:
        (data / name).unlink()
    analysis = destination / 'analysis/analysis.edi'
    text = analysis.read_text().replace(
        '_minimizer.max_iterations 1000', '_minimizer.max_iterations 1'
    )
    if '_fitting_mode.type sequential' not in text:
        raise ValueError('The input must remain a sequential scan')
    analysis.write_text(text)
    for path in (destination / 'analysis').glob('results*.csv'):
        path.unlink()
    return names[:count]

"""Author bounded measured-data app inputs; labelled state controls, no physics oracle."""

import argparse
import hashlib
import json
from pathlib import Path

import crysta
import numpy as np

from tests.fixtures.background_estimate.fitted_baseline import KINDS
from tests.fixtures.background_estimate.readonly import snapshot

HERE = Path(__file__).resolve().parent


def hashes(directory):
    return {
        str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(directory.rglob('*'))
        if p.is_file()
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine-source-commit', required=True)
    args = parser.parse_args()
    receipt = {
        'claim': 'REGRESSION INPUT: separately executed settled Auto/save/reload authoring flow',
        'engine_source_commit': args.engine_source_commit,
        'engine_stamp': crysta.__build_commit__,
        'engine_binary_sha256': hashlib.sha256(Path(crysta.__file__).read_bytes()).hexdigest(),
        'command': 'python -m tests.fixtures.background_estimate.generate_app_lifecycle '
        '--engine-source-commit ' + args.engine_source_commit,
        'sampling': 'every fourth original measured row, plus the last row; no interpolation',
        'scope': 'bounded app worker/type/Undo lifecycle; full measured inputs and Manual-fit '
        'pins remain separate, and no physics accuracy claim uses this subset',
        'cases': {},
    }
    for kind in KINDS:
        source = HERE / 'projects' / ('fitted-auto-' + kind)
        destination = HERE / 'projects' / ('fitted-auto-fast-' + kind)
        if destination.exists():
            raise ValueError('Bounded regression inputs must be authored into fresh destinations')
        project = crysta.Project.load(source)
        data = project.experiment.data
        x, y, sigma = map(
            np.asarray,
            (
                data.two_theta,
                data.intensity_meas,
                data.intensity_meas_su,
            ),
        )
        keep = np.unique(np.r_[np.arange(0, len(x), 4), len(x) - 1])
        project.experiment.data = crysta.PdCwlData(
            two_theta=x[keep], intensity_meas=y[keep], intensity_meas_su=sigma[keep]
        )
        project.analysis.calculate()
        project.analysis.calculate()
        rows = (
            project.experiment.background
            if kind == 'line-segment'
            else project.experiment.background_terms
        )
        for row in rows:
            (row.intensity if kind == 'line-segment' else row.coef).free = True
        project.save_as(destination)
        before = snapshot(project)
        reloaded = crysta.Project.load(destination)
        reloaded.analysis.calculate()
        if snapshot(reloaded) != before or not all(row[3] for row in before):
            raise ValueError(
                'The bounded saved input must retain every free row on first calculation'
            )
        receipt['cases'][kind] = {
            'source_sha256': hashes(source),
            'source_points': len(x),
            'measured_points': len(keep),
            'initial_rows': before,
            'sha256': hashes(destination),
        }
    (HERE / 'app-lifecycle.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()

"""Author a current saved guided input once; a state regression input, not a physics oracle."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import crysta

from tests.fixtures.background_estimate.lifecycle import persisted_points

HERE = Path(__file__).resolve().parent


def hashes(directory):
    return {
        p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(directory.rglob('*'))
        if p.is_file()
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine-source-commit', required=True)
    args = parser.parse_args()
    manifest_path = HERE / 'lifecycle-cases.json'
    manifest = json.loads(manifest_path.read_text())
    source = HERE / 'projects/lifecycle-guided'
    before = hashes(source)
    if before != manifest['cases']['lifecycle-guided']['sha256']:
        raise ValueError('The preceding labelled input must match its complete recorded inventory')
    destination = source.with_name('lifecycle-guided-current')
    if destination.exists():
        raise ValueError('The authoring destination must be fresh')
    project = crysta.Project.load(source)
    project.analysis.calculate()
    project.save_as(destination)
    reloaded = crysta.Project.load(destination)
    expected = [(r.position, r.intensity.value) for r in reloaded.experiment.background]
    reloaded.analysis.calculate()
    actual = [(r.position, r.intensity.value) for r in reloaded.experiment.background]
    if actual != expected:
        raise ValueError(
            'The new saved input must be settled before it can witness unchanged loading'
        )
    shutil.rmtree(source)
    destination.rename(source)
    manifest['cases']['lifecycle-guided'] = {
        'points': persisted_points(source),
        'sha256': hashes(source),
        'authoring': {
            'claim': 'REGRESSION INPUT: independently executed calculate/save/reload flow',
            'before_sha256': before,
            'engine_source_commit': args.engine_source_commit,
            'engine_stamp': crysta.__build_commit__,
            'engine_binary_sha256': hashlib.sha256(Path(crysta.__file__).read_bytes()).hexdigest(),
            'command': 'python -m tests.fixtures.background_estimate.generate_current_lifecycle '
            '--engine-source-commit ' + args.engine_source_commit,
            'adaptation': 'Before a digestless historical estimate; '
            'after a current saved baseline '
            'whose row-content digest excludes the free flag; no physics claim',
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()

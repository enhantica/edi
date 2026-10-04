"""Capture only  extension pins; never replace  pre-move pins.

These are post-feature serialization/golden REGRESSION PINS, not physics oracles.
Run with the tested package and its matching source; independent FullProf remains
in manifest.json. Every input byte must equal the named committed source first.
"""

import hashlib
import importlib.util
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = 'edi'
SPEC = importlib.util.spec_from_file_location(
    'legacy_bytes', ROOT / 'tests/fixtures/c34_t28_baseline/generate_bytes.py'
)
REFERENCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REFERENCE)
CASES = {'corpus:lif-xray-s1/project'}
if PACKAGE == 'edi':
    CASES.add('repo:docs/user/cli/pd-xray-cwl_lif_single/project')


def main():
    git = shutil.which('git')
    assert git is not None, ' regression capture requires Git'
    result = {'kind': ' post-feature regression pins', 'cases': {}, 'goldens': {}}
    with tempfile.TemporaryDirectory() as temporary:
        for index, name in enumerate(sorted(CASES)):
            source = REFERENCE.inputs()[name]
            repository = ROOT if name.startswith('repo:') else REFERENCE.corpus_root().parents[1]
            sha = subprocess.check_output(
                [git, '-C', str(repository), 'rev-parse', 'HEAD'], text=True
            ).strip()
            for path in sorted(source.rglob('*')):
                if path.is_file():
                    committed = subprocess.check_output([
                        git,
                        '-C',
                        str(repository),
                        'show',
                        sha + ':' + path.relative_to(repository).as_posix(),
                    ])
                    assert path.read_bytes() == committed, (
                        ' regression capture requires exact committed input bytes'
                    )
            result['cases'][name] = {
                'source_commit': sha,
                'input_sha256': REFERENCE.hashes(source),
                'saved_sha256': REFERENCE.observe(source, Path(temporary) / str(index)),
            }
    if PACKAGE == 'crysta':
        relative = 'tests/fitting/lif-xray-s1/expected.json'
        result['goldens'][relative] = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    Path(__file__).with_name('regression-pins.json').write_text(
        json.dumps(result, indent=2, sort_keys=True) + '\n'
    )


if __name__ == '__main__':
    main()

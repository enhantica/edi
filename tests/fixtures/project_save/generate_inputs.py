"""Record added or changed project inputs without replacing historical byte pins."""

import argparse
import hashlib
import json
from pathlib import Path

from tests.fixtures.cwl_family.historical import original_tokens

ROOT = Path(__file__).resolve().parents[3]
FOLDER = Path(__file__).resolve().parent
ADDITIONS = (
    'lam7o3-p021',
    'single-crystal-joint-larson',
    'single-crystal-senju-taurine-converged',
)


def hashes(folder):
    return {
        path.relative_to(folder).as_posix(): hashlib.sha256(
            original_tokens(path.read_bytes())
        ).hexdigest()
        for path in sorted(folder.rglob('*'))
        if path.is_file()
    }


def main(selected=()):
    baseline = json.loads((ROOT / 'tests/fixtures/c34_t28_baseline/saved-bytes.json').read_text())
    previous = baseline['post_feature_fixed_points']
    prior = json.loads((FOLDER / 'input-transitions.json').read_text()) if selected else {}
    cases = dict(prior.get('cases', {}))
    eligible = set(previous) | {'corpus:' + name + '/project' for name in ADDITIONS}
    if not set(selected) <= eligible:
        message = 'An input capture may select only an existing declared fixed-point witness'
        raise ValueError(message)
    for identity, row in previous.items():
        if selected and identity not in selected:
            continue
        if 'single-crystal' not in identity and '/sc-neut-' not in identity:
            continue
        kind, relative = identity.split(':', 1)
        folder = (ROOT if kind == 'repo' else ROOT / 'build/crysta-src/tests/fitting') / relative
        cases[identity] = {'before': row, 'after': {'input_sha256': hashes(folder)}}
    for name in ADDITIONS:
        identity = 'corpus:' + name + '/project'
        if selected and identity not in selected:
            continue
        folder = ROOT / 'build/crysta-src/tests/fitting' / name / 'project'
        if identity in previous or identity in baseline['cases']:
            raise ValueError('An added input cannot replace a historical witness')
        cases[identity] = {'before': None, 'after': {'input_sha256': hashes(folder)}}
    record = {
        **prior,
        'claim': 'REGRESSION PIN: committed input bytes, with the historical witness retained; '
        'second-save equality is the serialization invariant.',
        'cases': cases,
        'catalogue_identity_aliases': baseline.get('catalogue_identity_aliases', {}),
    }
    (FOLDER / 'input-transitions.json').write_text(
        json.dumps(record, indent=2, sort_keys=True) + '\n'
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', action='append', default=[])
    main(parser.parse_args().case)

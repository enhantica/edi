"""Archive the committed LiF count window beside its immutable retention witness."""

import copy
import hashlib
import json
from pathlib import Path

from tests.fixtures.example_catalogue.capture_adaptations import committed

HERE = Path(__file__).parent
ROOT = HERE.resolve().parents[2]
CASE = 'pd-xray-cwl_lif_single'
NAME = f'docs/user/cli/{CASE}/expected.json'
AFTER = 'fc877e53'


def main():
    inventory = json.loads((HERE / 'retained-projects.json').read_text())['projects']
    retained = next(row for row in inventory if row['id'] == CASE)
    before, after = (committed(revision, NAME) for revision in (AFTER + '^', AFTER))
    assert hashlib.sha256(before).hexdigest() == retained['sha256']['expected.json'], (
        'The LiF archive must start at the unchanged complete historical retention witness'
    )
    old, new = json.loads(before), json.loads(after)
    projected = copy.deepcopy(old)
    quantities = projected['variants']['fast-descent']['quantities']
    assert quantities['iterations'] == {
        'value': 5.0,
        'kind': 'regression-pin',
        'tol_abs': 0.0,
        'tol_rel': None,
    }, 'The original LiF count was an exact five-iteration regression pin'
    quantities['iterations'] = {
        'value': 4.5,
        'kind': 'regression-pin',
        'tol_abs': 0.5,
        'tol_rel': None,
    }
    assert projected == new, (
        'Only the documented LiF iteration midpoint and radius may differ; '
        'all quality pins, references, tolerances and schema remain exact'
    )
    assert (ROOT / NAME).read_bytes() == after, (
        'The archived LiF replacement must equal every current committed expectation byte'
    )
    target = HERE / 'retention-adaptations.json'
    document = json.loads(target.read_text())
    document['files'][NAME] = {
        'source_commit': AFTER,
        'reason': (
            'CI 44137760653: Windows count 4, Linux/macOS count 5; '
            'iteration midpoint 4.5/radius 0.5 only; all other bytes retained'
        ),
        'before_sha256': hashlib.sha256(before).hexdigest(),
        'after_sha256': hashlib.sha256(after).hexdigest(),
        'before': before.decode(),
        'after': after.decode(),
    }
    target.write_text(json.dumps(document, indent=2) + '\n')


if __name__ == '__main__':
    main()

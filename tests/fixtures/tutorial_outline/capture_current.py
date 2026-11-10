"""Capture chapter expectations from the independently supplied pinned upstream tree."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


def capture(repository, records):
    revision = subprocess.check_output(
        ['git', '-C', str(repository), 'rev-parse', 'cb2cda7b^{commit}'], text=True
    ).strip()
    contract = json.loads((Path(__file__).parents[1] / 'tutorial_cases/contract.json').read_text())
    by_id = {record['id']: record for record in records}
    simulation = by_id[contract['simulations'][0]]
    cases = {}
    for case in contract['cases']:
        record = by_id.get(case)
        if record is None:
            if case not in contract['simulations']:
                raise ValueError('A non-simulation case needs its declared published reference')
            record = {**simulation, 'id': case}
        source = 'docs/docs/tutorials/' + record['diffraction_lib']['tutorial'] + '.py'
        blob = subprocess.check_output(
            ['git', '-C', str(repository), 'rev-parse', revision + ':' + source], text=True
        ).strip()
        payload = subprocess.check_output(['git', '-C', str(repository), 'cat-file', 'blob', blob])
        sections = [
            re.sub(r'^[^\w]+', '', match[1]).strip()
            for line in payload.decode().splitlines()
            if (match := re.match(r'^# ## (.+)', line))
        ]
        cases[record['id']] = {
            'blob': blob,
            'sha256': hashlib.sha256(payload).hexdigest(),
            'sections': sections,
        }
    return {
        'repository': 'https://github.com/easyscience/diffraction-lib',
        'commit': revision,
        'adaptation': (
            'Use app vocabulary and create the empty project before its entities. '
            'The new single-crystal simulation follows the published simulation '
            'chapter outline; no numerical reference is claimed.'
        ),
        'cases': cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', type=Path)
    parser.add_argument('records', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    document = capture(args.repository, json.loads(args.records.read_text()))
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()

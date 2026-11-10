"""Capture published fit cycles using the committed gap case map, never edi implementations."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from tests.fixtures.tutorial_cases.contract import CASES, CONTRACT
from tests.fixtures.tutorial_cases.stages import observe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', type=Path)
    parser.add_argument('gap', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    revision = subprocess.check_output(
        ['git', '-C', str(args.repository), 'rev-parse', 'cb2cda7b^{commit}'], text=True
    ).strip()
    mapping = {}
    original = 0
    for line in args.gap.read_text().splitlines():
        match = re.fullmatch(r'\| ([\w-]+) \| (.+) \|', line)
        if not match or not match[1].startswith(('pd-', 'sc-')) or match[2].startswith('none'):
            continue
        case = match[1]
        tutorial = re.match(r'[\w-]+', match[2])[0]
        original += 1
        if case == 'pd-neut-cwl_yap-spodi_3k':
            case = 'pd-neut-cwl_yalo3-al2o3-spodi'  # Owner 36db88225 folds this counterpart.
        if case in CASES and case not in CONTRACT['simulations']:
            mapping[case] = tutorial
    result = {
        'commit': revision,
        'source': str(args.gap.name),
        'original_matched': original,
        'adaptation': 'Retired simulations are omitted; YAP counterpart follows the folded case.',
        'cases': {},
    }
    for case, tutorial in mapping.items():
        path = 'docs/docs/tutorials/' + tutorial + '.py'
        blob = subprocess.check_output([
            'git',
            '-C',
            str(args.repository),
            'show',
            revision + ':' + path,
        ])
        source_blob = subprocess.check_output(
            ['git', '-C', str(args.repository), 'rev-parse', revision + ':' + path], text=True
        ).strip()
        result['cases'][case] = {
            'source_blob': source_blob,
            'source_sha256': hashlib.sha256(blob).hexdigest(),
            **observe(blob.decode()),
        }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()

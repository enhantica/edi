"""Read an independently captured dictionary contract, including with a binary SDK."""

import argparse
import hashlib
import json
from pathlib import Path

import yaml

FIXTURE = Path(__file__).with_name('dictionary_reference.json')


def from_yaml(path):
    document = yaml.safe_load(path.read_text())
    category_keys = ('id', 'edi_name', 'title', 'loop_title', 'loop', 'icon', 'order', 'mark')
    item_keys = ('uid', 'category', 'display_name', 'display_units', 'dtype')
    return {
        'categories': [
            {key: row[key] for key in category_keys if key in row}
            for row in document['categories']
        ],
        'items': [
            {
                **{key: row[key] for key in item_keys if key in row},
                'options': [
                    {key: option[key] for key in ('token', 'display_name')}
                    for option in row.get('options', [])
                ],
            }
            for row in document['parameters'] + document.get('items', [])
        ],
    }


def reference():
    return json.loads(FIXTURE.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'sdk_path', nargs='?', help='Legacy observer argument; the SDK need not ship YAML'
    )
    parser.add_argument('--generate', type=Path)
    parser.add_argument('--revision')
    args = parser.parse_args()
    if args.generate:
        if not args.revision:
            parser.error('Capturing a dictionary requires its committed source revision')
        data = from_yaml(args.generate)
        data['source'] = {
            'revision': args.revision,
            'path': 'data/dictionary/parameters.yaml',
            'sha256': hashlib.sha256(args.generate.read_bytes()).hexdigest(),
        }
        FIXTURE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    else:
        print(json.dumps(reference()))


if __name__ == '__main__':
    main()

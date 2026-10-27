"""Read the selected SDK's YAML without going through the display bridge."""

import json
import sys
from pathlib import Path

import yaml


def reference(path):
    document = yaml.safe_load(path.read_text())
    return {
        'categories': document['categories'],
        'items': document['parameters'] + document.get('items', []),
    }


if __name__ == '__main__':
    print(json.dumps(reference(Path(sys.argv[1]))))

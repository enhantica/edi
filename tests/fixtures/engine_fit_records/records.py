"""Current model parity records, independently captured from the pinned engine CLI."""

import json
from pathlib import Path


def record(name):
    payload = json.loads(Path(__file__).with_name(name + '.json').read_text())
    fields = dict(line.split('=', 1) for line in payload['record'].splitlines())
    # The retained historical transcript predates these machine-report spellings.
    if 'reduced_chi_square' in fields:
        fields['reduced_chi2'] = fields['reduced_chi_square']
    for key, value in list(fields.items()):
        if key.endswith('.uncertainty'):
            fields[key.removesuffix('.uncertainty') + '.esd'] = value
    return fields

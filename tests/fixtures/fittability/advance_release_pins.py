"""Advance labelled byte regressions from sealed retained release receipts.

This never imports the scientific extension or creates new calculated references.
The independent triage established unchanged parameters/free flags and measured
inputs. Its full report hashes must be validated before using the retained saves.
"""

import argparse
import hashlib
import json
from pathlib import Path

from tests.fixtures.fittability.saved_reference import ROOT, fingerprints


def main():  # noqa: PLR0914 - one sealed transition keeps its evidence together
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seal', required=True, type=Path)
    parser.add_argument('--capture', required=True, type=Path)
    parser.add_argument('--parameters', required=True, type=Path)
    parser.add_argument('--measurements', required=True, type=Path)
    args = parser.parse_args()
    seal = json.loads(args.seal.read_text())
    reports = (args.capture, args.parameters, args.measurements)
    for path in reports:
        expected = seal['receipts'][str(path)]['sha256']
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Every retained evidence report must match its committed seal')
    rows = json.loads(args.capture.read_text())['rows']
    parameters = json.loads(args.parameters.read_text())
    measured = json.loads(args.measurements.read_text())

    def keys(values):
        return {(row['case'], row['rule']) for row in values}

    if (
        len(rows) != 20
        or len(keys(rows)) != 20
        or keys(rows) != keys(parameters)
        or keys(rows) != keys(measured)
    ):
        raise ValueError('The release transition must retain exactly its complete sealed case set')
    if not all(row['same_values_and_free_flags_as_previous_saved_output'] for row in parameters):
        raise ValueError(
            'A scientific parameter or free-flag change refuses this regression update'
        )
    root = Path(__file__).parent
    pins_path = root / 'saved-main.json'
    changes_path = root / 'rounded-save-transitions.json'
    pins = json.loads(pins_path.read_text())
    changes = json.loads(changes_path.read_text())
    for row in rows:
        case, rule = row['case'], row['rule']
        if row.get('projection_error') not in (
            None,
            'A live descriptive input must match its entire independently archived source, '
            'including every scientific byte',
        ):
            raise ValueError(
                'Only the independently repaired archival composition may be replayed'
            )
        if row.get('error'):
            raise ValueError('A failed retained release save cannot become a regression reference')
        expected = pins['projects'][case][rule]
        actual = fingerprints(Path(row['saved']), order_reference=expected, source=ROOT / case)
        changed = {
            name
            for name in actual.keys() | expected.keys()
            if actual.get(name) != expected.get(name)
        }
        if 'mismatches' in row and changed != set(row['mismatches']):
            raise ValueError('Every changed retained path must match the sealed release triage')
        if set(expected) - set(actual):
            raise ValueError('The release regression transition cannot remove a saved path')
        for name in sorted(changed):
            changes['changes'].append({
                'case': case,
                'rule': rule,
                'path': name,
                'before': expected.get(name),
                'after': actual[name],
                'reason': (
                    'Retained release byte regression; parameter/free and '
                    'measured-input equivalence sealed independently'
                ),
            })
        pins['projects'][case][rule] = actual
    changes['release_source'] = {
        'edi': seal['release_head'],
        'crysta': seal['crysta_head'],
        'capture_sha256': hashlib.sha256(args.capture.read_bytes()).hexdigest(),
        'parameters_sha256': hashlib.sha256(args.parameters.read_bytes()).hexdigest(),
        'measurements_sha256': hashlib.sha256(args.measurements.read_bytes()).hexdigest(),
    }
    pins_path.write_text(json.dumps(pins, indent=2, sort_keys=True) + '\n')
    changes_path.write_text(json.dumps(changes, indent=2) + '\n')


if __name__ == '__main__':
    main()

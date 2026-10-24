"""Derive experiment spellings from the official dictionaries and frozen upstream tables."""

import argparse
import json
from pathlib import Path

from reference import key, official_frames

QUANTITIES = {
    'instrument.setup_wavelength': '_diffrn_radiation_wavelength.value',
    'peak.broad_gauss_u': None,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    frames = official_frames(args.source)
    here = Path(__file__).resolve().parent
    upstream = json.loads((here / 'upstream-names.json').read_text())
    output = {}
    for uid, canonical in QUANTITIES.items():
        edi = '_' + uid
        names = {
            name
            for row in upstream['entries']
            if edi in row['edi_names']
            for name in row['cif_names']
        }
        names.add('_edi_' + uid)
        if canonical is not None and key(canonical) in frames:
            names.discard('_edi_' + uid)
            names.update(frames[key(canonical)][1])
        # Both CIF notations name the same quantity, including extension categories.
        names |= {name.replace('.', '_', 1) for name in names}
        output[uid] = sorted(names)
    (here / 'experiment_names.json').write_text(json.dumps(output, indent=2) + '\n')


if __name__ == '__main__':
    main()

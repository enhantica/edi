"""Read structure-name witnesses directly from the official and upstream references."""

import argparse
import hashlib
import json
from pathlib import Path

from reference import key, official_frames

QUANTITIES = {
    '_cell.length_a': '_cell.length_a',
    '_cell.length_b': '_cell.length_b',
    '_cell.length_c': '_cell.length_c',
    '_cell.angle_alpha': '_cell.angle_alpha',
    '_cell.angle_beta': '_cell.angle_beta',
    '_cell.angle_gamma': '_cell.angle_gamma',
    '_space_group.name_h_m': '_space_group.name_H-M_alt',
    '_space_group.it_number': '_space_group.IT_number',
    '_atom_site.id': '_atom_site.label',
    '_atom_site.type_symbol': '_atom_site.type_symbol',
    '_atom_site.fract_x': '_atom_site.fract_x',
    '_atom_site.fract_y': '_atom_site.fract_y',
    '_atom_site.fract_z': '_atom_site.fract_z',
    '_atom_site.occupancy': '_atom_site.occupancy',
    '_atom_site.wyckoff_letter': '_atom_site.Wyckoff_symbol',
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('dictionary_root', type=Path)
    args = parser.parse_args()
    frames = official_frames(args.dictionary_root)
    upstream = json.loads(Path(__file__).with_name('upstream-names.json').read_text())
    names = {}
    for edi, canonical in QUANTITIES.items():
        _default, aliases = frames[key(canonical)]
        external = {
            name
            for row in upstream['entries']
            if edi in row['edi_names']
            for name in row['cif_names']
        }
        names[canonical] = sorted(aliases | external)
    hashes = {
        filename: hashlib.sha256(
            (args.dictionary_root / 'data/cif-dictionaries' / filename).read_bytes()
        ).hexdigest()
        for filename in ('cif_core.dic', 'cif_pow.dic')
    }
    output = {
        'official_sha256': hashes,
        'upstream_sha256': upstream['sha256'],
        'names': names,
        'official_defaults': sorted({name for name, _aliases in frames.values()}),
    }
    Path(__file__).with_name('structure_names.json').write_text(
        json.dumps(output, indent=2) + '\n'
    )


if __name__ == '__main__':
    main()

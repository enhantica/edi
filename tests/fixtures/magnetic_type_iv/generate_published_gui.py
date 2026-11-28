"""Copy the independently idealised MAGNDATA parent into the live note witness."""

import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('reference_parent', type=Path)
    args = parser.parse_args()
    root = Path(__file__).parent
    folder = root / 'gui/note-mn3o4'
    for subfolder in ['structures', 'experiments']:
        (folder / subfolder).mkdir(parents=True, exist_ok=True)
    source = args.reference_parent.read_bytes()
    (folder / 'structures/parent.edi').write_bytes(source)
    (folder / 'project.edi').write_text('_edi.schema_version 3\n_metadata.name published_note\n')
    bank = (root / 'gui/popup/experiments/first.edi').read_text()
    bank = bank.split('loop_\n_preferred_orientation.')[0]
    bank = bank.replace('unrelated .9 true\n', '').replace('parent 3.6 true', 'parent 1 true')
    (folder / 'experiments/first.edi').write_text(bank)
    (folder / 'PROVENANCE.json').write_text(
        json.dumps(
            {
                'source': 'MAGNDATA 1.1 Mn3O4; independent parent from generate_parents.py',
                'parent_sha256': hashlib.sha256(source).hexdigest(),
                'parent_space_group': 'Pbcm',
                'k': '1/2,0,0',
                'bns': '62.452',
                'expected': (
                    'A nonzero seeded transverse magnetic signal in the 20 to 110 degree window'
                ),
                'reference': 'https://webbdcrista1.ehu.es/magndata/index.php?index=1.1',
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()

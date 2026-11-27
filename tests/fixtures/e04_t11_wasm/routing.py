"""Materialize browser routing inputs from the committed native CLI project.

Names and empty/full inventories are deliberate test inputs. Scientific bytes are
copied as inputs, never used as a generated correctness oracle.
"""

import re
import shutil
import sys
from pathlib import Path


def materialize(target, *, replacement=False):
    root = Path(__file__).resolve().parents[3]
    source = root / 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-4/project'
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    for name in ('routing_initial', 'routing_a', 'routing_b'):
        folder = target / name
        shutil.copytree(source, folder)
        marker = folder / 'project.edi'
        marker.write_text(
            re.sub(
                r'^_metadata.name\s+.*$',
                f'_metadata.name {name}',
                marker.read_text(),
                flags=re.MULTILINE,
            )
        )
    if replacement:
        folder = target / 'routing_empty'
        folder.mkdir()
        (folder / 'project.edi').write_text(
            '_edi.schema_version 2\n'
            '_metadata.name routing_empty\n'
            '_metadata.description "A project with no data"\n',
            encoding='utf-8',
        )
    files = target / 'blocks'
    files.mkdir()
    structure = (source / 'structures/lbco.edi').read_text()
    (files / 'structure.edi').write_text(structure)
    (files / 'structure-2.edi').write_text(structure.replace('data_lbco', 'data_other', 1))
    experiment = (source / 'experiments/hrpt.edi').read_text()
    # Keep the linked-structure loop pointing at the structure loaded by the browser.
    for number in (1, 2):
        (files / f'experiment-{number}.edi').write_text(
            experiment.replace('data_hrpt', f'data_imported_{number}', 1)
        )


if __name__ == '__main__':
    materialize(sys.argv[1], replacement='--replacement' in sys.argv[2:])

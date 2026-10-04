"""Materialize browser routing inputs from the committed native CLI project.

Names and empty/full inventories are deliberate test inputs. Scientific bytes are
copied as inputs, never used as a generated correctness oracle.
"""

import re
import shutil
import sys
from pathlib import Path


def materialize(target):
    root = Path(__file__).resolve().parents[3]
    source = root / 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-4/project'
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    for name in ('routing_a', 'routing_b'):
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
    files = target / 'blocks'
    files.mkdir()
    structure = (source / 'structures/lbco.edi').read_text()
    (files / 'structure.edi').write_text(structure)
    experiment = (source / 'experiments/hrpt.edi').read_text()
    # The standalone format requires its linked-structure loop even when the
    # receiving live project has no structure yet. Retain the committed valid block.
    for number in (1, 2):
        (files / f'experiment-{number}.edi').write_text(
            experiment.replace('data_hrpt', f'data_imported_{number}', 1)
        )


if __name__ == '__main__':
    materialize(sys.argv[1])

# SPDX-License-Identifier: BSD-3-Clause
"""Check that an exported crysta source is the tree an SDK was built from.

  crysta_source_tree.py id SOURCE                print the Git tree id of the exported files
  crysta_source_tree.py check SOURCE MANIFEST    exit 1 unless it is the SDK manifest's source_tree

The id comes from the files themselves, through an empty Git directory and a temporary index, so
nothing written beside the source can vouch for it. The two files an export adds are left out.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# What crysta-src.sh writes into an export, at its top level.
GENERATED = ('CRYSTA_SOURCE_SHA', 'runner-source-objects.json')
# The bytes and modes as they are on disk, whatever attributes or settings say.
SETTINGS = (
    'core.autocrlf=false',
    'core.fileMode=true',
    'core.symlinks=true',
    'core.bare=false',
    'core.looseCompression=0',
    f'core.attributesFile={os.devnull}',
    f'core.excludesFile={os.devnull}',
)


def tree_id(source: Path) -> str:
    """The Git tree id of every file under ``source`` but the generated ones."""
    with tempfile.TemporaryDirectory() as scratch:
        home = Path(scratch) / 'git'
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        env |= {'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull}

        def git(*args: str) -> str:
            run = subprocess.run(
                ['git', *args], env=env, cwd=source, capture_output=True, text=True, check=False
            )
            if run.returncode:
                raise SystemExit(f'crysta-source-tree: git {args[-1]} failed on {source}')
            return run.stdout.strip()

        git('init', '-q', '--bare', '--template=', str(home))
        (home / 'info').mkdir(exist_ok=True)
        (home / 'info/attributes').write_text(
            '* -text -filter -ident -working-tree-encoding\n', encoding='utf-8'
        )
        env |= {'GIT_DIR': str(home), 'GIT_WORK_TREE': str(source.resolve())}
        env |= {'GIT_INDEX_FILE': str(home / 'export-index')}
        options = [part for setting in SETTINGS for part in ('-c', setting)]
        git(*options, 'add', '--all', '--force', '.')
        git('update-index', '--force-remove', '--', *GENERATED)
        return git('write-tree')


def main() -> int:
    """Print the id, or compare it with a manifest's."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('id', 'check'):
        commands.add_parser(name).add_argument('source', type=Path)
    commands.choices['check'].add_argument('manifest', type=Path)
    args = parser.parse_args()
    if not args.source.is_dir():
        print(f'crysta-source-tree: {args.source} is not a folder', file=sys.stderr)
        return 1
    found = tree_id(args.source)
    if args.command == 'id':
        print(found)
        return 0
    try:
        want = json.loads(args.manifest.read_text(encoding='utf-8'))['source_tree']
    except (OSError, ValueError, KeyError, TypeError):
        print(f'crysta-source-tree: {args.manifest} names no source_tree', file=sys.stderr)
        return 1
    if found != want:
        print(f'crysta-source-tree: {args.source} is tree {found}, not {want}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

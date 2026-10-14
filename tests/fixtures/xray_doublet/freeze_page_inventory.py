"""Record the committed pre-feature page inventory once at authoring time."""

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = 'bd72193'
git = shutil.which('git')
if git is None:
    message = 'The inventory generator requires git'
    raise RuntimeError(message)
listing = subprocess.check_output(
    [git, '-C', str(ROOT), 'ls-tree', '-r', '--name-only', BASE, 'docs/dev/verification'],
    text=True,
)
pages = sorted(Path(line).stem for line in listing.splitlines() if line.endswith('.py'))
(Path(__file__).parent / 'page-baseline.json').write_text(
    json.dumps(
        {'provenance': 'Committed edi main snapshot ' + BASE, 'before_pages': pages}, indent=2
    )
    + '\n'
)

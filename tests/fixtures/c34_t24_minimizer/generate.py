"""Capture the original seed analysis bytes from edi main before ."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = '61c3e03'


def read(path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{SOURCE}:{path}'], text=True)


def main():
    ids = json.loads(read('tests/fixtures/c34_t23_cli_projects/project-ids.json'))[
        'source_to_project'
    ]
    rows = {
        source: read(f'docs/user/cli/{pid}/project/analysis/analysis.edi')
        for source, pid in ids.items()
    }
    Path(__file__).with_name('seed-analysis-before.json').write_text(
        json.dumps(rows, indent=2) + '\n'
    )
    Path(__file__).with_name('scan-expected-before.json').write_text(
        read('docs/user/cli/pd-neut-cwl_cosio-d20_scan-3f/expected.json')
    )


if __name__ == '__main__':
    main()

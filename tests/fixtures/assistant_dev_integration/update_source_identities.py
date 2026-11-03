"""Record source regression pins from the commits that changed their contract."""

import hashlib
import json
import re
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def committed(revision, path):
    return subprocess.check_output(['git', 'show', f'{revision}:{path}'], cwd=ROOT)


def generate():
    baseline = json.loads((HERE / 'baseline.json').read_text())
    gui_source = '8016dd521096e5e6985a3c8b68430ce464ee35ce'
    dev_source = 'f069972c75913ae85e66197931b29324b499129c'
    merged_source = '4df77c9e'
    specs = {
        'gui_commit': ('cmake/EdiGuiBase.cmake', gui_source),
        'sdk_tag': ('pixi.toml', dev_source),
        'docs/dev/adrs/0038-colour-schemes-and-their-rules.md': (
            'docs/dev/adrs/0038-colour-schemes-and-their-rules.md',
            dev_source,
        ),
        'docs/dev/adrs/0041-scan-pattern-views.md': (
            'docs/dev/adrs/0041-scan-pattern-views.md',
            merged_source,
        ),
    }
    updates = {}
    for key, (path, revision) in specs.items():
        commit = subprocess.check_output(
            ['git', 'rev-parse', f'{revision}^{{commit}}'], cwd=ROOT, text=True
        ).strip()
        content = committed(commit, path)
        if key == 'gui_commit':
            after = (
                re
                .search(rb'(?m)^set\(EDI_GUI_COMPONENTS_SHA\s+([0-9a-f]{40})\)', content)
                .group(1)
                .decode()
            )
        elif key == 'sdk_tag':
            config = tomllib.loads(content.decode())
            tags = {
                target['activation']['env']['CRYSTA_SDK_TAG']
                for target in config['target'].values()
                if 'CRYSTA_SDK_TAG' in target.get('activation', {}).get('env', {})
            }
            if len(tags) != 1:
                raise ValueError('The source commit must declare one platform SDK identity')
            after = tags.pop()
        else:
            after = hashlib.sha256(content).hexdigest()
        before = baseline[key] if key in baseline else baseline['preserved_files'][key]
        updates[key] = {'before': before, 'after': after, 'source_commit': commit, 'path': path}
    (HERE / 'source_updates.json').write_text(json.dumps(updates, indent=2) + '\n')


if __name__ == '__main__':
    generate()

"""The current application link set must be represented in its bundled notices."""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ORACLE = json.loads((ROOT / 'tests/fixtures/e04_t12_public_release/oracle.json').read_text())


def test_real_application_links_have_local_dependency_notices():
    binary = ROOT / 'build/app/app/edi_app'
    assert binary.is_file(), 'the app licence gate must inspect the actual built application'
    command = ['otool', '-L'] if sys.platform == 'darwin' else ['ldd']
    executable = shutil.which(command[0])
    assert executable, 'the application licence check requires the platform link-set inspector'
    result = subprocess.run(
        [executable, *command[1:], str(binary)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0 and result.stdout.strip(), (
        'the real application must expose a nonempty inspectable link set: ' + result.stderr
    )
    assert 'not found' not in result.stdout, 'the inspected app must have all dynamic dependencies'
    notice = ROOT / 'THIRD-PARTY-NOTICES'
    assert notice.is_file(), 'the built app must carry its local dependency licence notices'
    text = notice.read_text().casefold()
    for library, component in ORACLE['linked_libraries'].items():
        if library in result.stdout:
            assert component.casefold() in text, (
                'a linked library must have a bundled component notice: ' + component
            )
    # FTL's preferred attribution is a copyright notice, not a JPEG-style credit.
    assert re.search(
        r'portions of this software are copyright © [0-9]{4} the freetype '
        r'project \(https://(?:www\.)?freetype\.org\). all rights reserved\.',
        ' '.join(text.split()),
    ), 'the bundled FreeType notice must retain the FTL attribution with an actual year'
    for component in ('Eigen', 'nanobind', 'robin-map', 'crysta'):
        assert component.casefold() in text, (
            'statically included dependencies need notices too: ' + component
        )

"""A renderer-independent check of the real maintenance walk admission script."""

import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.native_process import fixture_shell

ROOT = Path(__file__).resolve().parents[3]
PAGES = {
    'add': (
        'Introduction',
        'AssistantForm',
        'ReadyForInstallation',
        'PerformInstallation',
        'Finished',
    ),
    'update': ('Introduction', 'ReadyForInstallation', 'PerformInstallation', 'Finished'),
    'remove': ('Introduction', 'ReadyForInstallation', 'PerformInstallation', 'Finished'),
}


def executable(path, text):
    path.write_text('#!/bin/bash\nset -eu\n' + text, encoding='utf-8', newline='\n')
    path.chmod(0o755)


@pytest.mark.parametrize('mode', list(PAGES))
@pytest.mark.parametrize(
    'evidence', ['aggregate-only', 'tree'], ids=['missing-page-reads', 'tree']
)
def test_maintenance_accessibility_requires_complete_tree_free_page_reads(
    tmp_path, mode, evidence
):
    binary = tmp_path / 'MaintenanceTool.app/Contents/MacOS/MaintenanceTool'
    binary.parent.mkdir(parents=True)
    executable(
        binary,
        """
for page in ${A11Y_EXPECT_PAGES//,/ }; do
  touch "$EDI_INSTALLER_CAPTURE/maintenance-$page-light.png"
done
touch "$TEST_ROOT/walk-finished"
""",
    )
    shim = tmp_path / 'bin'
    shim.mkdir()
    # The real shell validates its observations. Only the process ports are fixtures.
    executable(shim / 'sleep', 'exec /bin/sleep .025\n')
    executable(
        shim / 'swiftc',
        r"""
test "$1" = -O && test "$2" = -o
cat > "$3" <<'CLIENT'
#!/bin/bash
if [ "$WALK_EVIDENCE" = tree ]; then
  printf '  AXOutline maintenance component list\n'
fi
printf 'AXWindow Introduction\nlayout-pages: 1\na11y-client: 7 multiple-attribute queries\n'
touch "$TEST_ROOT/client-finished"
CLIENT
chmod +x "$3"
""",
    )
    env = {
        **os.environ,
        'HOME': tmp_path.as_posix(),
        'TMPDIR': tmp_path.as_posix(),
        'TEST_ROOT': tmp_path.as_posix(),
        'WALK_EVIDENCE': evidence,
        'A11Y_EXPECT_PAGES': ','.join(PAGES[mode]),
        'EDI_INSTALLER_MAINTENANCE_MODE': mode,
    }
    result = subprocess.run(
        fixture_shell(shim, 'exec "$BASH" "$@"')
        + [
            (ROOT / 'tools/installer/a11y-check.sh').as_posix(),
            binary.parents[2].as_posix(),
            (tmp_path / 'logs').as_posix(),
            '--own-script',
        ],
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert (tmp_path / 'walk-finished').is_file() and (tmp_path / 'client-finished').is_file(), (
        'The check consumed the completed walk and accessibility ports\n'
        f'{result.stdout}{result.stderr}'
    )
    assert result.returncode != 0, (
        f'Maintenance {mode} refuses incomplete or tree-bearing evidence despite the captures'
    )

""": native file-open observation closes polling and eager-copy escapes.

Darwin uses the shared observer's explicit dyld interposition, Linux LD_PRELOAD.
The positive control requires native reads even if Python's audit hook sees data:
unsupported injection must fail visibly, never silently satisfy the I/O bounds.
"""

import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from conftest import _build_native_observer  # noqa: PLC2701 - reuse the shared test observer

ROOT = Path(__file__).resolve().parents[3]
CASE = (
    Path(os.environ.get('EDI_CRYSTA_CORPUS_ROOT', ROOT / 'build/crysta-src/tests/fitting'))
    / 'cosio-d20-scan-3f/project'
)


@pytest.fixture(scope='module')
def native_observer(tmp_path_factory):
    return _build_native_observer(tmp_path_factory.mktemp('-observer'))


PROBE = r"""
import json, os, pathlib, runpy, sys
import edi
project, log, result, mode = sys.argv[1:]
python_opens = []
def audit(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes)):
        path = os.fsdecode(args[0])
        if path.endswith('.dat'): python_opens.append(path)
sys.addaudithook(audit)
def native_data_opens():
    lines = pathlib.Path(log).read_text().splitlines()
    return [line.split('\t', 1)[1] for line in lines
            if '\t' in line and line.endswith('.dat')]
def data_opens():
    return python_opens + native_data_opens()
os.environ['EDI_C08_NATIVE_OBSERVER_ACTIVE'] = '1'
if mode == 'events':
    snapshots = []
    def complete(row): snapshots.append(data_opens())
    edi.Project.load(project).analysis.fit(on_file_complete=complete)
    payload = snapshots
else:
    sys.argv = ['edi', 'fit', project, '--verbosity', 'off'] + (['--dry'] if mode == 'dry' else [])
    try:
        runpy.run_module('edi', run_name='__main__')
    except SystemExit as end:
        if end.code: raise
    payload = data_opens()
pathlib.Path(result).write_text(json.dumps({'observed': payload, 'native': native_data_opens()}))
"""


def _run(tmp_path, native_observer, mode):
    target = tmp_path / mode
    shutil.copytree(CASE, target)
    analysis = target / 'analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text().replace(
            '_minimizer.max_iterations 1000', '_minimizer.max_iterations 1'
        )
    )
    library, variable = native_observer
    log, result = tmp_path / f'{mode}.log', tmp_path / f'{mode}.json'
    env = {
        **os.environ,
        variable: str(library),
        'EDI_C08_NATIVE_OBSERVER_LOG': str(log),
        'OMP_NUM_THREADS': '1',
    }
    if sys.platform == 'darwin':
        # Explicit dyld tuples preserve two-level binding; flat namespace is unnecessary.
        env.pop('DYLD_FORCE_FLAT_NAMESPACE', None)
    completed = subprocess.run(
        [sys.executable, '-c', PROBE, str(target), str(log), str(result), mode],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
        env=env,
    )
    assert completed.returncode == 0, (
        f' native I/O probe must execute its real scan: {completed.stderr}'
    )
    return json.loads(result.read_text())


def test_native_observer_reaches_the_real_data_reads(tmp_path, native_observer):
    observed = _run(tmp_path, native_observer, 'normal')['native']
    assert len({Path(path).name for path in observed}) == 3, (
        ' gate 5: the positive native-observer control must reach all scan files'
    )


def test_completion_precedes_opening_the_next_data_file(tmp_path, native_observer):
    snapshots = _run(tmp_path, native_observer, 'events')['observed']
    assert len(snapshots) == 3, ' gate 5: real native scan must emit all file-completion events'
    counts = [len({Path(path).name for path in rows}) for rows in snapshots]
    assert counts == [1, 2, 3], (
        ' gate 5: completion must fire before opening the NEXT data file; '
        f'native data-open counts at events={counts}, polling delivers late'
    )


def test_dry_scan_has_no_extra_native_data_opens(tmp_path, native_observer):
    # The ordinary CLI saves after fitting, which can reread scan files. Compare
    # with the final completion boundary: all fit reads, before persistence.
    normal = _run(tmp_path, native_observer, 'events')['observed'][-1]
    dry = _run(tmp_path, native_observer, 'dry')['observed']
    assert len({Path(path).name for path in normal}) == 3, (
        ' gate 5: native observer must actually reach every scan data read'
    )
    assert Counter(Path(path).name for path in dry) == Counter(
        Path(path).name for path in normal
    ), (
        ' gate 5: --dry must perform the same per-file data reads as a real fit, '
        'with no additional opens for scratch copies'
    )

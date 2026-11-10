"Run the delivered scan endpoint with an optional post-validation I/O failure."

import ctypes
import importlib
import os
import sys
from pathlib import Path

sys.meta_path[:] = [
    finder
    for finder in sys.meta_path
    if type(finder).__module__ not in {'_crysta_editable', '_edi_editable'}
]
engine = importlib.import_module(sys.argv[1])
project = engine.Project.load(Path(sys.argv[2]))
if len(sys.argv) > 4:
    project._dry_run_into(sys.argv[4])


def iteration(_step):
    if os.environ.get('SCAN_FAULT_READ_PATH'):
        ctypes.CDLL(None).setenv(b'SCAN_FAULT_ARMED', b'1', 1)


print('scan-enter', flush=True)
if sys.argv[3] == 'direct' and sys.argv[1] == 'edi':
    getattr(project, 'fit_' + project.analysis.fitting_mode)(
        on_iteration=iteration, on_scan_start=lambda _scan: None
    )
elif sys.argv[1] == 'crysta':
    project.fit(on_iteration=iteration)
else:
    project.analysis.fit(on_iteration=iteration, on_scan_start=lambda _scan: None)
print('scan-complete', flush=True)

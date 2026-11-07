# SPDX-License-Identifier: BSD-3-Clause
"""Exercise independent native trial-lock conservation checks."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    'observersCannotEditOrSaveDuringSettlement',
    'stopCannotRestoreAnotherOwner',
    'markerUnwindsOnExceptionAndDeletedOwner',
    'notificationCannotLendItsWriteExemption',
    'structureViewAndReportCannotWriteDuringTrial',
    'rollbackRemovesOnlyTrialReportFiles',
    'interruptedSecondFitRestoresFirstRecord',
]


@pytest.mark.parametrize('case', CASES)
def test_native_trial_lock_conserves_accepted_state(case):
    suffix = '.exe' if os.name == 'nt' else ''
    executable = ROOT / f'build/app/assistant-ui-probe/assistant_independent_lock{suffix}'
    result = subprocess.run(
        [str(executable), case],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        env={
            **os.environ,
            'QT_QPA_PLATFORM': os.environ.get('QT_QPA_PLATFORM', 'offscreen'),
            'QT_QUICK_BACKEND': 'software',
        },
    )
    assert result.returncode == 0 and '0 failed' in result.stdout, (
        'The native trial-lock invariant must hold: ' + case + '\n' + result.stdout + result.stderr
    )

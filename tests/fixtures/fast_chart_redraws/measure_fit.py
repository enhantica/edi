"""Time both chart tabs and both Every pattern choices through the real UI."""

import json
import os
from pathlib import Path

from tests.fixtures.fast_chart_redraws.rendering import ROOT, actor, capture, qt_reference
from tests.fixtures.fast_chart_redraws.timing import fit_tab_comparisons

LABELS = {
    'catchup': 'Every pattern, display catches up',
    'wait': 'Every pattern, fit waits for the display',
    'adaptive': 'Adaptive',
}
CASE_TIMEOUT_SECONDS = 150


def run_sample(destination, mode, tab, backend):
    if mode not in LABELS or tab not in {'pattern', 'stacked'}:
        raise ValueError('A fit timing actor needs one declared mode and chart tab')
    destination.mkdir(parents=True, exist_ok=False)
    case = 'ScanUpdates::test_timing_' + tab + '_' + mode
    command = [
        Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests')),
        '-input',
        ROOT / 'tests/system/app/ScanUpdates.qml',
        '-o',
        '-,txt',
        case,
    ]
    print(f'Fit timing actor: {case}; one case, watchdog {CASE_TIMEOUT_SECONDS} s', flush=True)
    status, log = capture(command, timeout=CASE_TIMEOUT_SECONDS)
    if status != 0:
        raise RuntimeError('The real sequential-fit timing actor must finish: ' + log)
    observed = qt_reference(log)
    if observed != backend:
        raise ValueError('Every fit timing must retain the independently observed Qt backend')
    receipts = [
        json.loads(line.split('FIT_TIMING ', 1)[1])
        for line in log.splitlines()
        if 'FIT_TIMING ' in line
    ]
    if len(receipts) != 1:
        raise ValueError('Each fit timing needs exactly one completed real UI receipt')
    receipt = receipts[0]
    if receipt['selection'] != LABELS[mode] or receipt['tab'] != tab or receipt['fitted'] != 162:
        raise ValueError(
            'The timed fit must use the requested actual UI choice, tab and complete scan'
        )
    sample = {'command': list(map(str, command)), 'backend': observed, **receipt}
    (destination / 'sample.json').write_text(json.dumps(sample, indent=2) + '\n')
    return sample


def measure_fit_tabs(directory, repetitions=3):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    status, output = actor('test_qt_reference')
    if status != 0:
        raise RuntimeError(
            'Fit timing requires the independent Qt renderer observation: ' + output
        )
    backend = qt_reference(output)
    fits = {
        tab: {'display_catches_up_ms': [], 'fit_waits_for_display_ms': [], 'adaptive_ms': []}
        for tab in ('pattern', 'stacked')
    }
    fields = {
        'catchup': 'display_catches_up_ms',
        'wait': 'fit_waits_for_display_ms',
        'adaptive': 'adaptive_ms',
    }
    receipts = []
    for repeat in range(repetitions):
        for tab in fits:
            modes = (
                ('catchup', 'wait', 'adaptive')
                if repeat % 2 == 0
                else ('adaptive', 'wait', 'catchup')
            )
            for mode in modes:
                sample = run_sample(directory / f'{tab}-{mode}-{repeat}', mode, tab, backend)
                fits[tab][fields[mode]].append(sample['milliseconds'])
                receipts.append(sample)
                print(
                    'Fit timing complete: ' + tab + ' ' + mode + ' repeat ' + str(repeat),
                    flush=True,
                )
    result = {
        'backend': backend,
        'fits': fits,
        'comparisons': fit_tab_comparisons(fits, backend=backend),
        'receipts': receipts,
    }
    print('Fit samples by backend and tab: ' + json.dumps(result), flush=True)
    (directory / 'fit-comparisons.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    import sys

    measure_fit_tabs(sys.argv[1])

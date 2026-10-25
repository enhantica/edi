"""Run both chart tabs through the app's real sequential-fit timing route."""

import csv
import json
import os
from pathlib import Path

from tests.fixtures.fast_chart_redraws.rendering import ROOT, actor, capture, qt_reference
from tests.fixtures.fast_chart_redraws.timing import fit_tab_comparisons


def run_sample(destination, scenario, backend):
    destination.mkdir(parents=True, exist_ok=False)
    command = [
        Path(os.environ.get('EDI_APP_BINARY', ROOT / 'build/app/app/edi_app')),
        '--demo',
        destination,
        '--demo-only',
        scenario,
    ]
    status, log = capture(command, env=dict(os.environ, QSG_INFO='1'), timeout=180)
    if status != 0:
        raise RuntimeError('The real sequential-fit timing route must finish: ' + log)
    if backend['api'].lower() not in log.lower() or (
        backend['api'] == 'OpenGL' and backend['renderer'] not in log
    ):
        raise ValueError('Every fit timing must identify the observed Qt backend: ' + log)
    with (destination / 'timings.tsv').open() as stream:
        rows = list(csv.reader(stream, delimiter='\t'))
    selected = [row for row in rows if len(row) == 3 and row[:2] == [scenario, 'fit']]
    if len(selected) != 1:
        raise ValueError('Each timed app invocation must produce its requested tab and mode')
    return {
        'command': list(map(str, command)),
        'backend': backend,
        'timings': rows,
        'milliseconds': float(selected[0][2]),
    }


def measure_fit_tabs(directory, repetitions=3):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    status, output = actor('test_qt_reference')
    if status != 0:
        raise RuntimeError(
            'Fit timing requires the independent Qt renderer observation: ' + output
        )
    backend = qt_reference(output)
    fits = {tab: {'every_pattern_ms': [], 'adaptive_ms': []} for tab in ('pattern', 'stacked')}
    receipts = []
    for repeat in range(repetitions):
        for tab in fits:
            modes = ('every', 'adaptive') if repeat % 2 == 0 else ('adaptive', 'every')
            for mode in modes:
                scenario = f'perf-fit-{mode}-{tab}'
                sample = run_sample(directory / f'{scenario}-{repeat}', scenario, backend)
                field = 'every_pattern_ms' if mode == 'every' else 'adaptive_ms'
                fits[tab][field].append(sample['milliseconds'])
                receipts.append(sample)
                print('Fit timing complete: ' + scenario + ' repeat ' + str(repeat), flush=True)
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

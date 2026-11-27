"""Run: python3 tests/fixtures/gui_contract_report/check_reducer.py

Feeds the layout report small summaries and checks that a receipt counting nothing,
an unsampled table and a missing witness never read as a pass.
"""

import pathlib
import subprocess
import sys
import tempfile

REPORT = pathlib.Path(__file__).resolve().parents[3] / 'tools' / 'dev' / 'gui_contract_report.py'
FRAME = 'e58-sweep-1-demo-full-1280x800'
WITNESS = ''.join(
    f'{FRAME}\t{r}:checked\ttable\t2 things\n' for r in ('T1', 'T2', 'T3', 'T4', 'T5', 'T9')
)


def report(lines: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        (pathlib.Path(tmp) / 'summary.tsv').write_text(lines, encoding='utf-8')
        done = subprocess.run(
            [sys.executable, '-I', str(REPORT), tmp], capture_output=True, text=True, check=False
        )
    return done.stdout


def expect(name: str, text: str, wanted: str, *, present: bool) -> None:
    if (wanted in text) != present:
        sys.exit(f'{name}: {"missing" if present else "unexpected"} {wanted!r}\n{text}')


expect(
    'witness missing',
    report(WITNESS.replace('T5:checked', 'T5:inapplicable')),
    'no measurement witnessed: T5',
    present=True,
)
expect('all witnessed', report(WITNESS), 'no measurement witnessed', present=False)
expect(
    'zero count',
    report(WITNESS + f'{FRAME}\tT5:checked\tt2\t0 kinds, 0 columns\n'),
    'no measurement witnessed',
    present=False,
)
expect(
    'unsampled',
    report(WITNESS + f'{FRAME}\tT1:unsampled\tt2\t4 rows, 3 columns, 0 cells read\n'),
    'T1 unsampled in',
    present=True,
)
print('ok')

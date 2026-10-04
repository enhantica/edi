"""bounded cost gate: count work, not noisy clock samples.

Exercises the real CLI progress consumer at the owner's 5184-file cardinality.
Each row access has constant cost; counting accesses proves the absence of the
quadratic recount independent of machine speed. The full fitted per-file timing
curve (first/last 648, OMP_NUM_THREADS=1, <=5%) remains an implementation measurement.
"""

import io
from pathlib import Path
from types import SimpleNamespace

import edi
import edi.__main__ as cli


def test_progress_work_per_file_stays_flat_through_5184_events(monkeypatch):
    accesses = [0]
    work = []

    class Row:
        file_name = 'scan.dat'
        reduced_chi_square = 6.25

        @property
        def converged(self):
            accesses[0] += 1
            return True

    class Analysis:
        fitting_mode = 'sequential'

        @staticmethod
        def fit(*, on_scan_start, on_file_complete, **_kwargs):
            on_scan_start(SimpleNamespace(total_files=5184, completed_rows=[]))
            for _ in range(5184):
                before = accesses[0]
                on_file_complete(Row())
                work.append(accesses[0] - before)
            return SimpleNamespace()

    monkeypatch.setattr(cli.sys, 'stdout', io.StringIO())
    cli._run_human(
        SimpleNamespace(analysis=Analysis()), edi.VerbosityEnum.COMPACT, 'cost', clock=lambda: 1.0
    )
    assert len(work) == 5184, ' gate 5: the cost probe must consume the full scan cardinality'
    assert sum(work[-648:]) <= 1.05 * max(sum(work[:648]), 648), (
        ' gate 5: the final 648 completion events must cost at most 5% more '
        'than the first 648; scanning prior rows on every event is quadratic'
    )


def test_csv_polling_watcher_is_removed():

    source = (Path(__file__).resolve().parents[3] / 'core/src/adapter.cpp').read_text()
    assert 'ScanCsvWatch' not in source, (
        ' scope 4: remove ScanCsvWatch; consume the engine completion callback'
    )

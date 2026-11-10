"""Bank explicit native red-first holes through edi's existing manifest writer.

Run after the baseline focused doctest execution. A failing duration is never recorded
as a measurement. Green native cases are taken from doctest's own duration line.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'tests/unit/cpp/test_e05_t1_fit_job.cpp'


def main() -> None:
    log_path = Path(sys.argv[1])
    log = log_path.read_text(encoding='utf-8')
    baseline = sys.argv[2] if len(sys.argv) > 2 else 'd775b5fd'
    if '[doctest] test cases:' not in log:
        raise RuntimeError(' runtime bank requires a completed focused doctest run')
    spec = importlib.util.spec_from_file_location(
        'runtime_bank', ROOT / 'tools/checks/per_pr_runtimes.py'
    )
    bank = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bank)
    _, values = bank.load_manifest()
    holes = bank._unmeasured_in(bank.MANIFEST.read_text(encoding='utf-8'))
    reasons = bank._unmeasured_reasons(bank.MANIFEST.read_text(encoding='utf-8'))
    durations = {}
    for seconds, name in re.findall(r'([0-9]+\.[0-9]+) s: ([^\n]+)', log):
        durations[name] = float(seconds)
    names = re.findall(r'TEST_CASE\("([^"]+)"\)', SOURCE.read_text(encoding='utf-8'))
    # Doctest separates cases with a file/line header; only a clean case can be banked.
    chunks = re.split(r'(?m)^=+\s*$', log)
    for name in names:
        node = SOURCE.relative_to(ROOT).as_posix() + '::' + name
        matching = [chunk for chunk in chunks if 'TEST CASE:  ' + name + '\n' in chunk]
        if not matching and (node in values or node in holes):
            continue  # An unchanged case was not selected: retain its banked evidence.
        failed = any(
            re.search(r'(?:ERROR|FATAL ERROR|THREW|CRASHED)', chunk) for chunk in matching
        )
        if not matching or failed or name not in durations:
            values.pop(node, None)
            reasons[node] = (
                'expected-red-on-' + baseline if failed else 'not-proved-green-in-focused-run'
            )
            holes.add(node)
        else:
            seconds = durations[name]
            if seconds > bank.threshold_for(node):
                raise RuntimeError(' native gate exceeds its unit-tier bound: ' + name)
            values[node] = seconds
            holes.discard(node)
            reasons.pop(node, None)
    for node in holes:
        reasons.setdefault(node, 'carried-unmeasured')
    bank._write_banked(
        values, reasons, bank.load_module_costs(), str(log_path), list(values) + list(holes)
    )


if __name__ == '__main__':
    main()

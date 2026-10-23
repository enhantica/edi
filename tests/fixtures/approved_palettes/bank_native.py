"""Update only the adapted native consumers through the canonical runtime writer."""

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def main():
    path = Path(sys.argv[1])
    text = path.read_text(encoding='utf-8')
    if '[doctest] Status: SUCCESS!' not in text:
        raise ValueError('Only a complete passing native consumer run can supply measurements')
    spec = importlib.util.spec_from_file_location('bank', ROOT / 'tools/checks/per_pr_runtimes.py')
    bank = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bank)
    _, values = bank.load_manifest()
    reasons = bank._unmeasured_reasons(bank.MANIFEST.read_text())
    costs = bank.load_module_costs()
    old = (
        'tests/unit/cpp/test_report_presentation_boundaries.cpp::'
        'Every structure palette entry and wraparound retains its Bragg colour'
    )
    values.pop(old, None)
    reasons.pop(old, None)
    for seconds, name in re.findall(r'([0-9]+\.[0-9]+) s: ([^\n]+)', text):
        matches = [
            p
            for p in (ROOT / 'tests/unit/cpp').glob('test_*.cpp')
            if f'TEST_CASE("{name}")' in p.read_text()
        ]
        if len(matches) != 1:
            raise ValueError('Each measured native case must resolve to one current source')
        node = matches[0].relative_to(ROOT).as_posix() + '::' + name
        if float(seconds) > bank.threshold_for(node):
            raise ValueError('The native consumer exceeds the existing unit-tier bound')
        values[node] = float(seconds)
        reasons.pop(node, None)
    bank._write_banked(values, reasons, costs, str(path), list(values) + list(reasons))


if __name__ == '__main__':
    main()

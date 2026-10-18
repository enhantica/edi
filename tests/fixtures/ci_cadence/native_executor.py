"""A doctest-shaped process fixture; outcomes model the executable boundary only."""

import os
import sys
from pathlib import Path

args = sys.argv[1:]
cases = [
    (f'planted native {tier} calculation', f'tests/{tier}/cpp/test_planted.cpp')
    for tier in ('unit', 'integration', 'system')
]
if any('list-test-cases' in arg or arg == '-ltc' for arg in args):
    print('[doctest] listing all test case names')
    for name, _ in cases:
        print(name)
    print('[doctest] unskipped test cases passing the current filters: 3')
    sys.exit(0)
Path(os.environ['CI_CADENCE_MARKER']).write_text('native process executed', encoding='utf-8')
outcome = os.environ['CI_CADENCE_OUTCOME']
failed = int(outcome == 'failed')
skipped = int(outcome == 'skipped')
# ruff: noqa: E501
# XML attributes stay on one line to model the native reporter's exact transport shape.
cases_xml = ''.join(
    f'<TestCase name="{name}" filename="{source}" line="1" skipped="{"true" if skipped else "false"}">'
    f'<OverallResultsAsserts successes="{1 - failed}" failures="{failed}" test_case_success="{"false" if failed else "true"}" />'
    '</TestCase>'
    for name, source in cases
)
xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<doctest binary="native-planted" version="2.5.3">
<TestSuite>{cases_xml}</TestSuite>
<OverallResultsTestCases successes="{3 * (1 - failed - skipped)}" failures="{3 * failed}" skipped="{3 * skipped}" />
</doctest>'''

output = next((arg.split('=', 1)[1] for arg in args if arg.startswith(('--out=', '-o='))), None)
if output is None:
    output = next((args[i + 1] for i, arg in enumerate(args[:-1]) if arg in {'--out', '-o'}), None)
if output:
    Path(output).write_text(xml, encoding='utf-8')
else:
    print(xml)
sys.exit(failed)

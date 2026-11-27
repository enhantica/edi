# SPDX-License-Identifier: BSD-3-Clause
"""Say what crysta's checkers and tests found, by file, line and check name only.

    python3 tools/ci/crysta_findings.py run KIND REPORT -- COMMAND...
    python3 tools/ci/crysta_findings.py show KIND REPORT

crysta's source is private (ADR-0083): a test's message or a checker's note can quote it, so a
crysta job keeps the raw output on the runner and prints one line per finding. KIND is

    pytest      REPORT is the file tools/ci/crysta_pytest.py writes
    doctest     REPORT is a folder searched for the C++ tier's XML reports
    clang-tidy  REPORT is the command's own output (run writes it there)
    cppcheck    the same

`run` keeps the command's output on the runner (in REPORT for the two checkers, else in
$RUNNER_TEMP/findings), prints the findings and exits with the command's own code; doctest reports
older than the command are left out. A command that failed without a finding shows the end of its
output, which the step's filter still checks line by line.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET  # noqa: S405 - the reports are this job's own
from collections import Counter
from pathlib import Path

TAIL = 40

# clang-tidy and cppcheck end a finding's first line with the check's name in brackets.
CHECKER = re.compile(
    r'^(?P<file>[^\s:][^:]*):(?P<line>\d+):(?:\d+:)?\s*(?P<kind>warning|error|style|performance|portability|information|note)\b.*\[(?P<check>[A-Za-z0-9_.,-]+)\]\s*$'
)


def relative(path: str, root: Path | None) -> str:
    """A path as the checkout names it, without the runner's folders."""
    if root is not None:
        try:
            return str(Path(path).resolve().relative_to(root.resolve()))
        except (OSError, ValueError):
            pass
    return path


def checker(log: Path, root: Path | None) -> list[str]:
    """One line per clang-tidy or cppcheck finding; notes belong to the finding before them."""
    found = []
    for raw in log.read_text(encoding='utf-8', errors='replace').splitlines():
        match = CHECKER.match(raw.strip())
        if match and match['kind'] != 'note':
            found.append(f'{relative(match["file"], root)}:{match["line"]} {match["check"]}')
    return sorted(set(found))


def doctest(folder: Path, since: float = 0.0) -> list[str]:
    """Each failed C++ case of the reports written since `since`, by file, line and name."""
    found = []
    for report in sorted(folder.rglob('*.xml')) if folder.is_dir() else []:
        if report.stat().st_mtime < since:
            continue
        try:
            root = ET.parse(report).getroot()  # noqa: S314 - this job's own
        except ET.ParseError:
            continue
        for case in root.iter('TestCase'):
            checks = [e for e in case.iter('Expression') if e.get('success') == 'false']
            ended = sorted({
                e.tag for e in case.iter() if e.tag in {'Exception', 'FatalErrorCondition'}
            })
            if checks or ended:
                where = f'{Path(str(case.get("filename"))).name}:{case.get("line")}'
                lines = sorted({
                    f'{Path(str(e.get("filename"))).name}:{e.get("line")}' for e in checks
                })
                checked = ' '.join(lines) or '-'
                found.append(
                    f'{where} {case.get("name")} checks {checked} {" ".join(ended)}'.rstrip()
                )
    return found


def pytest(report: Path) -> tuple[list[str], Counter]:
    """Each failed or erroring test by node id, with the outcome counts."""
    found, counts = [], Counter()
    for row in records(report):
        when, outcome = row.get('when'), row.get('outcome')
        if outcome == 'skipped':
            counts['skipped'] += 1
        elif when == 'call':
            counts[str(outcome)] += 1
        else:
            counts[f'error in {when}'] += 1
        if outcome == 'failed':
            found.append(
                f'FAILED {row.get("nodeid")} ({row.get("file")}:{row.get("line")}, {when})'
            )
    return found, counts


def records(report: Path) -> list[dict]:
    """The rows crysta_pytest.py wrote; a torn last line is left out."""
    rows = []
    for raw in report.read_text(encoding='utf-8').splitlines() if report.is_file() else []:
        try:
            rows.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return rows


def times(report: Path, slowest: int = 15) -> None:
    """The slowest tests and each file's total, for choosing part counts and per-test bounds."""
    rows = [r for r in records(report) if r.get('when') == 'call']
    total = sum(r.get('seconds') or 0 for r in rows)
    print(f'pytest times: {len(rows)} test(s), {total / 60:.1f} min of test calls')
    for row in sorted(rows, key=lambda r: -(r.get('seconds') or 0))[:slowest]:
        print(f'pytest times: {row.get("seconds"):9.1f} s  {row.get("nodeid")}')
    per_file: Counter = Counter()
    for row in rows:
        per_file[row.get('file')] += row.get('seconds') or 0
    for file, seconds in per_file.most_common(slowest):
        print(f'pytest times: {seconds:9.1f} s  file {file}')


def show(kind: str, report: Path, root: Path | None, since: float = 0.0) -> int:
    """Print the findings; the count of them is the return value."""
    counts: Counter = Counter()
    if kind == 'pytest':
        found, counts = pytest(report)
        times(report)
    elif kind == 'doctest':
        found = doctest(report, since)
    elif kind in {'clang-tidy', 'cppcheck'}:
        found = checker(report, root) if report.is_file() else []
    else:
        raise SystemExit(f'crysta_findings: unknown kind {kind}')
    for line in found:
        print(f'{kind}: {line}')
    tally = ', '.join(f'{n} {name}' for name, n in sorted(counts.items()))
    print(f'{kind}: {len(found)} finding(s){"; " + tally if tally else ""}')
    return len(found)


def run(kind: str, report: Path, command: list[str], root: Path | None) -> int:
    """Run the command with its output kept on the runner, then report."""
    kept = Path(os.environ.get('RUNNER_TEMP', report.parent)) / 'findings'
    log = report if kind in {'clang-tidy', 'cppcheck'} else kept / f'{kind}.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    started = time.time() - 1
    with log.open('wb') as sink:
        status = subprocess.run(
            command, stdout=sink, stderr=subprocess.STDOUT, check=False
        ).returncode
    found = show(kind, report, root, started)
    if status and not found:
        print(
            f'{kind}: the command ended with exit {status} and no finding; the end of its output:'
        )
        lines = log.read_text(encoding='utf-8', errors='replace').splitlines()
        for line in lines[-TAIL:]:
            print(f'  {line}')
    print(f'{kind}: exit {status}')
    return status


def main(argv: list[str]) -> int:
    """`run KIND REPORT -- COMMAND...` or `show KIND REPORT`; `--root DIR` makes paths relative."""
    root = None
    if len(argv) > 2 and argv[0] == '--root':
        root, argv = Path(argv[1]), argv[2:]
    if len(argv) >= 3 and argv[0] == 'show':
        show(argv[1], Path(argv[2]), root)
        return 0
    if len(argv) >= 5 and argv[0] == 'run' and argv[3] == '--':
        return run(argv[1], Path(argv[2]), argv[4:], root)
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))

# SPDX-License-Identifier: BSD-3-Clause
"""Say what crysta's commands found, by file, line and check name only.

    python3 tools/ci/crysta_findings.py [--root DIR] run KIND REPORT -- COMMAND...
    python3 tools/ci/crysta_findings.py [--root DIR] show KIND REPORT

crysta's source is private (ADR-0083): a test's message, a compiler's note or a checker's report
can quote it, so a crysta job keeps the raw output on the runner and prints one line per finding.
KIND is

    pytest      REPORT is the file tools/ci/crysta_pytest.py writes
    doctest     REPORT is a folder searched for the C++ tier's XML reports
    clang-tidy  REPORT is the command's own output (run writes it there), as for every kind below
    cppcheck
    build       compiler, linker and CMake errors and warnings: file:line and the -W flag
    check       a crysta guard or contract script: its file:line lines, named after the script
                the command runs, or after the command's last word (a pixi task)
    ruff        ruff's concise lines: file:line and the rule code
    perf        ab_perf's verdicts: workload, verdict and the numbers
    quiet       nothing but the exit code

--root makes the paths printed relative to DIR. `run` prints the findings and exits with the
command's own code; doctest reports older than the command are left out. A command that failed
without a finding (a warning is not one) shows the end of its output, which the step's filter still
checks line by line.
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
# A compiler's message quotes identifiers, so only the place, the level and the flag are kept.
COMPILER = re.compile(
    r'^(?P<file>[^\s:][^:]*):(?P<line>\d+):(?:\d+:)? (?P<level>fatal error|error|warning): '
    r'.*?(?: \[(?P<flag>-W[^\]\s]+)\])?$'
)
CMAKE = re.compile(r'^CMake Error at (?P<file>[^:]+):(?P<line>\d+)')
# A linker names the symbol it missed, so its errors are all one finding.
LINKER = re.compile(
    r'undefined reference|undefined symbol|Undefined symbols|multiple definition'
    r'|symbol\(s\) not found|\bld(?:\.\w+)?: error|ld returned|linker command failed'
)
LOCATED = re.compile(r'^(?P<file>[^\s:]*/[^\s:]+|[^\s:/]+\.[A-Za-z]\w*):(?P<line>\d+)\b')
# A warning a check prints, such as pytest's summary of them, fails nothing.
WARNED = re.compile(r'^\S+:\d+: (?:[A-Z]\w*)?Warning\b')
RUFF = re.compile(r'^(?P<file>[^\s:][^:]*):(?P<line>\d+):\d+: (?P<code>[A-Za-z][\w-]*)')
REFORMAT = re.compile(r'^Would reformat: (?P<file>\S.*)$')
# ab_perf's verdicts can carry a declared delta's cause; the numbers are what the runs measured.
VERDICT = re.compile(
    r'^\[(?P<workload>[\w.+-]+)\] '
    r'(?P<verdict>(?:PASS|FAIL|ADVISORY)(?: [A-Z][A-Z-]+)*)(?P<rest>.*)$'
)
NUMBER = re.compile(
    r'(?:\b[a-z]+\()?\b[a-z]\w*=(?:\[[-+]?\d[\d.]*(?:, [-+]?\d[\d.]*)*\]|[-+]?\d[\d.]*)'
)
OUTPUT_KINDS = {'clang-tidy', 'cppcheck', 'build', 'check', 'ruff', 'perf', 'quiet'}


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


def output(kind: str, log: Path, root: Path | None, name: str) -> list[str]:
    """One line per finding in the output of a build, check, ruff or perf command."""
    found = []
    text = log.read_text(encoding='utf-8', errors='replace') if log.is_file() else ''
    for raw in text.splitlines():
        line = raw.strip()
        if kind == 'build':
            if match := COMPILER.match(line):
                flag = f' {match["flag"]}' if match['flag'] else ''
                found.append(f'{place(match, root)} {match["level"]}{flag}')
            elif match := CMAKE.match(line):
                found.append(f'{place(match, root)} cmake error')
            elif LINKER.search(line):
                found.append('link error')
        elif kind == 'check' and (match := LOCATED.match(line)) and not WARNED.match(line):
            found.append(f'{place(match, root)} {name}')
        elif kind == 'ruff':
            if match := RUFF.match(line):
                found.append(f'{place(match, root)} {match["code"]}')
            elif match := REFORMAT.match(line):
                found.append(f'{relative(match["file"], root)} format')
        elif kind == 'perf' and (match := VERDICT.match(line)):
            numbers = ' '.join(m.group().replace('(', ' ') for m in NUMBER.finditer(match['rest']))
            found.append(f'{match["workload"]} {match["verdict"]} {numbers}'.rstrip())
    # Verdicts keep their order; a header's warning repeats in every file that includes it.
    return found if kind == 'perf' else sorted(set(found))


def place(match: re.Match, root: Path | None) -> str:
    """A finding's file and line."""
    return f'{relative(match["file"], root)}:{match["line"]}'


def named(command: list[str]) -> str:
    """A check's name: the script the command runs, else its last word (a pixi task)."""
    scripts = [Path(word).stem for word in command if word.endswith(('.py', '.sh'))]
    return scripts[0] if scripts else command[-1]


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


def show(
    kind: str, report: Path, root: Path | None, since: float = 0.0, name: str = 'check'
) -> int:
    """Print the findings; the count of those that can explain a failure is the return value."""
    counts: Counter = Counter()
    if kind == 'pytest':
        found, counts = pytest(report)
        times(report)
    elif kind == 'doctest':
        found = doctest(report, since)
    elif kind in {'clang-tidy', 'cppcheck'}:
        found = checker(report, root) if report.is_file() else []
    elif kind in OUTPUT_KINDS:
        found = output(kind, report, root, name)
    else:
        raise SystemExit(f'crysta_findings: unknown kind {kind}')
    for line in found:
        print(f'{kind}: {line}')
    tally = ', '.join(f'{n} {name}' for name, n in sorted(counts.items()))
    print(f'{kind}: {len(found)} finding(s){"; " + tally if tally else ""}')
    # A warning or a passed workload fails nothing, so the end of the output still shows.
    if kind == 'build':
        return sum(' warning' not in line for line in found)
    if kind == 'perf':
        return sum(' FAIL' in line for line in found)
    return len(found)


def run(kind: str, report: Path, command: list[str], root: Path | None) -> int:
    """Run the command with its output kept on the runner, then report."""
    kept = Path(os.environ.get('RUNNER_TEMP', report.parent)) / 'findings'
    log = report if kind in OUTPUT_KINDS else kept / f'{kind}.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    started = time.time() - 1
    with log.open('wb') as sink:
        status = subprocess.run(
            command, stdout=sink, stderr=subprocess.STDOUT, check=False
        ).returncode
    found = show(kind, report, root, started, named(command))
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

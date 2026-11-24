# SPDX-License-Identifier: BSD-3-Clause
"""Judge the layout of every installer page the accessibility client read (a11y-check.sh).

The client (a11y_client.swift) prints one 'pass: {json}' line per full look at a page. A problem
seen in two looks in a row at the same page fails, as does a page whose logo and left edge stood,
for two looks in a row, somewhere else than on the first page. A problem of one look only is
printed as 'layout-opening:' and fails nothing, unless that look is the only one the page got: a
page seen once has nothing to show that it changed. Output that is cut short or names no page
fails.
"""

import json
import re
import sys
from pathlib import Path


def same_problem(one: dict, other: dict) -> bool:
    """The same rule broken at the same place, or with the same words but for their numbers."""

    def words(problem: dict) -> str:
        return re.sub(r'\d+', '#', problem['text'])

    return one['kind'] == other['kind'] and (
        one['place'] == other['place'] or words(one) == words(other)
    )


def same_place(one: dict, other: dict) -> bool:
    return abs(one['top'] - other['top']) <= 0.5 and abs(one['edge'] - other['edge']) <= 0.5


def looks_by_page(lines: list) -> dict:
    """Every look the client printed, by page; refused unless it printed all it announced."""
    looks, announced = {}, None
    for line in lines:
        if line.startswith('pass: '):
            look = json.loads(line[len('pass: ') :])
            looks.setdefault(look['page'], []).append(look)
        elif line.startswith('layout-pages: '):
            announced = int(line.split()[1])
    printed = sum(map(len, looks.values()))
    if not printed or announced != printed:
        raise ValueError(f'the client announced {announced} looks and printed {printed}')
    return looks


def in_a_row(seen: list) -> list:
    return [(seen[number - 1], seen[number]) for number in range(1, len(seen))]


def lasting_problems(seen: list) -> list:
    """The problems seen in two looks in a row (or in a page's only look), each once."""
    found = list(seen[0]['problems']) if len(seen) == 1 else []
    for before, after in in_a_row(seen):
        found += [
            problem
            for problem in after['problems']
            if any(same_problem(problem, earlier) for earlier in before['problems'])
        ]
    kept = []
    for problem in found:
        if not any(same_problem(problem, earlier) for earlier in kept):
            kept.append(problem)
    return kept


def places(seen: list) -> list:
    """Where the page stood for two looks in a row (or in its only look)."""
    if len(seen) == 1:
        return seen
    return [after for before, after in in_a_row(seen) if same_place(before, after)]


def judge(lines: list) -> tuple:
    """The failures and the single-look problems in the client's output."""
    failures, opening, first = [], [], None
    for page, seen in looks_by_page(lines).items():
        lasting = lasting_problems(seen)
        failures += [f'[{page}] {problem["text"]}' for problem in lasting]
        for problem in (problem for look in seen for problem in look['problems']):
            note = f'[{page}] {problem["text"]}'
            if not any(same_problem(problem, kept) for kept in lasting) and note not in opening:
                opening.append(note)
        stood = places(seen)
        if not stood:
            failures.append(f'[{page}] never stood still for two looks')
            continue
        first = first or (page, stood[-1])
        moved = next((look for look in stood if not same_place(look, first[1])), None)
        if moved:
            failures.append(
                f'not on the page template: [{page}] starts at ({moved["edge"]:g},'
                f' {moved["top"]:g}) with {moved["leader"]}, [{first[0]}] at'
                f' ({first[1]["edge"]:g}, {first[1]["top"]:g})'
            )
    return failures, opening


def main() -> int:
    lines = Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace').splitlines()
    try:
        failures, opening = judge(lines)
    except (ValueError, KeyError, TypeError) as error:
        failures, opening = [f'the client output cannot be judged: {error}'], []
    for note in opening:
        print(f'layout-opening: {note}')
    for failure in failures:
        print(f'layout: {failure}')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

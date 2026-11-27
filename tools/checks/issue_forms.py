#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""edi's issue forms set only labels edi has (ADR-0101).

Every form in .github/ISSUE_TEMPLATE is read as YAML:

- each label it sets is in the closed table of docs/dev/adrs/0101-issue-labels.md, in a row whose
  Repos cell has E (a label of enhantica/edi; F rows are edi-feedback's);
- it keeps GitHub's issue-form schema: a name, a description and a body whose items have a type
  GitHub knows (markdown, textarea, input, dropdown, checkboxes), ids of a-z, 0-9, `_` and `-`,
  unique in the form, and none on a markdown item;
- config.yml has only the chooser's two settings, each link with a name, an https URL and a text.

With --live the E rows are also compared with the labels of the repository, names and colours,
through `gh api`. It only reads; the labels themselves change only by the owner's decision.

    python tools/checks/issue_forms.py [--root <edi tree>] [--live [--repo <owner/name>]]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
FORMS = Path('.github/ISSUE_TEMPLATE')
ADR = Path('docs/dev/adrs/0101-issue-labels.md')
TYPES = {'markdown', 'textarea', 'input', 'dropdown', 'checkboxes'}
ID = re.compile(r'[a-z0-9_-]+')
COLOUR = re.compile(r'[0-9A-Fa-f]{6}')


def table_rows(adr: Path) -> tuple[list[tuple[list[str], list[str], set[str]]], list[str]]:
    """The label table's rows as (labels, colours, repos), and what is wrong with the table."""
    lines = adr.read_text(encoding='utf-8').splitlines()
    header = next(
        (i for i, line in enumerate(lines) if line.startswith('| Group | Label |')), None
    )
    if header is None:
        return [], [f'{ADR}: no label table (a row starting "| Group | Label |")']
    columns = [cell.strip() for cell in lines[header].strip().strip('|').split('|')]
    missing = {'Label', 'Colour', 'Repos'} - set(columns)
    if missing:
        return [], [f'{ADR}: the label table has no {", ".join(sorted(missing))} column']
    rows, found = [], []
    for number, line in enumerate(lines[header + 2 :], start=header + 3):
        if not line.startswith('|'):
            break
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) != len(columns):
            found.append(f'{ADR}:{number}: {len(cells)} cells, the header has {len(columns)}')
            continue
        row = dict(zip(columns, cells, strict=True))
        labels = re.findall(r'`([^`]+)`', row['Label'])
        colours = re.findall(r'`([^`]+)`', row['Colour'])
        repos = set(row['Repos'].split())
        if not labels:
            found.append(f'{ADR}:{number}: a row without a label')
        elif len(colours) != len(labels) or not all(COLOUR.fullmatch(c) for c in colours):
            found.append(f'{ADR}:{number}: needs one six-digit colour per label')
        elif not repos or not repos <= {'E', 'F'}:
            found.append(f'{ADR}:{number}: Repos must be E, F or both, not "{row["Repos"]}"')
        else:
            rows.append((labels, colours, repos))
    if not rows and not found:
        found.append(f'{ADR}: the label table has no rows')
    return rows, found


def edi_labels(rows: list[tuple[list[str], list[str], set[str]]]) -> dict[str, str]:
    """The E rows' labels with their colours."""
    return {
        label: colour.upper()
        for labels, colours, repos in rows
        if 'E' in repos
        for label, colour in zip(labels, colours, strict=True)
    }


def item_problems(where: str, index: int, item: object, ids: set[str]) -> list[str]:
    at = f'{where}: body item {index + 1}'
    if not isinstance(item, dict):
        return [f'{at} is not a mapping']
    kind = item.get('type')
    if kind not in TYPES:
        return [f'{at} has type {kind!r}, not one of {", ".join(sorted(TYPES))}']
    found = []
    if 'id' in item:
        name = item['id']
        if kind == 'markdown':
            found.append(f'{at}: a markdown item takes no id')
        elif not isinstance(name, str) or not ID.fullmatch(name):
            found.append(f'{at}: id {name!r} is not made of a-z, 0-9, _ and -')
        elif name in ids:
            found.append(f'{at}: id {name!r} is used twice')
        else:
            ids.add(name)
    attributes = item.get('attributes')
    if not isinstance(attributes, dict):
        return [*found, f'{at}: no attributes']
    needed = 'value' if kind == 'markdown' else 'label'
    if not isinstance(attributes.get(needed), str) or not attributes[needed].strip():
        found.append(f'{at}: a {kind} item needs attributes.{needed}')
    if kind in {'dropdown', 'checkboxes'}:
        options = attributes.get('options')
        if not isinstance(options, list) or not options:
            found.append(f'{at}: a {kind} item needs options')
        elif kind == 'checkboxes' and not all(
            isinstance(o, dict) and isinstance(o.get('label'), str) for o in options
        ):
            found.append(f'{at}: every checkbox option needs a label')
    return found


def form_problems(path: Path, allowed: dict[str, str]) -> list[str]:
    where = str(FORMS / path.name)
    try:
        form = yaml.safe_load(path.read_text(encoding='utf-8'))
    except yaml.YAMLError as error:
        return [f'{where}: not readable YAML ({error})']
    if not isinstance(form, dict):
        return [f'{where}: not a mapping']
    found = [
        f'{where}: needs a {key}'
        for key in ('name', 'description')
        if not isinstance(form.get(key), str) or not form[key].strip()
    ]
    labels = form.get('labels', [])
    # GitHub takes the labels as a list or as one comma-separated string.
    if isinstance(labels, str):
        labels = [label.strip() for label in labels.split(',') if label.strip()]
    if not isinstance(labels, list) or not all(isinstance(label, str) for label in labels):
        found.append(f'{where}: labels must be a list of names')
    else:
        found += [
            f'{where}: label {label!r} is not in an E row of {ADR}'
            for label in labels
            if label not in allowed
        ]
    body = form.get('body')
    if not isinstance(body, list) or not body:
        return [*found, f'{where}: needs a body of at least one item']
    ids: set[str] = set()
    for index, item in enumerate(body):
        found += item_problems(where, index, item, ids)
    if not ids:
        found.append(f'{where}: needs at least one field to fill in')
    return found


def config_problems(path: Path) -> list[str]:
    where = str(FORMS / path.name)
    try:
        config = yaml.safe_load(path.read_text(encoding='utf-8'))
    except yaml.YAMLError as error:
        return [f'{where}: not readable YAML ({error})']
    if not isinstance(config, dict):
        return [f'{where}: not a mapping']
    found = [
        f'{where}: unknown key {key!r}'
        for key in config
        if key not in {'blank_issues_enabled', 'contact_links'}
    ]
    if not isinstance(config.get('blank_issues_enabled', True), bool):
        found.append(f'{where}: blank_issues_enabled must be true or false')
    links = config.get('contact_links', [])
    if not isinstance(links, list):
        return [*found, f'{where}: contact_links must be a list']
    for index, link in enumerate(links):
        if not isinstance(link, dict) or not all(
            isinstance(link.get(key), str) and link[key].strip()
            for key in ('name', 'url', 'about')
        ):
            found.append(f'{where}: contact link {index + 1} needs a name, a url and an about')
        elif not link['url'].startswith('https://'):
            found.append(f'{where}: contact link {index + 1} needs an https URL')
    return found


def problems(root: Path) -> list[str]:
    adr = root / ADR
    if not adr.is_file():
        return [f'{ADR}: missing']
    rows, found = table_rows(adr)
    allowed = edi_labels(rows)
    forms_dir = root / FORMS
    files = sorted(p for p in forms_dir.glob('*') if p.suffix in {'.yml', '.yaml'})
    forms = [p for p in files if p.stem != 'config']
    if not forms:
        return [*found, f'{FORMS}: no issue forms']
    for path in forms:
        found += form_problems(path, allowed)
    for path in files:
        if path.stem == 'config':
            found += config_problems(path)
    return found


def live_problems(root: Path, repo: str) -> list[str]:
    """The E rows against the repository's labels, both ways, names and colours."""
    if not (root / ADR).is_file():
        return []  # problems() has reported it
    rows, broken = table_rows(root / ADR)
    if broken:
        return []
    try:
        listed = subprocess.run(
            ['gh', 'api', '--paginate', f'repos/{repo}/labels?per_page=100', '--jq', '.[]'],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        return [f'gh could not be run to list the labels of {repo} ({error})']
    if listed.returncode != 0:
        return [f'gh api could not list the labels of {repo}: {listed.stderr.strip()}']
    try:
        labels = [json.loads(line) for line in listed.stdout.splitlines() if line.strip()]
        actual = {label['name']: label['color'].upper() for label in labels}
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as error:
        return [f'gh api gave an unreadable label list for {repo} ({error})']
    expected = edi_labels(rows)
    found = [
        f'{repo}: no label {name!r} (an E row of {ADR})'
        for name in expected.keys() - actual.keys()
    ]
    found += [
        f'{repo}: label {name!r} is in no E row of {ADR}'
        for name in actual.keys() - expected.keys()
    ]
    found += [
        f'{repo}: label {name!r} is #{actual[name]}, {ADR} says #{expected[name]}'
        for name in expected.keys() & actual.keys()
        if actual[name] != expected[name]
    ]
    return sorted(found)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--root', type=Path, default=ROOT, help='the edi tree (default: this one)')
    parser.add_argument(
        '--live', action='store_true', help="also compare with the repository's labels"
    )
    parser.add_argument('--repo', default='enhantica/edi', help='the repository --live reads')
    args = parser.parse_args()
    found = problems(args.root)
    if args.live:
        found += live_problems(args.root, args.repo)
    for problem in found:
        print(problem, file=sys.stderr)
    if found:
        print('issue forms: the labels and fields above do not follow ADR-0101', file=sys.stderr)
        return 1
    forms = [p for p in (args.root / FORMS).glob('*.y*ml') if p.stem != 'config']
    live = f'; the E rows match the labels of {args.repo}' if args.live else ''
    print(f"issue forms: {len(forms)} forms set only labels of ADR-0101's E rows{live}")
    return 0


if __name__ == '__main__':
    sys.exit(main())

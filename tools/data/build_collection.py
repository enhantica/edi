#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Build or check a data collection: plain files and one index.json (edi ADR-0068).

    python tools/data/build_collection.py populate OUTPUT   # the examples and tutorial files
    python tools/data/build_collection.py index OUTPUT      # (re)write OUTPUT/index.json
    python tools/data/build_collection.py check OUTPUT      # index, files and schema agree

A collection (ADR-0068) is `structures/`, `experiments/`, `data/` and `projects/` beside
`index.json`. Each
file may have a sidecar `<file>.meta.json` holding what the file does not say about itself (a
name, a description, the facility); `populate` writes those from the examples' metadata, and
`index` folds them into the entries with the file's sha256 and size. The schema is
`edi-data-index/1`: entries with an id, a kind (structure, experiment, data or project), name,
description, formula (Hill notation, when the file states one), elements (the symbols present,
Hill order), space_group, cell, radiation, technique, instrument, facility, source and files,
each file with path, format, sha256 and bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / 'docs/user/cli'
METADATA = ROOT / 'app/examples/metadata.json'
TUTORIAL_FILES = ROOT / 'app/tutorials/files'
try:
    import edi  # the core reader, for `check`; `populate` and `index` need no build
except ImportError:  # pragma: no cover - the environment decides
    edi = None

SCHEMA = 'edi-data-index/1'
KINDS = ('structure', 'experiment', 'data', 'project')
FOLDERS = {
    'structure': 'structures',
    'experiment': 'experiments',
    'data': 'data',
    'project': 'projects',
}
FORMATS = {
    '.cif': 'cif',
    '.edi': 'edi',
    '.xye': 'xye',
    '.xy': 'xy',
    '.dat': 'dat',
    '.txt': 'txt',
    '.csv': 'csv',
    '.int': 'int',
    '.hkl': 'hkl',
    '.zip': 'zip',
}
ELEMENT = re.compile(r'^[A-Z][a-z]?')


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def cif_value(text: str, tag: str) -> str:
    match = re.search(r'^' + re.escape(tag) + r'[ \t]+(.+?)[ \t]*$', text, re.MULTILINE)
    if not match:
        return ''
    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in '\'"':
        value = value[1:-1]
    return value


def number(text: str) -> float | None:
    try:
        return float(re.sub(r'\(.*\)$', '', text))
    except ValueError:
        return None


def hill(symbols: list[str]) -> str:
    unique = sorted(set(symbols))
    if 'C' in unique:
        unique = (
            ['C'] + (['H'] if 'H' in unique else []) + [s for s in unique if s not in {'C', 'H'}]
        )
    return ' '.join(unique)


def structure_facts(text: str) -> dict:
    """What a structure file says about itself: space group, cell and the elements present."""
    facts = {}
    group = ''
    for tag in (
        '_space_group.name_h_m',
        '_space_group.name_H-M_alt',
        '_space_group_name_H-M_alt',
        '_symmetry_space_group_name_H-M',
    ):
        group = group or cif_value(text, tag)
    formula = cif_value(text, '_chemical_formula_sum') or cif_value(text, '_chemical_formula.sum')
    if formula:
        facts['formula'] = formula
    if group:
        facts['space_group'] = group
    # The project's dotted tags (`_cell.length_a`) or a plain CIF's (`_cell_length_a`, as COD
    # writes them).
    cell = [
        number(cif_value(text, f'_cell.{name}') or cif_value(text, f'_cell_{name}'))
        for name in (
            'length_a',
            'length_b',
            'length_c',
            'angle_alpha',
            'angle_beta',
            'angle_gamma',
        )
    ]
    if all(v is not None for v in cell):
        facts['cell'] = cell
    loop = re.search(r'loop_\s*((?:_atom_site[._][A-Za-z_]+\s*)+)((?:.+\n)+?)(?:\n|loop_|$)', text)
    if loop:
        columns = loop.group(1).split()
        column = -1
        for tag in ('_atom_site.type_symbol', '_atom_site_type_symbol'):
            if tag in columns:
                column = columns.index(tag)
                break
        if column >= 0:
            symbols = []
            for row in loop.group(2).splitlines():
                fields = row.split()
                if len(fields) > column:
                    match = ELEMENT.match(fields[column])
                    if match:
                        symbols.append(match.group(0))
            if symbols:
                facts['elements'] = hill(symbols).split()
                # A file that states no formula gives its elements as one, without counts: enough
                # for the amount-free search and an honest column.
                facts.setdefault('formula', ' '.join(facts['elements']))
    return facts


def experiment_facts(text: str) -> dict:
    facts = {}
    probe = cif_value(text, '_experiment_type.radiation_probe')
    if probe:
        facts['radiation'] = probe
    form = cif_value(text, '_experiment_type.sample_form')
    mode = cif_value(text, '_experiment_type.beam_mode')
    if form or mode:
        facts['technique'] = ' '.join(part for part in (form, mode) if part)
    for tag, key in (('_instrument.name', 'instrument'), ('_instrument.facility', 'facility')):
        value = cif_value(text, tag)
        if value:
            facts[key] = value
    return facts


def linked_structures(text: str) -> list[str]:
    """The structure ids an experiment links: its `_linked_structure` loop or single tag."""
    single = cif_value(text, '_linked_structure.structure_id')
    if single:
        return [single]
    match = re.search(
        r'^loop_\s*\n((?:_linked_structure\.\S+[ \t]*\n)+)((?:[^_\n][^\n]*\n?)*)',
        text,
        re.MULTILINE,
    )
    if not match:
        return []
    tags = match.group(1).split()
    if '_linked_structure.structure_id' not in tags:
        return []
    column = tags.index('_linked_structure.structure_id')
    ids = []
    for row in match.group(2).splitlines():
        parts = row.split()
        if len(parts) > column and parts[0] != 'loop_':
            ids.append(parts[column].strip('\'"'))
    return ids


def write_sidecar(path: Path, meta: dict) -> None:
    meta = {k: v for k, v in meta.items() if v not in ('', None, [])}
    path.with_name(path.name + '.meta.json').write_text(
        json.dumps(meta, ensure_ascii=False, indent=1) + '\n'
    )


def sample_facts(structure_texts: list[str]) -> dict:
    """The sample's formula and elements from a project's structure files.

    One structure gives its formula; several phases give the union of their elements as one
    formula without counts, which is what the amount-free search needs. Empty when no file names
    an element.
    """
    formulas = []
    symbols: set[str] = set()
    for text in structure_texts:
        facts = structure_facts(text)
        if facts.get('formula'):
            formulas.append(facts['formula'])
        symbols.update(facts.get('elements', []))
    out: dict = {}
    if symbols:
        out['elements'] = hill(sorted(symbols)).split()
    if len(formulas) == 1:
        out['formula'] = formulas[0]
    elif symbols:
        out['formula'] = ' '.join(out['elements'])
    return out


def populate(output: Path) -> int:
    metadata = json.loads(METADATA.read_text())['examples']
    for folder in FOLDERS.values():
        (output / folder).mkdir(parents=True, exist_ok=True)
    count = 0
    for example, meta in sorted(metadata.items()):
        project = EXAMPLES / example / 'project'
        if not (project / 'project.edi').is_file():
            continue
        values = meta.get('values', {})

        def first(key: str, values: dict = values) -> str:
            return (values.get(key) or [''])[0]

        structure_texts = [
            f.read_text(errors='replace') for f in sorted((project / 'structures').glob('*.edi'))
        ]
        common = {
            **sample_facts(structure_texts),
            'name': ' / '.join(meta.get('samples', [])),
            'description': meta.get('detail', ''),
            'radiation': first('probe'),
            'technique': ' '.join(
                part for part in (first('sampleForm'), first('beamMode')) if part
            ),
            'instrument': first('instruments'),
            'facility': first('facilities'),
            'source': 'EasyDiffraction',
        }
        # The whole project, zipped with its folder name inside, as the Project page opens it.
        archive = output / 'projects' / f'{example}.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zipped:
            for file in sorted(project.rglob('*')):
                if file.is_file():
                    zipped.write(file, Path(example) / file.relative_to(project))
        write_sidecar(archive, {'id': example, **common})
        count += 1
        for structure in sorted((project / 'structures').glob('*.edi')):
            target = output / 'structures' / f'{example}-{structure.stem}.edi'
            shutil.copyfile(structure, target)
            write_sidecar(
                target,
                {
                    'id': f'{example}-{structure.stem}',
                    'name': ' / '.join(meta.get('samples', [])),
                    'description': common['description'],
                    'source': 'EasyDiffraction',
                },
            )
            count += 1
        for experiment in sorted((project / 'experiments').glob('*.edi')):
            target = output / 'experiments' / f'{example}-{experiment.stem}.edi'
            shutil.copyfile(experiment, target)
            # The structures it links, by their entry ids: Load from the web brings them with it.
            linked = [
                f'{example}-{name}'
                for name in linked_structures(experiment.read_text(errors='replace'))
                if (project / 'structures' / f'{name}.edi').is_file()
            ]
            write_sidecar(
                target, {'id': f'{example}-{experiment.stem}', 'structures': linked, **common}
            )
            count += 1
    # The tutorials' inputs: a structure CIF and a measured pattern, both of the CIF's sample.
    tutorial_sample = sample_facts([
        f.read_text(errors='replace') for f in sorted(TUTORIAL_FILES.glob('*.cif'))
    ])
    for file in sorted(TUTORIAL_FILES.iterdir()):
        kind = 'structure' if file.suffix == '.cif' else 'data'
        target = output / FOLDERS[kind] / f'tutorial-{file.name}'
        shutil.copyfile(file, target)
        meta = {
            **tutorial_sample,
            'id': f'tutorial-{file.stem}',
            'name': 'La0.5Ba0.5CoO3' + ('' if kind == 'structure' else ' pattern from HRPT'),
            'description': "The onboarding tutorials' input",
            'source': 'EasyDiffraction',
        }
        if kind == 'data':
            meta.update({
                'radiation': 'neutron',
                'technique': 'powder constant wavelength',
                'instrument': 'HRPT',
                'facility': 'PSI',
            })
        write_sidecar(target, meta)
        count += 1
    print(f'populate: {count} files under {output}')
    return 0


def entries_of(output: Path) -> list[dict]:
    entries = []
    for kind, folder in FOLDERS.items():
        for file in sorted((output / folder).glob('*')):
            if not file.is_file() or file.name.endswith('.meta.json'):
                continue
            fmt = FORMATS.get(file.suffix.lower())
            if fmt is None:
                raise SystemExit(
                    f'build_collection: {file} has a format the collection does not hold'
                )
            sidecar = file.with_name(file.name + '.meta.json')
            meta = json.loads(sidecar.read_text()) if sidecar.is_file() else {}
            facts = {}
            if kind in {'structure', 'experiment'} and fmt in {'cif', 'edi'}:
                text = file.read_text(errors='replace')
                facts = structure_facts(text) if kind == 'structure' else experiment_facts(text)
            entry = {'id': meta.get('id', file.stem), 'kind': kind}
            for key in (
                'name',
                'description',
                'formula',
                'elements',
                'space_group',
                'cell',
                'radiation',
                'technique',
                'instrument',
                'facility',
                'source',
                'authors',
                'journal',
                'volume',
                'first_page',
                'year',
                'doi',
                'structures',
            ):
                value = meta.get(key, facts.get(key))
                if value not in (None, '', []):
                    entry[key] = value
            entry['files'] = [
                {
                    'path': f'{folder}/{file.name}',
                    'format': fmt,
                    'sha256': sha256_of(file),
                    'bytes': file.stat().st_size,
                }
            ]
            entries.append(entry)
    return entries


def index(output: Path) -> int:
    document = {'schema': SCHEMA, 'entries': entries_of(output)}
    ids = [e['id'] for e in document['entries']]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise SystemExit(f'build_collection: repeated ids {duplicates}')
    (output / 'index.json').write_text(json.dumps(document, ensure_ascii=False, indent=1) + '\n')
    print(f'index: {len(ids)} entries written to {output / "index.json"}')
    return 0


def _defined_formula(output: Path, entry: dict) -> str:
    """The formula the entry's own files define: a structure file's, or a project's structures'."""
    files = entry.get('files') or []
    if not files or not isinstance(files[0], dict):
        return ''
    path = output / str(files[0].get('path', ''))
    if not path.is_file():
        return ''
    if entry.get('kind') == 'structure':
        return structure_facts(path.read_text(errors='replace')).get('formula', '')
    if entry.get('kind') == 'project' and path.suffix == '.zip':
        with zipfile.ZipFile(path) as archive:
            texts = [
                archive.read(name).decode('utf-8', errors='replace')
                for name in archive.namelist()
                if '/structures/' in name and name.endswith(('.edi', '.cif'))
            ]
        return sample_facts(texts).get('formula', '')
    return ''


def _entry_problems(output: Path, entry: dict, seen: set) -> list[str]:
    where = f'entry {entry.get("id")!r}'
    problems = []
    # Every entry carries its sample formula where its files define one (the owner, 2026-11-04).
    if not entry.get('formula') and _defined_formula(output, entry):
        problems.append(f'{where} has no formula although its files define one')
    if not entry.get('id'):
        problems.append('an entry has no id')
    elif entry['id'] in seen:
        problems.append(f'{where} appears twice')
    seen.add(entry.get('id'))
    if entry.get('kind') not in KINDS:
        problems.append(f'{where} has the kind {entry.get("kind")!r}')
    cell = entry.get('cell')
    if cell is not None and (not isinstance(cell, list) or len(cell) != 6):
        problems.append(f'{where} has a cell without six values')
    files = entry.get('files')
    if not isinstance(files, list) or not files:
        problems.append(f'{where} has no files')
        files = []
    for file in files:
        if not isinstance(file, dict):
            problems.append(f'{where} has a file that is not an object')
            continue
        problems.extend(_file_problems(output, where, file))
    return problems


# The reader's grammar for a file path inside a collection: segments of letters, digits, '.', '_',
# '~' and '-', each starting with a letter or digit, joined by single slashes; no drive, scheme,
# backslash, percent-encoding, '.' or '..'.
RELATIVE_PATH = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._~-]*(/[A-Za-z0-9][A-Za-z0-9._~-]*)*$')


def _file_problems(output: Path, where: str, file: dict) -> list[str]:
    rel = file.get('path', '')
    if not isinstance(rel, str) or not RELATIVE_PATH.match(rel):
        return [f'{where}: {rel!r} is not a relative path inside the collection']
    on_disk = output / rel
    if not on_disk.is_file():
        return [f'{where}: {rel} is missing']
    problems = []
    if file.get('sha256') and file['sha256'] != sha256_of(on_disk):
        problems.append(f'{where}: {rel} does not match its sha256')
    if file.get('bytes') is not None and file['bytes'] != on_disk.stat().st_size:
        problems.append(f'{where}: {rel} does not match its size')
    return problems


def _reader_problem(output: Path) -> str:
    """What the core reader, the one parser every interface uses, refuses in the index.

    Empty if nothing. The check never accepts an index the app, the CLI or Python would
    refuse, so it asks that reader rather than restating its rules.
    """
    if edi is None:
        raise SystemExit(
            'check: the edi package (the core reader) is not importable; run the check in the'
            ' project environment'
        )
    try:
        edi.load_collection(str(output))
    except Exception as problem:  # noqa: BLE001 - the reader's message is the finding
        return str(problem)
    return ''


def _index_document(path: Path) -> tuple[dict, list[dict], list[str]]:
    """The index as JSON, its entries array and what is wrong with their shape."""
    problems: list[str] = []
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as problem:
        return {}, [], [f'index.json is not JSON: {problem}']
    if not isinstance(document, dict):
        return {}, [], ['index.json is not an object']
    if document.get('schema') != SCHEMA:
        problems.append(f'schema is {document.get("schema")!r}, not {SCHEMA}')
    entries = document.get('entries')
    if not isinstance(entries, list):
        problems.append('the index has no entries array')
        entries = []
    shaped = [e for e in entries if isinstance(e, dict)]
    unshaped = [e for e in entries if not isinstance(e, dict)]
    problems.extend(f'an entry is not an object: {e!r}' for e in unshaped)
    return document, shaped, problems


def check(output: Path) -> int:
    path = output / 'index.json'
    if not path.is_file():
        print(f'check: {path} is missing', file=sys.stderr)
        return 1
    _, entries, problems = _index_document(path)
    if reader := _reader_problem(output):
        problems.append(f'the core reader refuses the index: {reader}')
    seen: set = set()
    for entry in entries:
        problems.extend(_entry_problems(output, entry, seen))
    listed = {f.get('path') for e in entries for f in e.get('files') or [] if isinstance(f, dict)}
    for folder in FOLDERS.values():
        for file in sorted((output / folder).glob('*')):
            missing = file.is_file() and not file.name.endswith('.meta.json')
            if missing and f'{folder}/{file.name}' not in listed:
                problems.append(f'{folder}/{file.name} is not in the index')
    for problem in problems:
        print(f'check: {problem}', file=sys.stderr)
    if not problems:
        print(f'check: {len(seen)} entries, every file present with its hash')
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('populate', 'index', 'check'):
        sub.add_parser(name).add_argument('output', type=Path)
    args = parser.parse_args(argv)
    return {'populate': populate, 'index': index, 'check': check}[args.command](
        args.output.resolve()
    )


if __name__ == '__main__':
    sys.exit(main())

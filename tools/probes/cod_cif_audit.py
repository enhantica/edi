"""Compare headless Edi imports of a local cache of unmodified COD structure CIFs.

With Edi and Gemmi importable, record a snapshot using:
    python tools/probes/cod_cif_audit.py snapshot CACHE BASELINE.json

Build the candidate, then record and compare:
    python tools/probes/cod_cif_audit.py snapshot CACHE CANDIDATE.json
    python tools/probes/cod_cif_audit.py compare BASELINE.json CANDIDATE.json RESULTS.csv

Keep the JSON snapshots for the full import diagnostics and the affected sites.
"""

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import warnings
from pathlib import Path

import edi
import gemmi
from gemmi import cif


def _declared(block: cif.Block, *names: str) -> bool:
    return any(block.find_value(name) not in {None, '.', '?'} for name in names)


def _defaulted_fields(path: Path, structure: edi.Structure) -> dict:
    """Inspect source tokens independently and show values Edi used for absent fields."""
    blocks = [
        block
        for block in cif.read_file(str(path))
        if _declared(block, '_cell_length_a', '_cell.length_a')
    ]
    if len(blocks) != 1:
        raise ValueError('cannot identify a unique source structure block')

    block = blocks[0]
    defaults = {}
    for item in ('length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma'):
        if not _declared(block, f'_cell_{item}', f'_cell.{item}'):
            defaults[f'cell.{item}'] = getattr(structure.cell, item).value

    atom_loop = next(
        (
            item.loop
            for item in block
            if item.loop
            and any(
                name.lower() in {'_atom_site_label', '_atom_site.label', '_atom_site.id'}
                for name in item.loop.tags
            )
        ),
        None,
    )
    if atom_loop is None:
        if len(structure.atom_sites):
            raise ValueError('cannot identify the source atom-site loop')
        return defaults

    tags = [name.lower() for name in atom_loop.tags]

    def read(row: int, *names: str) -> str | None:
        for name in names:
            if name in tags:
                value = atom_loop[row, tags.index(name)]
                if not cif.is_null(value):
                    return cif.as_string(value)
        return None

    sites = {site.id: site for site in structure.atom_sites}
    for row in range(atom_loop.length()):
        label = read(row, '_atom_site_label', '_atom_site.label', '_atom_site.id')
        site = sites.get(label)
        if site is None:
            raise ValueError(f'cannot match source site {label!r} to the imported model')
        if read(row, '_atom_site_occupancy', '_atom_site.occupancy') is None:
            defaults.setdefault('occupancy', {})[label] = site.occupancy.value
        if read(row, '_atom_site_type_symbol', '_atom_site.type_symbol') is None:
            defaults.setdefault('element inferred from label', {})[label] = site.type_symbol
        if (
            site.adp_type.lower() in {'uiso', 'biso'}
            and read(
                row,
                '_atom_site_u_iso_or_equiv',
                '_atom_site.u_iso_or_equiv',
                '_atom_site_b_iso_or_equiv',
                '_atom_site.b_iso_or_equiv',
            )
            is None
        ):
            defaults.setdefault('isotropic displacement', {})[label] = {
                'value': site.adp_iso.value,
                'form': site.adp_type,
            }
    return defaults


def _probe(path: Path) -> dict:
    with warnings.catch_warnings(record=True) as messages:
        warnings.simplefilter('always')
        try:
            structure = edi.StructureFactory.from_cif_path(path)
        except (ValueError, RuntimeError, UnicodeError) as error:
            result = {'status': 'refused', 'detail': str(error).replace(str(path), path.name)}
        else:
            try:
                defaults = _defaulted_fields(path, structure)
            except (ValueError, RuntimeError) as error:
                result = {'status': 'imported; source audit incomplete', 'detail': str(error)}
            else:
                result = {'status': 'imported', 'defaults': defaults}
                if defaults:
                    result['status'] = 'imported with source fields absent'
                if not len(structure.atom_sites):
                    result['status'] += '; no atom sites'
                result['atom_sites'] = len(structure.atom_sites)
                result['space_group'] = structure.space_group.it_number
    result['warnings'] = [str(message.message) for message in messages]
    return result


def _snapshot(cache: Path, output: Path) -> None:
    entries = {}
    for path in sorted(cache.glob('*.cif')):
        if not re.fullmatch(r'[0-9]{7}', path.stem):
            continue
        try:
            run = subprocess.run(
                [sys.executable, __file__, '_probe', str(path)],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except subprocess.TimeoutExpired:
            result = {'status': 'timed out', 'detail': '30-second import budget exceeded'}
        else:
            if run.returncode == 0:
                result = json.loads(run.stdout)
                if run.stderr.strip():
                    result['native_diagnostics'] = run.stderr.strip()
            else:
                result = {
                    'status': 'process failed',
                    'detail': f'{run.returncode}: {run.stderr.strip()}',
                }
        result['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        entries[path.stem] = result
        if len(entries) % 50 == 0:
            print(f'Checked {len(entries)} CIFs', file=sys.stderr, flush=True)
    if not entries:
        raise SystemExit(f'No seven-digit COD CIFs in {cache}')
    root = Path(__file__).resolve().parents[2]
    source = subprocess.check_output(
        ['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True
    ).strip()
    native = Path(edi._edi.__file__).resolve()
    linked_source = next(
        (
            path.read_text(encoding='utf-8').strip()
            for path in (native.parent / '.crysta-sha', native.parents[2] / '.crysta-linked-sha')
            if path.is_file()
        ),
        None,
    )
    report = {
        'edi_source': source,
        'edi_built_source': edi._edi.__build_commit__,
        'edi_extension_sha256': hashlib.sha256(native.read_bytes()).hexdigest(),
        'gemmi_version': gemmi.__version__,
        'linked_crysta_source': linked_source,
        'entries': entries,
    }
    with output.open('x', encoding='utf-8') as target:
        json.dump(report, target, indent=2, sort_keys=True)
        target.write('\n')


def _detail(entry: dict) -> str:
    fields = [
        f'{name} ({len(value)} sites)' if isinstance(value, dict) else f'{name}={value}'
        for name, value in sorted(entry.get('defaults', {}).items())
    ]
    return entry.get('detail', ', '.join(fields))


def _status(entry: dict) -> str:
    status = entry['status']
    if status == 'imported with source fields absent' and any(
        'taken as a default' in warning for warning in entry.get('warnings', [])
    ):
        return 'imported with defaults reported'
    return status


def _compare(baseline: Path, candidate: Path, output: Path) -> None:
    initial = json.loads(baseline.read_text(encoding='utf-8'))['entries']
    current = json.loads(candidate.read_text(encoding='utf-8'))['entries']
    for entry_id in initial.keys() & current.keys():
        if initial[entry_id]['sha256'] != current[entry_id]['sha256']:
            raise ValueError(f'COD {entry_id}: snapshot CIF bytes differ')
    with output.open('w', newline='', encoding='utf-8') as target:
        writer = csv.writer(target, lineterminator='\n')
        writer.writerow((
            'cod_entry_id',
            'initial_status',
            'status_after_fix',
            'initial_detail',
            'detail_after_fix',
            'source_url',
            'cif_sha256',
        ))
        for entry_id in sorted(initial.keys() | current.keys()):
            before = initial.get(entry_id)
            after = current.get(entry_id)
            missing = {'status': 'not run'}
            writer.writerow((
                entry_id,
                _status(before or missing),
                _status(after or missing),
                _detail(before or missing),
                _detail(after or missing),
                f'https://www.crystallography.net/cod/{entry_id}.cif',
                (before or after)['sha256'],
            ))


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == '_probe':
        print(json.dumps(_probe(Path(sys.argv[2]))))
        return
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    record = commands.add_parser('snapshot')
    record.add_argument('cache', type=Path)
    record.add_argument('output', type=Path)
    report = commands.add_parser('compare')
    report.add_argument('baseline', type=Path)
    report.add_argument('candidate', type=Path)
    report.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.command == 'snapshot':
        _snapshot(args.cache, args.output)
    else:
        _compare(args.baseline, args.candidate, args.output)


if __name__ == '__main__':
    main()

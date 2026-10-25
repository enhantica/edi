#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Write the example catalogue's ``expected.json`` records (ADR-0048).

    python tools/cli_projects/catalogue_expected.py [case ...]

A fitted example takes its references from FullProf's fit of the same start
(``knowledge/fitting/fullprof/<case>/reference.json``): the number of free parameters, R_wp
within 5 % relative, and the cell lengths and angles, atomic coordinates and isotropic ADPs both
programs refine, each within two of edi's standard uncertainties. One ``python -m edi fit`` of a
copy gives the regression pins: iterations and reduced chi-square. A reference the fit misses
is kept and printed, so the check reports it.

A scan is compared on its template file's single fit, as FullProf's reference is. An example whose
Bérar-Baldinozzi asymmetry differs in form between the programs has a FullProf fit with the
asymmetry fixed at 0 beside its reference (``asymmetry-off/``): the full model is compared on
R_wp and the number of free parameters only, and every shared value on the ``asymmetry-off``
variant. A simulation pins the point count and the checksum ``python -m edi calc`` reports. A
dropped example with no FullProf fit keeps edi's result as regression pins. The run's seconds are
printed for ``runtimes.tsv``.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'checks'))
from cli_projects import fit_template_only, fix_asymmetry_off  # noqa: E402 - the check's own rules

CLI = ROOT / 'docs' / 'user' / 'cli'
FULLPROF = ROOT / 'knowledge' / 'fitting' / 'fullprof'
ASYMMETRY_OFF = 'asymmetry-off'
SHARED = re.compile(
    r'^(?P<structure>[^.]+)\.(?:cell\.(?P<cell>(length|angle)_\w+)'
    r'|atom_site\.(?P<site>[^.]+)\.(?P<attr>fract_[xyz]|adp_iso))$'
)
SIGMA_MULTIPLE = 2.0
RWP_TOLERANCE = 0.05
# The default descent must reach a fast-descent case's own result: R_wp within 2 % relative and
# these values within two standard uncertainties. The case keeps its declared fast descent.
LADDER_WITNESS = {'pd-xray-cwl_lam7o3-p021': ('param.O1.fract_x',)}
LADDER_RWP_TOLERANCE = 0.02
# With the asymmetry off, LATP's two weak AlPO4 phases have flat cells: edi moves them to a lower
# minimum than FullProf reaches, and P1's Biso moves with them, so they are pins of edi's own
# result. That fit stops after the engine's allowed resumes, every value settled; a refit from its
# end converges at the same values.
ASYMMETRY_OFF_PINNED = {
    'pd-xray-cwl_latp-bm01_scan': (
        'alpo4_c2221.cell.',
        'alpo4_p63mc.cell.',
        'latp.atom_site.P1.adp_iso',
    )
}
ASYMMETRY_OFF_STATUS = {'pd-xray-cwl_latp-bm01_scan': 'max_iter'}


def machine_run(project: Path, command: str = 'fit') -> tuple[dict[str, str], float]:
    argv = [sys.executable, '-m', 'edi', command, str(project), '--report', 'machine']
    started = time.perf_counter()
    run = subprocess.run(
        [*argv, '--verbosity', 'full'], capture_output=True, text=True, check=True, timeout=900
    )
    seconds = time.perf_counter() - started
    return dict(line.split('=', 1) for line in run.stdout.splitlines() if '=' in line), seconds


def setting(project: Path, name: str) -> str | None:
    for path in sorted(project.rglob('*.edi')):
        match = re.search(rf'(?m)^{re.escape(name)} "?([^"\n]+?)"?$', path.read_text('utf-8'))
        if match:
            return match[1]
    return None


def count(project: Path, folder: str) -> int:
    return len(list((project / folder).glob('*.edi')))


def label(unique: str, structures: int) -> str | None:
    """The label edi's report gives a structure parameter's unique name."""
    match = SHARED.match(unique)
    if not match:
        return None
    prefix = f'{match["structure"]}.' if structures > 1 else ''
    if match['cell']:
        return f'{prefix}cell_{match["cell"]}'
    return f'{prefix}{match["site"]}.{match["attr"]}'


def quantity(value: float, kind: str, tol_abs: float | None, tol_rel: float | None) -> dict:
    return {'value': float(value), 'kind': kind, 'tol_abs': tol_abs, 'tol_rel': tol_rel}


def references(case: str, fit: str = '') -> tuple[dict, dict[str, float]]:
    """A FullProf record and its shared values by edi unique name."""
    record = json.loads((FULLPROF / case / fit / 'reference.json').read_text(encoding='utf-8'))
    values = {}
    for unique, code in record['parameter_codes'].items():
        if SHARED.match(unique) and code:
            values[unique] = record['fullprof_parameters'][str(code)]['value']
    return record, values


def check(case: str, name: str, spec: dict, measured: float, notes: list[str]) -> None:
    """Note a reference the fit misses: it stays in the record, as gate 4 reports it."""
    bound = spec['tol_abs'] if spec['tol_abs'] is not None else spec['tol_rel'] * spec['value']
    if not abs(measured - spec['value']) <= bound:
        notes.append(
            f'{case}: {name} edi {measured:.7g}, FullProf {spec["value"]:.7g} (bound {bound:.2g})'
        )


def pins(machine: dict[str, str]) -> dict:
    return {
        'iterations': quantity(machine['iterations'], 'regression-pin', 0.0, None),
        'reduced_chi_square': quantity(
            machine['reduced_chi_square'], 'regression-pin', 1e-6, None
        ),
    }


def pins_only(machine: dict[str, str]) -> dict:
    """A dropped example with no FullProf fit of its own keeps edi's result as regression pins."""
    return {
        'n_free': quantity(machine['n_free'], 'regression-pin', 0.0, None),
        'rwp': quantity(machine['rwp'], 'regression-pin', None, 1e-6),
        **pins(machine),
    }


def n_free(case: str, record: dict, machine: dict[str, str], notes: list[str]) -> dict:
    spec = quantity(record['n_free'], 'reference', 0.0, None)
    check(case, 'n_free', spec, float(machine['n_free']), notes)
    return {'n_free': spec}


def shared_values(
    case: str,
    project: Path,
    shared: dict[str, float],
    machine: dict[str, str],
    notes: list[str],
    pinned: tuple[str, ...] = (),
) -> dict:
    """Each shared FullProf value within two of edi's uncertainties; a pinned one is edi's own."""
    structures = count(project, 'structures')
    quantities = {}
    for unique, value in shared.items():
        name = f'param.{label(unique, structures)}'
        su = float(machine.get(f'{name}.uncertainty', 'nan'))
        if not su > 0:
            raise SystemExit(f'{case}: {unique} has no edi uncertainty as {name}')
        if unique.startswith(pinned):
            quantities[f'{name}.value'] = quantity(
                machine[f'{name}.value'], 'regression-pin', SIGMA_MULTIPLE * su, None
            )
            continue
        spec = quantity(value, 'reference', SIGMA_MULTIPLE * su, None)
        quantities[f'{name}.value'] = spec
        check(case, f'{name}.value', spec, float(machine[f'{name}.value']), notes)
    return quantities


def ladder_variant(case: str, machine: dict[str, str]) -> dict:
    """The default descent's witness for a fast-descent case, from that case's own fit."""
    quantities = {'rwp': quantity(machine['rwp'], 'regression-pin', None, LADDER_RWP_TOLERANCE)}
    for name in LADDER_WITNESS[case]:
        su = float(machine[f'{name}.uncertainty'])
        quantities[f'{name}.value'] = quantity(
            machine[f'{name}.value'], 'regression-pin', SIGMA_MULTIPLE * su, None
        )
    return {'ladder': {'quantities': quantities}}


def asymmetry_off_variant(case: str, start: Path, notes: list[str]) -> tuple[dict, float]:
    """Every shared value on the fit with the Bérar-Baldinozzi asymmetry fixed at 0 in both."""
    record, shared = references(case, ASYMMETRY_OFF)
    off = start.parent / ASYMMETRY_OFF
    shutil.copytree(start, off)
    fix_asymmetry_off(off)
    machine, seconds = machine_run(off)
    pinned = ASYMMETRY_OFF_PINNED.get(case, ())
    quantities = {
        **n_free(case, record, machine, notes),
        **shared_values(case, off, shared, machine, notes, pinned),
        **pins(machine),
    }
    block = {'quantities': quantities}
    status = ASYMMETRY_OFF_STATUS.get(case, 'done')
    if machine['status'] != status:
        notes.append(f'{case}: {ASYMMETRY_OFF} ends {machine["status"]}, not {status}')
    if status != 'done':
        block['status'] = status
    return {ASYMMETRY_OFF: block}, seconds


def fitted(case: str, start: Path, notes: list[str]) -> tuple[dict, dict, float]:
    """The record's quantities and variants, and the seconds the fits took.

    Every fit runs on its own copy of ``start``: a fit saves its result into its project.
    """
    project = start.parent / 'project'
    shutil.copytree(start, project)
    machine, seconds = machine_run(project)
    if not (FULLPROF / case / 'reference.json').exists():
        return pins_only(machine), {}, seconds
    record, shared = references(case)
    quantities = n_free(case, record, machine, notes)
    quantities['rwp'] = quantity(record['r_wp'], 'reference', None, RWP_TOLERANCE)
    check(case, 'rwp', quantities['rwp'], float(machine['rwp']), notes)
    variants = {}
    if (FULLPROF / case / ASYMMETRY_OFF / 'reference.json').exists():
        variants, more = asymmetry_off_variant(case, start, notes)
        seconds += more
    else:
        quantities.update(shared_values(case, project, shared, machine, notes))
    quantities.update(pins(machine))
    if case in LADDER_WITNESS:
        variants.update(ladder_variant(case, machine))
    return quantities, variants, seconds


def write(case: str, notes: list[str]) -> float:
    home = CLI / case
    with tempfile.TemporaryDirectory(prefix=f'catalogue-{case}-') as scratch:
        project = Path(scratch) / 'start'
        shutil.copytree(home / 'project', project)
        if setting(project, '_metadata.purpose') == 'simulation':
            machine, seconds = machine_run(project, 'calc')
            document = {
                'schema': 1,
                'source': {
                    'engine': 'edi (regression pins; the FullProf agreement is a test of its own)',
                    'artifact': 'machine record (python -m edi calc --report machine)',
                    'provenance': 'PROVENANCE.md',
                },
                'calc': {
                    'quantities': {
                        'n_points': quantity(machine['n_points'], 'regression-pin', 0.0, None),
                        'checksum': quantity(machine['checksum'], 'regression-pin', None, 1e-6),
                    }
                },
            }
        else:
            scan = setting(project, '_fitting_mode.type') == 'sequential'
            if scan:
                fit_template_only(project)
            quantities, variants, seconds = fitted(case, project, notes)
            referenced = (FULLPROF / case / 'reference.json').exists()
            document = {
                'schema': 1,
                'source': {
                    'engine': 'FullProf 8.40 (references); edi (regression pins)'
                    if referenced
                    else 'edi (regression pins; no FullProf fit of this start)',
                    'artifact': f'../../../../knowledge/fitting/fullprof/{case}/reference.json'
                    if referenced
                    else 'machine record (python -m edi fit --report machine)',
                    'provenance': 'PROVENANCE.md',
                },
            }
            if scan:
                document['template'] = True
            document['quantities'] = quantities
            if variants:
                document['variants'] = variants
    (home / 'expected.json').write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')
    return seconds


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n', 1)[0])
    parser.add_argument('cases', nargs='*', help='default: every catalogue case')
    args = parser.parse_args(argv)
    rows = yaml.safe_load((CLI / 'projects.yml').read_text(encoding='utf-8'))['projects']
    cases = args.cases or [row['id'] for row in rows if row.get('user-facing') is True]
    notes: list[str] = []
    for case in cases:
        seconds = write(case, notes)
        print(f'{case}\t{seconds:.2f}')
    for note in notes:
        print(f'differs from FullProf: {note}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())

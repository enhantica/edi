# SPDX-License-Identifier: BSD-3-Clause
"""Build the single-crystal CLI projects from FullProf's references.

Each verification project reproduces one of diffraction-lib's ``sc-*`` verification pages: the
structure, extinction and scale of the FullProf ``.pcr`` the page reads, and the measured
reflections of its ``.int`` file, with the parameters the page frees left free. The fitting
examples start the same data from rough values. The FullProf files are the committed references
under ``tests/fixtures/single_crystal/fullprof/`` (diffraction-lib's ``docs/docs/verification/
fullprof/sc-*``, unchanged).

Usage (writes ``docs/user/cli/<id>/project/``, every project or the ids given)::

    python tools/cli_projects/build_sc_projects.py [--out DIR] [ID ...]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FP = ROOT / 'tests' / 'fixtures' / 'single_crystal' / 'fullprof'
# FullProf's fits of the same pages on their measured reflections, which the verification projects'
# expected values come from.
FITTED = ROOT / 'tests' / 'fixtures' / 'single_crystal' / 'fitting' / 'fullprof'

PR2NIO4_SITES = [
    # id, type, x, y, z, wyckoff, occupancy, adp_type, adp_iso, beta (11 22 33 12 13 23)
    (
        'Pr',
        'Pr',
        '0',
        '0',
        '0.35973',
        'i',
        '1',
        'beta',
        None,
        ('0.0071', '0.0071', '0.00084', '0', '0', '0'),
    ),
    (
        'Ni',
        'Ni',
        '0',
        '0',
        '0',
        'a',
        '1',
        'beta',
        None,
        ('0.0028', '0.0028', '0.00151', '0', '0', '0'),
    ),
    (
        'O1',
        'O',
        '0.25',
        '0.25',
        '0',
        'e',
        '1',
        'beta',
        None,
        ('0.005', '0.005', '0.00413', '-0.0014', '0', '0'),
    ),
    (
        'O2',
        'O',
        '0',
        '0',
        '0.17385',
        'i',
        '0.722965',
        'beta',
        None,
        ('0.01716', '0.01716', '0.00045', '0', '0', '0'),
    ),
    (
        'Oi',
        'O',
        '0.25',
        '0.25',
        '0.25',
        'f',
        '0.074655',
        'beta',
        None,
        ('0.01033', '0.01176', '0.001', '0', '0', '0'),
    ),
    ('Od', 'O', '0.07347', '0.07347', '0.17349', 'p', '0.074654', 'Biso', '2.31435', None),
]

TBTI_ISO_SITES = [
    ('Tb', 'Tb', '0.5', '0.5', '0.5', 'd', '1', 'Biso', '0', None),
    ('Ti', 'Ti', '0', '0', '0', 'c', '1', 'Biso', '0', None),
    ('O1', 'O', '0.32804', '0.125', '0.125', 'f', '1', 'Biso', '0', None),
    ('O2', 'O', '0.375', '0.375', '0.375', 'b', '1', 'Biso', '0', None),
]

TBTI_ANISO_SITES = [
    (
        'Tb',
        'Tb',
        '0.5',
        '0.5',
        '0.5',
        'd',
        '1',
        'beta',
        None,
        ('0.00099', '0.00099', '0.00099', '-0.00048', '-0.00048', '-0.00048'),
    ),
    (
        'Ti',
        'Ti',
        '0',
        '0',
        '0',
        'c',
        '1',
        'beta',
        None,
        ('0.00091', '0.00091', '0.00091', '-0.00017', '-0.00017', '-0.00017'),
    ),
    (
        'O1',
        'O',
        '0.32804',
        '0.125',
        '0.125',
        'f',
        '1',
        'beta',
        None,
        ('0.00123', '0.00078', '0.00078', '0', '0', '0.00041'),
    ),
    (
        'O2',
        'O',
        '0.375',
        '0.375',
        '0.375',
        'b',
        '1',
        'beta',
        None,
        ('0.00061', '0.00061', '0.00061', '0', '0', '0'),
    ),
]

TAURINE_SITES = [
    (sid, typ, x, y, z, 'e', '1', 'Biso', biso, None)
    for sid, typ, x, y, z, biso in [
        ('S1', 'S', '0.19448', '0.35173', '0.3473', '1.37018'),
        ('O1', 'O', '0.31207', '0.23951', '0.35143', '2.68011'),
        ('O2', 'O', '-0.05909', '0.33563', '0.29636', '3.50515'),
        ('O3', 'O', '0.22105', '0.41215', '0.50573', '1.83513'),
        ('N1', 'N', '0.2634', '0.62808', '0.33048', '2.07364'),
        ('H1', 'H', '0.12861', '0.58669', '0.41769', '3.31527'),
        ('H2', 'H', '0.18953', '0.71385', '0.31124', '4.46988'),
        ('H3', 'H', '0.4397', '0.62023', '0.34592', '4.34151'),
        ('C1', 'C', '0.34384', '0.44116', '0.20155', '1.73667'),
        ('H11', 'H', '0.55246', '0.43345', '0.24304', '3.32279'),
        ('H12', 'H', '0.32537', '0.3897', '0.08264', '3.05746'),
        ('C2', 'C', '0.20029', '0.55716', '0.18272', '1.66017'),
        ('H21', 'H', '0.2765', '0.60004', '0.07688', '2.15403'),
        ('H22', 'H', '-0.00383', '0.54767', '0.15762', '4.71303'),
    ]
]

PROJECTS = {
    'sc-neut-tof_taurine-unknown_basic': {
        'source': 'sc-neut-tof_taurine_basic/taurine.int',
        'structure': 'taurine',
        'title': 'Taurine [P2₁/c] · Unknown instrument',
        'description': 'Single crystal · Time of flight · Isotropic ADPs · Scale-only fit',
        'space_group': ('P 21/c', 'b1'),
        'cell': ('5.272901', '11.656488', '7.838297', '90', '94.010994', '90'),
        'sites': TAURINE_SITES,
        'scale': '2.711()',
        'extinction': ('gauss', '0', '0'),
        'tof': True,
        # FullProf fits only the reflections it does not exclude (I > 3 sigma, and one more).
        'select': 'sc-neut-tof_taurine-unknown_basic/taurine.out',
    },
    'sc-neut-cwl_pr2nio4-5c2_basic': {
        'source': 'sc-neut-cwl_pr2nio4_basic/prnio.int',
        'structure': 'pr2nio4',
        'title': 'Pr₂NiO₄ [Fmmm] · Unknown instrument',
        'description': 'Single crystal · Anisotropic β tensors · Scale-only fit',
        'space_group': ('F m m m', None),
        'cell': ('5.417799', '5.4146', '12.483399', '90', '90', '90'),
        'sites': PR2NIO4_SITES,
        'scale': '4.031()',
        'extinction': ('gauss', '0', '0'),
    },
    'sc-neut-cwl_tb2ti2o7-heidi_basic': {
        'source': 'sc-neut-cwl_tbti_basic/tbti.int',
        'structure': 'tb2ti2o7',
        'experiment': 'heidi',
        'title': 'Tb₂Ti₂O₇ [Fd-3m] · HEiDi @ MLZ (FRM II)',
        'instrument': 'HEiDi',
        'facility': 'MLZ (FRM II)',
        'description': 'Single crystal · Isotropic ADPs · Scale-only fit',
        'space_group': ('F d -3 m', '2'),
        'cell': ('10.13', '10.13', '10.13', '90', '90', '90'),
        'sites': TBTI_ISO_SITES,
        'scale': '3.653()',
        'extinction': ('gauss', '0', '0'),
    },
    'sc-neut-cwl_tb2ti2o7-heidi_isotropic-extinction': {
        'source': 'sc-neut-cwl_tbti_isotropic-extinction/tbti.int',
        'structure': 'tb2ti2o7',
        'experiment': 'heidi',
        'title': 'Tb₂Ti₂O₇ [Fd-3m] · HEiDi @ MLZ (FRM II)',
        'instrument': 'HEiDi',
        'facility': 'MLZ (FRM II)',
        'description': 'Single crystal · Becker-Coppens extinction · Scale and radius fit',
        'space_group': ('F d -3 m', '2'),
        'cell': ('10.13', '10.13', '10.13', '90', '90', '90'),
        'sites': TBTI_ISO_SITES,
        'scale': '4.1744()',
        'extinction': ('gauss', '10()', '35000'),
    },
    'sc-neut-cwl_tb2ti2o7-heidi_anisotropic-adp': {
        'source': 'sc-neut-cwl_tbti_anisotropic-adp/tbti.int',
        'structure': 'tb2ti2o7',
        'experiment': 'heidi',
        'title': 'Tb₂Ti₂O₇ [Fd-3m] · HEiDi @ MLZ (FRM II)',
        'instrument': 'HEiDi',
        'facility': 'MLZ (FRM II)',
        'description': 'Single crystal · Anisotropic β tensors · Scale-only fit',
        'space_group': ('F d -3 m', '2'),
        'cell': ('10.13', '10.13', '10.13', '90', '90', '90'),
        'sites': TBTI_ANISO_SITES,
        'scale': '4.6()',
        'extinction': ('gauss', '0', '0'),
    },
}


# The app's fitting examples: displacements from a small start, one extinction parameter free
# at most, the free coordinates moved off their refined values.
U = '0.0026()'
TBTI_FIT_SITES = [
    (
        'Tb',
        'Tb',
        '0.5',
        '0.5',
        '0.5',
        'd',
        '1',
        'Uani',
        '0.0026',
        (U, '0.0026', '0.0026', '0()', '0', '0'),
    ),
    (
        'Ti',
        'Ti',
        '0',
        '0',
        '0',
        'c',
        '1',
        'Uani',
        '0.0026',
        (U, '0.0026', '0.0026', '0()', '0', '0'),
    ),
    (
        'O1',
        'O',
        '0.3300()',
        '0.125',
        '0.125',
        'f',
        '1',
        'Uani',
        '0.0026',
        (U, U, '0.0026', '0', '0', '0()'),
    ),
    (
        'O2',
        'O',
        '0.375',
        '0.375',
        '0.375',
        'b',
        '1',
        'Uani',
        '0.0026',
        (U, '0.0026', '0.0026', '0', '0', '0'),
    ),
]
PR2NIO4_FIT_SITES = [
    ('Pr', 'Pr', '0', '0', '0.3620()', 'i', '1', 'Biso', '0.5()', None),
    ('Ni', 'Ni', '0', '0', '0', 'a', '1', 'Biso', '0.5()', None),
    ('O1', 'O', '0.25', '0.25', '0', 'e', '1', 'Biso', '0.5()', None),
    ('O2', 'O', '0', '0', '0.1760()', 'i', '0.722965', 'Biso', '0.5()', None),
    ('Oi', 'O', '0.25', '0.25', '0.25', 'f', '0.074655', 'Biso', '0.5()', None),
    ('Od', 'O', '0.0750()', '0.0750()', '0.1750()', 'p', '0.074654', 'Biso', '0.5()', None),
]
FIT_PROJECTS = {
    'sc-neut-tof_taurine_fit': {
        'source': 'sc-neut-tof_taurine_basic/taurine.int',
        'structure': 'taurine',
        'title': 'Taurine [P2₁/c] · Unknown instrument',
        'description': (
            'Single crystal · Time of flight · Isotropic displacements from a rough start'
        ),
        'purpose': 'refinement',
        'space_group': ('P 21/c', 'b1'),
        'cell': ('5.272901', '11.656488', '7.838297', '90', '94.010994', '90'),
        'sites': [
            (sid, typ, x, y, z, w, occ, adp, '1.5()', None)
            for sid, typ, x, y, z, w, occ, adp, _, _ in TAURINE_SITES
        ],
        'scale': '1()',
        'extinction': ('gauss', '0', '0'),
        'tof': True,
    },
    'sc-neut-cwl_tb2ti2o7-heidi_fit': {
        'source': 'sc-neut-cwl_tbti_basic/tbti.int',
        'structure': 'tb2ti2o7',
        'experiment': 'heidi',
        'title': 'Tb₂Ti₂O₇ [Fd-3m] · HEiDi @ MLZ (FRM II)',
        'instrument': 'HEiDi',
        'facility': 'MLZ (FRM II)',
        'description': (
            'Single crystal · Anisotropic displacements and extinction from a rough start'
        ),
        'purpose': 'refinement',
        'space_group': ('F d -3 m', '2'),
        'cell': ('10.13', '10.13', '10.13', '90', '90', '90'),
        'sites': TBTI_FIT_SITES,
        'scale': '4()',
        'extinction': ('gauss', '25', '0()'),
    },
    'sc-neut-cwl_pr2nio4-5c2_fit': {
        'source': 'sc-neut-cwl_pr2nio4_basic/prnio.int',
        'structure': 'pr2nio4',
        'experiment': 'llb_5c2',
        'title': 'Pr₂NiO₄ [Fmmm] · 5C2 @ LLB',
        'instrument': '5C2',
        'facility': 'LLB',
        'description': (
            'Single crystal · Isotropic displacements and coordinates from a rough start'
        ),
        'purpose': 'refinement',
        'space_group': ('F m m m', None),
        'cell': ('5.417799', '5.4146', '12.483399', '90', '90', '90'),
        'sites': PR2NIO4_FIT_SITES,
        'scale': '4()',
        'extinction': ('gauss', '0', '0'),
    },
}


def read_int(path: Path) -> tuple[float, list[tuple[int, int, int, str, str]]]:
    """Return the wavelength and the (h, k, l, F², su) rows of a FullProf .int file."""
    lines = path.read_text(encoding='utf-8').splitlines()
    wavelength = float(lines[2].split()[0])
    rows = []
    for line in lines[3:]:
        fields = line.split()
        if len(fields) < 5:
            continue
        rows.append((
            int(fields[0]),
            int(fields[1]),
            int(fields[2]),
            fields[3],
            fields[4],
            fields[6] if len(fields) > 6 else None,
        ))
    return wavelength, rows


def included(path: Path) -> set[tuple[int, int, int]]:
    """Return the reflections a FullProf .out lists without its `Excl` mark."""
    lines = path.read_text(encoding='utf-8').splitlines()
    start = next(n for n, line in enumerate(lines) if 'F2obs' in line and 'F2cal' in line)
    kept = set()
    for line in lines[start + 1 :]:
        fields = line.split()
        try:
            key = (int(fields[0]), int(fields[1]), int(fields[2]))
        except (ValueError, IndexError):
            break
        if 'Excl' not in line:
            kept.add(key)
    return kept


def number(text: str) -> str:
    """A FullProf number as the .edi writes it (no leading-dot form)."""
    value = float(text)
    return repr(value) if value != int(value) else str(int(value))


def quoted(text: str | None) -> str:
    return f'"{text}"' if text else '?'


def write_project(root: Path, pid: str, spec: dict) -> None:  # noqa: PLR0914 — one file per block, written in order
    project = root / pid / 'project'
    for sub in ('structures', 'experiments', 'analysis'):
        (project / sub).mkdir(parents=True, exist_ok=True)
    wavelength, rows = read_int(FP / spec['source'])
    if 'select' in spec:
        kept = included(FITTED / spec['select'])
        rows = [row for row in rows if row[:3] in kept]
    name = spec['structure']
    experiment = spec.get('experiment', name)
    (project / 'project.edi').write_text(
        '_edi.schema_version 3\n\n'
        f'_metadata.name             {pid.replace("-", "_")}\n'
        f'_metadata.title "{spec["title"]}"\n'
        f'_metadata.description "{spec["description"]}"\n'
        '_metadata.created          "22 Oct 2026 18:00:00"\n'
        '_metadata.last_modified    "22 Oct 2026 18:00:00"\n'
        '_metadata.timestamp        ?\n'
        f'_metadata.purpose "{spec.get("purpose", "verification")}"\n'
        '_metadata.dimensionality "1D"\n'
        f'_metadata.instrument {quoted(spec.get("instrument"))}\n'
        f'_metadata.facility {quoted(spec.get("facility"))}\n'
        '_metadata.polarisation "none"\n',
        encoding='utf-8',
    )
    (project / 'analysis' / 'analysis.edi').write_text(
        '_edi.schema_version 3\n\n_fitting_mode.type single\n\n'
        f'loop_\n_joint_fit.experiment_id\n_joint_fit.weight\n{experiment} 1\n',
        encoding='utf-8',
    )
    group, code = spec['space_group']
    a, b, c, al, be, ga = spec['cell']
    text = [
        f'data_{name}',
        '',
        '_edi.schema_version 3',
        '',
        f'_cell.length_a {a}',
        f'_cell.length_b {b}',
        f'_cell.length_c {c}',
        f'_cell.angle_alpha {al}',
        f'_cell.angle_beta {be}',
        f'_cell.angle_gamma {ga}',
        '',
        f'_space_group.name_h_m "{group}"',
    ]
    if code:
        text.append(f'_space_group.coord_system_code {code}')
    text += [
        '',
        'loop_',
        '_atom_site.id',
        '_atom_site.type_symbol',
        '_atom_site.fract_x',
        '_atom_site.fract_y',
        '_atom_site.fract_z',
        '_atom_site.wyckoff_letter',
        '_atom_site.occupancy',
        '_atom_site.adp_type',
        '_atom_site.adp_iso',
    ]
    aniso = []
    for sid, typ, x, y, z, w, occ, adp_type, adp_iso, beta in spec['sites']:
        text.append(f'{sid} {typ} {x} {y} {z} {w} {occ} {adp_type} {adp_iso or "0"}')
        if beta:
            aniso.append(f'{sid} ' + ' '.join(beta))
    if aniso:
        text += [
            '',
            'loop_',
            '_atom_site_aniso.id',
            '_atom_site_aniso.adp_11',
            '_atom_site_aniso.adp_22',
            '_atom_site_aniso.adp_33',
            '_atom_site_aniso.adp_12',
            '_atom_site_aniso.adp_13',
            '_atom_site_aniso.adp_23',
            *aniso,
        ]
    (project / 'structures' / f'{name}.edi').write_text('\n'.join(text) + '\n', encoding='utf-8')
    model, radius, mosaicity = spec['extinction']
    beam_mode = 'time-of-flight' if spec.get('tof') else 'constant wavelength'
    text = [
        f'data_{experiment}',
        '',
        '_edi.schema_version 3',
        '',
        '_experiment_type.sample_form "single crystal"',
        f'_experiment_type.beam_mode "{beam_mode}"',
        '_experiment_type.radiation_probe "neutron"',
        '_experiment_type.scattering_type "bragg"',
        '_scattering_source.neutron_scattering_length sears1992',
        '',
        '_calculator.type crysta',
        '',
        *(
            []
            if spec.get('tof')
            else [f'_instrument.setup_wavelength {number(str(wavelength))}', '']
        ),
        '_extinction.type becker-coppens',
        f'_extinction.model {model}',
        f'_extinction.radius {radius}',
        f'_extinction.mosaicity {mosaicity}',
        '',
        'loop_',
        '_linked_structure.structure_id',
        '_linked_structure.scale',
        f'{name} {spec["scale"]}',
        '',
        'loop_',
        '_refln.id',
        '_refln.index_h',
        '_refln.index_k',
        '_refln.index_l',
        '_refln.intensity_meas',
        '_refln.intensity_meas_su',
        *(['_refln.wavelength'] if spec.get('tof') else []),
    ]
    for index, (h, k, ell, f2, su, lam) in enumerate(rows, start=1):
        text.append(
            f'{index} {h} {k} {ell} {number(f2)} {number(su)}'
            + (f' {number(lam)}' if spec.get('tof') else '')
        )
    (project / 'experiments' / f'{experiment}.edi').write_text(
        '\n'.join(text) + '\n', encoding='utf-8'
    )


def write_references(root: Path, pid: str) -> None:
    """Write a verification project's expected.json and PROVENANCE.md from FullProf's fit."""
    reference = json.loads((FITTED / pid / 'expected.json').read_text(encoding='utf-8'))
    artifact = f'../../../../tests/fixtures/single_crystal/fitting/fullprof/{pid}/'
    reference['source'] = {
        'engine': reference['source']['engine'],
        'artifact': artifact + reference['source']['artifact'],
        'provenance': 'PROVENANCE.md',
    }
    (root / pid / 'expected.json').write_text(
        json.dumps(reference, indent=2) + '\n', encoding='utf-8'
    )
    rows = '\n'.join(
        f'| `{name}` | {item["kind"]} | {item["value"]} | '
        + ', '.join(f'{key} {item[key]}' for key in ('tol_abs', 'tol_rel') if key in item)
        + ' |'
        for name, item in reference['quantities'].items()
    )
    caveat = (
        ''
        if reference.get('comparable_parameters', True)
        else '\nFullProf fits its own extinction model (model 1, Ext1), not the Becker-Coppens '
        'radius this project frees, so its values do not describe the same model. diffraction-lib '
        'marks '
        'the same difference on its page. FullProf 8.40 has no Becker-Coppens sphere model (only '
        'model 1 and the anisotropic model 4), so no FullProf fit can be its reference: the '
        'project stays out of the executing set until a reference from the Becker-Coppens '
        'engine diffraction-lib uses (CrysPy) exists.\n'
    )
    (root / pid / 'PROVENANCE.md').write_text(
        f"""# {pid}: provenance

Built by `tools/cli_projects/build_sc_projects.py` from FullProf's files for the matching
diffraction-lib verification page (`tests/fixtures/single_crystal/fullprof/`). The structure,
extinction and starting scale are the page's FullProf values; the measured reflections are its
`.int` file. The parameters the page frees are free.

## Which values are references

Every value comes from FullProf's own fit of the same parameters on the same reflections
(`{artifact}`, see the `README.md` there), never from edi or crysta.

| quantity | kind | value | tolerance |
| --- | --- | --- | --- |
{rows}

The scale's tolerance is FullProf's own uncertainty plus half its last printed digit; the
reduced chi-square is FullProf's residual sum over N - p.
{caveat}""",
        encoding='utf-8',
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--out', type=Path, default=ROOT / 'docs' / 'user' / 'cli')
    parser.add_argument('ids', nargs='*')
    args = parser.parse_args()
    projects = {**PROJECTS, **FIT_PROJECTS}
    unknown = set(args.ids) - set(projects)
    if unknown:
        parser.error(f'unknown project ids: {sorted(unknown)}')
    for pid, spec in projects.items():
        if not args.ids or pid in args.ids:
            write_project(args.out, pid, spec)
            if pid in PROJECTS:
                write_references(args.out, pid)
            print('wrote', pid)
    return 0


if __name__ == '__main__':
    sys.exit(main())

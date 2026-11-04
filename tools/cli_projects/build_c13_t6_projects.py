# SPDX-License-Identifier: BSD-3-Clause
"""Build the three CLI projects from their vendored FullProf fitting references.

- ``pd-neut-tof_cecoal-polaris_chebyshev``: CeCoAl3 on POLARIS, the Chebyshev background
  (FullProf ``Nba -5``);
- ``pd-neut-tof_ceo2-pearl_polynomial``: CeO2 on PEARL, the polynomial background (``Nba 0``);
- ``pd-neut-cwl_lab6-11b-echidna_tch-fcj``: the owner's LaB6 TCH x FCJ fit, the polynomial
  background.

Each project is the model of ``knowledge/fitting/fullprof/<id>/``'s ``.pcr``: its data, excluded
regions, profile, calibration, absorption, structure and background, every value at FullProf's
converged state, and FullProf's free set (every parameter with a non-zero code). So FullProf's
refined values and standard uncertainties are independent references for
``python -m edi fit`` (each project's ``expected.json``). The translations (each project's
``PROVENANCE.md`` states them):

- an ``Occ`` is site occupancy x site multiplicity / general multiplicity; the project declares the
  site occupancy, 1 for every site (CeCoAl3's Al3, which FullProf refines to 1.020(8), starts at 1
  because crysta admits [0, 1]);
- the scattering lengths are FullProf's: Sears (1992) for CeCoAl3 and CeO2; for the 11B-enriched
  LaB6 the structure declares both values FullProf used, La 8.24 fm (its table) and 11B 6.65 fm
  (its additional scattering factor), since a declared map and a source cannot be combined
  (ADR-0067 section 6);
- FullProf's ``Wdt`` is ``_peak.cutoff_fwhm``; the Chebyshev domain is the ``.pcr``'s TOF-min and
  TOF-max, and the polynomial origin its ``Bkpos``.

CeCoAl3's reference is the project's own ``fullprof/ls-fit.sum``, FullProf's least-squares refit:
the vendored ``.pcr`` refines by maximum likelihood (``Iwg 1``), a different estimator.

Usage (the first writes ``docs/user/cli/<id>/project/`` and refuses an existing directory; the
second writes each ``expected.json`` from ``<records>/<id>.record``, the machine record of
``python -m edi fit <project> --dry --report machine --verbosity full``)::

    pixi run python tools/cli_projects/build_c13_t6_projects.py
    pixi run python tools/cli_projects/build_c13_t6_projects.py --expected <records>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FULLPROF = ROOT / 'knowledge' / 'fitting' / 'fullprof'
CLI = ROOT / 'docs' / 'user' / 'cli'
NUMBER = r'[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?'


class Pcr:
    """The lines of a FullProf ``.pcr`` the three references use, read by their marker comments."""

    def __init__(self, path: Path) -> None:
        self.lines = path.read_text(encoding='latin-1').splitlines()

    def after(self, marker: str, offset: int = 1) -> list[float]:
        index = next(i for i, line in enumerate(self.lines) if marker in line)
        return [float(token) for token in re.findall(NUMBER, self.lines[index + offset])]

    def pairs(self, marker: str) -> list[tuple[float, float]]:
        """The (value, code) pairs on the value and code lines below ``marker``."""
        return list(zip(self.after(marker, 1), self.after(marker, 2), strict=False))

    def blocks_after(self, marker: str) -> list[list[float]]:
        """Every numeric line below ``marker`` up to the next comment line."""
        index = next(i for i, line in enumerate(self.lines) if marker in line) + 1
        out = []
        for line in self.lines[index:]:
            if line.lstrip().startswith('!') or not line.strip():
                break
            out.append([float(token) for token in re.findall(NUMBER, line)])
        return out

    def background(self) -> list[tuple[float, float]]:
        rows = self.blocks_after('Background coefficients')
        return [
            pair
            for v, c in zip(rows[0::2], rows[1::2], strict=True)
            for pair in zip(v, c, strict=True)
        ]

    def atoms(self) -> list[dict]:
        index = next(i for i, line in enumerate(self.lines) if line.startswith('!Atom'))
        out = []
        for line, codes in zip(
            self.lines[index + 1 :: 2], self.lines[index + 2 :: 2], strict=False
        ):
            if line.lstrip().startswith('!'):
                break
            fields = line.split()
            values = [float(token) for token in fields[2:7]]
            flags = [float(token) for token in codes.split()[:5]]
            out.append({'id': fields[0], 'values': values, 'codes': flags})
        return out

    def space_group(self) -> str:
        line = next(line for line in self.lines if '<--Space group symbol' in line)
        return line.split('<--')[0].strip()

    def excluded(self) -> list[tuple[float, float]]:
        return [tuple(row) for row in self.blocks_after('Excluded regions')]


def read_dat(path: Path) -> list[tuple[float, float, float]]:
    """FullProf XYDATA (``Ins = 10``): the (x, y, sigma) rows, header lines skipped."""
    rows = []
    for line in path.read_text(encoding='latin-1').splitlines():
        fields = line.split()
        if len(fields) == 3 and all(re.fullmatch(NUMBER, field) for field in fields):
            rows.append(tuple(float(field) for field in fields))
    return rows


def fmt(value: float) -> str:
    return repr(float(value))


def param(value: float, code: float) -> str:
    """An ``.edi`` parameter: free (``()``) when FullProf refined it (a non-zero code)."""
    return fmt(value) + ('()' if code else '')


# The site occupancies (the `.pcr` Occ x M / m) and the Wyckoff letters, per reference.
SITES = {
    'cecoal': {
        'Ce': ('e', 2, 1.0),
        'Co': ('e', 2, 1.0),
        'Al1': ('a', 2, 1.0),
        'Al2': ('f', 2, 1.0),
        # FullProf refines Al3 to a site occupancy of 1.020(8), outside crysta's [0, 1]: the
        # project starts it at full occupancy, free as in FullProf.
        'Al3': ('j', 4, 1.0),
    },
    'pearl': {'Ce': ('a', 4, 1.0), 'O': ('c', 8, 1.0)},
    'lab6': {'La': ('a', 1, 1.0), 'B': ('f', 6, 1.0)},
}
ELEMENTS = {
    'Ce': 'Ce',
    'Co': 'Co',
    'Al1': 'Al',
    'Al2': 'Al',
    'Al3': 'Al',
    'O': 'O',
    'La': 'La',
    'B': 'B',
}

CASES = {
    'cecoal': {
        'id': 'pd-neut-tof_cecoal-polaris_chebyshev',
        'folder': 'pd-neut-tof_cecoal-polaris_chebyshev',
        'stem': 'cecoal',
        'structure': 'cecoal',
        'experiment': 'polaris',
        'title': 'CeCoAl3, POLARIS (ISIS), Chebyshev background',
    },
    'pearl': {
        'id': 'pd-neut-tof_ceo2-pearl_polynomial',
        'folder': 'pd-neut-tof_ceo2-pearl_polynomial',
        'stem': 'Ceo2_PEARL',
        'structure': 'ceo2',
        'experiment': 'pearl',
        'title': 'CeO2, PEARL (ISIS), polynomial background',
    },
    'lab6': {
        'id': 'pd-neut-cwl_lab6-11b-echidna_tch-fcj',
        'folder': 'pd-neut-cwl_lab6-11b-echidna_tch-fcj',
        'stem': 'ECH0030684_LaB6_1p622A',
        'structure': 'lab6',
        'experiment': 'echidna',
        'title': 'LaB6 (11B), ECHIDNA (ANSTO), TCH x FCJ, polynomial background',
    },
}


def structure_text(case: str, pcr: Pcr, name: str) -> str:
    cell = pcr.pairs('Cell Info')
    lines = [f'data_{name}', '', '_edi.schema_version 3', '']
    for tag, (value, code) in zip(
        ('length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma'),
        cell,
        strict=True,
    ):
        lines.append(f'_cell.{tag} {param(value, code)}')
    lines += ['', f'_space_group.name_h_m "{pcr.space_group().replace(" 3 ", " -3 ")}"', '']
    if case == 'lab6':
        # FullProf's two lengths: La from its table, 11B from the .pcr's additional scattering
        # factor (0.665e-12 cm), declared together because a map and a source cannot be combined.
        lines += [
            'loop_',
            '_scattering_length.type_symbol',
            '_scattering_length.length_fm',
            'B 6.65',
            'La 8.24',
            '',
        ]
    lines += [
        'loop_',
        '_atom_site.id',
        '_atom_site.type_symbol',
        '_atom_site.fract_x',
        '_atom_site.fract_y',
        '_atom_site.fract_z',
        '_atom_site.wyckoff_letter',
        '_atom_site.multiplicity',
        '_atom_site.occupancy',
        '_atom_site.adp_iso',
        '_atom_site.adp_type',
    ]
    for atom in pcr.atoms():
        letter, multiplicity, occupancy = SITES[case][atom['id']]
        x, y, z, biso, _ = atom['values']
        cx, cy, cz, cb, cocc = atom['codes']
        if case == 'lab6' and atom['id'] == 'B':
            # FullProf writes B at (1/2, 1/2, z); crysta's 6f representative is (x, 1/2, 1/2), the
            # same orbit (a cubic axis permutation), so the free coordinate is x.
            x, z, cx, cz = z, x, cz, cx
        lines.append(
            ' '.join([
                atom['id'],
                ELEMENTS[atom['id']],
                param(x, cx),
                param(y, cy),
                param(z, cz),
                letter,
                str(multiplicity),
                param(occupancy, cocc),
                param(biso, cb),
                'Biso',
            ])
        )
    return '\n'.join(lines) + '\n'


def background_lines(case: str, pcr: Pcr) -> list[str]:
    coefficients = pcr.background()
    if case == 'cecoal':
        tof = pcr.after('!NCY')
        head = [
            '_background.type chebyshev',
            f'_background.x_min {fmt(tof[6])}',
            f'_background.x_max {fmt(tof[8])}',
        ]
    else:
        origin = pcr.after('Bkpos')[0] if case == 'pearl' else pcr.after('Lambda1')[3]
        head = ['_background.type polynomial', f'_background.origin {fmt(origin)}']
    rows = [f'{order} {param(value, code)}' for order, (value, code) in enumerate(coefficients)]
    return [*head, '', 'loop_', '_background.order', '_background.coef', *rows]


def experiment_text(case: str, pcr: Pcr, name: str, structure: str, data) -> str:
    cw = case == 'lab6'
    scale = pcr.pairs('!  Scale')[0]
    lines = [f'data_{name}', '', '_edi.schema_version 3', '']
    lines += [
        '_experiment_type.sample_form powder',
        f'_experiment_type.beam_mode "{"constant wavelength" if cw else "time-of-flight"}"',
        '_experiment_type.radiation_probe neutron',
        '_experiment_type.scattering_type bragg',
        '',
        '_calculator.type crysta',
        '',
    ]
    if not cw:
        lines += ['_scattering_source.neutron_scattering_length sears1992', '']
        sigma = pcr.pairs('Sigma-2')
        gamma = pcr.pairs('Gamma-2')
        shape = pcr.pairs('alph0')
        wdt = pcr.after('Bkpos')[1]
        lines += [
            f'_peak.rise_alpha_0 {param(*shape[2])}',
            f'_peak.rise_alpha_1 {param(*shape[4])}',
            f'_peak.decay_beta_0 {param(*shape[3])}',
            f'_peak.decay_beta_1 {param(*shape[5])}',
            f'_peak.broad_gauss_sigma_0 {param(*sigma[2])}',
            f'_peak.broad_gauss_sigma_1 {param(*sigma[1])}',
            f'_peak.broad_gauss_sigma_2 {param(*sigma[0])}',
            '_peak.broad_gauss_size 0',
            '_peak.broad_gauss_strain 0',
            f'_peak.broad_lorentz_gamma_0 {param(*gamma[2])}',
            f'_peak.broad_lorentz_gamma_1 {param(*gamma[1])}',
            f'_peak.broad_lorentz_gamma_2 {param(*gamma[0])}',
            '_peak.broad_lorentz_size 0',
            '_peak.broad_lorentz_strain 0',
            f'_peak.cutoff_fwhm {fmt(wdt)}',
            '_peak.type tof-jorgensen-von-dreele',
            '',
        ]
        calib = pcr.after('2ThetaBank')
        lines += [
            f'_instrument.setup_twotheta_bank {fmt(calib[8])}',
            f'_instrument.calib_d_to_tof_offset {param(calib[0], calib[1])}',
            f'_instrument.calib_d_to_tof_linear {param(calib[2], calib[3])}',
            f'_instrument.calib_d_to_tof_quadratic {param(calib[4], calib[5])}',
            f'_instrument.calib_d_to_tof_reciprocal {param(calib[6], calib[7])}',
            '',
        ]
        abscor = pcr.after('ABSCOR1', 0)
        lines += [
            '_absorption.type cylinder',
            f'_absorption.abscor1 {param(abscor[0], abscor[1])}',
            f'_absorption.abscor2 {param(abscor[2], abscor[3])}',
            '',
        ]
    else:
        uvw = pcr.pairs('!       U ')
        asymmetry = pcr.pairs('S_L')
        wave = pcr.after('Lambda1')
        zero = pcr.after('!  Zero ')
        lines += [
            f'_peak.broad_gauss_u {param(*uvw[0])}',
            f'_peak.broad_gauss_v {param(*uvw[1])}',
            f'_peak.broad_gauss_w {param(*uvw[2])}',
            f'_peak.broad_lorentz_x {param(*uvw[3])}',
            f'_peak.broad_lorentz_y {param(*uvw[4])}',
            f'_peak.asym_fcj_1 {param(*asymmetry[6])}',
            f'_peak.asym_fcj_2 {param(*asymmetry[7])}',
            f'_peak.cutoff_fwhm {fmt(wave[4])}',
            '_peak.type cwl-tch-pseudo-voigt-fcj',
            '',
            f'_instrument.setup_wavelength {param(zero[6], zero[7])}',
            f'_instrument.calib_twotheta_offset {param(zero[0], zero[1])}',
            f'_instrument.calib_sample_displacement {param(zero[2], zero[3])}',
            f'_instrument.calib_sample_transparency {param(zero[4], zero[5])}',
            '',
            '_absorption.type cylinder-hewat',
            f'_absorption.mu_r {fmt(wave[6])}',
            '',
        ]
    excluded = [f'{i} {fmt(a)} {fmt(b)}' for i, (a, b) in enumerate(pcr.excluded(), start=1)]
    lines += [
        'loop_',
        '_excluded_region.id',
        '_excluded_region.start',
        '_excluded_region.end',
        *excluded,
        '',
    ]
    lines += [
        'loop_',
        '_linked_structure.structure_id',
        '_linked_structure.scale',
        f'{structure} {param(*scale)}',
        '',
    ]
    lines += [*background_lines(case, pcr), '']
    axis = '_data.two_theta' if cw else '_data.time_of_flight'
    lines += ['loop_', axis, '_data.id', '_data.intensity_meas', '_data.intensity_meas_su']
    lines += [f'{fmt(x)} {i} {fmt(y)} {fmt(s)}' for i, (x, y, s) in enumerate(data, start=1)]
    return '\n'.join(lines) + '\n'


SIGMA_MULTIPLE = 4  # every reference tolerance: four of FullProf's standard uncertainties


def sum_pair(lines: list[str], marker: str, offset: int = 0) -> tuple[float, float]:
    """The (value, su) pair a ``.sum`` prints on, or ``offset`` lines below, ``marker``."""
    index = next(i for i, line in enumerate(lines) if marker in line)
    text = lines[index].split(':', 1)[-1] if offset == 0 else lines[index + offset]
    values = [float(token) for token in re.findall(NUMBER, text)]
    return values[-2], values[-1]


def sum_atoms(lines: list[str]) -> dict[str, tuple[float, float]]:
    """The refined coordinates and Biso: ``value(last-digit su)`` in the ``.sum`` atom table."""
    out = {}
    index = next(i for i, line in enumerate(lines) if 'Name      x' in line)
    for line in lines[index + 1 :]:
        if not line.strip():
            break
        site = line.split()[0]
        cells = re.findall(r'(' + NUMBER + r')\(\s*(\d+)\)', line)
        for name, (value, su) in zip(
            ('fract_x', 'fract_y', 'fract_z', 'adp_iso'), cells, strict=False
        ):
            digits = len(value.split('.')[1]) if '.' in value else 0
            if int(su):
                out[f'{site}.{name}'] = (float(value), int(su) * 10.0**-digits)
    return out


def sum_background(lines: list[str]) -> list[tuple[float, float]]:
    index = next(i for i, line in enumerate(lines) if 'Background' in line and '==>' in line)
    out = []
    for line in lines[index + 1 :]:
        values = [float(token) for token in re.findall(NUMBER, line)]
        if len(values) != 2:
            break
        out.append((values[0], values[1]))
    return out


def sum_references(case: str, path: Path) -> dict[str, tuple[float, float]]:
    """FullProf's refined values and standard uncertainties, by machine-record parameter label."""
    lines = path.read_text(encoding='latin-1').splitlines()
    refs = {'scale': sum_pair(lines, 'scale factor')}
    if case == 'lab6':
        refs['calib_twotheta_offset'] = sum_pair(lines, 'Zero-point')
        refs['setup_wavelength'] = sum_pair(lines, 'wavelength (Lambda1)')
        refs['calib_sample_displacement'] = sum_pair(lines, 'Cos(2theta)-shift')
        refs['calib_sample_transparency'] = sum_pair(lines, 'Sin(2theta)-shift')
        for name, offset in (('broad_gauss_u', 0), ('broad_gauss_v', 1), ('broad_gauss_w', 2)):
            refs[name] = sum_pair(lines, 'Halfwidth parameters', offset)
        refs['broad_lorentz_y'] = sum_pair(lines, 'X and y parameters', 1)
    else:
        refs['calib_d_to_tof_offset'] = sum_pair(lines, 'Zero-point')
        refs['calib_d_to_tof_linear'] = sum_pair(lines, 'T.O.F.- dtt1')
        refs['calib_d_to_tof_quadratic'] = sum_pair(lines, 'T.O.F.- dtt2')
        for name, offset in (('broad_gauss_sigma_2', 1), ('broad_gauss_sigma_1', 2)):
            refs[name] = sum_pair(lines, 'Gaussian variances Sig-2', offset)
        refs['broad_lorentz_gamma_1'] = sum_pair(lines, 'Lorentzian FWHM Gam-2', 2)
        # The (value, su) pairs of alpha0, beta0, alpha1, beta1, packed three numbers to a line.
        index = next(i for i, line in enumerate(lines) if 'Peak shape parameter alpha0' in line)
        packed = [float(token) for line in lines[index + 1 : index + 5] for token in line.split()]
        for name, at in (
            ('rise_alpha_0', 0),
            ('decay_beta_0', 2),
            ('rise_alpha_1', 4),
            ('decay_beta_1', 6),
        ):
            refs[name] = (packed[at], packed[at + 1])
    atoms = sum_atoms(lines)
    if case == 'lab6':
        # The orbit permutation of the structure file: FullProf's B z is crysta's 6f x.
        atoms['B.fract_x'] = atoms.pop('B.fract_z')
    refs.update(atoms)
    for order, pair in enumerate(sum_background(lines)):
        refs[f'background[{order}]'] = pair
    return {name: pair for name, pair in refs.items() if pair[1] > 0}


REFERENCE_SUM = {
    'cecoal': Path('fullprof')
    / 'ls-fit.sum',  # project-local: the least-squares refit (PROVENANCE)
    'pearl': None,
    'lab6': None,
}


def write_expected(case: str, record: Path) -> Path:
    """``expected.json``: FullProf's references (4 sigma) and the regression pins of ``record``."""
    spec = CASES[case]
    home = CLI / spec['id']
    local = REFERENCE_SUM[case]
    source = home / local if local else FULLPROF / spec['folder'] / f'{spec["stem"]}.sum'
    lines = source.read_text(encoding='latin-1').splitlines()
    n_free = int(
        re.findall(NUMBER, next(line for line in lines if 'No. of fitted parameters' in line))[-1]
    )
    machine = dict(
        line.strip().split('=', 1)
        for line in record.read_text(encoding='utf-8').splitlines()
        if '=' in line
    )
    quantities = {
        'n_free': {'value': float(n_free), 'kind': 'reference', 'tol_abs': 0.0, 'tol_rel': None}
    }
    for name, (value, sigma) in sum_references(case, source).items():
        if f'param.{name}.value' not in machine:
            raise SystemExit(f'{case}: the record has no param.{name}.value')
        quantities[f'param.{name}.value'] = {
            'value': value,
            'kind': 'reference',
            'tol_abs': round(SIGMA_MULTIPLE * sigma, 12),
            'tol_rel': None,
        }
    for key, tol in (('iterations', 0.0), ('reduced_chi_square', 1e-6), ('rwp', 1e-9)):
        quantities[key] = {
            'value': float(machine[key]),
            'kind': 'regression-pin',
            'tol_abs': tol,
            'tol_rel': None,
        }
    relative = (
        source.relative_to(home)
        if local
        else Path('..') / '..' / '..' / '..' / source.relative_to(ROOT)
    )
    document = {
        'schema': 1,
        'source': {
            'engine': 'FullProf 8.40 (references); edi (regression pins)',
            'artifact': str(relative),
            'provenance': 'PROVENANCE.md',
        },
        'quantities': quantities,
    }
    out = home / 'expected.json'
    out.write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')
    return out


def write_project(case: str) -> Path:
    spec = CASES[case]
    folder = FULLPROF / spec['folder']
    pcr = Pcr(folder / f'{spec["stem"]}.pcr')
    data = read_dat(folder / f'{spec["stem"]}.dat')
    project = CLI / spec['id'] / 'project'
    if project.exists():
        raise SystemExit(f'{project} exists; remove it to rebuild')
    for sub in ('structures', 'experiments', 'analysis'):
        (project / sub).mkdir(parents=True)
    (project / 'project.edi').write_text(
        '_edi.schema_version 3\n\n'
        f'_metadata.name             {spec["id"].replace("-", "_")}\n'
        f'_metadata.title            "{spec["title"]}"\n'
        '_metadata.description      ?\n',
        encoding='utf-8',
    )
    (project / 'analysis' / 'analysis.edi').write_text(
        '_edi.schema_version 3\n\n_fitting_mode.type single\n\n'
        '_minimizer.type crysta\n_minimizer.max_iterations 1000\n'
        '_minimizer.chi_square_tolerance 1e-4\n',
        encoding='utf-8',
    )
    (project / 'structures' / f'{spec["structure"]}.edi').write_text(
        structure_text(case, pcr, spec['structure']), encoding='utf-8'
    )
    (project / 'experiments' / f'{spec["experiment"]}.edi').write_text(
        experiment_text(case, pcr, spec['experiment'], spec['structure'], data), encoding='utf-8'
    )
    return project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--case', choices=sorted(CASES), action='append')
    parser.add_argument(
        '--expected',
        type=Path,
        metavar='RECORD_DIR',
        help='write expected.json from <RECORD_DIR>/<id>.record (an edi fit machine record)',
    )
    args = parser.parse_args(argv)
    for case in args.case or sorted(CASES):
        if args.expected:
            print(write_expected(case, args.expected / f'{CASES[case]["id"]}.record'))
        else:
            print(write_project(case))
    return 0


if __name__ == '__main__':
    sys.exit(main())

"""Build the catalogue's external calculation inputs from the committed projects."""

import argparse
import json
import math
import re
import shlex
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]


def number(token):
    return float(token.split('(')[0])


def read_cif(path):
    """Read the scalar and loop records used by the example projects."""
    tokens = shlex.split(path.read_text(), comments=True)
    scalars, loops = {}, []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == 'loop_':  # noqa: S105 - CIF grammar, not a credential
            index += 1
            keys = []
            while index < len(tokens) and tokens[index].startswith('_'):
                keys.append(tokens[index])
                index += 1
            values = []
            while index < len(tokens) and not tokens[index].startswith(('_', 'data_', 'loop_')):
                values.append(tokens[index])
                index += 1
            if not keys or len(values) % len(keys):
                raise ValueError(f'Incomplete loop in {path}')
            loops.append([
                dict(zip(keys, values[i : i + len(keys)], strict=True))
                for i in range(0, len(values), len(keys))
            ])
        elif token.startswith('_'):
            scalars[token] = tokens[index + 1]
            index += 2
        else:
            index += 1
    return scalars, loops


def rows(loops, category):
    return next(
        (loop for loop in loops if loop and any(k.startswith(category + '.') for k in loop[0])), []
    )


class Codes:
    """Keep equal and complementary constraints on one FullProf parameter."""

    def __init__(self, analysis, fixed):
        self.fixed = fixed
        _, loops = read_cif(analysis)
        aliases = {
            r['_alias.id']: r['_alias.parameter_unique_name'] for r in rows(loops, '_alias')
        }
        self.ties = {}
        for row in rows(loops, '_constraint'):
            target, expression = (
                part.strip() for part in row['_constraint.expression'].split('=')
            )
            complement = re.fullmatch(r'1\s*-\s*(\w+)', expression)
            leader = complement[1] if complement else expression
            if target not in aliases or leader not in aliases:
                raise ValueError(f'Unsupported constraint: {row}')
            self.ties[aliases[target]] = (aliases[leader], -1 if complement else 1)
        self.assigned = {}
        self.free = {}

    def register(self, name, token):
        self.free[name] = '(' in token

    def code(self, name, multiplier=1):
        if self.fixed:
            return 0
        while name in self.ties:
            name, factor = self.ties[name]
            multiplier *= factor
        if not self.free.get(name, False):
            return 0
        if name not in self.assigned:
            self.assigned[name] = len(self.assigned) + 1
        return math.copysign(self.assigned[name] * 10 + abs(multiplier), multiplier)


def line(values):
    return ' '.join(f'{value:.10g}' for value in values)


def multiplicities(structure):
    """Use the independent cctbx table and the standard hexagonal special positions."""
    group = structure['_space_group.name_h_m'].replace(' ', '')
    setting = structure.get('_space_group.coord_system_code', '')
    key = group
    if group == 'Fd-3m':
        key += ':' + (setting or '2')
    elif group == 'R-3c':
        key += ':H'
    table = json.loads((ROOT / 'tests/fixtures/c34_t25_fullprof/wyckoff.json').read_text())[
        'groups'
    ]
    if key in table:
        row = table[key]
        return row['general'], {r['letter']: r['multiplicity'] for r in row['wyckoff']}
    return {
        'R-3m': (36, {'a': 3, 'b': 3, 'c': 6, 'e': 9, 'h': 18}),
        'Im-3m': (96, {'a': 2}),
        'C2221': (8, {'a': 4, 'b': 4, 'c': 8}),
        'P63mc': (12, {'a': 2, 'b': 2, 'c': 6}),
    }[group]


def load_case(case):
    project = ROOT / 'docs/user/cli' / case / 'project'
    structures = []
    for path in sorted((project / 'structures').glob('*.edi')):
        values, loops = read_cif(path)
        structures.append({'id': path.stem, 'values': values, 'loops': loops})
    experiments = []
    for path in sorted((project / 'experiments').glob('*.edi')):
        values, loops = read_cif(path)
        tof = values['_experiment_type.beam_mode'] == 'time-of-flight'
        axis = 'time_of_flight' if tof else 'two_theta'
        observed = rows(loops, '_data')
        if observed:
            data = np.array([
                [
                    number(r[f'_data.{axis}']),
                    number(r['_data.intensity_meas']),
                    number(r['_data.intensity_meas_su']),
                ]
                for r in observed
            ])
        else:
            low, high, step = [
                number(values[f'_data_range.{axis}_{key}']) for key in ['min', 'max', 'step']
            ]
            x = np.arange(round((high - low) / step) + 1) * step + low
            data = np.column_stack([x, np.ones(len(x)), np.ones(len(x))])
        limits = [float(data[0, 0]), float(np.median(np.diff(data[:, 0]))), float(data[-1, 0])]
        included = data[:, 2] > 0
        for region in rows(loops, '_excluded_region'):
            included &= (data[:, 0] < number(region['_excluded_region.start'])) | (
                data[:, 0] > number(region['_excluded_region.end'])
            )
        data = data[included]
        experiments.append({
            'id': path.stem,
            'values': values,
            'loops': loops,
            'tof': tof,
            'data': data,
            'limits': limits,
        })
    return project, structures, experiments


def register_parameters(codes, structures, experiments):  # noqa: PLR0912 - explicit model families
    parameters = {}
    for structure in structures:
        phase, values, loops = structure['id'], structure['values'], structure['loops']
        for key, token in values.items():
            if key.startswith('_cell.'):
                parameters[f'{phase}.{key[1:]}'] = token
        for atom in rows(loops, '_atom_site'):
            for field in ['fract_x', 'fract_y', 'fract_z', 'adp_iso', 'occupancy']:
                parameters[f'{phase}.atom_site.{atom["_atom_site.id"]}.{field}'] = atom[
                    f'_atom_site.{field}'
                ]
        for atom in rows(loops, '_atom_site_aniso'):
            for field in ['11', '22', '33', '12', '13', '23']:
                parameters[f'{phase}.atom_site.{atom["_atom_site_aniso.id"]}.adp_{field}'] = atom[
                    f'_atom_site_aniso.adp_{field}'
                ]
        group = values['_space_group.name_h_m'].replace(' ', '')
        if group in {'Pm-3m', 'Fm-3m', 'Fd-3m', 'Im-3m', 'Ia-3', 'I213'}:
            for field in ['length_b', 'length_c']:
                codes.ties[f'{phase}.cell.{field}'] = (f'{phase}.cell.length_a', 1)
        elif group.startswith(('R', 'P6')):
            codes.ties[f'{phase}.cell.length_b'] = (f'{phase}.cell.length_a', 1)
        for atom in rows(loops, '_atom_site'):
            base = f'{phase}.atom_site.{atom["_atom_site.id"]}'
            letter = atom['_atom_site.wyckoff_letter']
            if group == 'I213' and letter == 'a':
                for field in ['fract_y', 'fract_z']:
                    codes.ties[f'{base}.{field}'] = (f'{base}.fract_x', 1)
            if group == 'Ia-3' and letter == 'b':
                for field in ['22', '33']:
                    codes.ties[f'{base}.adp_{field}'] = (f'{base}.adp_11', 1)
                for field in ['13', '23']:
                    codes.ties[f'{base}.adp_{field}'] = (f'{base}.adp_12', 1)
    for experiment in experiments:
        bank, values, loops = experiment['id'], experiment['values'], experiment['loops']
        for key, token in values.items():
            if key.startswith(('_peak.', '_instrument.', '_absorption.')) and re.match(
                r'[-+\d.]', token
            ):
                parameters[f'{bank}.{key[1:]}'] = token
        for linked in rows(loops, '_linked_structure'):
            parameters[
                f'{bank}.linked_structure.{linked["_linked_structure.structure_id"]}.scale'
            ] = linked['_linked_structure.scale']
        for row in rows(loops, '_background'):
            field = 'coef' if '_background.coef' in row else 'intensity'
            parameters[f'{bank}.background.{row["_background.id"]}.{field}'] = row[
                f'_background.{field}'
            ]
    for name, token in parameters.items():
        codes.register(name, token)
    return parameters


class Writer:
    """Write the documented PCR records with their value/code pairs together."""

    def __init__(self, case, fixed, cycles=200):
        if cycles < 1:
            raise ValueError('The FullProf cycle budget must be positive')
        self.cycles = cycles
        self.project, self.structures, self.experiments = load_case(case)
        self.codes = Codes(self.project / 'analysis/analysis.edi', fixed)
        self.parameters = register_parameters(self.codes, self.structures, self.experiments)
        self.fixed = fixed
        self.out = []

    def put(self, *records):
        self.out.extend(records)

    def pair(self, name, factor=1):
        return number(self.parameters.get(name, '0')) * factor, self.codes.code(name, factor)

    def paired(self, names, extra=0):
        values, codes = zip(*(self.pair(name) for name in names), strict=True)
        self.put(line([*values, *([0] * extra)]), line(codes))

    @staticmethod
    def profile_number(experiment):
        return {
            'cwl-tch-pseudo-voigt': 7,
            'cwl-tch-pseudo-voigt-fcj': 7,
            'cwl-pseudo-voigt-berar-baldinozzi': 5,
            'tof-jorgensen': 9,
            'tof-jorgensen-von-dreele': 9,
            'tof-pseudo-voigt': 7,
        }[experiment['values']['_peak.type']]

    @staticmethod
    def background_number(experiment):
        kind = experiment['values'].get('_background.type', 'none')
        return {'chebyshev': -5, 'polynomial': 0, 'none': 0}.get(
            kind, len(rows(experiment['loops'], '_background'))
        )

    @staticmethod
    def limits(experiment):
        values, limits = experiment['values'], experiment['limits']
        return [
            number(values.get('_background.x_min', str(limits[0]))),
            limits[1],
            number(values.get('_background.x_max', str(limits[2]))),
        ]

    def header(self, destination):  # noqa: PLR0912, PLR0914, PLR0915 - PCR record order
        multi = len(self.experiments) > 1
        self.put('COMM ' + self.project.parent.name)
        if multi:
            n = len(self.experiments)
            self.put(
                f'NPATT {n} ' + ' '.join(['1'] * n),
                'W_PAT ' + ' '.join(['1'] * n),
                '!Nph Dum Ias Nre Cry Opt Aut',
                f'{len(self.structures)} 0 0 0 0 1 1',
                '!Job Npr Nba Nex Nsc Nor Iwg Ilo Res Ste Uni Cor Anm Int',
            )
        for index, exp in enumerate(self.experiments, 1):
            values = exp['values']
            tof = exp['tof']
            job = -1 if tof else int(values['_experiment_type.radiation_probe'] != 'xray')
            npr, nba, nex = self.profile_number(exp), self.background_number(exp), 0
            if multi:
                self.put(
                    line([job, npr, nba, nex, 0, 0, 0, 0, 0, 0, int(tof), 0, 0, 0])
                    + f' !-> Patt#: {index}'
                )
            else:
                self.put(
                    '!Job Npr Nph Nba Nex Nsc Nor Dum Iwg Ilo Ias Res Ste Nre Cry Uni Cor Opt Aut',
                    line([
                        job,
                        npr,
                        len(self.structures),
                        nba,
                        nex,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        int(tof),
                        0,
                        1,
                        1,
                    ]),
                )
        if multi:
            self.put('!File names of data(patterns) files')
            self.put(*(f'{destination.stem}_{i}.dat' for i in range(1, len(self.experiments) + 1)))
            self.put(
                '!Mat Pcr NLI Rpa Sym Sho',
                '0 2 0 1 1 1',
                '!Ipr Ppl Ioc Ls1 Ls2 Ls3 Prf Ins Hkl Fou Ana',
            )
            self.put(
                *(
                    f'2 2 1 0 4 0 2 10 0 0 1 !-> Patt#: {i}'
                    for i in range(1, len(self.experiments) + 1)
                )
            )
        else:
            self.put(
                '!Ipr Ppl Ioc Mat Pcr Ls1 Ls2 Ls3 NLI Prf Ins Rpa Sym Hkl Fou Sho Ana',
                '2 2 1 0 2 0 4 0 0 2 10 1 1 0 0 1 1',
            )
        for i, exp in enumerate(self.experiments, 1):
            v = exp['values']
            origin = number(v.get('_background.origin', str(np.mean(exp['data'][:, 0]))))
            width = max(48, number(v.get('_peak.cutoff_fwhm', '30')) * 2)
            if exp['tof']:
                self.put(f'! Bkpos Wdt Iabscor for Pattern# {i}', line([origin, width, 2]))
            else:
                lam = number(v['_instrument.setup_wavelength'])
                pol = number(v.get('_instrument.setup_polarization_coefficient', '0'))
                angle = number(v.get('_instrument.setup_monochromator_twotheta', '0'))
                if pol not in {0, 0.5}:
                    raise ValueError('Unsupported polarization mapping')
                cthm = math.cos(math.radians(angle)) ** 2 if pol else 0
                self.put(
                    '! Lambda1 Lambda2 Ratio Bkpos Wdt Cthm muR AsyLim Rpolarz '
                    f'2nd-muR for Pattern# {i}',
                    line([
                        lam,
                        number(v.get('_instrument.setup_wavelength_2', str(lam))),
                        number(v.get('_instrument.setup_wavelength_2_to_1_ratio', '0')),
                        origin,
                        width,
                        cthm,
                        number(v.get('_absorption.mu_r', '0')),
                        180,
                        0,
                        0,
                    ]),
                )
        cycles = [1 if self.fixed else self.cycles, 0.1, 0.2, 0.2, 0.2, 0.2]
        self.put('!NCY Eps R_at R_an R_pr R_gl')
        if multi:
            self.put(line(cycles))
            for i, exp in enumerate(self.experiments, 1):
                self.put(
                    f'! Range minimum step maximum for Pattern# {i}',
                    line(self.limits(exp) + ([] if exp['tof'] else [0, 0])),
                )
        else:
            self.put(
                line(
                    cycles
                    + self.limits(self.experiments[0])
                    + ([] if self.experiments[0]['tof'] else [0, 0])
                )
            )
        for i, exp in enumerate(self.experiments, 1):
            if self.background_number(exp) > 0:
                self.put(f'!2Theta/TOF/E(Kev) Background for Pattern# {i}')
                for row in rows(exp['loops'], '_background'):
                    self.put(
                        line([
                            number(row['_background.position']),
                            *self.pair(
                                f'{exp["id"]}.background.{row["_background.id"]}.intensity'
                            ),
                        ])
                    )
            self.put(f'! Excluded regions (LowT HighT) for Pattern# {i}')
            # Masked data omit exclusions while retaining background anchors and their codes.
        self.count_index = len(self.out)
        self.put('COUNT')
        for i, exp in enumerate(self.experiments, 1):
            bank = exp['id']
            if exp['tof']:
                names = [
                    'calib_d_to_tof_offset',
                    'calib_d_to_tof_linear',
                    'calib_d_to_tof_quadratic',
                    'calib_d_to_tof_reciprocal',
                ]
                self.put(
                    f'! Zero Code Dtt1 Code Dtt2 Code Dtt_1overd Code 2ThetaBank -> Patt# {i}',
                    line(
                        [x for name in names for x in self.pair(f'{bank}.instrument.{name}')]
                        + [number(exp['values']['_instrument.setup_twotheta_bank'])]
                    ),
                )
            else:
                names = [
                    'calib_twotheta_offset',
                    'calib_sample_displacement',
                    'calib_sample_transparency',
                ]
                self.put(
                    f'! Zero Code SyCos Code SySin Code Lambda Code MORE -> Patt# {i}',
                    line(
                        [x for name in names for x in self.pair(f'{bank}.instrument.{name}')]
                        + [0, 0, 0]
                    ),
                )
            if self.background_number(exp) <= 0:
                count = 24 if self.background_number(exp) == -5 else 6
                coefficients = {
                    int(row['_background.order']): row for row in rows(exp['loops'], '_background')
                }
                self.put(f'! Background coefficients/codes for Pattern# {i}')
                for block in range(0, count, 6):
                    names = [
                        f'{bank}.background.{coefficients[j]["_background.id"]}.coef'
                        if j in coefficients
                        else 'absent'
                        for j in range(block, block + 6)
                    ]
                    self.paired(names)

    def phase(self, structure, index):  # noqa: PLR0914 - PCR phase record order
        phase, values, loops = structure['id'], structure['values'], structure['loops']
        atoms = rows(loops, '_atom_site')
        general, sites = multiplicities(values)
        multi = len(self.experiments) > 1
        self.put(f'! Data for PHASE number: {index}', phase)
        if multi:
            self.put(
                '!Nat Dis Ang Jbt Isy Str Furth ATZ Nvk More',
                f'{len(atoms)} 0 0 0 0 0 0 0 0 0',
                '!Contributions (0/1) of this phase to the patterns',
                ' '.join(['1'] * len(self.experiments)),
            )
            for i, exp in enumerate(self.experiments, 1):
                job = (
                    -1
                    if exp['tof']
                    else int(exp['values']['_experiment_type.radiation_probe'] != 'xray')
                )
                self.put(
                    f'!Irf Npr Jtyp Nsp_Ref Ph_Shift for Pattern# {i}',
                    line([0, self.profile_number(exp), job, 0, 0]),
                    f'! Pr1 Pr2 Pr3 Brind Rmua Rmub Rmuc for Pattern# {i}',
                    '0 0 1 1 0 0 0',
                )
        else:
            self.put(
                '!Nat Dis Ang Pr1 Pr2 Pr3 Jbt Irf Isy Str Furth ATZ Nvk Npr More',
                f'{len(atoms)} 0 0 0 0 1 0 0 0 0 0 0 0 '
                f'{self.profile_number(self.experiments[0])} 0',
            )
        group = values['_space_group.name_h_m']
        # FullProf's standard Fd-3m origin is the centrosymmetric choice.
        shift = (
            0.125
            if group.replace(' ', '') == 'Fd-3m'
            and values.get('_space_group.coord_system_code') == '1'
            else 0
        )
        self.put(
            group + ' <--Space group symbol', '!Atom Typ X Y Z Biso Occ In Fin N_t Spc /Codes'
        )
        for atom in atoms:
            label = atom['_atom_site.id']
            base = f'{phase}.atom_site.{label}'
            names = [f'{base}.{key}' for key in ['fract_x', 'fract_y', 'fract_z', 'adp_iso']]
            nums, flags = zip(*(self.pair(name) for name in names), strict=True)
            beta = atom['_atom_site.adp_type'] == 'beta'
            nums = [nums[0] + shift, nums[1] + shift, nums[2] + shift, 0 if beta else nums[3]]
            fraction = sites[atom['_atom_site.wyckoff_letter']] / general
            occ, occ_code = self.pair(f'{base}.occupancy', factor=fraction)
            symbol = {'2H': 'D'}.get(
                atom['_atom_site.type_symbol'], atom['_atom_site.type_symbol']
            ).upper()
            self.put(
                f'{label} {symbol} {line([*nums, occ])} 0 0 {2 if beta else 0} 0',
                line([*flags[:3], 0 if beta else flags[3], occ_code]),
            )
            if beta:
                self.paired([f'{base}.adp_{key}' for key in ['11', '22', '33', '12', '13', '23']])
        for i, exp in enumerate(self.experiments, 1):
            self.profile(exp, phase, i)

    def profile(self, exp, phase, index):  # noqa: PLR0914 - PCR profile record order
        bank, v = exp['id'], exp['values']
        tof = exp['tof']
        npr = self.profile_number(exp)
        self.put(
            f'! Profile Parameters for Pattern # {index} Phase {phase}',
            '! Scale Shape1 Bov Str1 Str2 Str3 Strain-Model',
        )
        factor = 0.5 if number(v.get('_instrument.setup_polarization_coefficient', '0')) else 1
        scale, scale_code = self.pair(f'{bank}.linked_structure.{phase}.scale', factor=factor)
        mixing, mixing_code = self.pair(f'{bank}.peak.mixing_eta_0') if npr == 5 else (0, 0)
        self.put(line([scale, mixing, 0, 0, 0, 0, 0]), line([scale_code, mixing_code, 0, 0, 0, 0]))
        if tof:
            self.put(
                '! Sigma-2 Sigma-1 Sigma-0 Sigma-Q Iso-GStrain Iso-GSize Ani-LSize Size-Model'
            )
            names = [f'{bank}.peak.broad_gauss_sigma_{j}' for j in [2, 1, 0]] + ['absent'] * 4
            self.paired(names, extra=1)
            self.put('! Gamma-2 Gamma-1 Gamma-0 Iso-LorStrain Iso-LorSize')
            self.paired(
                [f'{bank}.peak.broad_lorentz_gamma_{j}' for j in [2, 1, 0]] + ['absent'] * 2
            )
        else:
            self.put('! U V W X Y GauSiz LorSiz Size-Model')
            names = [
                f'{bank}.peak.{name}'
                for name in [
                    'broad_gauss_u',
                    'broad_gauss_v',
                    'broad_gauss_w',
                    'broad_lorentz_x',
                    'broad_lorentz_y',
                ]
            ] + ['absent'] * 2
            self.paired(names, extra=1)
        self.put('! a b c alpha beta gamma')
        self.paired([
            f'{phase}.cell.{name}'
            for name in [
                'length_a',
                'length_b',
                'length_c',
                'angle_alpha',
                'angle_beta',
                'angle_gamma',
            ]
        ])
        if tof:
            self.put('! Pref1 Pref2 alph0 beta0 alph1 beta1 alphQ betaQ')
            self.paired(
                ['absent'] * 2
                + [
                    f'{bank}.peak.{name}'
                    for name in ['rise_alpha_0', 'decay_beta_0', 'rise_alpha_1', 'decay_beta_1']
                ]
                + ['absent'] * 2
            )
            self.put(
                '!Absorption correction parameters',
                line([
                    *self.pair(f'{bank}.absorption.abscor1'),
                    *self.pair(f'{bank}.absorption.abscor2'),
                ])
                + ' ABS: ABSCOR1 ABSCOR2',
            )
        else:
            asym = [0, 0, 0, 0]
            acodes = [0, 0, 0, 0]
            if npr == 5:
                for j in [0, 1]:
                    a, ca = self.pair(f'{bank}.peak.asym_beba_a{j}')
                    b, cb = self.pair(f'{bank}.peak.asym_beba_b{j}')
                    asym[2 * j : 2 * j + 2] = [-a + 3 * b, -b]
                    acodes[2 * j : 2 * j + 2] = [ca or cb, cb]
            fcj = [self.pair(f'{bank}.peak.{name}') for name in ['asym_fcj_1', 'asym_fcj_2']]
            self.put(
                '! Pref1 Pref2 Asy1 Asy2 Asy3 Asy4 S_L D_L',
                line([0, 0, *asym] + ([] if npr == 5 else [fcj[0][0], fcj[1][0]])),
                line([0, 0, *acodes] + ([] if npr == 5 else [fcj[0][1], fcj[1][1]])),
            )

    def write(self, destination):
        self.header(destination)
        for index, structure in enumerate(self.structures, 1):
            self.phase(structure, index)
        for index, exp in enumerate(self.experiments, 1):
            self.put(
                '! 2Th1/TOF1 2Th2/TOF2 Pattern to plot',
                line([exp['data'][0, 0], exp['data'][-1, 0], index]),
            )
        self.out[self.count_index] = f'{len(self.codes.assigned)} !Number of refined parameters'
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text('\n'.join(self.out) + '\n')
        for i, exp in enumerate(self.experiments, 1):
            name = (
                destination.with_suffix('.dat')
                if len(self.experiments) == 1
                else destination.with_name(f'{destination.stem}_{i}.dat')
            )
            # Ins=10 skips six header records before the x/y/sigma triples.
            np.savetxt(
                name,
                exp['data'],
                header='\n'.join(['2theta-or-TOF intensity sigma'] * 6),
                fmt='%.12g',
            )
        return len(self.codes.assigned)


def cw_input(case, destination, *, fixed=False):
    return Writer(case, fixed).write(destination)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case')
    parser.add_argument('output', type=Path)
    parser.add_argument('--fixed', action='store_true')
    options = parser.parse_args()
    print(cw_input(options.case, options.output, fixed=options.fixed))

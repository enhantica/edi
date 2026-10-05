""": independent layout, cctbx multiplicity and FullProf evidence gates.

Old input numbers in baseline.json are historical pins, NOT correctness oracles.
Correctness comes from the packet, cctbx operations, and independent FullProf runs.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
FIX = ROOT / 'tests/fixtures/c34_t25_fullprof'
BASE = json.loads((FIX / 'baseline.json').read_text())
ORACLE = json.loads((FIX / 'wyckoff.json').read_text())['groups']
FITTING = {
    'pd-neut-tof_cecoal-polaris_chebyshev',
    'pd-neut-tof_ceo2-pearl_polynomial',
    'pd-neut-tof_si-sepd_ikeda-carpenter',
    'pd-neut-cwl_lab6-11b-echidna_tch-fcj',
    'pd-neut-cwl_yap-spodi_3k',
}
PROJECTS = [
    (home, name)
    for home in ('verification', 'fitting')
    for name in sorted(BASE)
    if home == 'verification' or name in FITTING
]
FLOAT = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?'


def numbers(line):
    return [float(n.replace('D', 'E')) for n in re.findall(FLOAT, line)]


def next_data(lines, index):
    return next(
        i
        for i in range(index + 1, len(lines))
        if lines[i].strip() and not lines[i].lstrip().startswith('!')
    )


# Keep the positional grammar in FullProf record order for auditability.
def parameter_records(text):  # noqa: PLR0912, PLR0914, PLR0915
    """Read PCR records positionally, never trusting comments to identify codes.

    FullProf manual pp. 13, 68-69, 86-90, 108-110 (distributed PDF):
    codeword = sign(multiplier) * (10*index + abs(multiplier)).
    This corpus uses single-pattern nuclear Jbt=0, isotropic atoms, CW 5/7 and
    TOF 9/13. Other option families FAIL CLOSED instead of silently skipping
    their extra records. Every consumed value/code pair enters the same map.
    """
    rows = [re.split(r'[!#]|<--|<-', line, maxsplit=1)[0].split() for line in text.splitlines()]
    rows = [row for row in rows if row]
    cursor = 1  # title
    params, codes = {}, {}

    def take(count=None):
        nonlocal cursor
        assert cursor < len(rows), ' PCR record inventory must not end early'
        row = rows[cursor]
        cursor += 1
        assert count is None or len(row) in count, ' PCR record shape must be supported'
        return row

    def numeric(count):
        row = take(count)
        assert all(re.fullmatch(FLOAT, token) for token in row), (
            ' PCR numerical records cannot hide unparsed fields'
        )
        values = [float(token.replace('D', 'E')) for token in row]
        assert all(np.isfinite(values)), ' PCR values and codes must be finite'
        return values

    def flags(names):
        return dict(zip(names.split(), numeric({len(names.split())}), strict=True))

    def fixed(key, values):
        params[key] = values

    def pairs(key, values, code):
        assert len(values) == len(code), ' each parameter must have its code inventoried'
        fixed(key, values)
        codes[key] = code

    def paired(key, size, *, tail=False):
        values = numeric({size + int(tail)})
        if tail:
            assert values[-1] == 0, ' unsupported size/strain models must fail closed'
        pairs(key, values[:size], numeric({size}))

    multi = rows[cursor][0] == 'NPATT'
    if multi:
        assert take() == ['NPATT', '1', '1'], ' only one active pattern is supported'
        assert take() == ['W_PAT', '1.000'], ' pattern weighting must be declared'
        global_flags = flags('Nph Dum Ias Nre Cry Opt Aut')
        job = flags('Job Npr Nba Nex Nsc Nor Iwg Ilo Res Ste Uni Cor Anm Int')
        take({1})  # measured data filename
        output = flags('Mat Pcr NLI Rpa Sym Sho')
        output.update(flags('Ipr Ppl Ioc Ls1 Ls2 Ls3 Prf Ins Hkl Fou Ana'))
    else:
        job = flags('Job Npr Nph Nba Nex Nsc Nor Dum Iwg Ilo Ias Res Ste Nre Cry Uni Cor Opt Aut')
        global_flags = job
        output = flags('Ipr Ppl Ioc Mat Pcr Ls1 Ls2 Ls3 NLI Prf Ins Rpa Sym Hkl Fou Sho Ana')
    assert all(global_flags[k] == 0 for k in ('Nre', 'Cry')), (
        ' unsupported constraints or single crystal modes must fail closed'
    )
    assert all(job[k] == 0 for k in ('Res', 'Cor', 'Ste')), (
        ' unsupported satellite/shift/correction records must fail closed'
    )
    assert job['Uni'] in {0, 1} and job['Npr'] in {5, 7, 9, 13}, (
        ' unsupported diffraction/profile modes must fail closed'
    )
    tof = job['Uni'] == 1
    instrument = numeric({3} if tof else {9, 10})
    assert tof or instrument[2] >= 0, ' separate wavelength-two profile families must fail closed'
    fixed('instrument', instrument)
    cycles = numeric({6} if multi else ({9} if tof else {11}))
    fixed('range', numeric({3}) if multi else cycles[6:])
    nba = int(job['Nba'])
    assert nba >= 0 or nba in {-4, -5}, ' unsupported background modes must fail closed'
    for i in range(max(0, nba)):
        point = numeric({3})
        fixed(f'background-x:{i}', point[:1])
        pairs(f'background:{i}', point[1:2], point[2:])
    for i in range(int(job['Nex'])):
        fixed(f'excluded:{i}', numeric({2}))
    for _ in range(int(job['Nsc'])):
        scatter = take({4})
        assert float(scatter[3]) == 0, ' tabulated scattering extensions must fail closed'
        fixed(f'scattering:{scatter[0]}', list(map(float, scatter[1:3])))
    npar = numeric({1})[0]
    assert npar >= 0 and npar == int(npar), ' variable count must be a nonnegative integer'
    calibration = numeric({9})
    pairs('calibration', calibration[:8:2], calibration[1:8:2])
    if tof:
        fixed('bank-angle', calibration[8:])
    else:
        assert calibration[8] == 0, ' extra calibration families must fail closed'
    for i in range({0: 1, -4: 3, -5: 4}.get(nba, 0)):
        paired(f'background-polynomial:{i}', 6)
    for phase in range(1, int(global_flags['Nph']) + 1):
        take()  # phase title
        if multi:
            ph = flags('Nat Dis Ang Jbt Isy Str Furth ATZ Nvk More')
            assert numeric({1}) == [1], ' each phase must contribute to the pattern'
            ph.update(flags('Irf Npr Jtyp Nsp_Ref Ph_Shift'))
            fixed(f'orientation:{phase}', numeric({7}))
        else:
            ph = flags('Nat Dis Ang Pr1 Pr2 Pr3 Jbt Irf Isy Str Furth ATZ Nvk Npr More')
            fixed(f'orientation:{phase}', [ph[k] for k in ('Pr1', 'Pr2', 'Pr3')])
        assert all(
            ph[k] == 0 for k in ('Dis', 'Ang', 'Jbt', 'Isy', 'Str', 'Furth', 'Nvk', 'Irf')
        ), ' unsupported structural/code families must fail closed'
        assert ph['More'] in {0, 1}, ' phase extension selector must be supported'
        if ph['More']:
            more = flags(
                'Jvi Jdi Hel Sol Mom Ter Brind RMua RMub RMuc Jtyp Nsp_Ref Ph_Shift N_Domains'
            )
            assert all(
                more[k] == 0
                for k in ('Jvi', 'Hel', 'Sol', 'Mom', 'Ter', 'Nsp_Ref', 'Ph_Shift', 'N_Domains')
            ), ' extended phase code families must fail closed'
            assert more['Jdi'] in {0, 3}, ' unsupported distance modes must fail closed'
            if more['Jdi'] == 3:
                take({3})  # bond-valence display options, not fitted parameters
                counts = numeric({3})
                if counts[0]:
                    take({int(counts[0])})
                if counts[1]:
                    take({int(counts[1])})
        group = take()
        assert group and not re.fullmatch(FLOAT, group[0]), ' phase must expose its space group'
        for _ in range(int(ph['Nat'])):
            row = take({11})
            assert list(map(float, row[7:10])) == [0, 0, 0], (
                ' unsupported magnetic/anisotropic atom records must fail closed'
            )
            pairs(f'atom:{phase}:{row[0]}', list(map(float, row[2:7])), numeric({5}))
        paired(f'scale-shape-strain:{phase}', 6, tail=True)
        paired(f'profile:{phase}', 7, tail=True)
        if tof:
            paired(f'lorentzian:{phase}', 5)
        paired(f'cell:{phase}', 6)
        size = 6 if ph['Npr'] == 5 else 8
        paired(f'orientation-asymmetry:{phase}', size)
        if tof:
            # FullProf appends ABS: labels to the four numerical entries.
            row = take()
            assert row[4:] == ['ABS:', 'ABSCOR1', 'ABSCOR2'], (
                ' absorption record must expose exactly both parameters and codes'
            )
            vals = list(map(float, row[:4]))
            pairs(f'absorption:{phase}', vals[::2], vals[1::2])
    numeric({2, 3})  # plotting interval; never a fitted parameter
    assert cursor == len(rows), ' every PCR data record must be consumed; unknown families refuse'
    return {'values': params, 'codes': codes, 'npar': npar, **output}


def check_code_inventory(records):
    active = [abs(code) for row in records['codes'].values() for code in row if code]
    indices = {int(code // 10) for code in active}
    assert all(code >= 10 and code % 10 != 0 for code in active), (
        ' active FullProf codes must carry a variable index and nonzero multiplier'
    )
    assert indices == set(range(1, int(records['npar']) + 1)), (
        ' declared variable count must equal the complete active code inventory'
    )
    return indices


def parse_pcr(text):
    lines = text.splitlines()
    result = {'atoms': [], 'scales': [], 'scale_codes': [], 'atom_codes': []}
    phase = 0
    for i, line in enumerate(lines):
        if line.startswith('!Ipr'):
            keys = line.lstrip('!').split()
            vals = numbers(lines[next_data(lines, i)])
            result.update(dict(zip(keys, vals[: len(keys)], strict=True)))
        if 'Number of refined parameters' in line:
            result['npar'] = int(line.split()[0])
        if '<--Space group symbol' in line:
            phase += 1
            group = line.split('<--')[0].replace(' ', '')
            # FullProf accepts these historical cubic abbreviations and origin 1.
            group = {'Fm3m': 'Fm-3m', 'Fd3m': 'Fd-3m:2', 'Fd-3m': 'Fd-3m:2', 'R-3c': 'R-3c:H'}.get(
                group, group
            )
        if re.match(r'!\s*Atom\s+Typ', line):
            j = next_data(lines, i)
            while j < len(lines):
                row = lines[j].split()
                if not row or not re.match(r'^[A-Za-z][A-Za-z0-9+-]*$', row[0]):
                    break
                result['atoms'].append({
                    'phase': phase,
                    'label': row[0],
                    'group': group,
                    'xyz': list(map(float, row[2:5])),
                    'occ': float(row[6]),
                })
                code = next_data(lines, j)
                result['atom_codes'].extend(numbers(lines[code])[:5])
                j = code + 1
                if j >= len(lines) or lines[j].lstrip().startswith('!'):
                    break
        if re.match(r'!\s*Scale\s+', line):
            j = next_data(lines, i)
            result['scales'].append(numbers(lines[j])[0])
            result['scale_codes'].append(numbers(lines[next_data(lines, j)])[0])
    assert result['atoms'] and result['scales'], ' must parse every phase and scale'
    assert phase == len(result['scales']), ' every phase must have its scale parsed'
    result['records'] = parameter_records(text)
    return result


def project(home, name):
    directory = ROOT / f'knowledge/{home}/fullprof' / name
    assert directory.is_dir(), ' every required project must exist in its declared home'
    files = list(directory.rglob('*.pcr'))
    assert len(files) == 1, ' each project folder must contain exactly one PCR'
    return directory, files[0], parse_pcr(files[0].read_text())


def check_layout(directory, home, allowed):
    assert directory.name in allowed, ' ids must use exactly the packet instrument mapping'
    files = list(directory.rglob('*.pcr'))
    assert len(files) == 1, ' each project folder must contain exactly one PCR'
    p = parse_pcr(files[0].read_text())
    records = parameter_records(files[0].read_text())
    active = check_code_inventory(records)
    if home == 'verification':
        assert p['npar'] == 0, ' verification projects must fix every parameter'
        assert not active, ' zero declared variables cannot hide any active code family'
        assert p['Prf'] == 2, ' verification must emit the existing IGOR extraction format'
        assert files[0].with_suffix('.prf').read_text().startswith('IGOR'), (
            ' extraction output must exist and actually use IGOR'
        )
    else:
        assert records['Pcr'] == 2, ' fitting projects must save the fitted PCR as NEW'
        assert p['npar'] > 0 and active, (
            ' fitting projects must have an active parameter, not just claim a count'
        )


def evidence(directory):
    path = directory / 'PROVENANCE.md'
    assert path.is_file(), ' every project must carry its provenance'
    blocks = re.findall(r'```json\s*\n(.*?)\n```', path.read_text(), re.DOTALL)
    rows = [json.loads(b) for b in blocks]
    rows = [r for r in rows if isinstance(r, dict) and r.get('schema') == 'fullprof-evidence-1']
    assert len(rows) == 1, (
        ' provenance must expose one fullprof-evidence-1 numerical evidence record'
    )
    return rows[0]


def multiplicity(atom):
    group = ORACLE[atom['group']]
    xyz = np.array(atom['xyz'])
    images = []
    for operation in group['operations']:
        image = (np.array(operation['r']).reshape(3, 3) @ xyz + operation['t']) % 1
        if not any(np.max(np.abs((image - old + 0.5) % 1 - 0.5)) < 2e-5 for old in images):
            images.append(image)
    mult = len(images)
    assert mult in {p['multiplicity'] for p in group['wyckoff']}, (
        ' site orbit must be a cctbx Wyckoff multiplicity'
    )
    return mult, group['general']


def check_occupancies(pcr, sites):
    keys = {f'{a["phase"]}:{a["label"]}' for a in pcr['atoms']}
    assert set(sites) == keys, ' provenance must state site occupancy for every site'
    for atom in pcr['atoms']:
        mult, general = multiplicity(atom)
        occupancy = sites[f'{atom["phase"]}:{atom["label"]}']
        assert np.isfinite(occupancy) and occupancy > 0, (
            ' site occupancy must be finite and positive'
        )
        assert atom['occ'] == pytest.approx(occupancy * mult / general, abs=5.1e-6), (
            ' Occ must equal site occupancy times cctbx site/general multiplicity'
        )


def initial_atoms(out):
    atoms = []
    for block in out.split('=> Initial parameters ==>')[1:]:
        for line in block.split('=>')[0].splitlines():
            row = line.split()
            if len(row) >= 11 and re.fullmatch(r'[A-Za-z][A-Za-z0-9+-]*', row[0]):
                try:
                    atoms.append((row[0], float(row[6])))
                except ValueError:
                    continue
    return atoms


def fitted_scales(out):
    return [
        float(v)
        for v in re.findall(r'Parameter number\s+\d+\s*:\s*Scale_\S+\s+(' + FLOAT + ')', out)
    ]


def requires_refit(home, name):
    # New verification twins always owe a scale fit, including the k=1 LaB6
    # twin. The exemption is decided from frozen INPUTS, never missing fit_out
    # or the current project's claimed occupancy factor.
    if home == 'verification' and name in FITTING:
        return True
    for atom in BASE[name]['atoms']:
        site = 1.0
        if 'lbco' in name:
            site = {'La': 0.5, 'Ba': 0.5, 'O': 0.97856}.get(atom['label'], site)
        if 'cecoal' in name and atom['label'] == 'Al3':
            site = 1.020655
        mult, general = multiplicity(atom)
        if abs(atom['occ'] - site * mult / general) > 5.1e-6:
            return True
    return False


def check_unchanged_inputs(directory, pcr_path, name):
    # Historical byte pins are regression constraints under the committed
    # k=1 decision, not a scientific correctness oracle. Output is deliberately
    # absent here: PRF/SUM bytes are checked against authoring provenance.
    pins = json.loads((FIX / 'unchanged-inputs.json').read_text())['projects'][name]
    assert hashlib.sha256(pcr_path.read_bytes()).hexdigest() == pins['pcr_sha256'], (
        ' exempt k=1 PCR input must remain byte-identical to its source'
    )
    actual = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in directory.iterdir()
        if path.suffix.lower() in {'.dat', '.gss', '.irf', '.hkl', '.int'}
    }
    # Layout may rename a data alias (Y2O3); bytes and multiplicity are fixed.
    # The authoring provenance separately binds every input and output hash.
    assert sorted(actual.values()) == sorted(pins['auxiliary_sha256'].values()), (
        ' exempt k=1 data and auxiliary inputs must remain byte-identical to source'
    )
    assert parse_pcr(pcr_path.read_text())['atoms'] == BASE[name]['atoms'], (
        ' exempt k=1 projects must preserve every source site and occupancy'
    )


@pytest.mark.parametrize(
    ('home', 'name', 'required'),
    [
        ('verification', 'pd-neut-cwl_lbco-hrpt_basic', False),
        ('fitting', 'pd-neut-cwl_lab6-11b-echidna_tch-fcj', False),
        ('verification', 'pd-neut-cwl_lab6-11b-echidna_tch-fcj', True),
        ('verification', 'pd-neut-tof_diamond-dream_basic', True),
        ('fitting', 'pd-neut-cwl_yap-spodi_3k', True),
    ],
)
def test_refit_boundary_uses_source_occupancy_and_retains_twins(home, name, required):
    assert requires_refit(home, name) is required, (
        ' k=1 source projects alone are exempt; changed phases and new twins still fit'
    )


@pytest.mark.parametrize('escape', ['none', 'pcr', 'data', 'irf', 'missing-data', 'extra-data'])
def test_k_one_exemption_rejects_changed_input_bytes(tmp_path, escape):
    name = 'pd-neut-tof_ncaf-wish_jorgensen-von-dreele'
    source, original, _ = project('verification', name)
    directory = tmp_path / name
    shutil.copytree(source, directory)
    pcr = directory / original.name
    data = next(directory.glob('*.gss'))
    if escape == 'pcr':
        pcr.write_bytes(pcr.read_bytes() + b'\n')
    elif escape == 'data':
        data.write_bytes(data.read_bytes() + b'\n')
    elif escape == 'irf':
        irf = next(directory.glob('*.irf'))
        irf.write_bytes(irf.read_bytes() + b'\n')
    elif escape == 'missing-data':
        data.unlink()
    elif escape == 'extra-data':
        (directory / 'replacement.dat').write_text('changed input\n')
    if escape == 'none':
        check_unchanged_inputs(directory, pcr, name)
    else:
        with pytest.raises(AssertionError, match='byte-identical'):
            check_unchanged_inputs(directory, pcr, name)


@pytest.mark.parametrize(('home', 'name'), PROJECTS)
def test_layout(home, name):
    directory, _, _ = project(home, name)
    check_layout(directory, home, BASE if home == 'verification' else FITTING)


def test_no_unaccounted_project_homes_or_invented_instruments():
    added_verification_projects = {
        'pd-neut-cwl_lab6-echidna_fcj-asymmetry',
        'pd-neut-cwl_pbso4_beba-asymmetry',
        'pd-neut-tof_fe_pseudo-voigt',
        'pd-xray-cwl_lif_single',
        'pd-xray-cwl_lif_single-polarization',
        'pd-neut-cwl_lbco-hrpt_preferred-orientation',
        'pd-neut-cwl_cosio-d20_biso-tied',
    }
    for home, names in [
        ('verification', set(BASE) | added_verification_projects),
        ('fitting', FITTING | {'pd-neut-cwl_cosio-d20_biso-tied'}),
    ]:
        root = ROOT / f'knowledge/{home}/fullprof'
        assert root.is_dir(), ' both FullProf homes must exist'
        assert {p.name for p in root.iterdir() if p.is_dir()} == names, (
            ' inventory must equal the source corpus, YAP,  shapes, '
            ' LiF,  polarization,  LBCO texture and fitting twins'
        )
    for pcr in (ROOT / 'knowledge').rglob('*.pcr'):
        assert pcr.parts[-4:-2] in {('verification', 'fullprof'), ('fitting', 'fullprof')}, (
            ' no FullProf project may remain outside the two homes'
        )


@pytest.mark.parametrize(('home', 'name'), PROJECTS)
def test_every_site_uses_independent_cctbx_multiplicity(home, name):
    directory, _, pcr = project(home, name)
    data = evidence(directory)
    check_occupancies(pcr, data['site_occupancies'])
    for atom in pcr['atoms']:
        key = f'{atom["phase"]}:{atom["label"]}'
        # The named structures are fully occupied except these declared source sites.
        if 'lbco' in name and atom['label'] in {'La', 'Ba', 'O'}:
            expected = {'La': 0.5, 'Ba': 0.5, 'O': 0.97856}[atom['label']]
            assert (
                data['site_occupancies'][key],
                data['start_site_occupancies'][key],
            ) == pytest.approx((expected, expected), abs=3e-4), (
                ' mixed La/Ba and oxygen vacancies must retain source composition'
            )
        elif 'cecoal' in name and atom['label'] == 'Al3':
            assert data['start_site_occupancies'][key] == pytest.approx(1.020655, abs=2e-5), (
                ' Al3 starts relative to the full multiplicity-two source sites'
            )
        else:
            assert data['site_occupancies'][key] == data['start_site_occupancies'][key] == 1, (
                ' a fully occupied source site cannot invent vacancy to hide a wrong Occ'
            )
    if 'cecoal' in name:
        assert data.get('al3_explanation'), ' Al3 overoccupation requires structural explanation'


def fit_record(directory, filename, pcr, data, home):
    out_path = (directory / filename).resolve()
    assert out_path.is_relative_to(directory.resolve()) and out_path.suffix == '.out', (
        ' fit evidence must be a local FullProf OUT'
    )
    out = out_path.read_text()
    assert 'Convergence reached at this CYCLE' in out, ' every post-conversion fit must converge'
    snapshots = data.get('fit_inputs', {})
    assert filename in snapshots, ' every fit OUT must name its exact saved input'
    input_path = (directory / snapshots[filename]).resolve()
    assert input_path.is_relative_to(directory.resolve()) and input_path.suffix == '.inp', (
        ' saved post-conversion fit input must be a local INP snapshot'
    )
    start = parse_pcr(input_path.read_text())
    assert start['records']['Pcr'] == 2, ' saved fit input must write its final NEW result'
    assert check_code_inventory(start['records']), ' saved input must actually fit parameters'
    assert [(a['phase'], a['label']) for a in start['atoms']] == [
        (a['phase'], a['label']) for a in pcr['atoms']
    ], ' saved input and committed result must describe the same sites'
    check_occupancies(start, data['start_site_occupancies'])
    atoms = initial_atoms(out)
    assert len(atoms) == len(start['atoms']), ' OUT must expose all phases initial atoms'
    for (label, occ), atom in zip(atoms, start['atoms'], strict=True):
        assert label == atom['label'] and occ == pytest.approx(atom['occ'], abs=5.1e-6), (
            ' OUT initial sites must match the saved post-conversion input'
        )
    initial = re.findall(r'Symbolic Name:\s*(\S+)\s+(' + FLOAT + ')', out)
    assert initial, ' OUT must prove parameters were varied'
    if home == 'verification':
        assert len(initial) == 1 and initial[0][0].startswith('Scale_'), (
            ' verification evidence must be a one-parameter scale fit'
        )
    scales = re.findall(r'Parameter number\s+\d+\s*:\s*Scale_ph(\d+)_pat1\s+(' + FLOAT + ')', out)
    assert scales, ' OUT must expose each fitted phase scale'
    return {int(phase): float(value) for phase, value in scales}


@pytest.mark.parametrize(('home', 'name'), PROJECTS)
def test_post_conversion_fit_is_real_and_scale_is_bound(home, name):
    directory, path, pcr = project(home, name)
    data = evidence(directory)
    assert pcr['scales'] == pytest.approx(data['new_scales'], rel=1e-6), (
        ' provenance new scales must equal committed PCR scales'
    )
    assert data['old_scales'] == BASE[name]['scales'], (
        ' old scales must match the frozen pre-change inputs'
    )
    check_scale_conservation(pcr, BASE[name], data)
    if not requires_refit(home, name):
        check_unchanged_inputs(directory, path, name)
        return
    assert data.get('fit_out'), ' changed projects and twins must retain fit evidence'
    names = data['fit_out']
    if isinstance(names, str):
        names = [names]
    scales_by_phase = {}
    for filename in names:
        result = fit_record(directory, filename, pcr, data, home)
        assert not (result.keys() & scales_by_phase.keys()), (
            ' every phase scale must have one unambiguous fit result'
        )
        scales_by_phase.update(result)
    assert set(scales_by_phase) == set(range(1, len(pcr['scales']) + 1)), (
        ' scale evidence must cover every phase including both YAP phases'
    )
    scales = [scales_by_phase[i] for i in sorted(scales_by_phase)]
    assert pcr['scales'] == pytest.approx(scales, rel=1e-5), (
        ' fixed or fitted PCR scales must equal the actual scale fit result'
    )


def check_scale_conservation(pcr, baseline, data):
    # NEW serializes Occ as F-style five decimal places (independent fp2k 8.40).
    # Intersect the rounding intervals of ALL sites rather than selecting the
    # first site's rounded factor (CeO2's two rounded factors straddle 1/24).
    # The physical 1e-4 bound is unchanged; only input quantization propagates.
    intervals = [
        ((a['occ'] - 0.000005) / old['occ'], (a['occ'] + 0.000005) / old['occ'])
        for a, old in zip(pcr['atoms'], baseline['atoms'], strict=True)
    ]
    lower, upper = max(a for a, _ in intervals), min(b for _, b in intervals)
    if lower <= upper:
        new, old = np.array(pcr['scales']), np.array(data['old_scales'])
        assert np.all(new * lower**2 <= old * (1 + 1e-4)) and np.all(
            new * upper**2 >= old * (1 - 1e-4)
        ), ' a uniform Occ factor must conserve scale times k squared'
    else:
        assert data.get('nonuniform_change'), (
            ' nonuniform occupancy changes require the fit change report'
        )


@pytest.mark.parametrize('scale_error', [0, 0.001, 0.5])
def test_scale_rounding_allowance_does_not_hide_changed_scale(scale_error):
    # Closed form: fully occupied 4a/8c of Fm-3m, versus old Occ 1/2 and 1.
    baseline = {'atoms': [{'occ': 0.5}, {'occ': 1.0}]}
    pcr = {
        'atoms': [{'occ': 0.02083}, {'occ': 0.04167}],
        'scales': [576 * (1 + scale_error)],
    }
    data = {'old_scales': [1]}
    if scale_error:
        with pytest.raises(AssertionError, match='must conserve scale'):
            check_scale_conservation(pcr, baseline, data)
    else:
        check_scale_conservation(pcr, baseline, data)


def test_cctbx_oracle_nontrivial_sites_and_partial_occupancy_escape():
    atom = {'phase': 1, 'label': 'La', 'group': 'Pm-3m', 'xyz': [0, 0, 0], 'occ': 0.0104166667}
    assert multiplicity(atom) == (1, 48), ' cctbx La site must have multiplicity 1 of 48'
    check_occupancies({'atoms': [atom]}, {'1:La': 0.5})
    with pytest.raises(AssertionError, match='Occ must equal'):
        check_occupancies({'atoms': [dict(atom, occ=0.5)]}, {'1:La': 0.5})


@pytest.mark.parametrize(
    'escape',
    [
        'second-pcr',
        'verification-free',
        'fitting-fixed',
        'invented-instrument',
        'no-extraction',
        'background-free',
        'profile-free',
        'cell-free',
        'calibration-free',
        'atom-free',
    ],
)
def test_layout_escape_is_reached(tmp_path, escape):
    name = 'pd-neut-cwl_pbso4_basic'
    folder = tmp_path / (
        name if escape != 'invented-instrument' else 'pd-neut-cwl_pbso4-guessed_basic'
    )
    folder.mkdir()
    text = BASE[name]['pcr']
    (folder / 'case.prf').write_text('IGOR\n')
    if escape == 'verification-free':
        text = text.replace(
            '0    !Number of refined parameters', '1    !Number of refined parameters'
        )
    if escape.endswith('-free') and escape != 'verification-free':
        lines = text.splitlines()
        markers = {
            'background-free': '!2Theta',
            'profile-free': '!       U',
            'cell-free': '!     a',
            'calibration-free': '!  Zero',
            'atom-free': '!Atom',
        }
        i = next(i for i, line in enumerate(lines) if line.startswith(markers[escape]))
        j = next_data(lines, i)
        col = {'background-free': 2, 'calibration-free': 1}.get(escape, 0)
        if escape not in {'background-free', 'calibration-free'}:
            j = next_data(lines, j)
        row = lines[j].split()
        row[col] = '11.00'
        lines[j] = ' '.join(row)
        text = '\n'.join(lines)  # npar deliberately remains ZERO
    if escape == 'no-extraction':
        (folder / 'case.prf').write_text('not extraction\n')
    (folder / 'case.pcr').write_text(text)
    if escape == 'second-pcr':
        (folder / 'extra.pcr').write_text(text)
    home = 'fitting' if escape == 'fitting-fixed' else 'verification'
    if home == 'fitting':
        # Lie about the count as well as fixing every actual code.
        text = text.replace(
            '0    !Number of refined parameters', '1    !Number of refined parameters'
        )
        lines = text.splitlines()
        i = next(i for i, line in enumerate(lines) if line.startswith('!Ipr'))
        j = next_data(lines, i)
        values = lines[j].split()
        values[lines[i].lstrip('!').split().index('Pcr')] = '2'
        lines[j] = ' '.join(values)
        (folder / 'case.pcr').write_text('\n'.join(lines))
    diagnostic = (
        'complete active code inventory'
        if escape.endswith('-free')
        else {
            'second-pcr': 'exactly one PCR',
            'fitting-fixed': 'complete active code inventory',
            'invented-instrument': 'instrument mapping',
            'no-extraction': 'IGOR',
        }[escape]
    )
    with pytest.raises(AssertionError, match=diagnostic):
        check_layout(folder, home, {name})


@pytest.mark.parametrize('name', sorted(BASE))
def test_occupancy_convention_on_materialized_source_even_before_move(name):
    target = ROOT / 'knowledge/verification/fullprof' / name
    files = list(target.glob('*.pcr'))
    if not files:
        old = ROOT / BASE[name]['source']
        assert old.is_file(), ' must materialize every source project including YAP'
        files = [old]
    pcr = parse_pcr(files[0].read_text())
    for atom in pcr['atoms']:
        if ('lbco' in name and atom['label'] in {'La', 'Ba', 'O'}) or (
            'cecoal' in name and atom['label'] == 'Al3'
        ):
            continue  # These have explicit source-composition/evidence checks above.
        mult, general = multiplicity(atom)
        assert atom['occ'] == pytest.approx(mult / general, abs=5.1e-6), (
            ' full source sites need the independent cctbx multiplicity ratio'
        )


@pytest.mark.parametrize('name', sorted(BASE))
def test_complete_code_inventory_covers_original_fullprof_records(name):
    # Historical files are grammar fixtures, not correctness values.
    records = parameter_records(BASE[name]['pcr'])
    active = check_code_inventory(records)
    assert len(active) == records['npar'], ' source grammar controls must enumerate every variable'


def test_unknown_code_family_cannot_be_silently_ignored(tmp_path):
    folder = tmp_path / 'pd-neut-cwl_pbso4_basic'
    folder.mkdir()
    text = BASE[folder.name]['pcr'] + '\n1.2 11.0\n'
    (folder / 'case.pcr').write_text(text)
    (folder / 'case.prf').write_text('IGOR\n')
    with pytest.raises(AssertionError, match='every PCR data record'):
        check_layout(folder, 'verification', {folder.name})

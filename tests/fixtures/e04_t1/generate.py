"""Freeze  expectations from committed .edi text, never category APIs.

Run from the repository root with Python. The field declarations are transcribed
from diffraction-lib 0ffba46f peak/{cwl,tof}.py and *_mixins.py, instrument/{cwl,tof}.py,
plus accepted packet §2b divergences D-a..D-j. Fixture scalars/loops supply values.
No import of edi, and no screenshot is generated here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shlex
import shutil
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CW = ['broad_gauss_u', 'broad_gauss_v', 'broad_gauss_w', 'broad_lorentz_x', 'broad_lorentz_y']
GAUSS = [
    'broad_gauss_sigma_0',
    'broad_gauss_sigma_1',
    'broad_gauss_sigma_2',
    'broad_gauss_size',
    'broad_gauss_strain',
]
LORENTZ = [
    'broad_lorentz_gamma_0',
    'broad_lorentz_gamma_1',
    'broad_lorentz_gamma_2',
    'broad_lorentz_size',
    'broad_lorentz_strain',
]
B2B = ['rise_alpha_0', 'rise_alpha_1', 'decay_beta_0', 'decay_beta_1']
FCJ = ['asym_fcj_1', 'asym_fcj_2']
BEBA = ['asym_beba_a0', 'asym_beba_b0', 'asym_beba_a1', 'asym_beba_b1', 'asym_beba_limit']
PROFILES = {
    # FullProf Npr 0 and 1 share the Caglioti width, with eta fixed to 0 and 1.
    'cwl-gaussian': CW[:3],
    'cwl-lorentzian': CW[:3],
    # FullProf Npr 5: Caglioti U/V/W and eta0 + eta1 * two-theta.
    'cwl-pseudo-voigt': CW[:3] + ['mixing_eta_0', 'mixing_eta_1'],
    'cwl-tch-pseudo-voigt': CW,
    'cwl-tch-pseudo-voigt-fcj': CW + FCJ,
    'cwl-pseudo-voigt-berar-baldinozzi': CW[:3] + ['mixing_eta_0', 'mixing_eta_1'] + BEBA,
    'tof-jorgensen': B2B + GAUSS,
    'tof-jorgensen-von-dreele': B2B + GAUSS + LORENTZ,
    'tof-pseudo-voigt': GAUSS + LORENTZ,
}
INSTRUMENT = {
    # FullProf La11B6 corpus: SyCos/SySin are the declared displacement/
    # transparency fields (the case's PROVENANCE.md maps the original PCR).
    'cwl': [
        'setup_wavelength',
        'calib_twotheta_offset',
        'calib_sample_displacement',
        'calib_sample_transparency',
    ],
    'tof': [
        'setup_twotheta_bank',
        'calib_d_to_tof_offset',
        'calib_d_to_tof_linear',
        'calib_d_to_tof_quadratic',
        'calib_d_to_tof_reciprocal',
    ],
}


def numeric(token):
    number = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'
    match = re.fullmatch(rf'({number})(?:\((\d*|{number})\))?', token)
    if match is None:
        return token
    raw, digits = match.groups()
    value = float(raw)
    exponent = int(raw.lower().split('e')[1]) if 'e' in raw.lower() else 0
    fraction = raw.lower().split('e')[0].partition('.')[2]
    uncertainty = (
        None
        if digits is not None and not digits
        else (
            (int(digits) * 10 ** (exponent - len(fraction)) if digits.isdigit() else float(digits))
            if digits
            else 0.0
        )
    )
    return {'value': value, 'free': digits is not None, 'uncertainty': uncertainty}


def scalars(path):
    result = {}
    for line in path.read_text().splitlines():
        if line.startswith('_'):
            tokens = shlex.split(line, comments=True)
            if len(tokens) == 2:
                result[tokens[0]] = numeric(tokens[1])
    return result


def tables(path, extra=()):
    wanted = {
        '_atom_site',
        '_background',
        '_excluded_region',
        '_preferred_orientation',
        '_linked_structure',
    }
    wanted.update(extra)
    # The owner's ASCII records contain CR as an in-row field separator.
    # LF ends a record; universal-newline decoding would invent another row.
    lines = path.read_bytes().decode().split('\n')
    result = {}
    index = 0
    while index < len(lines):
        if lines[index].strip() != 'loop_':
            index += 1
            continue
        index += 1
        headers = []
        while index < len(lines) and lines[index].startswith('_'):
            headers.append(lines[index].strip())
            index += 1
        category = headers[0].split('.')[0] if headers else ''
        values = []
        while (
            index < len(lines)
            and lines[index].strip()
            and not lines[index].startswith(('_', 'loop_'))
        ):
            row = shlex.split(lines[index], comments=True)
            if len(row) != len(headers):
                raise ValueError(f'fixture loop shape is ambiguous: {path}:{index + 1}')
            if category in wanted:
                values.append({
                    key.split('.')[1]: numeric(value)
                    for key, value in zip(headers, row, strict=True)
                })
            index += 1
        if category in wanted:
            result[category.removeprefix('_')] = values
    return result


def measured_range(path):
    data = tables(path, ('_data',)).get('data', [])
    if not data:
        return []
    axis = 'two_theta' if 'two_theta' in data[0] else 'time_of_flight'
    values = [row[axis]['value'] for row in data]
    return [values[0], values[-1], (values[-1] - values[0]) / (len(values) - 1), len(values)]


def scan_inputs(project, analysis):
    """Independent file catalogue and measured-range witnesses; never import the app."""
    if analysis.get('_fitting_mode.type') not in {'sequential', 'independent'}:
        return []
    directory = project / analysis['_sequential_fit.data_dir']
    files = sorted(directory.glob(analysis['_sequential_fit.file_pattern']))
    if analysis.get('_sequential_fit.reverse') == 'true':
        files.reverse()
    datasets = []
    selected = {0, len(files) // 2, len(files) - 1}
    for file_index, file in enumerate(files):
        rows = []
        for line in file.read_bytes().decode().split('\n'):
            fields = line.split()
            if len(fields) not in {2, 3}:
                continue
            try:
                row = [float(field) for field in fields]
            except ValueError:
                continue
            # The owner rule skips negative scan points. The scan reference
            # in scan_template/REFERENCE.md uses Poisson sqrt(y), with tiny
            # sigma replaced below; the single-pattern importer differs.
            if row[1] < 0:
                continue
            if len(row) == 2:
                row.append(math.sqrt(row[1]))
            rows.append(row)
        if len(rows) < 2:
            raise ValueError('Scan range witness requires independent measured ASCII rows')
        axis = [row[0] for row in rows]
        dataset = {
            'file': file.name,
            'sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
            'range': [axis[0], axis[-1], (axis[-1] - axis[0]) / (len(axis) - 1), len(axis)],
        }
        if file_index in selected:
            # Independent ASCII convention: diffraction-lib bragg_pd.py,
            # as cited in scan_template/REFERENCE.md; never an app-generated value.
            dataset['samples'] = [
                {
                    'index': index,
                    'values': [
                        round(rows[index][0], 4),
                        rows[index][1],
                        1.0 if rows[index][2] < 0.0001 else rows[index][2],
                    ],
                }
                for index in sorted({0, len(rows) // 2, len(rows) - 1})
            ]
        datasets.append(dataset)
    return datasets


def profile_fixtures():
    # Keep every FullProf profile category covered without mislabeling a scan.
    projects = []
    for kind, profile in (
        ('eta', 'cwl-pseudo-voigt'),
        ('gaussian', 'cwl-gaussian'),
        ('lorentzian', 'cwl-lorentzian'),
    ):
        project = ROOT / 'tests/fixtures/e04_t1' / (kind + '-project')
        shutil.copytree(project.with_name('xray-project'), project, dirs_exist_ok=True)
        (project / 'project.edi').write_text(
            f'_edi.schema_version 3\n_metadata.name "{kind.title()} profile category witness"\n'
        )
        experiment = project / 'experiments/experiment.edi'
        text = experiment.read_text().replace('cwl-tch-pseudo-voigt', profile)
        text = (
            '\n'.join(
                line
                for line in text.splitlines()
                if not line.startswith(('_peak.broad_lorentz_x ', '_peak.broad_lorentz_y '))
            )
            + '\n'
        )
        # Nontrivial X-ray polarization input is transcribed from the saved LiF example.
        text += (
            '_instrument.setup_polarization_coefficient 0.4\n'
            '_instrument.setup_monochromator_twotheta 20\n'
        )
        if kind == 'eta':
            text += '_peak.mixing_eta_0 0.37\n_peak.mixing_eta_1 0.0023\n'
        experiment.write_text(text)
        projects.append(project)
    return projects


def generate(warning_project=None, added_project=None):  # noqa: PLR0914 - one capture retains old witnesses
    projects = []
    registry = yaml.safe_load((ROOT / 'docs/user/cli/projects.yml').read_text())['projects']
    selected = [
        entry for entry in registry if added_project is None or entry['id'] == added_project
    ]
    if added_project is not None and len(selected) != 1:
        raise ValueError('Project addition requires exactly one registered project')
    for entry in selected:
        project = ROOT / 'docs/user/cli' / entry['id'] / 'project'
        structures = [
            {
                'name': file.stem,
                'atoms': len(tables(file)['atom_site']),
                'cellA': scalars(file)['_cell.length_a']['value'],
                'spaceGroup': scalars(file)['_space_group.name_h_m'],
                'cell': [
                    scalars(file)['_cell.' + field]['value']
                    for field in (
                        'length_a',
                        'length_b',
                        'length_c',
                        'angle_alpha',
                        'angle_beta',
                        'angle_gamma',
                    )
                ],
            }
            for file in sorted((project / 'structures').glob('*.edi'))
        ]
        files = sorted(project.glob('*.edi'))
        files += sorted((project / 'structures').glob('*.edi'))
        files += sorted((project / 'experiments').glob('*.edi'))
        files += sorted((project / 'analysis').glob('*.edi'))
        analysis = project / 'analysis/analysis.edi'
        projects.append({
            'id': entry['id'],
            'path': str(project.relative_to(ROOT)),
            'metadata': scalars(project / 'project.edi'),
            'analysis': scalars(analysis) if analysis.exists() else {},
            'structures': structures,
            'experiments': [p.stem for p in sorted((project / 'experiments').glob('*.edi'))],
            'datasets': scan_inputs(project, scalars(analysis) if analysis.exists() else {}),
            'loaderWarning': loader_warning(
                scalars(analysis) if analysis.exists() else {},
                [scalars(file) for file in sorted((project / 'experiments').glob('*.edi'))],
                scalars(project / 'project.edi'),
                entry['id'],
            ),
            'files': {
                str(p.relative_to(project)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in files
            },
        })
    corpus = []
    corpus_projects = (
        [ROOT / 'docs/user/cli' / added_project / 'project']
        if added_project is not None
        else [*sorted((ROOT / 'docs/user/cli').glob('*/project')), *profile_fixtures()]
    )
    for project in corpus_projects:
        for file in sorted((project / 'experiments').glob('*.edi')):
            fields = scalars(file)
            profile = fields['_peak.type']
            mode = 'cwl' if profile.startswith('cwl-') else 'tof'
            expected = list(PROFILES[profile])
            # Unmodified CrySPY b37f9f3 powder_diffraction_tof.py calc_sigma/
            # calc_sigma_gamma defaults the optional size and strain terms to zero.
            for name in (
                'broad_gauss_size',
                'broad_gauss_strain',
                'broad_lorentz_size',
                'broad_lorentz_strain',
            ):
                if name in expected:
                    fields.setdefault(
                        '_peak.' + name, {'value': 0.0, 'free': False, 'uncertainty': None}
                    )
            unused = [
                name
                for name in CW + B2B + GAUSS + LORENTZ + FCJ + BEBA
                if name not in expected
                and isinstance(fields.get('_peak.' + name), dict)
                and fields['_peak.' + name]['free']
            ]
            corpus.append({
                'project': str(project.relative_to(ROOT)),
                'experiment': file.stem,
                'sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
                'peakType': profile,
                'mode': mode,
                'peakFields': expected,
                'unusedFreeFields': unused,
                # Absent optional mixing / extra broadening is fixed neutral zero;
                # this is a declared input rule, not a calculated engine value.
                'peakDefaults': {
                    name: {'value': 0.0, 'free': False}
                    for name in (
                        'mixing_eta_0',
                        'mixing_eta_1',
                        'broad_gauss_size',
                        'broad_gauss_strain',
                        'broad_lorentz_size',
                        'broad_lorentz_strain',
                    )
                    if name in expected and '_peak.' + name not in fields
                },
                # FullProf shift and polarization fields are optional; include each
                # explicitly saved field once alongside the base instrument fields.
                'instrumentFields': [
                    name
                    for name in INSTRUMENT[mode]
                    if name not in {'calib_sample_displacement', 'calib_sample_transparency'}
                ]
                + [
                    name
                    for name in (
                        'calib_sample_displacement',
                        'calib_sample_transparency',
                        'setup_polarization_coefficient',
                        'setup_monochromator_twotheta',
                    )
                    if '_instrument.' + name in fields
                ],
                'range': measured_range(file),
                'scalars': fields,
                'loops': tables(file)
                if project.parent.name
                in {
                    'pd-neut-cwl_lbco-hrpt_start-2',
                    'pd-neut-tof_si-sepd_start-2',
                    'pd-neut-cwl_cosio-d20_start-1',
                }
                else {},
            })
    examples = [
        {
            'id': 'pd-neut-cwl_lbco-hrpt_start-2',
            'structure': 'lbco',
            'experiment': 'hrpt',
            'rows': 42,
            'free': 17,
            'atoms': 4,
            'background': 5,
            'excluded': 2,
            'texture': 1,
            'spaceGroup': 'P m -3 m',
            'code': '1',
            'system': 'cubic',
            'range': [10.0, 164.85, 0.05, 3098],
        },
        {
            'id': 'pd-neut-tof_si-sepd_start-2',
            'structure': 'si',
            'experiment': 'sepd',
            'rows': 45,
            'free': 23,
            'atoms': 1,
            'background': 14,
            'excluded': 0,
            'spaceGroup': 'F d -3 m',
            'code': '2',
            'system': 'cubic',
            'range': [2000.0, 29995.0, 5.0, 5600],
        },
        {
            'id': 'pd-neut-cwl_cosio-d20_start-1',
            'structure': 'cosio',
            'experiment': 'd20',
            'rows': 58,
            'free': 43,
            'atoms': 6,
            'background': 14,
            'excluded': 0,
            'texture': 0,
            'spaceGroup': 'P n m a',
            'code': 'abc',
            'system': 'orthorhombic',
            'range': [8.0953, 150.0953, 0.10021171489061398, 1418],
        },
    ]
    for example in examples:
        project = ROOT / 'docs/user/cli' / example['id'] / 'project'
        file = project / 'structures' / (example['structure'] + '.edi')
        example['structureScalars'] = scalars(file)
        example['structureLoops'] = tables(file)
        example['projectScalars'] = scalars(project / 'project.edi')
    data = {
        'source': ('diffraction-lib 0ffba46f declarations +  §2b D-a..D-j + CLI files'),
        'profiles': PROFILES,
        'instrument': INSTRUMENT,
        'examples': examples,
        'projects': projects,
        'corpus': corpus,
    }
    output = Path(__file__).parent / 'oracle.js'
    if warning_project is not None:
        data = warning_only_oracle(output, projects, warning_project)
    if added_project is not None:
        retained = json.loads(output.read_text().split('var frozen = ', 1)[1].rsplit(';', 1)[0])
        if any(row['id'] == added_project for row in retained['projects']):
            # Re-run an uncommitted addition from its committed prior fixture;
            # never refresh a previously committed project's expectations.
            prior = subprocess.check_output(
                ['git', '-C', str(ROOT), 'show', 'HEAD:' + output.relative_to(ROOT).as_posix()],
                text=True,
            )
            retained = json.loads(prior.split('var frozen = ', 1)[1].rsplit(';', 1)[0])
            if any(row['id'] == added_project for row in retained['projects']):
                raise ValueError('Project addition cannot replace a committed oracle row')
        by_id = {row['id']: row for row in [*retained['projects'], *projects]}
        if set(by_id) != {entry['id'] for entry in registry}:
            raise ValueError('Project addition cannot omit or introduce another registry identity')
        retained['projects'] = [by_id[entry['id']] for entry in registry]
        retained['corpus'].extend(corpus)
        data = retained
    output.write_text(
        '// Independent category oracle. Regenerate only with generate.py.\nvar frozen = '
        + json.dumps(data, indent=2, ensure_ascii=False)
        + ';\n'
    )


def warning_only_oracle(output, projects, project_id):
    retained = json.loads(output.read_text().split('var frozen = ', 1)[1].rsplit(';', 1)[0])
    previous = [row for row in retained['projects'] if row['id'] == project_id]
    current = [row for row in projects if row['id'] == project_id]
    if len(previous) != 1 or len(current) != 1:
        raise ValueError('Warning-only generation requires one existing project id')
    if previous[0]['files'] != current[0]['files']:
        raise ValueError('Warning-only generation requires unchanged selected project inputs')
    previous[0]['loaderWarning'] = current[0]['loaderWarning']
    return retained


def loader_warning(analysis, experiments, metadata, project_id=None):
    #  idea 26: independent file declarations determine calculator and
    # minimizer warning bodies. Never ask the loader to generate its own oracle.
    warnings = []
    if project_id == 'pd-neut-cwl_yap-spodi_3k':
        # The retained FullProf yap_3k.pcr Al1 Biso is negative. Preserve the
        # saved value and require its exact diagnostic, only for this example.
        path = ROOT / 'docs/user/cli' / project_id / 'project/structures/Al2O3.edi'
        al1 = next(row for row in tables(path)['atom_site'] if row['id'] == 'Al1')
        if al1['adp_iso']['value'] != -0.13591 or al1['adp_type'] != 'Biso':
            raise ValueError('YAP warning witness must retain the FullProf Al1 Biso')
        warnings.append(
            'Warning: structures[Al2O3].atom_sites[Al1].adp_iso = -0.13591 '
            'is outside its admissible range [0, 10]; loaded as saved '
            '(a fit may leave a value there)'
        )
    seen = set()
    for experiment in experiments:
        calculator = experiment.get('_calculator.type', 'crysta')
        if calculator != 'crysta' and calculator not in seen:
            warnings.append(f'Warning: unsupported _calculator.type "{calculator}" - using crysta')
            seen.add(calculator)
    minimizer = analysis.get('_minimizer.type', 'crysta')
    if minimizer != 'crysta':
        warnings.append(f'Warning: unsupported _minimizer.type "{minimizer}" - using crysta')
    # Idea 26's third unsupported-but-loadable declaration lives in project.edi.
    renderer = metadata.get('_rendering_plot.type', 'auto')
    if renderer not in {'auto', '?', ''}:
        warnings.append(f'Warning: unsupported _rendering_plot.type "{renderer}" - using auto')
    return '\n'.join(warnings)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--loader-warning-only', metavar='PROJECT_ID')
    parser.add_argument('--add-project', metavar='PROJECT_ID')
    args = parser.parse_args()
    if args.loader_warning_only and args.add_project:
        parser.error('warning adaptation and project addition are separate operations')
    generate(args.loader_warning_only, args.add_project)

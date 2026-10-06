"""Freeze  expectations from committed .edi text, never category APIs.

Run from the repository root with Python. The field declarations are transcribed
from diffraction-lib 0ffba46f peak/{cwl,tof}.py and *_mixins.py, instrument/{cwl,tof}.py,
plus accepted packet §2b divergences D-a..D-j. Fixture scalars/loops supply values.
No import of edi, and no screenshot is generated here.
"""

from __future__ import annotations

import hashlib
import json
import re
import shlex
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
    'cwl-pseudo-voigt': CW,
    'cwl-thompson-cox-hastings': CW + FCJ,
    'cwl-pseudo-voigt-berar-baldinozzi-asymmetry': CW + BEBA,
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
    lines = path.read_text().splitlines()
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


def generate():
    projects = []
    for entry in yaml.safe_load((ROOT / 'docs/user/cli/projects.yml').read_text())['projects']:
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
            'loaderWarning': loader_warning(
                scalars(analysis) if analysis.exists() else {},
                [scalars(file) for file in sorted((project / 'experiments').glob('*.edi'))],
                scalars(project / 'project.edi'),
            ),
            'files': {
                str(p.relative_to(project)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in files
            },
        })
    corpus = []
    for project in sorted((ROOT / 'docs/user/cli').glob('*/project')):
        for file in sorted((project / 'experiments').glob('*.edi')):
            fields = scalars(file)
            profile = fields['_peak.type']
            mode = 'cwl' if profile.startswith('cwl-') else 'tof'
            expected = list(PROFILES[profile])
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
                #  extends the prior input oracle: keep the two CW
                # fields, then the independently declared polarization pair.
                'instrumentFields': INSTRUMENT[mode]
                + [
                    name
                    for name in ('setup_polarization_coefficient', 'setup_monochromator_twotheta')
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
    output.write_text(
        '// Independent category oracle. Regenerate only with generate.py.\nvar frozen = '
        + json.dumps(data, indent=2, ensure_ascii=False)
        + ';\n'
    )


def loader_warning(analysis, experiments, metadata):
    #  idea 26: independent file declarations determine calculator and
    # minimizer warning bodies. Never ask the loader to generate its own oracle.
    warnings = []
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
    generate()

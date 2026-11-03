"""Author measured-data FullProf fits beside the fixed verification references."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

from generate_fullprof import CASES, reflections

HERE = Path(__file__).resolve().parent
REVISION = 'cb2cda7be6117199be8f8cac0a666a7bccd32d90'
IDS = {
    'sc-neut-cwl_pr2nio4_basic': 'sc-neut-cwl_pr2nio4-5c2_basic',
    'sc-neut-cwl_tbti_basic': 'sc-neut-cwl_tb2ti2o7-heidi_basic',
    'sc-neut-cwl_tbti_anisotropic-adp': 'sc-neut-cwl_tb2ti2o7-heidi_anisotropic-adp',
    'sc-neut-cwl_tbti_isotropic-extinction': 'sc-neut-cwl_tb2ti2o7-heidi_isotropic-extinction',
    'sc-neut-tof_taurine_basic': 'sc-neut-tof_taurine-unknown_basic',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fitting_input(text, extinction):
    lines = text.splitlines()
    for index, line in enumerate(tuple(lines)):
        if line.startswith('!Ipr '):
            fields = lines[index + 1].split()
            fields[3:5] = ['1', '2']
            lines[index + 1] = ' '.join(fields)
        elif line.startswith('!NCY '):
            fields = lines[index + 1].split()
            fields[:6] = ['50', '0.001', '1.0', '1.0', '1.0', '1.0']
            lines[index + 1] = ' '.join(fields)
        elif 'Number of ' in line and 'parameters' in line:
            lines[index] = str(2 if extinction else 1) + ' ' + line[line.index('!') :]
        elif line.startswith('!   Sc1'):
            lines[index + 2] = '11 0 0 0 0 0'
        elif line.startswith('!   Ext1') and extinction:
            lines[index + 2] = '21 0 0 0 0 0 0'
    return '\n'.join(lines) + '\n'


def extract(work, stem, extinction):
    output = (work / f'{stem}.out').read_text()
    fitted = re.findall(
        r'Parameter number\s+\d+\s+:\s+(\w+)\s+([\d.E+-]+)\s*'
        r'\(\s*\+/-\s*([\d.E+-]+)\s*\)',
        output,
    )
    names = {'Scale1': 'scale', 'Ext1': 'fullprof_ext1'}
    parameters = [
        {'name': names[name], 'value': float(value), 'su': float(su)} for name, value, su in fitted
    ]
    if len(parameters) != (2 if extinction else 1):
        message = 'The final FullProf parameter list must match the declared free set'
        raise ValueError(message)
    chi = re.search(
        r'Chi2 \(Bragg contrib\.\) =\s*([\d.E+-]+)', (work / f'{stem}.new').read_text()
    )
    rows = reflections(output)
    return {
        'parameters': parameters,
        'chi2_reported': float(chi[1]),
        'correlations_percent': [int(value) for value in re.findall(r'->\s+(-?\d+)%', output)],
        'calculated_rows': rows,
        'n_selected': sum(not row['excluded_from_fit'] for row in rows),
        'converged': 'Convergence reached' in output,
        'banner': next(line.strip() for line in output.splitlines() if 'Version' in line),
    }


def stage_project(case, record, destination):
    project = destination / 'project'
    shutil.copytree(HERE / 'projects' / case, project, dirs_exist_ok=True)
    experiment = project / 'experiments/experiment.edi'
    text = experiment.read_text()
    text = re.sub(r'(?m)^structure (\S+)$', r'structure \1()', text)
    if 'extinction' in case:
        text = text.replace('_extinction.domain_radius 10\n', '_extinction.domain_radius 10()\n')
    header, rows = text.split('_refln.intensity_meas_su\n')
    if 'tof' in case:
        wavelength, rows = rows.split('\n', 1)
        header += '_refln.intensity_meas_su\n' + wavelength + '\n'
    else:
        header += '_refln.intensity_meas_su\n'
    values = rows.splitlines()
    if len(values) != len(record['calculated_rows']):
        msg = 'The fit project must preserve the FullProf observation selection'
        raise ValueError(msg)
    selected = [
        row
        for row, ref in zip(values, record['calculated_rows'], strict=True)
        if not ref['excluded_from_fit']
    ]
    residual_sum = 0.0
    for row, ref in zip(values, record['calculated_rows'], strict=True):
        fields = row.split()
        if list(map(int, fields[:3])) != ref['hkl']:
            message = 'FullProf output and input observation indices must stay aligned'
            raise ValueError(message)
        if not ref['excluded_from_fit']:
            residual_sum += ((float(fields[3]) - ref['f2_calc']) / float(fields[4])) ** 2
    record['residual_sum_from_printed_f2'] = residual_sum
    record['reduced_chi_square'] = residual_sum / (len(selected) - len(record['parameters']))
    experiment.write_text(header + '\n'.join(selected) + '\n')
    analysis = project / 'analysis/analysis.edi'
    analysis.parent.mkdir(exist_ok=True)
    analysis.write_text(
        '_edi.schema_version 3\n_fitting_mode.type single\n'
        '_minimizer.max_iterations 100\n_minimizer.chi_square_tolerance 1e-10\n'
    )
    scale = record['parameters'][0]
    quantities = {
        'n_free': {'value': len(record['parameters']), 'kind': 'reference', 'tol_abs': 0},
        'n_points_fitted': {'value': record['n_selected'], 'kind': 'reference', 'tol_abs': 0},
        'param.scale.value': {
            'value': scale['value'],
            'kind': 'reference',
            'tol_abs': scale['su'] + 0.0000005,
        },
        'reduced_chi_square': {
            'value': record['reduced_chi_square'],
            'kind': 'reference',
            'tol_abs': 0.06,
            'tol_rel': 0.002,
        },
    }
    (destination / 'expected.json').write_text(
        json.dumps(
            {
                'schema': 1,
                'source': {
                    'engine': 'FullProf 8.40',
                    'artifact': f'{stem_for(case)}.out',
                    'provenance': '../../README.md',
                },
                'comparable_parameters': record['comparable_parameters'],
                'quantities': quantities,
            },
            indent=2,
        )
        + '\n'
    )


def stem_for(case):
    return CASES[case]


def page_contract(upstream):
    records = {}
    for case in CASES:
        page = case.replace('pr2nio4', 'Pr2NiO4').replace('tbti', 'Tb2Ti2O7')
        path = f'docs/docs/verification/{page}.py'
        source = subprocess.check_output([
            shutil.which('git') or '/usr/bin/git',
            '-C',
            str(upstream),
            'show',
            f'{REVISION}:{path}',
        ])
        tree = ast.parse(source)
        assignments = [
            {'line': node.lineno, 'assignment': ast.unparse(node)}
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Attribute) and t.attr == 'free' for t in node.targets)
        ]
        records[case] = {
            'path': path,
            'sha256': hashlib.sha256(source).hexdigest(),
            'free_assignments': assignments,
            'observations': 'Synthetic FullProf F2 via verify.set_reference_reflections',
        }
    (HERE / 'fitting/page-contract.json').write_text(
        json.dumps({'revision': REVISION, 'pages': records}, indent=2) + '\n'
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fp2k', type=Path, required=True)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--upstream', type=Path, required=True)
    parser.add_argument('--reuse-output', action='store_true')
    args = parser.parse_args()
    manifest = {
        'upstream_revision': REVISION,
        'fp2k_sha256': digest(args.fp2k),
        'cases': {},
    }
    for case, stem in CASES.items():
        extinction = 'extinction' in case
        source = HERE / 'fullprof' / case
        dest = HERE / 'fitting/fullprof' / IDS[case]
        dest.mkdir(parents=True, exist_ok=True)
        work = args.run_dir / IDS[case]
        work.mkdir(parents=True, exist_ok=True)
        pcr = fitting_input((source / f'{stem}.pcr').read_text(), extinction)
        if not args.reuse_output:
            if (work / f'{stem}.out').exists():
                msg = 'An existing FullProf output must be reused, never rerun implicitly'
                raise ValueError(msg)
            (work / f'{stem}.pcr').write_text(pcr)
            shutil.copyfile(source / f'{stem}.int', work / f'{stem}.int')
            print(f'FullProf start {case}', flush=True)
            with (work / 'run.log').open('w') as log:
                run = subprocess.run(
                    [str(args.fp2k.resolve())],
                    input=f'{stem}\n\nn\n',
                    text=True,
                    cwd=work,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=25,
                    check=False,
                )
            (work / 'run.exit').write_text(str(run.returncode) + '\n')
        record = extract(work, stem, extinction)
        if (work / 'run.exit').read_text().strip() != '0' or not record['converged']:
            msg = f'FullProf fit must complete and converge: {case}'
            raise ValueError(msg)
        if any(p['su'] <= 0 for p in record['parameters']):
            msg = f'FullProf must report positive parameter uncertainties: {case}'
            raise ValueError(msg)
        (dest / f'{stem}.pcr').write_text(pcr)
        for ext in ('int', 'new', 'out', 'sum'):
            shutil.copyfile(work / f'{stem}.{ext}', dest / f'{stem}.{ext}')
        record.update({
            'project_id': IDS[case],
            'stem': stem,
            'source_pcr_sha256': digest(source / f'{stem}.pcr'),
            'source_int_sha256': digest(source / f'{stem}.int'),
            'start_scale': float(pcr.split('!   Sc1')[1].splitlines()[1].split()[0]),
            'page_free': ['scale', 'radius'] if extinction else ['scale'],
            'comparable_parameters': not extinction,
            'extinction_note': (
                'FullProf model 1 Ext1 is empirical, not Becker-Coppens radius. '
                'This fit is a diagnostic; radius and its uncertainty have no FullProf mapping.'
                if extinction
                else None
            ),
            'artifacts': {
                f'{stem}.{ext}': digest(dest / f'{stem}.{ext}')
                for ext in ('pcr', 'int', 'new', 'out', 'sum')
            },
        })
        stage_project(case, record, dest)
        manifest['cases'][case] = record
        print(
            f'FullProf complete {case}: {record["parameters"]}, chi2={record["chi2_reported"]}',
            flush=True,
        )
    (HERE / 'fitting/fullprof.json').write_text(json.dumps(manifest, indent=2) + '\n')
    page_contract(args.upstream)


if __name__ == '__main__':
    main()

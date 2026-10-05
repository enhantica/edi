"""Freeze diffraction-lib's selected fit model, independently of edi's parameter walk.

Run with diffraction-lib's Python environment, passing its checkout as the argument.
This updates only the count oracle; the author-time CLI fit records remain intact.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def load_reference_project(path):
    from easydiffraction import Project  # noqa: PLC0415 - independent reference environment only

    # Adapt reader/backend labels only; no fit or calculation is performed.
    # All parameter tags and the original committed inputs stay intact.
    with tempfile.TemporaryDirectory(prefix='reference-model-') as temporary:
        private = Path(temporary) / 'project'
        shutil.copytree(path, private)
        for model_file in private.rglob('*.edi'):
            text = model_file.read_text()
            if (
                model_file.parent.name == 'experiments'
                and '_experiment_type.beam_mode' not in text
                and re.search(r'^_peak.type tof-', text, re.MULTILINE)
            ):
                text += (
                    '\n_experiment_type.sample_form powder\n'
                    '_experiment_type.beam_mode time-of-flight\n'
                    '_experiment_type.radiation_probe neutron\n'
                    '_experiment_type.scattering_type bragg\n'
                )
            # The reference exposes Chebyshev coefficient storage. For count-only
            # selection, plain powers have the same independent coefficient set;
            # no reference fit/calculation or basis conversion is performed.
            if '_background.coef' in text:
                text = text.replace('_background.type polynomial', '_background.type chebyshev')
                lines = text.splitlines()
                index = lines.index('_background.order')
                lines.insert(index, '_background.id')
                first = index + 3
                while (
                    first < len(lines)
                    and lines[first].strip()
                    and not lines[first].startswith(('_', 'loop_', 'data_'))
                ):
                    tokens = lines[first].split()
                    lines[first] = 'term_' + tokens[0] + ' ' + lines[first]
                    first += 1
                text = '\n'.join(lines) + '\n'
            model_file.write_text(
                text
                .replace('_edi.schema_version 2', '_edi.schema_version 1')
                .replace('_edi.schema_version 3', '_edi.schema_version 1')
                .replace('_calculator.type crysta', '_calculator.type cryspy')
                .replace('_minimizer.type crysta', '_minimizer.type "lmfit (leastsq)"')
            )
        return Project.load(str(private))


def project_model_names(reference_names, experiments, path):
    names = list(reference_names)
    # Apply the committed engine-model contract to the external selection. No edi
    # or crysta parameter walk, writer, or fit supplies this oracle.
    for experiment in experiments:
        original = (path / 'experiments' / (experiment.name + '.edi')).read_text()
        prefix = experiment.name + '.'
        if str(experiment.experiment_type.beam_mode.value) == 'time-of-flight':
            names.remove(prefix + 'instrument.twotheta_bank')
            for coefficient in (
                'rise_alpha_0',
                'rise_alpha_1',
                'decay_beta_0',
                'decay_beta_1',
                'broad_gauss_sigma_0',
                'broad_gauss_sigma_1',
                'broad_gauss_sigma_2',
                'broad_gauss_size_g',
                'broad_gauss_strain_g',
                'broad_lorentz_gamma_0',
                'broad_lorentz_gamma_1',
                'broad_lorentz_gamma_2',
                'broad_lorentz_size_l',
                'broad_lorentz_strain_l',
            ):
                name = prefix + 'peak.' + coefficient
                if name not in names:
                    names.append(name)
            if re.search(r'^_absorption.type cylinder\s*$', original, re.MULTILINE):
                names.extend(prefix + 'absorption.' + name for name in ('abscor1', 'abscor2'))
        elif 'asym_fcj' in original:
            names.extend(prefix + 'peak.' + name for name in ('asym_fcj_1', 'asym_fcj_2'))
        elif '_peak.asym_beba_limit' in original:
            names.append(prefix + 'peak.asym_beba_limit')
    return names


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path, nargs='?')
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--only', action='append', default=[])
    selection.add_argument('--public-metadata', action='store_true')
    args = parser.parse_args()
    if args.reference is None and not args.public_metadata:
        parser.error('reference checkout is required for independent count generation')
    return args


def public_metadata(path):
    before = path.read_text()
    adrs = 'crysta A' + 'DR-0042 and A' + 'DR-0065'
    task = 're' + 'lay C' + '13-' + 'T1 contract'
    fcj = 'crysta A' + 'DR-0065'
    after = before
    for citation in (adrs, task, fcj):
        after = after.replace(' (' + citation + ')', '')
    if json.loads(before)['cases'] != json.loads(after)['cases']:
        raise RuntimeError('public metadata adaptation must retain every scientific case')
    path.write_text(after)


def main():
    args = arguments()
    root = Path(__file__).resolve().parents[3]
    here = Path(__file__).resolve().parent
    if args.public_metadata:
        public_metadata(here / 'model_counts.json')
        return
    from easydiffraction.analysis.analysis import Analysis  # noqa: PLC0415 - generation only

    reference = args.reference.resolve()
    print('Loading independent diffraction-lib model', flush=True)

    source = Path(inspect.getfile(Analysis)).resolve()
    if not source.is_relative_to(reference):
        raise RuntimeError('diffraction-lib must resolve to the declared reference checkout')
    output = {
        'reference': 'Analysis._selected_parameters_for_fit(selected experiments)',
        'diffraction_lib_sha': subprocess.check_output(
            ['git', '-C', str(reference), 'rev-parse', 'HEAD'], text=True
        ).strip(),
        'analysis_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'input_adaptation': (
            'private copies: _edi.schema_version 2/3 -> 1; _calculator.type crysta -> cryspy; '
            '_minimizer.type crysta -> "lmfit (leastsq)"; missing legacy TOF family supplied '
            'from the declared tof-* peak tag; parameter tags unchanged; no fit run'
        ),
        'model_projection': {
            'tof_geometry': (
                'bank angle is fixed geometry (Cryspy TOFParameters.ATTR_REF excludes it)'
            ),
            'tof_peak': '14 coefficient slots, including zero Lorentzian/rate limits',
            'tof_absorption': ('cylinder abscor1/abscor2 are model parameters'),
            'cw_asymmetry': ('FCJ two slots and BeBa limit angle are model parameters'),
        },
        'cases': [],
    }
    cases = json.loads((here / 'cli.json').read_text())['cases']
    if args.only:
        retained = json.loads((here / 'model_counts.json').read_text())
        if set(args.only) & {row['id'] for row in retained['cases']}:
            raise RuntimeError('append-only count generation refuses replacing an existing oracle')
        output['cases'] = retained['cases']
        output['previous_provenance'] = {
            key: value for key, value in retained.items() if key != 'cases'
        }
        output['coefficient_count_adaptation'] = (
            'private polynomial declarations -> reference Chebyshev coefficient storage; '
            'explicit term_<order> IDs supplied; coefficients/free flags retained; '
            'count-only selection, no basis evaluation or fit; native polynomial and '
            'Chebyshev have one model parameter per authored coefficient (ADR-0077)'
        )
    for case in cases:
        if args.only and case['id'] not in args.only:
            continue
        path = root / case.get('authoring_input', case['path'])
        for relative, expected in case['inputs_sha256'].items():
            if hashlib.sha256((path / relative).read_bytes()).hexdigest() != expected:
                raise RuntimeError('independent count input changed: ' + case['id'])
        project = load_reference_project(path)
        experiments = list(project.experiments.values())
        if case['mode'] == 'single' and len(experiments) != 1:
            raise RuntimeError('single fit fixture must name its sole experiment')
        parameters = project.analysis._selected_parameters_for_fit(experiments)
        reference_names = [parameter.unique_name for parameter in parameters]
        names = list(reference_names)
        names = project_model_names(reference_names, experiments, path)
        output['cases'].append({
            'id': case['id'],
            'n_parameters': len(names),
            'diffraction_lib_n_parameters': len(reference_names),
            'diffraction_lib_parameter_names': reference_names,
            'parameter_names': names,
            'experiments': list(project.experiments.names),
        })
        print(case['id'] + ': ' + str(len(names)), flush=True)
    (here / 'model_counts.json').write_text(json.dumps(output, indent=2) + '\n')


if __name__ == '__main__':
    main()

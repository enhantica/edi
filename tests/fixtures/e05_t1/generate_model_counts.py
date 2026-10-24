"""Freeze diffraction-lib's selected fit model, independently of edi's parameter walk.

Run with diffraction-lib's Python environment, passing its checkout as the argument.
This updates only the count oracle; the author-time CLI fit records remain intact.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import re
import shutil
import subprocess
import tempfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch


def reference_spelling(text):
    # The external loop reader cannot parse exponent notation before its empty su.

    def plain_decimal(match):
        original = match.group()
        converted = format(Decimal(original), 'f')
        assert float(original) == float(converted), (
            'Count-only numeric spelling must preserve the exact loaded floating value'
        )
        return converted

    text = re.sub(
        r'(?<!\S)[+-]?(?:\d+(?:\.\d*)?|\.\d+)[eE][+-]?\d+(?=\s|$)',
        plain_decimal,
        text,
    )
    lines = text.splitlines()
    if '_background.id' in lines:
        first = lines.index('_background.id')
        cursor = first
        while cursor < len(lines) and lines[cursor].startswith('_background.'):
            cursor += 1
        while (
            cursor < len(lines)
            and lines[cursor].strip()
            and not lines[cursor].startswith(('_', 'loop_', 'data_'))
        ):
            tokens = lines[cursor].split()
            if not re.fullmatch(r'[A-Za-z0-9_]+', tokens[0]):
                tokens[0] = 'point_' + str(cursor - first)
                lines[cursor] = ' '.join(tokens)
            cursor += 1
        text = '\n'.join(lines) + '\n'
    return text


def load_reference_project(path, retained_ranges=None):
    from cryspy.A_functions_base.function_2_space_group import (  # noqa: PLC0415
        get_name_hm_extended_by_it_number_it_coordinate_system_code,
    )
    from easydiffraction import Project  # noqa: PLC0415 - independent reference environment only
    from easydiffraction.core.validation import RangeValidator  # noqa: PLC0415
    from easydiffraction.datablocks.experiment.item.enums import (  # noqa: PLC0415
        PeakProfileTypeEnum,
    )

    # Counting must retain saved values, including a fit's out-of-range result.
    # Type and membership validation remain active; only finite range violations
    # are retained during the private load. No fit or calculation is performed.
    original_range = RangeValidator.validated

    def saved_range(validator, value, name, default=None, current=None):
        if math.isfinite(value) and not (
            validator.ge <= value <= validator.le and validator.gt < value < validator.lt
        ):
            if retained_ranges is not None:
                retained_ranges.append({'name': name, 'value': value})
            return value
        return original_range(validator, value, name, default=default, current=current)

    # Adapt reader/backend labels only; no fit or calculation is performed.
    # All parameter tags and the original committed inputs stay intact.
    with tempfile.TemporaryDirectory(prefix='reference-model-') as temporary:
        private = Path(temporary) / 'project'
        shutil.copytree(path, private)
        for model_file in private.rglob('*.edi'):
            text = model_file.read_text()
            text = reference_spelling(text)
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
            if re.search(r'^_space_group.name_h_m "P b n m"$', text, re.MULTILINE):
                # The reference reader requires a standard short name plus its
                # axis qualifier. Cryspy's own IT table proves the equivalence.
                if (
                    get_name_hm_extended_by_it_number_it_coordinate_system_code(62, 'cab')
                    != 'P b n m'
                ):
                    raise RuntimeError(
                        'reference space-group table must preserve the saved setting'
                    )
                if '_space_group.coord_system_code' in text:
                    raise RuntimeError(
                        'alternate space-group adaptation requires an implicit setting'
                    )
                text = text.replace(
                    '_space_group.name_h_m "P b n m"', '_space_group.name_h_m "P n m a"'
                )
                text += '\n_space_group.coord_system_code cab\n'
            # Keep the current native tag in this source; the frozen external
            # reader supplies its own canonical spelling through its enum.
            for native, external in (
                ('cwl-tch-pseudo-voigt', PeakProfileTypeEnum.CWL_PSEUDO_VOIGT),
                ('cwl-tch-pseudo-voigt-fcj', PeakProfileTypeEnum.CWL_THOMPSON_COX_HASTINGS),
                (
                    'cwl-pseudo-voigt-berar-baldinozzi',
                    PeakProfileTypeEnum.CWL_PSEUDO_VOIGT_BERAR_BALDINOZZI_ASYMMETRY,
                ),
            ):
                text = re.sub(
                    r'^_peak.type ' + native + r'$',
                    '_peak.type ' + external,
                    text,
                    flags=re.MULTILINE,
                )
            # The reference exposes Chebyshev coefficient storage. For count-only
            # selection, plain powers have the same independent coefficient set;
            # no reference fit/calculation or basis conversion is performed.
            if '_background.coef' in text:
                text = text.replace('_background.type polynomial', '_background.type chebyshev')
                lines = text.splitlines()
                index = lines.index('_background.order')
                if '_background.id' not in lines:
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
        with patch.object(RangeValidator, 'validated', saved_range):
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
        names = xray_model_names(names, original, prefix)
    return names


def xray_model_names(names, original, prefix):
    # X-ray CW has the prior polarization pair and the two doublet
    # slots beyond the external reader's four CW parameters. The fixed-zero
    # defaults are still part of the declared model; no native walk supplies them.
    if not re.search(
        r'^_experiment_type.radiation_probe ["\']?xray["\']?$', original, re.MULTILINE
    ):
        return names
    for field in (
        'setup_polarization_coefficient',
        'setup_monochromator_twotheta',
        'setup_wavelength_2',
        'setup_wavelength_2_to_1_ratio',
    ):
        name = prefix + 'instrument.' + field
        if name not in names:
            names.append(name)
    # The declared Npr5 BeBa shape uses eta0/eta1, not the external TCH X/Y
    # storage. This is count/identity projection only, never a coefficient map.
    if re.search(r'^_peak.type cwl-pseudo-voigt(?:-berar-baldinozzi)?$', original, re.MULTILINE):
        for field in ('broad_lorentz_x', 'broad_lorentz_y'):
            names.remove(prefix + 'peak.' + field)
        names.extend(prefix + 'peak.' + field for field in ('mixing_eta_0', 'mixing_eta_1'))
    return names


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path, nargs='?')
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--only', action='append', default=[])
    selection.add_argument('--update', action='append', default=[])
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
        'numeric_input_adaptation': (
            'private scientific notation expanded to decimal for the reference loop reader; '
            'every loaded float checked equal, fields/free markers retained; '
            'private background labels use the external identifier grammar; '
            'row order, coordinates and coefficients retained; no fit or calculation'
        ),
        'reader_label_adaptation': (
            'private P b n m -> reference P n m a with cab, verified by Cryspy IT table; '
            'coordinates/cell values retained; native BeBa peak tag -> external canonical '
            'asymmetry tag; no fit/calculation or selected-parameter method changes'
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
    args.selected = args.only or args.update
    if args.selected:
        retained = json.loads((here / 'model_counts.json').read_text())
        if args.only and set(args.only) & {row['id'] for row in retained['cases']}:
            raise RuntimeError('append-only count generation refuses replacing an existing oracle')
        if args.update and not set(args.update) <= {row['id'] for row in retained['cases']}:
            raise ValueError('Count update requires existing declared cases')
        output['cases'] = [row for row in retained['cases'] if row['id'] not in args.update]
        output['previous_provenance'] = {
            key: value for key, value in retained.items() if key != 'cases'
        }
        output['coefficient_count_adaptation'] = (
            'private polynomial declarations -> reference Chebyshev coefficient storage; '
            'explicit term_<order> IDs supplied; coefficients/free flags retained; '
            'count-only selection, no basis evaluation or fit; native polynomial and '
            'Chebyshev have one model parameter per authored coefficient (ADR-0077)'
        )
    if args.selected and not set(args.selected) <= {case['id'] for case in cases}:
        raise ValueError('Count generation requires every selected CLI capture to exist')
    for case in cases:
        if args.selected and case['id'] not in args.selected:
            continue
        path = root / case.get('authoring_input', case['path'])
        for relative, expected in case['inputs_sha256'].items():
            if hashlib.sha256((path / relative).read_bytes()).hexdigest() != expected:
                raise RuntimeError('independent count input changed: ' + case['id'])
        retained_ranges = []
        project = load_reference_project(path, retained_ranges)
        experiments = list(project.experiments.values())
        if case['mode'] == 'single' and len(experiments) != 1:
            raise RuntimeError('single fit fixture must name its sole experiment')
        if retained_ranges:
            output.setdefault('saved_range_adaptation', {})[case['id']] = {
                'scope': 'finite numeric range checks during private load only; saved values '
                'retained; type/membership checks and external model selection unchanged; no fit',
                'retained': retained_ranges,
            }
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

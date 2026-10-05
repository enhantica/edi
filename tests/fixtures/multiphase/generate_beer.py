"""Transcribe the external BEER run without executing a reference calculator."""

import argparse
import json
import math
import re
import shutil
from pathlib import Path

import numpy as np

HOME = Path(__file__).with_name('beer')
CASE = 'beer-ferrite-austenite'
PROJECT_ID = 'pd-neut-tof_ferrite-austenite-beer_joint'


def scale_factor(reference, bank):
    """CrySPY to FullProf TOF scale from the independent reference geometry."""
    geometry = reference['stages'][0]['all_parameters'][f'{bank}.instrument.twotheta_bank']
    two_theta = geometry['value']
    if geometry['free'] or not math.isfinite(two_theta) or not 0 < two_theta <= 180:
        message = 'BEER scale conversion requires fixed physical reference bank geometry'
        raise ValueError(message)
    return 1 / math.sin(math.radians(two_theta / 2))


def mapped_parameters(reference, stage):
    """Preserve every external parameter, scaling phase values and their own SU."""
    mapped = {}
    for key, parameter in stage['parameters'].items():
        value = dict(parameter)
        if '.linked_structure.' in key and key.endswith('.scale'):
            conversion = scale_factor(reference, key.split('.')[0])
            value['value'] *= conversion
            value['su'] *= conversion
        mapped[key] = value
    return mapped


def mapped_scale_token(token, conversion):
    match = re.fullmatch(r'([+-]?(?:\d+\.?\d*|\.\d+))(?:\(([^)]*)\))?', token)
    if match is None:
        message = 'BEER phase scale must be a finite numeric parameter token'
        raise ValueError(message)
    mantissa, uncertainty = match.groups()
    value = float(mantissa) * conversion
    if not math.isfinite(value):
        message = 'BEER scale mapping must retain finite inputs'
        raise ValueError(message)
    result = f'{value:.17f}'.rstrip('0').rstrip('.')
    if uncertainty is not None:
        if uncertainty:
            su = float(uncertainty)
            if '.' not in uncertainty:
                su /= 10 ** len(mantissa.partition('.')[2])
            # A decimal bracket is an absolute SU, independent of mantissa precision.
            result += f'({su * conversion:.17f})'
        else:
            result += '()'
    return result


def transcribe(source, destination, background_free):
    destination.mkdir(parents=True, exist_ok=False)
    reference = json.loads((HOME / 'reference.json').read_text())
    for path in source.rglob('*.edi'):
        relative = path.relative_to(source)
        text = path.read_text().replace('_edi.schema_version 1', '_edi.schema_version 3')
        if relative.parts[0] == 'experiments':
            # The source run owns measured x/y/errors; the remaining data columns are outputs.
            text = text.split('loop_\n_data.time_of_flight')[0]
            # These four optional zero-valued descriptors are absent from crysta's
            # dictionary and contribute nothing to the tutorial's profile.
            text = re.sub(
                r'^_peak\.broad_(?:lorentz_(?:size_l|strain_l)|gauss_(?:size_g|strain_g)) 0\.\n',
                '',
                text,
                flags=re.MULTILINE,
            )
            # FullProf carries sin(theta_bank) in the TOF prefactor; CrySPY does not.
            # The bank angle and each start value come only from the saved external run.
            before, rest = text.split('_linked_structure.scale\n', 1)
            rows, after = rest.split('\n\n', 1)
            conversion = scale_factor(reference, path.stem)
            rows = '\n'.join(
                f'{phase} {mapped_scale_token(token, conversion)}'
                for phase, token in (row.split() for row in rows.splitlines())
            )
            text = before + '_linked_structure.scale\n' + rows + '\n\n' + after
            name = 'N2' if path.stem == 'expt_n2' else 'S2'
            data = np.loadtxt(HOME / 'data' / f'Duplex_in_HR_for_IRF_{name}.dat')
            data[data[:, 2] == 0, 2] = 1  # The tutorial loader's zero-error convention.
            text += 'loop_\n_data.time_of_flight\n_data.intensity_meas\n_data.intensity_meas_su\n'
            text += ''.join(' '.join(f'{v:.17g}' for v in row) + '\n' for row in data)
            if not background_free:
                before, rest = text.split('_background.intensity\n', 1)
                background, after = rest.split('\n\nloop_\n_data.', 1)
                # Preserve first-stage fitted backgrounds, fixed for the tutorial's second fit.
                background = re.sub(r'\([^)]*\)', '', background)
                text = (
                    before + '_background.intensity\n' + background + '\n\nloop_\n_data.' + after
                )
        if relative.parts[0] == 'analysis':
            # Keep the tutorial aliases and constraints; result fields precede them
            # in a saved first-stage record. The initial analysis is the clean model.
            text = (
                (HOME / 'reference-run/initial/analysis/analysis.edi')
                .read_text()
                .replace('_edi.schema_version 1', '_edi.schema_version 3')
            )
            if reference['reference_variant'] == 'unconstrained-independent-bank-scales':
                text = text.split('loop_\n_alias.id')[0].rstrip() + '\n'
            text += (
                '\nloop_\n_joint_fit.experiment_id\n_joint_fit.weight\nexpt_s2 0.5\nexpt_n2 0.5\n'
            )
            text = text.replace(
                '_minimizer.max_iterations 1000',
                '_minimizer.max_iterations 1000\n_minimizer.chi_square_tolerance 1e-8',
            )
        if relative.name == 'project.edi':
            text = '_edi.schema_version 3\n_metadata.name beer_mcstas\n'
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--corpus-root', type=Path, required=True)
    parser.add_argument('--fixture-output', type=Path, required=True)
    args = parser.parse_args()
    transcribe(
        HOME / 'reference-run/initial', args.fixture_output / 'initial', background_free=True
    )
    transcribe(
        HOME / 'reference-run/stage-1', args.fixture_output / 'second-fit', background_free=False
    )
    case = args.corpus_root / CASE
    case.mkdir(parents=True)
    shutil.copytree(args.fixture_output / 'second-fit', case / 'project')
    ref = json.loads((HOME / 'reference.json').read_text())
    (case / 'expected.json').write_text(
        json.dumps(
            {
                'schema': 1,
                'source': {
                    'engine': 'declared project invariant',
                    'artifact': 'PROVENANCE.md',
                    'provenance': 'PROVENANCE.md',
                },
                'quantities': {
                    'n_free': {
                        'value': len(ref['stages'][-1]['parameters']),
                        'kind': 'reference',
                        'tol_abs': 0,
                        'tol_rel': None,
                    },
                },
            },
            indent=2,
        )
        + '\n'
    )
    (case / 'PROVENANCE.md').write_text(
        'BEER joint-fit behavior vehicle. Only its sixteen declared non-background '
        'free parameters are an invariant expectation. Captured values initialize '
        'the model; no external Rwp, parameter or offset agreement is active.\n'
    )


if __name__ == '__main__':
    main()

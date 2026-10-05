"""Transcribe the external BEER run without executing a reference calculator."""

import argparse
import json
import re
import shutil
from pathlib import Path

import numpy as np

HOME = Path(__file__).with_name('beer')
CASE = 'beer-ferrite-austenite'
PROJECT_ID = 'pd-neut-tof_ferrite-austenite-beer_joint'


def transcribe(source, destination, background_free):
    destination.mkdir(parents=True, exist_ok=False)
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
                    'engine': 'diffraction-lib 0.19.1 / CrySPY 0.12.1',
                    'artifact': 'PROVENANCE.md',
                    'provenance': 'PROVENANCE.md',
                },
                'quantities': {
                    'n_free': {'value': 14, 'kind': 'reference', 'tol_abs': 0, 'tol_rel': None},
                    'rwp': {
                        'value': ref['stages'][-1]['active_rwp'],
                        'kind': 'reference',
                        'tol_abs': None,
                        'tol_rel': 0.05,
                    },
                },
            },
            indent=2,
        )
        + '\n'
    )
    (case / 'PROVENANCE.md').write_text(
        'Independent BEER ferrite/austenite two-bank joint-fit reference: diffraction-lib '
        '0d9f10e412a0cd08d4dd0af95845dd9bb597dcdf, default CrySPY 0.12.1.\n'
        'The visible author_beer.py captures the tutorial; reference.json and raw Edi output '
        'live in edi tests/fixtures/multiphase/beer. No test runs diffraction-lib.\n'
        'This corpus starts from the saved first fit with backgrounds fixed, then performs '
        'the second fit with all 14 remaining free parameters. Separate system gates execute '
        'both stages and compare every parameter within its own standard uncertainty.\n'
        'Rwp has no reported uncertainty; five percent relative permits independent optimizer '
        'termination while forbidding material fit-quality loss. Parameter bounds remain one SU.\n'
        'Schema changes to 3; measured columns come from the original archive at full precision. '
        'Zero measured error becomes one exactly as in the tutorial loader. First-stage Edi '
        'rounding is retained. CrySPY calculator/minimizer declarations '
        'are retained as provenance; '
        'crysta resolves its own backend on load.\n'
    )


if __name__ == '__main__':
    main()

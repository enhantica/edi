"""Rebuild archived GPX cases from Edi exports and compare both profile calculations."""

import argparse
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from GSASII import GSASIIscriptable

from tools.gsas_ii.build_project import build_project
from tools.gsas_ii.bundle import profile_metrics, require

_COLUMNS = ('X', 'Yobs', 'Yweight', 'Ycalc', 'Background')


def _observe(histogram) -> np.ndarray:
    return np.column_stack([np.ma.getdata(histogram.getdata(column)) for column in _COLUMNS])


def _prediction(project):
    project.set_Controls('cycles', 0)
    project.data['Controls']['data']['deriv type'] = 'analytic Hessian'
    project.do_refinements([{}])
    return project.histograms()


def _uses_models(project) -> bool:
    return any(
        link.get('Use', True)
        for phase in project.phases()
        for link in phase.data['Histograms'].values()
    )


def _comparison(source, rebuilt, edi: np.ndarray) -> dict:
    original, reverse = _observe(source), _observe(rebuilt)
    require(
        original.shape == reverse.shape
        and np.allclose(original[:, :3], reverse[:, :3], rtol=2e-6, atol=5e-7),
        'The rebuilt GPX changed observations or weights',
    )
    require(
        edi.shape == original.shape
        and np.allclose(edi[:, :2], original[:, :2], rtol=2e-6, atol=5e-7),
        'The saved Edi project changed the observation grid or intensities',
    )
    lo, hi = source.data['Limits'][1]
    low, high = rebuilt.data['Limits'][1]
    x = original[:, 0]
    selected = (x >= lo) & (x <= hi) & (original[:, 2] > 0)
    require(
        np.array_equal(
            selected, (reverse[:, 0] >= low) & (reverse[:, 0] <= high) & (reverse[:, 2] > 0)
        ),
        'The rebuilt GPX changed the active observation range',
    )
    for lo, hi in source.data['Limits'][2:]:
        selected &= (x < lo) | (x > hi)
    selected &= ~np.ma.getmaskarray(source.getdata('X'))
    selected &= np.isfinite(edi[:, 3]) & np.isfinite(edi[:, 4])
    sigma = 1 / np.sqrt(original[selected, 2])
    require(
        np.allclose(sigma, edi[selected, 2], rtol=2e-6, atol=5e-7),
        'The saved Edi project changed the active measurement uncertainties',
    )
    reference = original[selected, 3:5]
    return {
        'edi_reopened': profile_metrics(reference, edi[selected, 3:5], sigma),
        'gsas_rebuilt': profile_metrics(reference, reverse[selected, 3:5], sigma),
    }


def _check_rebuilt(original, reverse, artifact: Path) -> dict:
    if not _uses_models(original):
        require(not _uses_models(reverse), 'The reverse writer added an active phase link')
        for a, b in zip(original.histograms(), reverse.histograms(), strict=True):
            require(
                np.allclose(_observe(a)[:, :3], _observe(b)[:, :3], rtol=2e-6, atol=5e-7),
                'The rebuilt GPX changed observations or weights',
            )
        return {'status': 'data-roundtrip', 'profiles': 'no active source phase'}
    before, after = _prediction(original), _prediction(reverse)
    profiles = []
    for i, (base, fresh) in enumerate(zip(before, after, strict=True)):
        edi = np.loadtxt(artifact / f'edi-{i}.txt')
        profiles.append(_comparison(base, fresh, edi))
    return {'status': 'roundtrip-compared', 'histograms': profiles}


def check_case(source: Path, artifact: Path, scratch: Path) -> dict:
    """Use the pinned GSAS-II runtime on a trusted source file or a GPX rebuilt locally."""
    original_path = scratch / 'source.gpx'
    shutil.copyfile(source, original_path)
    rebuilt = artifact / 'rebuilt.gpx'
    errors = (GSASIIscriptable.G2ScriptException, OSError, ValueError, KeyError, TypeError)
    try:
        build_project(artifact / 'reverse.gsas.json', rebuilt)
    except errors as error:
        return {'status': 'blocked', 'stage': 'write GPX', 'message': str(error)}
    try:
        original = GSASIIscriptable.G2Project(str(original_path))
        reverse = GSASIIscriptable.G2Project(str(rebuilt), newgpx=str(scratch / 'reverse.gpx'))
        return _check_rebuilt(original, reverse, artifact)
    except errors as error:
        return {'status': 'blocked', 'stage': 'reopen and compare', 'message': str(error)}


def main() -> None:
    """Compare a batch produced by the native Edi corpus check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('corpus', type=Path, help='Trusted gsas-ii directory in software-examples')
    parser.add_argument('artifacts', type=Path, help='Artifacts produced by check_corpus')
    parser.add_argument('--report', required=True, type=Path, help='New report path')
    args = parser.parse_args()
    results = {}
    for category in ('projects', 'references'):
        for path in sorted((args.corpus / category).glob('*/*.gpx')):
            relative = path.relative_to(args.corpus)
            artifact = args.artifacts / relative.parent
            if not (artifact / 'reverse.gsas.json').is_file():
                continue
            with TemporaryDirectory(prefix='gsas-corpus-compare-') as directory:
                results[relative.as_posix()] = check_case(path, artifact, Path(directory))
    if not results:
        parser.error('No reverse export bundles were found for these cases')
    with args.report.open('x', encoding='utf-8') as output:
        json.dump(results, output, ensure_ascii=False, indent=2, allow_nan=False)
        output.write('\n')


if __name__ == '__main__':
    main()

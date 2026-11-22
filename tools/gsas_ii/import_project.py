"""Save a native GSAS-II import and optionally compare its recalculated profile."""

import argparse
import hashlib
import json
from pathlib import Path

import edi
import numpy as np

from tools.gsas_ii.bundle import FORMAT, profile_metrics, require


def _observations(project: edi.Project) -> np.ndarray:
    data = project.experiments['powder'].data
    return np.column_stack((data.two_theta, data.intensity_meas, data.intensity_meas_su))


def _reference_columns(source: Path, observed: np.ndarray, project_path: Path) -> np.ndarray:
    bundle = json.loads(source.read_text(encoding='ascii'))
    require(bundle['format'] == FORMAT, f'Expected bundle format {FORMAT}')
    if project_path.suffix.lower() == '.gpx':
        with project_path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        require(
            bundle['source']['sha256'] == digest, 'Reference belongs to a different source GPX'
        )
    rows = np.asarray(bundle['histogram']['observations'], dtype=float)
    require(
        rows.shape == observed.shape and np.isfinite(rows).all() and np.all(rows[:, 2] > 0),
        'Reference observations have a different shape or invalid values',
    )
    rows[:, 2] = 1 / np.sqrt(rows[:, 2])
    require(np.array_equal(observed, rows), 'Reference observations differ from the imported grid')

    reference = bundle['reference']
    result = np.column_stack((reference['calculated'], reference['background'])).astype(float)
    require(
        result.shape == (len(observed), 2) and np.isfinite(result).all(),
        'Reference profile has a different shape or invalid values',
    )
    require(np.linalg.norm(result[:, 0] - result[:, 1]) > 0, 'Reference has no Bragg signal')
    return result


def _compare(
    project: edi.Project, reference: np.ndarray, observed: np.ndarray, output: Path
) -> None:
    project.analysis.calculate()
    data = project.experiments['powder'].data
    calculated = np.asarray(data.intensity_calc)
    background = np.asarray(data.intensity_bkg)
    require(
        calculated.shape == background.shape == observed[:, 0].shape
        and np.isfinite(calculated).all()
        and np.isfinite(background).all(),
        'Reopened EasyDiffraction project did not calculate every exported observation',
    )
    difference = calculated - reference[:, 0]
    metrics = profile_metrics(reference, np.column_stack((calculated, background)), observed[:, 2])
    output.mkdir()
    (output / 'metrics.json').write_text(
        json.dumps(metrics, indent=2, allow_nan=False) + '\n',
        encoding='ascii',
    )
    np.savetxt(
        output / 'profiles.csv',
        np.column_stack((observed, reference, calculated, background, difference)),
        delimiter=',',
        header='two_theta,observed,sigma,gsas_calculated,gsas_background,'
        'edi_calculated,edi_background,edi_minus_gsas',
        comments='',
    )


def import_project(
    source: Path,
    output: Path,
    *,
    comparison: Path | None = None,
    reference_bundle: Path | None = None,
) -> edi.Project:
    """Create and reopen a new Edi project using Edi's normal project loader and writer."""
    require(not output.exists() and not output.is_symlink(), f'Output already exists: {output}')
    if comparison is not None:
        require(
            not comparison.exists()
            and not comparison.is_symlink()
            and not comparison.resolve().is_relative_to(output.resolve()),
            'Comparison needs a new directory outside the EasyDiffraction project',
        )
    project = edi.Project.load(source)
    observed = _observations(project)
    reference = (
        _reference_columns(reference_bundle or source, observed, source) if comparison else None
    )

    project.save_as(output)
    reopened = edi.Project.load(output / 'project.edi')
    saved = _observations(reopened)
    require(
        saved.shape == observed.shape
        and np.allclose(saved[:, 0], observed[:, 0], atol=1e-8, rtol=0),
        'Saved EasyDiffraction project changed the measurement grid',
    )
    require(
        np.allclose(saved[:, 1:], observed[:, 1:], rtol=1e-6, atol=1e-8),
        'Saved EasyDiffraction observations differ beyond text precision',
    )
    if comparison is not None:
        _compare(reopened, reference, observed, comparison)
    return reopened


def main() -> None:
    """Save a GSAS-II GPX or ASCII bundle as an EasyDiffraction project."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='GSAS-II project (.gpx or .gsas.json)')
    parser.add_argument('output', type=Path, help='New EasyDiffraction project directory')
    parser.add_argument('--comparison', type=Path, help='New directory for profile residuals')
    parser.add_argument(
        '--reference-bundle', type=Path, help='ASCII bundle containing GSAS-II profile'
    )
    args = parser.parse_args()
    if args.comparison and args.source.suffix.lower() == '.gpx' and not args.reference_bundle:
        parser.error('--reference-bundle is required to compare a GPX project')
    try:
        import_project(
            args.source,
            args.output,
            comparison=args.comparison,
            reference_bundle=args.reference_bundle,
        )
    except (KeyError, OSError, TypeError, ValueError, edi.IoError) as error:
        parser.exit(1, f'GSAS-II import: {error}\n')


if __name__ == '__main__':
    main()

"""Check unspecialized GPX opening, saving and recalculation across the example corpus."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import edi
import numpy as np

from tools.gsas_ii.export_edi import export_edi
from tools.gsas_ii.import_project import import_project

PROJECT_ERRORS = (edi.IoError, RuntimeError, ValueError, OSError, KeyError, TypeError)


def check_case(source: Path, scratch: Path) -> dict:
    """Use native project APIs throughout, comparing profiles when a reference is supplied."""
    output = scratch / 'project'
    reference = source.with_name('reference.gsas.json')
    try:
        project = edi.Project.load(source)
    except PROJECT_ERRORS as error:
        message = str(error).removeprefix(f"Cannot import GSAS-II project '{source}': ")
        return {'status': 'blocked', 'stage': 'open', 'message': message}

    if reference.is_file():
        comparison = scratch / 'comparison'
        try:
            import_project(source, output, comparison=comparison, reference_bundle=reference)
            metrics = json.loads((comparison / 'metrics.json').read_text(encoding='ascii'))
        except PROJECT_ERRORS as error:
            return {'status': 'blocked', 'stage': 'reference comparison', 'message': str(error)}
        return {'status': 'compared', 'metrics': metrics}

    stage = 'save and reopen'
    try:
        project.save_as(output)
        project = edi.Project.load(output / 'project.edi')
        stage = 'calculate'
        project.analysis.calculate()
    except PROJECT_ERRORS as error:
        return {'status': 'blocked', 'stage': stage, 'message': str(error)}
    return {'status': 'calculated', 'profile_reference': 'unavailable'}


def _write_roundtrip_artifacts(scratch: Path) -> None:
    saved = scratch / 'project' / 'project.edi'
    project = edi.Project.load(saved)
    project.analysis.calculate()
    for i, experiment in enumerate(project.experiments):
        data = experiment.data
        axis = data.time_of_flight if isinstance(data, edi.PdTofData) else data.two_theta
        columns = np.column_stack((
            axis,
            data.intensity_meas,
            data.intensity_meas_su,
            data.intensity_calc,
            data.intensity_bkg,
        ))
        np.savetxt(scratch / f'edi-{i}.txt', columns)
    export_edi(saved, scratch / 'reverse.gsas.json')


def main() -> None:
    """Check the canonical project folders and the independent reference folders."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('gsas_ii_corpus', type=Path, help='gsas-ii directory in software-examples')
    parser.add_argument('--report', type=Path, required=True, help='JSON results path')
    parser.add_argument('--roundtrip-dir', type=Path, help='Keep artifacts in a new directory')
    args = parser.parse_args()
    root = args.gsas_ii_corpus
    cases = sorted(
        source
        for category in ('projects', 'references')
        for source in (root / category).rglob('*')
        if source.is_file() and source.suffix.lower() == '.gpx'
    )
    if not cases:
        parser.error('No GPX cases found in projects/ or references/')
    results = {}
    if args.roundtrip_dir:
        args.roundtrip_dir.mkdir()
    for source in cases:
        relative = source.relative_to(root)
        if args.roundtrip_dir:
            scratch = args.roundtrip_dir / relative.parent
            scratch.mkdir(parents=True)
            result = check_case(source, scratch)
            if result['status'] != 'blocked':
                try:
                    _write_roundtrip_artifacts(scratch)
                except PROJECT_ERRORS as error:
                    result['writer'] = {'status': 'blocked', 'message': str(error)}
                else:
                    result['writer'] = {'status': 'bundle-written'}
        else:
            with TemporaryDirectory(prefix='edi-gpx-check-') as directory:
                result = check_case(source, Path(directory))
        results[relative.as_posix()] = result
    args.report.write_text(
        json.dumps(results, ensure_ascii=False, indent=2, allow_nan=False) + '\n',
        encoding='utf-8',
    )


if __name__ == '__main__':
    main()

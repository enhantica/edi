"""Check unspecialized GPX opening, saving and recalculation across the example corpus."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import edi

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


def main() -> None:
    """Check the canonical project folders and the independent reference folders."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('gsas_ii_corpus', type=Path, help='gsas-ii directory in software-examples')
    parser.add_argument('--report', type=Path, required=True, help='JSON results path')
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
    for source in cases:
        with TemporaryDirectory(prefix='edi-gpx-check-') as directory:
            results[source.relative_to(root).as_posix()] = check_case(source, Path(directory))
    args.report.write_text(
        json.dumps(results, ensure_ascii=False, indent=2, allow_nan=False) + '\n',
        encoding='utf-8',
    )


if __name__ == '__main__':
    main()

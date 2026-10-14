"""Dataset position and count are report inputs even when the template has one experiment."""

import json
import shutil
from pathlib import Path

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('declared', [False, True], ids=['first-fallback', 'later-template'])
def test_scan_report_retains_effective_dataset_position_and_full_scan_count(tmp_path, declared):
    folder = tmp_path / 'scan-report'
    shutil.copytree(ROOT / 'tests/fixtures/report_context/long-scan', folder)
    if not declared:
        file = folder / 'analysis/analysis.edi'
        file.write_text(file.read_text().replace('_sequential_fit.template_file point12.dat', ''))
    project = edi.Project.load(folder)
    document = json.loads(project.report.model().to_json())
    style = 'meas.12' if declared else 'meas.0'
    measured = [
        series
        for experiment in document['experiments']
        for series in experiment['pattern']['series']
        if series['kind'] == 'measured'
    ]
    assert measured and all(series['style'] == style for series in measured), (
        'A scan report retains the effective template dataset place in its measured style '
        f'identity; expected={style}, actual={[series["style"] for series in measured]}'
    )
    keys = {
        entry['key'] for entry in document['pattern_styles'] if entry['key'].startswith('meas.')
    }
    assert keys == {f'meas.{index}' for index in range(20)}, (
        'The hand-declared twenty-file scan supplies twenty measured styles, so every renderer '
        'uses its scan gradient rather than the one-experiment template set'
    )

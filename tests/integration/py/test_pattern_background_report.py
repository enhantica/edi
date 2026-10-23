"""Execute the actual report consumer against the owner-defined stroke contract."""

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('kind', ['background', 'structure'])
def test_report_background_dash_and_solid_structure_outline(kind):
    observed = subprocess.run(
        [
            str(ROOT / '.pixi/envs/default/bin/node'),
            str(ROOT / 'tests/fixtures/pattern_styles/observe_report.cjs'),
            str(ROOT / 'data/report/report.js'),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=3,
    )
    assert observed.returncode == 0, (
        'The complete report script must execute its real chart consumer'
    )
    result = json.loads(observed.stdout)
    assert result['layout']['showlegend'], 'The observed actual report includes its Plotly legend'
    trace = result['traces'][0 if kind == 'background' else 1]
    assert trace['line'].get('dash', 'solid') == ('dash' if kind == 'background' else 'solid'), (
        'The actual report and its automatic legend draw a dashed background and solid structure'
    )
    assert trace['line']['color'] == ('#8a8a8a' if kind == 'background' else '#d26e3c'), (
        'Stroke changes preserve the independently supplied role colour'
    )

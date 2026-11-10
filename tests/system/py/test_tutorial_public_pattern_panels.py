"""Owner 25826cf2e: complete public HTML delivery retains the app panel structure."""

import json
import subprocess

from tests.fixtures.tutorial_cases.contract import ROOT
from tests.integration.py.test_tutorial_empty_project import api
from tests.integration.py.test_tutorial_pattern_panels import assert_app_panel_structure
from tests.integration.py.test_tutorial_report_basis import html, model


def test_public_report_pattern_supplies_three_domains_to_the_shared_drawing_code(tmp_path):

    project = api().Project.load(ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt/project')
    delivered = html(project.report.as_html(offline=False, excluded=[]))
    report = model(delivered)
    assert report['experiments'], (
        'Gate 9: the measured reference project supplies an actual report experiment'
    )
    pattern = report['experiments'][0]['pattern']
    assert [pane['pane'] for pane in pattern['layout']] == ['main', 'bragg', 'residual'], (
        'Gate 9: the public report writer supplies all three app panels to the shared renderer'
    )
    programs = [source for attrs, source in delivered.scripts if attrs.get('type') == 'module']
    assert len(programs) == 1, (
        'Gate 9: the public report delivers exactly one shared drawing program'
    )
    source = tmp_path / 'delivered-report.js'
    source.write_text(programs[0])
    data = tmp_path / 'delivered-pattern.json'
    data.write_text(json.dumps({'height': 640, 'em': 16, 'pattern': pattern}))
    observed = subprocess.run(
        [
            'node',
            str(ROOT / 'tests/fixtures/tutorial_cases/observe_pattern.cjs'),
            str(source),
            str(data),
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert observed.returncode == 0, (
        'Gate 9: the actual delivered HTML drawing module must execute: ' + observed.stderr
    )
    plots = json.loads(observed.stdout)
    assert len(plots) == 1, 'Gate 9: the public HTML report actually draws its measured pattern'
    assert_app_panel_structure(plots[0])

"""Owner fd75d9139: automatic-background teaching spans CWL, TOF and all interfaces."""

import ast
import json
import re

import pytest

from tests.fixtures.tutorial_cases.contract import ROOT, interfaces_for
from tests.fixtures.tutorial_cases.install_cell import python_syntax
from tests.fixtures.tutorial_cases.stages import observe
from tests.integration.py.test_tutorial_fit_stages import FITTING, source


def automatic_before_fit(code):
    tree = ast.parse(python_syntax(code))
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    estimates = [
        node.lineno
        for node in calls
        if ast.unparse(node.func).endswith('.background.auto_estimate')
    ]
    fits = [node.lineno for node in calls if ast.unparse(node.func).endswith('.analysis.fit')]
    patterns = [
        node.lineno for node in calls if ast.unparse(node.func).endswith('.display.pattern')
    ]
    if not estimates or not fits or not any(estimates[0] < line < min(fits) for line in patterns):
        return False
    background_free = 'background' in observe(code)['cycles'][0]['active']
    manual = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Constant)
        and node.value.value == 'manual'
        and any(
            ast.unparse(target).endswith('.background_estimate.mode') for target in node.targets
        )
    ]
    return not background_free or any(estimates[0] < line < min(fits) for line in manual)


def command_background_lesson(written):
    if not re.search(r'_background_estimate.mode\s+auto', written):
        return False
    methods = re.findall(r'_background_estimate.method\s+(\w+)', written)
    if methods:
        return all(method in {'auto', 'arpls', 'snip', 'fabc'} for method in methods)
    return bool(re.search(r'\barPLS\b', written))


def app_background_lesson(steps):
    fits = [
        index for index, step in enumerate(steps) if step.get('target') == 'statusBar.fit.button'
    ]
    return bool(fits) and any(
        step.get('target') == 'background.estimate'
        and step.get('check') == 'background-estimated:'
        and index < min(fits)
        for index, step in enumerate(steps)
    )


def test_cwl_and_tof_cases_teach_the_same_auto_background_on_every_interface():
    entries = json.loads((ROOT / 'app/tutorials/manifest.json').read_text())['tutorials']
    admitted = []
    for case in FITTING:
        declared = interfaces_for(case)
        if 'python' in declared and not all(
            automatic_before_fit(source(case, surface)) for surface in ['script', 'notebook']
        ):
            continue
        if 'cli' in declared:
            page = ROOT / 'website/surfaces/docs/cli/tutorials/cases' / (case + '.md')
            if not page.is_file():
                continue
            written = page.read_text()
            if not command_background_lesson(written):
                continue
        if 'app' not in declared:
            admitted.append(case)
            continue
        matches = [entry for entry in entries if entry['id'] == case]
        if len(matches) != 1:
            continue
        entry = matches[0]
        steps = entry.get('steps', [])
        if 'tour' in entry:
            steps = [
                step
                for block in json.loads((ROOT / 'app/tutorials' / entry['tour']).read_text())[
                    'pages'
                ]
                for step in block['steps']
            ]
        if app_background_lesson(steps):
            admitted.append(case)
    assert any('-cwl_' in case for case in admitted) and any(
        '-tof_' in case for case in admitted
    ), (
        'Gate 3/4/5: CWL and TOF cases estimate and show the background before fitting '
        'on declared interfaces, converting to Manual before fitting background points'
    )


@pytest.mark.parametrize(
    'damage',
    ['no-mode', 'unknown-method', 'no-method-lesson', 'no-action', 'no-check', 'late-estimate'],
)
def test_background_teaching_observer_reaches_the_real_action_and_refuses_escapes(damage):
    written = (
        '_background_estimate.mode auto\nThe default arPLS method estimates the background.\n'
    )
    steps = [
        {'target': 'background.estimate', 'check': 'background-estimated:'},
        {'target': 'statusBar.fit.button'},
    ]
    assert command_background_lesson(written) and app_background_lesson(steps)
    if damage == 'no-mode':
        assert not command_background_lesson(written.replace('_background_estimate.mode auto', ''))
    elif damage == 'unknown-method':
        assert not command_background_lesson(written + '_background_estimate.method foreign\n')
    elif damage == 'no-method-lesson':
        assert not command_background_lesson(written.replace('arPLS', 'foreign'))
    elif damage == 'no-action':
        assert not app_background_lesson([{'text': 'automatic background arPLS'}, steps[1]])
    elif damage == 'no-check':
        assert not app_background_lesson([{'target': 'background.estimate'}, steps[1]])
    else:
        assert not app_background_lesson(list(reversed(steps)))

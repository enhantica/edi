"""Exercise the toolbar's actual bindings while the app runner is disabled."""

import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def body(source, declaration):
    start = source.index('{', source.index(declaration)) + 1
    depth = 1
    for index in range(start, len(source)):
        depth += (source[index] == '{') - (source[index] == '}')
        if depth == 0:
            return source[start:index]
    raise ValueError('The actual correlation declaration must close its block')


def source_and_options():
    source = (ROOT / 'app/qml/Components/CorrelationChart.qml').read_text()
    toolbar = source[source.index('objectName: "correlations.toolbar.parameters"') :]
    buttons = [
        body(toolbar[match.start() :], 'ChartToolButton')
        for match in re.finditer(r'ChartToolButton\s*\{', toolbar)
    ]
    assert len(buttons) == 2, 'The actual toolbar must have two toggles after Parameters'
    options = []
    for button in buttons:
        checked = re.search(r'checked:\s*chart\.(\w+)', button)
        handler = re.search(r'onClicked:\s*([^\n]+)', button)
        assert checked and handler, 'Both toolbar toggles must bind their checked state and action'
        name = checked[1]
        assert re.search(r'property bool ' + name + r':\s*false\b', source), (
            'Axis labels and full-matrix mode must each default to off'
        )
        options.append((name, handler[1].strip()))
    assert options[0][0] != options[1][0], 'The two toolbar options must have independent state'
    return source, options


def evaluate(script):
    result = subprocess.run(
        ['node', '-e', script], capture_output=True, text=True, check=False, timeout=3
    )
    assert result.returncode == 0, 'The real correlation bindings must execute: ' + result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize('axis', ['row', 'column'])
def test_label_toggle_controls_each_actual_axis_delegate(axis):
    source, options = source_and_options()
    name, handler = options[0]
    marker = f'index % area.{axis}LabelStep'
    visible = next(
        (
            line.split('visible:', 1)[1].strip()
            for line in source.splitlines()
            if 'visible:' in line and marker in line
        ),
        None,
    )
    assert visible, 'Both matrix axes must have their actual label visibility binding'
    script = (
        f'const chart={{{name}:false}}; const area={{rowLabelStep:1,columnLabelStep:1}};'
        f'const index=1; const observations=[Boolean({visible})];'
        + handler
        + ';observations.push(Boolean('
        + visible
        + '));'
        + handler
        + ';observations.push(Boolean('
        + visible
        + '));'
        + 'process.stdout.write(JSON.stringify(observations));'
    )
    assert evaluate(script) == [False, True, False], (
        'The actual labels toggle must hide, show and hide each axis through its real binding'
    )


def test_matrix_toggle_mirrors_nontrivial_signed_coefficients_and_is_reversible():
    source, options = source_and_options()
    name, handler = options[1]
    function = body(source, 'function valueAt(')
    script = (
        f'const chart={{{name}:false}}; const count=3;'
        'const values=[NaN,NaN,NaN,-0.37,NaN,NaN,0.63,-0.81,NaN];'
        'Object.assign(chart,{count,values});'
        f'function valueAt(index){{with(chart){{{function}}}}}'
        'chart.valueAt=valueAt;'
        'const observations=[[1,2,5,3,6,7].map(valueAt)];'
        + handler
        + ';observations.push([1,2,5,3,6,7].map(valueAt));'
        + handler
        + ';observations.push([1,2,5,3,6,7].map(valueAt));'
        + 'process.stdout.write(JSON.stringify(observations));'
    )
    lower = [None, None, None, -0.37, 0.63, -0.81]
    assert evaluate(script) == [lower, [-0.37, 0.63, -0.81, -0.37, 0.63, -0.81], lower], (
        'The actual matrix toggle must mirror every signed upper coefficient and preserve '
        'the lower triangle across both transitions'
    )


def test_toggles_disable_for_unfitted_and_filtered_empty_matrices():
    source, _ = source_and_options()
    toolbar = source[source.index('objectName: "correlations.toolbar.parameters"') :]
    declarations = [
        body(toolbar[m.start() :], 'ChartToolButton')
        for m in re.finditer(r'ChartToolButton\s*\{', toolbar)
    ]
    expressions = [re.search(r'enabled:\s*([^\n]+)', declaration) for declaration in declarations]
    assert all(expressions), 'Both actual toggle buttons must bind their enabled state'
    bindings = re.findall(r'(?:readonly )?property (?:bool|int|var) (\w+):\s*([^\n]+)', source)
    setup = ''.join(
        f'Object.defineProperty(chart,{json.dumps(name)},{{get:()=>({expr})}});'
        for name, expr in bindings
        if name in {'available', 'count', 'labels'}
    )
    script = 'const observations=[];'
    script += (
        'for(const correlations of [null,{available:3,labels:["a","b","c"]},'
        '{available:3,labels:[]},{available:3,labels:["a","b","c"]}]){'
    )
    script += 'const chart={correlations};' + setup
    script += (
        'observations.push(['
        + ','.join(f'Boolean({expression[1]})' for expression in expressions)
        + ']);}'
    )
    script += 'process.stdout.write(JSON.stringify(observations));'
    assert evaluate(script) == [[False, False], [True, True], [False, False], [True, True]], (
        'Both toggles must disable whenever no correlations are displayed, including a filter '
        'hiding every pair, and re-enable when pairs return'
    )


def test_colour_scale_visibility_follows_the_actual_names_toggle():
    source, options = source_and_options()
    scale = body(source[source.index('id: colourBar') - len('Item {\n            ') :], 'Item')
    visible = re.search(r'visible:\s*([^\n]+)', scale)
    assert visible, 'The actual colour-scale indicator must have its own visibility binding'
    name, handler = options[0]
    script = f'const chart={{{name}:false}};const seen=[Boolean({visible[1]})];'
    script += handler + f';seen.push(Boolean({visible[1]}));' + handler
    script += f';seen.push(Boolean({visible[1]}));process.stdout.write(JSON.stringify(seen));'
    assert evaluate(script) == [False, True, False], (
        'The colour scale must be hidden by default and show and hide with the actual '
        'tick-label control'
    )

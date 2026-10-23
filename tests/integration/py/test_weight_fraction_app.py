"""Read-only linked-structure display while the app execution tiers are disabled."""

import hashlib
import re
from pathlib import Path

import pytest

from tests.fixtures.table_display import gui_base
from tests.integration.py.test_table_display import run_functions

ROOT = Path(__file__).resolve().parents[3]


def source(path):
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', (ROOT / path).read_text(), flags=re.DOTALL)


def fraction_cell(text):
    start = text.index('EaComponents.ListViewParameter {')
    depth = 0
    for index in range(text.index('{', start), len(text)):
        if text[index] == '{':
            depth += 1
        elif text[index] == '}':
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    pytest.fail('The weight-fraction parameter cell must have a complete QML body')


def check_cell(cell):
    for role in ('value', 'uncertainty'):
        assert re.search(r'row\.weightFraction\.' + role + r'\b', cell), (
            'The parameter cell must consume the live weight-fraction value and uncertainty'
        )
    assert re.search(r'\breadOnly\s*:\s*true\b', cell), (
        'The derived weight-fraction parameter cell must be explicitly read-only'
    )
    for flag in ('fittable', 'fit'):
        assert re.search('"' + flag + r'"\s*:\s*false\b', cell), (
            'The derived weight-fraction cell must never enable fitting'
        )
    assert not re.search(
        r'on(?:Edited|Accepted|ValueChanged|EditingFinished|FitToggled)\s*:', cell
    ), 'Derived weight fractions must have no editing or fitting handler'
    assert 'NumberText.parameter(fractionValue, fractionError)' in cell, (
        'The derived fraction must use the common parameter value display rule'
    )
    assert 'NumberText.error(fractionError, 0, fractionValue)' in cell, (
        'The derived fraction must supply its uncertainty separately for the value menu'
    )
    assert re.search(r'"value"\s*:\s*""', cell), (
        'An unavailable or disabled fraction retains an empty value cell'
    )


def test_linked_structure_table_displays_weight_fraction_without_an_editor():
    text = source('app/qml/Pages/Experiment/LinkedStructureGroup.qml')
    assert re.search(r'qsTr\("[Ww]eight fraction"\)', text), (
        'Linked structures must display a weight fraction column'
    )
    cell = fraction_cell(text)
    check_cell(cell)
    for old, new in (
        ('row.weightFraction.value', '0'),
        ('row.weightFraction.uncertainty', '0'),
        ('readOnly: true', 'readOnly: false'),
        ('"fittable": false', '"fittable": true'),
        ('"fit": false', '"fit": true'),
    ):
        assert old in cell, 'The app escape must reach its real bound role or read-only flag'
        with pytest.raises(AssertionError):
            check_cell(cell.replace(old, new))


def check_fraction_routing(model):
    direct = re.search(
        r'static_cast<int>\(names.indexOf\(id\)\),\s*weight_fraction_cell\(\*link\)', model
    )
    fast_single = (
        re.search(
            r'if\s*\(enabled_links\s*>\s*1\)\s*\{\s*'
            r'return weight_fraction_cell\(link\);\s*\}',
            model,
        )
        and re.search(r'return QVariantMap\(\);\s*\};', model)
        and (
            re.search(
                r'if\s*\(link.enabled.get\(\)\)\s*\{\s*return QVariantMap\{\{'
                r'QStringLiteral\("value"\), 1.0\}',
                model,
            )
            and re.search(r'QStringLiteral\("uncertainty"\), 0.0', model)
            and re.search(r'static_cast<int>\(names.indexOf\(id\)\),\s*fraction\(\*link\)', model)
        )
    )
    assert direct or fast_single, (
        'Enabled rows supply their live fraction or exact single-phase unity without s.u.'
    )


def test_weight_fraction_role_and_menu_preserve_live_uncertainty_and_single_phase_unity():
    model = source('app/src/experiment_models.cpp')
    assert re.search(r'fraction\s*=\s*edi::weight_fraction\(link\)', model), (
        'The app role must obtain the live derived linked-structure result'
    )
    assert re.search(r'QStringLiteral\("value"\)\s*,\s*fraction->value', model), (
        'The weight-fraction role must carry the live derived value'
    )
    assert re.search(r'QStringLiteral\("uncertainty"\)\s*,\s*fraction->uncertainty', model), (
        'The weight-fraction role must carry the live derived uncertainty'
    )
    check_fraction_routing(model)
    if 'fraction(*link)' in model:
        for old, new in (
            ('enabled_links > 1', 'enabled_links > 0'),
            ('link.enabled.get()', 'true'),
            ('QStringLiteral("value"), 1.0', 'QStringLiteral("value"), 0.5'),
            ('QStringLiteral("uncertainty"), 0.0', 'QStringLiteral("uncertainty"), 0.1'),
        ):
            assert old in model, 'Fraction routing escapes must reach their actual model branch'
            with pytest.raises(AssertionError):
                check_fraction_routing(model.replace(old, new))
    cmake = source('cmake/EdiGuiBase.cmake')
    components = cmake[cmake.index('edi_gui_base_module(edi_gui_components') :]
    assert re.search(r'\bListViewParameter\b', components.split('REPLACED')[0]), (
        'The weight-fraction menu ships from the pinned upstream ListViewParameter'
    )
    assert 'ListViewParameter' not in components.split('REPLACED')[1].split(')')[0], (
        'The upstream parameter menu is consumed without a local replacement'
    )
    reference = ROOT / 'tests/fixtures/table_display/ListViewParameter.qml'
    assert hashlib.sha256(reference.read_bytes()).hexdigest() == gui_base.PARAMETER_SHA256, (
        'The menu reference is the byte-exact upstream parameter cell at the pinned revision'
    )
    control = reference.read_text()
    assert 'control.openContextMenu(menuArea)' in control, (
        'The read-only parameter must retain its ordinary value context menu'
    )
    assert re.search(
        r'visible:\s*\(control.fittable\s*\|\|\s*control.readOnly\)\s*&&\s*control.error', control
    ), 'A read-only derived value must show its uncertainty in the context menu'
    assert re.search(r'text:\s*control.error\b', control), (
        'The parameter menu must display the separate uncertainty role'
    )
    assert re.search(r'visible:\s*control.fittable\s*&&\s*!control.readOnly', control), (
        'A read-only value must hide the menu free checkbox'
    )


def test_single_fraction_cell_renders_unity_and_preserves_multiphase_formatting():
    actual = run_functions(
        ROOT / 'app/qml/Globals/NumberText.qml',
        ['parameter', 'error'],
        [{'name': 'fraction', 'args': args} for args in ([1.0, 0], [0.375, 0.012], [None, 0])],
        consumer='fraction',
    )
    assert actual == [
        {'value': '1.0', 'error': ''},
        {'value': '0.38', 'error': '0.01'},
        {'value': '', 'error': ''},
    ], 'The real cell displays 1.0; multiphase s.u. and unavailable cells retain their rules'

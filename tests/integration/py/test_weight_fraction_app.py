"""Read-only linked-structure display while the app execution tiers are disabled."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def source(path):
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', (ROOT / path).read_text(), flags=re.DOTALL)


def fraction_cell(text):
    start = text.index('EaComponents.TableViewParameter {')
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
        'An absent single-phase fraction must display an empty value cell'
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


def test_weight_fraction_role_and_menu_preserve_live_uncertainty_and_single_phase_empty():
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
    assert re.search(
        r'enabled_links\s*>\s*1\s*\?\s*weight_fraction_cell\(\*link\)\s*:\s*QVariantMap\(\)', model
    ), 'The single enabled phase must supply an empty map instead of displaying unity'
    control = source('app/qml/Base/Gui/Components/TableViewParameter.qml')
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

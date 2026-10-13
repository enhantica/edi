"""Read-only linked-structure display while the app execution tiers are disabled."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_linked_structure_table_displays_weight_fraction_without_an_editor():
    text = (ROOT / 'app/qml/Pages/Experiment/LinkedStructureGroup.qml').read_text()
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.DOTALL)
    assert re.search(r'qsTr\("[Ww]eight fraction"\)', text), (
        'Linked structures must display a weight fraction column'
    )
    cells = re.findall(
        r'(?:TableViewLabel|ParameterCell|TextFieldCell)\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', text
    )
    bound = [
        cell
        for cell in cells
        if re.search(r'(?:text|item)\s*:[^\n]*(?:weightFraction|weight_fraction)', cell)
    ]
    assert bound, 'The weight fraction cell must bind the live linked-structure result'
    for cell in bound:
        assert not re.search(r'on(?:Edited|Accepted|ValueChanged|EditingFinished)\s*:', cell), (
            'Derived weight fractions must have no editing handler'
        )
        if re.search(r'\bitem\s*:', cell):
            assert re.search(r'\breadOnly\s*:\s*true\b', cell), (
                'A parameter-style weight-fraction cell must be explicitly read-only'
            )

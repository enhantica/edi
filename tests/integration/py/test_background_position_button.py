"""Supplement the actual Qt actor with a closed declaration check, not a UI claim."""

import re

from tests.integration.py.test_scan_app_contract import block, property_value, source


def test_line_segment_background_exposes_the_position_naming_action():
    qml = source('qml/Pages/Experiment/BackgroundGroup.qml')
    layout = block(qml, 'id: lineSegmentLayout')
    declarations = re.findall(r'EaElements\.SideBarButton\s*\{', layout)
    assert len(declarations) == 3, (
        'Line-segment background must have Append, Reset and Name points by position buttons'
    )
    matches = list(re.finditer(r'text:\s*qsTr\("Name points by position"\)', layout))
    assert len(matches) == 1, 'The point-naming action must use the owner-approved visible label'
    from tests.integration.py.test_scan_app_contract import spans  # noqa: PLC0415

    begin, end = min(
        ((a, b) for a, b in spans(layout) if a < matches[0].start() < b),
        key=lambda span: span[1] - span[0],
    )
    action = layout[begin:end]
    assert property_value(action, 'onClicked').strip(), (
        'The visible point-naming button must bind an actual click action'
    )

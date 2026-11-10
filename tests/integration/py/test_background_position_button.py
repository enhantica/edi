"""Supplement the actual Qt actor with a closed declaration check, not a UI claim."""

import re

from tests.integration.py.test_scan_app_contract import block, property_value, source


def test_line_segment_background_exposes_the_position_naming_action():
    qml = source('qml/Pages/Experiment/BackgroundGroup.qml')
    layout = block(qml, 'id: lineSegmentLayout')
    declarations = re.findall(r'EaElements\.SideBarButton\s*\{', layout)
    assert len(declarations) >= 2, (
        'Line-segment background must retain its point and position-naming actions'
    )
    matches = list(re.finditer(r'objectName:\s*"background.namePoints"', layout))
    assert len(matches) == 1, (
        'The point-naming action must expose stable objectName background.namePoints'
    )
    from tests.integration.py.test_scan_app_contract import spans  # noqa: PLC0415

    begin, end = min(
        ((a, b) for a, b in spans(layout) if a < matches[0].start() < b),
        key=lambda span: span[1] - span[0],
    )
    action = layout[begin:end]
    assert 'Id from position' in property_value(action, 'text'), (
        'The stable point-id action must display the approved singular Id from position label'
    )
    assert property_value(action, 'onClicked').strip(), (
        'The visible point-naming button must bind an actual click action'
    )

    for label, tooltip in (
        ('Add point', 'Append new point'),
        ('Id from position', 'Name points by position'),
        ('Add term', 'Append new term'),
    ):
        hit = re.search(r'text:\s*qsTr\("' + re.escape(label) + r'"\)', qml)
        assert hit is not None, 'Background actions must show the committed shorter owner label'
        a, b = min(
            ((a, b) for a, b in spans(qml) if a < hit.start() < b),
            key=lambda span: span[1] - span[0],
        )
        button = qml[a:b]
        assert tooltip in property_value(button, 'ToolTip.text'), (
            'Short Background labels must retain the full action wording in tooltips'
        )

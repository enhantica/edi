"""All current-row tables share the app's row component (ADR-0015)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PAGES = (
    'Experiment/ExperimentsGroup.qml',
    'Structure/StructuresGroup.qml',
    'Analysis/ParametersGroup.qml',
)


def test_current_row_tables_use_one_shared_local_delegate():
    delegates = []
    for page in PAGES:
        source = (ROOT / 'app/qml/Pages' / page).read_text()
        # Parameters also has a picker delegate; identify the actual table row.
        match = re.search(r'delegate:\s*([\w.]+)\s*\{\s*id:\s*row\b', source)
        assert match, 'Each current-row table must instantiate its actual row delegate'
        delegates.append(match[1])
    assert len(set(delegates)) == 1, (
        'Experiments, Structures and Analysis parameters must use one shared row component'
    )
    assert '.' not in delegates[0], (
        'The current-row appearance belongs to a shared edi component under ADR-0015'
    )
    assert (ROOT / 'app/qml/Components' / (delegates[0] + '.qml')).is_file(), (
        'The shared current-row delegate must exist in the app component module'
    )


def test_current_row_tables_do_not_override_the_ordinary_background():
    for page in PAGES:
        source = (ROOT / 'app/qml/Pages' / page).read_text()
        assert 'EaStyle.Colors.tableHighlight' not in source, (
            'Current rows retain their ordinary alternating background in every table'
        )

"""Exact syntactic regression adaptation; the frozen archive remains the authority.

Run this visible verifier after editing the receipt; it never derives new pins.
"""

import hashlib
import json
import re
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
WITNESS = 'tests/unit/cpp/test_c34_t27_geometry_edit_freshness.cpp'
LINK = '    project.experiment().linked_structure().structure_id = structure.name;\n'
GUI_WITNESS = 'tests/unit/app/tst_c34_t26_equal_gui_writes.qml'
GUI_BEFORE = (
    '        verify(Probe.computedCurrent(experiment),\n'
    '               ": an equal-write witness must start with current computed categories");\n'
)
GUI_AFTER = (
    '        tryVerify(() => Probe.computedCurrent(experiment), 10000,\n'
    '                  "GUI edit: an equal-write witness must await the initial calculation");\n'
)


def tokens(text):
    # Keep string contents and every code token; ignore only comments and whitespace.
    pattern = r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/|\w+|[^\s]'
    return [token for token in re.findall(pattern, text) if not token.startswith(('//', '/*'))]


def adapted_blob(original):
    receipt = json.loads((HERE / 'api_witness_adaptation.json').read_text())
    assert receipt['schema'] == 1 and receipt['witness'] == WITNESS, (
        'the adaptation receipt identifies exactly the retained geometry witness'
    )
    assert hashlib.sha256(original).hexdigest() == receipt['original_sha256'], (
        'the adaptation starts from the independently frozen original bytes'
    )
    before = original.decode()
    after = before
    for replacement in receipt['replacements']:
        assert after.count(replacement['before']) == 1, (
            'each exact syntactic replacement has one unambiguous original site'
        )
        after = after.replace(replacement['before'], replacement['after'], 1)
    assert after.count(LINK) == 1, 'the fixture links exactly once to its own structure name'
    assert tokens(after.replace(LINK, '', 1)) == tokens(before), (
        'every original code token, assertion predicate and message survives the adaptation'
    )
    result = after.encode()
    assert hashlib.sha256(result).hexdigest() == receipt['adapted_sha256'], (
        'the adapted witness matches the fixed syntactic regression receipt'
    )
    return result


def adapted_gui_blob(original):
    receipt = json.loads((HERE / 'api_witness_adaptation.json').read_text())['gui']
    assert receipt['witness'] == GUI_WITNESS, (
        'the bounded-await receipt names exactly the retained equal-write GUI witness'
    )
    assert hashlib.sha256(original).hexdigest() == receipt['original_sha256'], (
        'the bounded-await adaptation starts from the immutable original GUI bytes'
    )
    assert receipt['replacement'] == {'before': GUI_BEFORE, 'after': GUI_AFTER}, (
        'the reviewed GUI adaptation changes only the setup wait and its exact public diagnostic'
    )
    before = original.decode()
    assert before.count(GUI_BEFORE) == 1, (
        'the queued initial-calculation adaptation reaches one original setup assertion'
    )
    result = before.replace(GUI_BEFORE, GUI_AFTER, 1).encode()
    assert hashlib.sha256(result).hexdigest() == receipt['adapted_sha256'], (
        'every other GUI witness byte remains bound to the original archive'
    )
    return result


if __name__ == '__main__':
    root = HERE.parents[2]
    with zipfile.ZipFile(
        root / 'tests/fixtures/e04_t12_public_release/history/api.zip'
    ) as archive:
        for witness, adapt in ((WITNESS, adapted_blob), (GUI_WITNESS, adapted_gui_blob)):
            assert (root / witness).read_bytes() == adapt(archive.read(witness)), (
                'each live witness is precisely its declared immutable-archive adaptation'
            )
    print('Original archive and exact geometry/link and GUI/await adaptations verified')

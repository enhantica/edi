"""Exact declared witness projections; the frozen archive remains the authority.

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


SAVE_WITNESS = 'tests/integration/py/test_c34_t26_live_currentness.py'
SAVE_EDITS = [
    (
        ('import test_c13_t4_march as march\n\n'),
        (
            'import test_c13_t4_march as march\n\nfrom tests.fixtures.'
            'project_save.computed_columns import check as check_com'
            'puted\n\n'
        ),
    ),
    (
        ("    original = (source / 'experiments/experiment.edi').read_text()\n"),
        (
            "    original = (source / 'experiments/experiment.edi')."
            'read_text()\n    # The same zero background is explicit '
            'so the independent interpolation\n    # reference reache'
            's authored anchors, without changing the Bragg witness.'
            "\n    original += (\n        '\\n_background.type line-seg"
            "ment\\nloop_\\n_background.id\\n'\n        '_background.pos"
            "ition\\n_background.intensity\\n'\n        'left 0 0\\nrigh"
            "t 180 0\\n'\n    )\n    (source / 'experiments/experiment."
            "edi').write_text(original)\n"
        ),
    ),
    (
        (
            "    assert '_data.intensity_calc' not in edited_file an"
            "d '_refln.index_h' not in edited_file, (\n        ' a st"
            "ale bank is omitted if saved before a non-UI read'\n    "
            ')\n'
        ),
        (
            "    assert '_data.intensity_calc' in edited_file and '_"
            "refln.index_h' in edited_file, (\n        'Save renews a"
            ' held stale bank from its own saved inputs before a non'
            "-UI read'\n    )\n    check_computed(destination, edi)\n"
        ),
    ),
    (
        (
            "    assert '_data.intensity_calc' not in saved_text(pro"
            "ject, tmp_path / route), (\n        ' an equal write sta"
            "les a computed unit before any read'\n    )\n"
        ),
        (
            "    assert '_data.intensity_calc' in saved_text(project"
            ", tmp_path / route), (\n        'Save renews held result"
            's after an equal dependency write before any non-UI rea'
            "d'\n    )\n    check_computed(tmp_path / route / 'saved',"
            ' edi)\n'
        ),
    ),
]


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


def adapted_save_blob(original):
    receipt = json.loads((HERE / 'api_witness_adaptation.json').read_text())['save']
    assert (
        receipt['kind'] == 'save-held-results-current-contract'
        and receipt['witness'] == SAVE_WITNESS
    ), 'The Save projection names only the original held-result currentness witness'
    assert hashlib.sha256(original).hexdigest() == receipt['original_sha256'], (
        'Save contract adaptation starts from its unchanged independent archived source'
    )
    assert receipt['replacements'] == [
        {'before': before, 'after': after} for before, after in SAVE_EDITS
    ], 'Save allows only declared renewal assertions, independent verification and zero anchors'
    result = original.decode()
    for before, after in SAVE_EDITS:
        assert result.count(before) == 1, (
            'Each authorized Save adaptation reaches one original site'
        )
        result = result.replace(before, after, 1)
    projected = result.encode()
    assert hashlib.sha256(projected).hexdigest() == receipt['adapted_sha256'], (
        'Every other original currentness witness byte remains bound to its archive'
    )
    return projected


if __name__ == '__main__':
    root = HERE.parents[2]
    with zipfile.ZipFile(
        root / 'tests/fixtures/e04_t12_public_release/history/api.zip'
    ) as archive:
        for witness, adapt in (
            (WITNESS, adapted_blob),
            (GUI_WITNESS, adapted_gui_blob),
            (SAVE_WITNESS, adapted_save_blob),
        ):
            assert (root / witness).read_bytes() == adapt(archive.read(witness)), (
                'each live witness is precisely its declared immutable-archive adaptation'
            )
    print('Original archive and all declared witness projections verified')

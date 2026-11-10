"""Operation boundaries own their writes, decisions and held-value publication."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.system.py import test_tutorial_project_ownership as ownership
from tests.system.py.test_save_policy_continuations import ROUTES

tutorial_observer = ownership.tutorial_observer
ROOT = Path(__file__).resolve().parents[3]


def operation(binary, tmp_path, group, dataset='scan'):
    corpus = Path(
        os.environ.get('EDI_CRYSTA_CORPUS_ROOT', ROOT / 'build/crysta-src/tests/fitting')
    )
    cases = {
        'scan': 'cosio-d20-scan-3f',
        'powder': 'lbco-hrpt-s2',
        'single-crystal': 'single-crystal-senju-taurine-converged',
    }
    source = corpus / cases[dataset] / 'project'
    assert source.is_dir(), (
        'Operation observations retain their independently saved scientific inputs'
    )
    result = subprocess.run(
        [binary, str(source), group],
        capture_output=True,
        text=True,
        timeout=25,
        check=False,
        env={
            **os.environ,
            'QT_QPA_PLATFORM': 'offscreen',
            'QT_QUICK_BACKEND': 'software',
            'TMPDIR': str(tmp_path),
            'EDI_ONLINE_SOURCES': f'cod={tmp_path.as_uri()};easydiffraction={tmp_path.as_uri()}',
        },
    )
    (tmp_path / 'observation.log').write_text(result.stdout + result.stderr)
    assert result.returncode == 0, (
        'The actual operation must reach its owned asynchronous or publication boundary: '
        + result.stderr
    )
    rows = json.loads(result.stdout.splitlines()[-1])
    assert len(rows) == 1, 'One observation belongs to exactly one declared operation accident'
    return rows[0]


@pytest.mark.parametrize('kind', ['stage', 'save'])
@pytest.mark.parametrize('order', ['old-first', 'new-first', 'without-successor'])
@pytest.mark.parametrize('ending', ['success', 'failure'])
def test_stale_operation_cannot_write_or_report_after_source_replacement(
    tutorial_observer, tmp_path, order, ending, kind
):
    row = operation(tutorial_observer, tmp_path, f'operation-files/{kind}/{order}/{ending}')
    if order == 'without-successor':
        assert (row['oldReports'], row['oldWriteCalls'], row['oldFilesUnchanged']) == (
            0,
            0,
            True,
        ), 'Cancellation alone forbids a late write or reply even without a successor request'
        return
    assert row['distinctRequests'], (
        'Separately admitted operations own distinct request identities'
    )
    assert (
        row['oldReports'],
        row['oldWriteCalls'],
        row['oldFilesUnchanged'],
        row['currentBytes'],
    ) == (0, 0, True, True), (
        'A canceled operation reports nothing, writes no file and preserves current input bytes'
    )
    assert row['currentReports'] == 1, (
        'The current operation publishes exactly its own successful outcome'
    )
    assert row['currentBytes'], (
        'Reversed old completions cannot replace any accepted current input bytes'
    )
    assert row['laterLoad'], (
        'The current operation keeps its actual staged files alive for a later real loader'
    )


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('owner', ['same', 'replacement'])
def test_reentrant_save_has_its_own_decision_instead_of_inheriting_call_depth(
    tutorial_observer, tmp_path, route, owner
):
    row = operation(tutorial_observer, tmp_path, f'operation-save/{route}/{owner}')
    assert row['entered'], (
        'The accident reaches a real direct model notification during the outer save'
    )
    if not row['replacementAdmitted']:
        assert not row['innerPrepared'], (
            'A refused replacement admits no save of a successor owner'
        )
        return
    assert row['questions'] == 1 or row['innerRefused'], (
        'A nested unrelated save must make its own decision or refuse before preparation'
    )
    assert not row['innerPrepared'], (
        'An independent Ask never publishes; a refused admission never prepares '
        'under the outer choice'
    )
    assert row['innerUnchanged'], (
        'Cancel or refusal leaves the original nested destination bytes unchanged'
    )
    assert row['sourceBytesUnchanged'], (
        'Neither operation changes the original independent measured source'
    )
    if row['outerPublished']:
        assert row['outerLinked'], (
            'A surviving outer writer uses its own frozen linked-data decision'
        )


@pytest.mark.parametrize('dataset', ['powder', 'single-crystal', 'scan'])
@pytest.mark.parametrize('completion', ['release-settled', 'release-busy'])
def test_held_value_has_no_change_listeners_until_one_release(
    tutorial_observer, tmp_path, dataset, completion
):
    row = operation(tutorial_observer, tmp_path, 'operation-held/' + completion, dataset)
    for index, step in enumerate(row['steps']):
        assert step['project'] == 0, (
            'Only calculation lifecycle signals may invoke project listeners during a held step'
        )
        assert step['fields'] == 0, (
            'No parameter change signal invokes any listener while its value is held'
        )
        assert step['general'] == 0, (
            'A chart-only held calculation never emits the general recalculated signal'
        )
        assert step['edits'] == 0, 'A held value never publishes save or assistant edit work'
        assert step['tables'] == 0, (
            'Held chart updates never republish or sort the reflection table'
        )
        if index < 2 or completion == 'release-settled':
            assert step['charted'], (
                'Each completed held calculation still updates its actual chart source'
            )
    if completion == 'release-busy':
        assert row['steps'][-1]['busy'], (
            'The busy-release witness releases before its actual calculation completes'
        )
    assert row['releaseChanges'] == 1, (
        'The selected value publishes one change after the complete held operation'
    )
    assert row['releaseGeneral'] == 1, (
        'The settled or busy release has one deferred general publication'
    )
    assert row['releaseEdits'] == 1, 'The release publishes one complete edit operation'
    assert row['finalValue'], (
        'The final published value is the independently specified nontrivial stimulus'
    )
    assert row['oneUndo'], 'One Undo reverses the whole held operation rather than its last step'

"""Save decisions describe one immutable scientific state and external inventory."""

import pytest

from tests.system.py import test_save_policy_continuations as policy

ROUTES = policy.ROUTES
tutorial_observer = policy.tutorial_observer

MUTATIONS = ('model', 'same-size', 'add-file', 'remove-file')
PICKERS = ('web-folder', 'web-zip', 'web-copy')
CASES = (
    [(route, 'question', mutation) for route in ROUTES for mutation in MUTATIONS]
    + [(route, 'picker', mutation) for route in PICKERS for mutation in MUTATIONS]
    + [
        (route, boundary, 'grow-large')
        for route, boundary in (
            ('save', 'question'),
            ('fresh-copy-folder', 'question'),
            ('fresh-zip', 'question'),
            ('web-folder', 'picker'),
        )
    ]
)


@pytest.mark.parametrize(('route', 'boundary', 'mutation'), CASES)
def test_every_save_writes_its_planned_snapshot_or_replans(
    tutorial_observer, tmp_path, route, boundary, mutation
):
    row = policy.observe(
        tutorial_observer, tmp_path, f'snapshot-save/{route}/{boundary}/{mutation}'
    )
    assert row['sourceUnchangedBySave'], (
        'Resuming a save never changes external measurements beyond the explicit fixture mutation'
    )
    assert not row['publishedBeforeReplan'], (
        'A changed inventory cannot publish under the previous decision before a fresh question'
    )
    if not row['published']:
        assert row['replanned'] or row['error'], (
            'An interrupted operation either makes a new decision or explicitly refuses its write'
        )
        return
    written = row['written']
    assert written, 'An accepted publication reaches its actual core writer with a readable model'
    original = (
        written['description'] == 'Independent planned state A'
        and written['lengthA'] == pytest.approx(10.3, rel=0, abs=1e-12)
        and written['hashes'] == row['hashesA']
    )
    if original:
        return
    assert row['replanned'], (
        'Changed scientific state or measured bytes require a new operation decision'
    )
    expected_description = (
        'Independent live state B' if mutation == 'model' else 'Independent planned state A'
    )
    assert written['description'] == expected_description, (
        'A replanned output retains the independently authored current project metadata'
    )
    expected_lattice = 10.4 if mutation == 'model' else 10.3
    assert written['lengthA'] == pytest.approx(expected_lattice, rel=0, abs=1e-12), (
        'A replanned output retains the current independent scientific lattice value'
    )
    assert written['hashes'] == row['hashesB'], (
        'A replanned model writes the same successor inventory described by its new decision'
    )
    if mutation == 'grow-large':
        assert row['warned'], 'A newly large payload cannot bypass its own large-save warning'

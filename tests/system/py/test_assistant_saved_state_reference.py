# SPDX-License-Identifier: BSD-3-Clause
"""Assertions over shared recorded turns and independent ordinary-control references."""

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    'assistant_reference_replay', Path(__file__).with_name('assistant_reference_replay.py')
)
REPLAY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPLAY)


@pytest.fixture(scope='module', params=[False, True], ids=['normal', 'shown'])
def saved_state(tmp_path_factory, request):
    with pytest.MonkeyPatch.context() as patch:
        return REPLAY.saved_state(tmp_path_factory.mktemp('saved-state'), patch, request.param)


@pytest.fixture(scope='module', params=[False, True], ids=['normal', 'shown'])
def relation_state(tmp_path_factory, request):
    with pytest.MonkeyPatch.context() as patch:
        return REPLAY.relation_state(
            tmp_path_factory.mktemp('relation-state'), patch, request.param
        )


@pytest.fixture(scope='module')
def working_state(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:
        return REPLAY.working_state(tmp_path_factory.mktemp('working-state'), patch)


@pytest.fixture(scope='module')
def skill_state(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:
        return REPLAY.skill_state(tmp_path_factory.mktemp('skill-state'), patch)


def test_fitted_assistant_save_equals_ordinary_save(saved_state):
    assert saved_state['delegated'] and saved_state['manual_saved'], (
        'Both delegated Save and ordinary Save Copy must publish scientific files'
    )
    assert saved_state['delegated'] == saved_state['ordinary'], (
        'The delegated disk project must equal the ordinary Save of its fitted state'
    )


def test_assistant_followup_fit_and_save_complete(saved_state):
    assert saved_state['replies'][2].get('adopted') and saved_state['replies'][3].get(
        'committed'
    ), 'A recorded assistant fit must adopt a native result and commit its follow-up Save'


def test_assistant_freed_tch_coefficient_remains_free_after_fit(saved_state):
    assert saved_state['free'], (
        'A TCH coefficient freed by the assistant must remain free after its native fit'
    )


def test_delegated_relation_matches_manual_relations_control(relation_state):
    assert relation_state['manual_fit'], (
        'The ordinary manual fit must adopt a result before its constraint effect is compared'
    )
    assert relation_state['initial'] == {'La': 1.25, 'Ba': 2.75}, (
        'The relation witness must begin with independently specified unequal displacements'
    )
    assert (
        relation_state['manual_values']['La'] == relation_state['manual_values']['Ba'] == 2.75
    ), 'The ordinary Relations control must apply La = Ba to the nontrivial seeded values'
    assert relation_state['actual'] == relation_state['manual'], (
        'The relation tool must retain the equality added with the ordinary Relations controls'
    )


def test_relation_refit_adopts_and_satisfies_shared_site_equality(relation_state):
    assert relation_state['replies'][1].get('adopted'), (
        'The shared-site relation must permit an adopted native fit'
    )
    values = relation_state['values']
    assert values['La'] == pytest.approx(
        relation_state['manual_values']['La'], abs=1e-10
    ) and values['Ba'] == pytest.approx(relation_state['manual_values']['Ba'], abs=1e-10), (
        'The refitted shared-site displacements must satisfy their declared equality'
    )


def test_show_actions_keeps_working_indicator_throughout_turn(working_state):
    assert len(working_state['samples']) == 3 and all(working_state['samples']), (
        'Show actions must keep the working indicator visible at every held-turn observation'
    )


def test_recorded_working_turn_reaches_completion(working_state):
    assert working_state['settled'], 'The held recorded turn must reach ordinary idle completion'


def test_skill_targets_exist_in_running_object_tree(skill_state):
    assert skill_state['targets'] <= skill_state['found'], (
        'Every declared skill target must exist in the current app and Load menus; missing: '
        + str(sorted(skill_state['targets'] - skill_state['found']))
    )

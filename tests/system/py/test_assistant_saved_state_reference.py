# SPDX-License-Identifier: BSD-3-Clause
"""Assertions over shared recorded turns and independent ordinary-control references."""

import importlib.util
import re
import shutil
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


def check_indicator(working_state):
    samples = working_state['samples']
    assert not working_state['overflow'], 'The temporal indicator witness must retain every sample'
    assert working_state['adopted'], 'The indicator witness must reach an adopted native fit'
    assert {
        'before-action',
        'between-action-and-fit',
        'after-adoption',
        'final-held',
        'completion-held',
        'completion',
    } <= {row['phase'] for row in samples}, (
        'The indicator witness must reach each held phase around actions and adoption'
    )
    phases = [row['phase'] for row in samples]
    assert (
        phases.index('final-held') < phases.index('completion-held') < phases.index('completion')
    ), 'The retained trace must span final response delivery through the terminal boundary'
    assert any(row['phase'] == 'completion-held' and row['active'] for row in samples) and any(
        row['phase'] == 'completion' and not row['active'] for row in samples
    ), 'The completion suffix must include the still-active hold and observed terminal state'
    assert any(row['fitting'] for row in samples), (
        'The indicator witness must observe the actual running native fit'
    )
    assert any(row['phase'] == 'action-pointer-pressed' for row in samples), (
        'The indicator witness must reach the shown action transition'
    )
    active = [row for row in samples if row['active']]
    assert active and all(
        row['visible'] and row['working'] and row['animating'] and row['text'] for row in active
    ), (
        'Show actions must keep the working indicator visible through every active action, '
        'native operation, adoption and held-phase observation'
    )


def test_show_actions_keeps_working_indicator_throughout_turn(working_state):
    check_indicator(working_state)


@pytest.mark.parametrize('phase', ['intermediate', 'completion'])
def test_intermediate_indicator_loss_fails_despite_a_correct_final_phase(
    tmp_path, monkeypatch, phase
):
    state = REPLAY.working_state(
        tmp_path,
        monkeypatch,
        intermediate_fault=phase == 'intermediate',
        completion_fault=phase == 'completion',
    )
    final = [row for row in state['samples'] if row['phase'] == 'final-held']
    assert final and all(row['visible'] for row in final), (
        'The intermediate-loss control must leave the final held indicator correct'
    )
    with pytest.raises(AssertionError, match='keep the working indicator visible'):
        check_indicator(state)


def test_recorded_working_turn_reaches_completion(working_state):
    assert working_state['settled'], 'The held recorded turn must reach ordinary idle completion'


@pytest.mark.parametrize(
    'guide',
    sorted(
        path.parent.name for path in (REPLAY.ROOT / 'data/assistant/skills').glob('*/SKILL.md')
    ),
)
def test_every_skill_replays_its_ordered_gui_steps(tmp_path, monkeypatch, guide):
    skill_state = REPLAY.skill_state(tmp_path, monkeypatch, only_guide=guide)
    assert skill_state and all(
        result['workflows']
        and result['steps']
        and all(row['completed'] for row in result['workflows'])
        and all(row['reachable'] for row in result['steps'])
        for result in skill_state.values()
    ), 'Every skill must execute nonempty ordered GUI steps and verify their resulting state'


@pytest.mark.parametrize('fault', ['missing', 'disabled', 'reordered'])
def test_unusable_skill_steps_fail_the_same_running_app_replay(tmp_path, monkeypatch, fault):
    guides = tmp_path / 'guides'
    shutil.copytree(REPLAY.ROOT / 'data/assistant/skills', guides)
    guide = guides / 'project-assistance/SKILL.md'
    text = guide.read_text(encoding='utf-8')
    if fault == 'missing':
        text = text.replace('ui:experiments.create', 'ui:independent.absent.skill.target')
    elif fault == 'reordered':
        text = text.replace('ui:experiments.create', 'ui:temporary-skill-placeholder')
        text = text.replace('ui:experiments.load.dataFile', 'ui:experiments.create')
        text = text.replace('ui:temporary-skill-placeholder', 'ui:experiments.load.dataFile')
    guide.write_text(text, encoding='utf-8')
    expected = {
        'missing': 'independent.absent.skill.target',
        'disabled': 'experiments.create',
        'reordered': 'experiments.load.dataFile',
    }[fault]
    with pytest.raises(
        AssertionError, match=re.escape('skill step is not reachable: ' + expected)
    ):
        REPLAY.skill_state(
            tmp_path,
            monkeypatch,
            guides=guides,
            only_guide='project-assistance',
            disabled=fault == 'disabled',
        )


def test_removing_all_skill_annotations_cannot_make_the_inventory_vacuous(tmp_path):
    guides = tmp_path / 'guides'
    shutil.copytree(REPLAY.ROOT / 'data/assistant/skills', guides)
    for guide in guides.glob('*/SKILL.md'):
        guide.write_text(
            re.sub(r'\bui:[A-Za-z0-9_.-]+', '', guide.read_text(encoding='utf-8')),
            encoding='utf-8',
        )
    with pytest.raises(AssertionError, match='ordered replay role'):
        REPLAY.skill_reference().inventory(guides)

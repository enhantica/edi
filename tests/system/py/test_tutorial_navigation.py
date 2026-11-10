"""Real Home entry, rendered callouts and user-driven written tutorial navigation."""

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = json.loads((ROOT / 'app/tutorials/manifest.json').read_text())['tutorials']
TOUR = next(tutorial for tutorial in MANIFEST if tutorial['id'] == 'interface')
# Accept inline and page-organised scripts; these enumerate the content under
# test, while real controls and scene geometry supply the independent census.
STEPS = TOUR.get('steps')
if STEPS is None:
    PAGES = json.loads((ROOT / 'app/tutorials' / TOUR['tour']).read_text())['pages']
    STEPS = [dict(step, page=page['page']) for page in PAGES for step in page['steps']]
LESSONS = [
    tutorial
    for tutorial in json.loads((ROOT / 'app/tutorials/manifest.json').read_text())['tutorials']
    if tutorial['id'] not in {'interface', 'simulation', 'fitting'}
]
CASES = [
    *[f'callout_vertical_margins_measure_visible_ink:{theme}' for theme in ('light', 'dark')],
    *[
        f'step_text_uses_unfolded_group_colour:{theme}-{place}'
        for theme in ('light', 'dark')
        for place in ('callout', 'status')
    ],
    'rightmost_strip_does_not_move_when_fit_status_appears',
    *[
        f'last_step_keeps_next_visible_and_disabled:{lesson}'
        for lesson in ('interface', 'pd-neut-cwl_lbco_simulation', 'pd-neut-cwl_lbco-hrpt')
    ],
    *[
        f'project_name_next_preserves_input_then_targets_ok:{lesson}-{typed}'
        for lesson in ('pd-neut-cwl_lbco_simulation', 'pd-neut-cwl_lbco-hrpt')
        for typed in ('empty', 'dew')
    ],
    *[
        f'each_step_shows_its_short_heading_and_tutorial_identity:{lesson}'
        for lesson in ('interface', 'pd-neut-cwl_lbco_simulation', 'pd-neut-cwl_lbco-hrpt')
    ],
    'back_never_replays_an_already_satisfied_action:pd-neut-cwl_lbco_simulation',
    'back_never_replays_an_already_satisfied_action:pd-neut-cwl_lbco-hrpt',
    'tour_next_runs_fit_before_results_pattern_and_correlations',
    'navigation_chevron_ink_is_centred:callout',
    'navigation_chevron_ink_is_centred:status',
    *[
        f'named_parameter_rows_survive_view_changes:{lesson}-{mode}'
        for lesson in ('interface', 'pd-neut-cwl_lbco_simulation', 'pd-neut-cwl_lbco-hrpt')
        for mode in (
            'all-ascending',
            'all-descending',
            'filtered-ascending',
            'filtered-descending',
        )
    ],
    'tour_groups_and_tabs_follow_live_layout_order',
    'pointer_directions_have_one_size_and_never_enter_the_target',
    *[
        f'last_step_choices_name_the_actual_project:{lesson}-{str(prior).lower()}-{action}'
        for lesson in ('interface', 'pd-neut-cwl_lbco_simulation', 'pd-neut-cwl_lbco-hrpt')
        for prior in (False, True)
        for action in ('keep', 'return', 'stop')
    ],
    *[
        f'manual_project_name_preserves_the_callout_and_context:{lesson}'
        for lesson in ('pd-neut-cwl_lbco_simulation', 'pd-neut-cwl_lbco-hrpt')
    ],
    *[
        f'each_step_fades_out_before_context_and_in_after_settling:{index + 1}-{step["target"]}'
        for (index, step) in enumerate(STEPS)
    ],
    *[
        f'scientific_lessons_begin_with_user_project_creation:{lesson}-{ending}'
        for lesson in ('pd-neut-cwl_lbco_simulation', 'pd-neut-cwl_lbco-hrpt')
        for ending in ('stop', 'last')
    ],
    *[
        f'status_strip_stays_fixed_and_drives_the_same_tutorial:{lesson}-{ending}'
        for lesson in ('interface', 'pd-neut-cwl_lbco_simulation', 'pd-neut-cwl_lbco-hrpt')
        for ending in ('stop', 'last')
    ],
    *[
        f'all_lesson_pointers_keep_one_size_and_touch_the_target:{lesson}'
        for lesson in ('interface', 'pd-neut-cwl_lbco_simulation', 'pd-neut-cwl_lbco-hrpt')
    ],
    'tour_table_lifecycle_emits_no_qml_runtime_errors',
    *[f'every_tour_step_restores_context:{mode}' for mode in ('forward', 'backward', 'direct')],
    'each_step_scrolls_only_to_the_nearest_visible_edge',
    'every_live_sidebar_group_has_a_tour_step',
    'analysis_order_and_every_filter_control_are_explained',
    'arrow_keys_navigate_and_escape_stops',
    'progress_is_at_the_step_title_right',
    'callout_is_one_opaque_curve_outline',
    'project_text_apply_is_explained_exactly_once',
    'disabled_tabs_have_exact_text_and_enabled_tabs_are_specific',
    'tutorial_filters_reuse_examples_component',
    'tutorial_search_filters_text_tags_and_counts',
    'tutorial_every_category_value_filters_rows_and_counts',
    *[
        f'tutorial_rows_reuse_examples_and_table_actions:{tutorial}-{fraction}'
        for tutorial in ('interface', 'pd-neut-cwl_lbco_simulation', 'pd-neut-cwl_lbco-hrpt')
        for fraction in ('0.05', '0.5', '0.95')
    ],
    *[
        f'parameter_status_splits_only_measured_projects:{kind}'
        for kind in ('simulation', 'measured')
    ],
    *[
        f'real_action_advances_without_next:{action}'
        for action in ('create-experiment', 'automatic-background')
    ],
    *[
        f'explanation_waits_for_next:{tutorial}'
        for tutorial in ('interface', 'pd-neut-cwl_lbco_simulation', 'pd-neut-cwl_lbco-hrpt')
    ],
    *[
        f'{case}:{lesson["id"]}-{index + 1}'
        for case in (
            'field_has_an_explicit_group_and_tab_predecessor',
            'field_pointer_aims_at_the_input_center',
        )
        for lesson in (
            [*LESSONS, {**TOUR, 'steps': STEPS}]
            if case == 'field_pointer_aims_at_the_input_center'
            else LESSONS
        )
        for (index, step) in enumerate(lesson['steps'])
        if not re.search(
            r'^(appBar|workflow|mainArea|statusBar|group|sideBar)\.|freeHeader$', step['target']
        )
        and (
            case != 'field_pointer_aims_at_the_input_center'
            or not re.search(r'\.(create|append|estimate|clearFilters|apply)$', step['target'])
        )
    ],
    *[f'callout_uses_readable_opaque_accent_blue:{theme}' for theme in ('light', 'dark')],
    *[
        f'{case}:{index + 1}-{step["target"]}'
        for case in (
            'callout_is_next_to_its_named_control',
            'pointer_faces_and_reaches_the_named_control',
            'elapsed_time_never_advances_the_tour',
            'tour_omits_expected_state_lines',
        )
        for (index, step) in enumerate(STEPS)
    ],
    *[
        f'{case}:{tutorial}'
        for case in ('lesson_starts_without_a_state_hint',)
        for tutorial in ('pd-neut-cwl_lbco_simulation', 'pd-neut-cwl_lbco-hrpt')
    ],
    *[
        f'every_page_tab_and_group_has_an_anchored_tour_step:{page}-{kind}'
        for page in ('project', 'structure', 'experiment', 'analysis', 'report')
        for kind in ('appbar', 'main', 'sidebar', 'groups')
    ],
    *[f'tour_preserves_the_set_aside_project:{ending}' for ending in ('stop', 'finish')],
    'navigation_uses_icon_buttons_with_tooltips',
    'invisible_target_has_an_explained_panel_fallback',
    'tour_visits_every_workflow_page',
    'next_advances_after_each_stated_state:interface',
]


@pytest.mark.parametrize('case', CASES)
def test_written_tutorial_navigation(case):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Tutorial navigation requires the actual production Qt host'
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_tutorial_navigation.qml'),
            '-o',
            '-,txt',
            f'TutorialNavigation::test_{case}',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=180 if case.startswith(('next_alone_', 'live_lesson_')) else 45,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, (
        'The real written tutorial must satisfy its navigation requirement: ' + output
    )
    function, _, tag = case.partition(':')
    assert f'::TutorialNavigation::test_{function}({tag})' in output and '0 failed' in output, (
        'The selected real-host tutorial gate must execute to completion: ' + output
    )
    assert not any(line.startswith('SKIP') for line in output.splitlines()), (
        'Tutorial navigation cannot be replaced with a skipped host case'
    )


@pytest.mark.parametrize('tutorial', ['pd-neut-cwl_lbco_simulation', 'pd-neut-cwl_lbco-hrpt'])
def test_each_page_transition_has_an_explicit_app_bar_predecessor(tutorial):
    # Class: an implicit page switch hides the result before the learner can see it.
    steps = next(lesson['steps'] for lesson in LESSONS if lesson['id'] == tutorial)
    transitions = 0
    for previous, current in zip(steps, steps[1:], strict=False):
        if current['page'] == previous['page']:
            continue
        transitions += 1
        home_entry = (
            previous['page'] == 'home'
            and previous['target'] == 'home.start'
            and current['page'] == 'project'
        )
        assert home_entry or previous['target'] == 'appBar.tab.' + current['page'], (
            'Home Start enters Project; every later page change has a visible destination '
            'app-bar action: ' + tutorial + ': ' + previous['target'] + ' -> ' + current['page']
        )
    assert transitions > 0, 'Each scientific lesson exercises actual changes between app pages'

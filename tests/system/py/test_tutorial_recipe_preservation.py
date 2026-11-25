"""Declared docs actions survive translation and actual pre-fit model state."""

import copy
import hashlib
import importlib.util
import json
import os
import sys
import time
import uuid
from pathlib import Path

import pytest

from tests.fixtures.tutorial_cases.notebook_fit import local_collection
from tests.fixtures.tutorial_recipe.native import (
    native_progress,
    native_records,
    run_native_observation,
)
from tests.fixtures.tutorial_recipe.reference import (
    boundary_contracts,
    recipe_action_error,
    significant,
    state_errors,
)

ROOT = Path(__file__).resolve().parents[3]
RECIPES = json.loads((ROOT / 'tests/fixtures/tutorial_recipe/recipes.json').read_text())


def load_translator():
    sys.path.insert(0, str(ROOT / 'tools/docs'))
    spec = importlib.util.spec_from_file_location(
        'recipe_translation_subject', ROOT / 'tools/docs/app_builtin_tutorials.py'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def translator():
    module = load_translator()
    # Loading each complete source/caption plan is a shared precondition for all
    # translation and mutation probes. Keep failures per case so one published
    # recipe cannot disable controls for every other tutorial.
    module.published_recipe_baselines = {}
    for case in RECIPES:
        try:
            module.published_recipe_baselines[case] = module.tutorial_steps(case)
        except (ValueError, RuntimeError, SystemExit) as error:
            module.published_recipe_baselines[case] = error
    return module


@pytest.fixture
def captions(translator, case):
    source = (ROOT / 'docs/user/tutorials' / (case + '.py')).read_text()
    # Action mutation tests hold presentation constant. Captions are independent
    # fixed fixture input, not a second invocation of the production prose parser.
    declared = {
        index: (title, 'Apply the declared recipe actions.')
        for index, (title, _paths) in enumerate(RECIPES[case]['fits'], 1)
    }
    # This identity guard follows the producer's syntax transport only; scientific
    # populations and mutation expectations remain the independently frozen recipe.
    return {case: (translator.unrolled(source), declared)}


def unchanged_captions(captions):
    def read(case, source):
        assert source == captions[case][0], (
            'Only identical normalized source is reused while independent recipe actions change'
        )
        return copy.deepcopy(captions[case][1])

    return read


@pytest.mark.parametrize('case', RECIPES)
def test_current_published_recipe_translates_without_a_caption_substitute(case, translator):
    baseline = translator.published_recipe_baselines[case]
    if isinstance(baseline, BaseException):
        raise baseline
    assert baseline, (
        'The complete current published recipe must translate with its actual source captions; '
        'the independent action-mutation fixture cannot conceal a production caption failure'
    )
    # The frozen docs recipe addresses the Python model. The learner types the
    # saved name of that same Co1 row in the GUI (2026-11-24 owner decision).
    source_filter = 'fill:parameters.nameFilter=structure.atom_sites[Co1].adp_iso'
    if any(source_filter in step['actions'] for step in RECIPES[case]['plan']['steps']):
        expected = 'cosio.atom_site.Co1.adp_iso'
        checks = [
            step
            for step in baseline
            if step.get('target') == 'parameters.nameFilter'
            and step.get('check', '').startswith('field:')
        ]
        assert any(
            step['check'] == f'field:parameters.nameFilter={expected}'
            and f'**{expected}**' in step['text']
            for step in checks
        ), 'The GUI lesson displays and checks the saved name of the independent Co1 parameter'
        assert all(source_filter[5:] not in step['check'] for step in checks), (
            'The GUI name filter rejects the frozen Python-path spelling as a lesson instruction'
        )


@pytest.mark.parametrize('case', RECIPES)
def test_every_declared_scientific_action_affects_translation_or_is_refused(
    case, translator, captions, monkeypatch
):
    monkeypatch.setattr(translator, 'stage_texts', unchanged_captions(captions))
    recipe = RECIPES[case]['plan']
    monkeypatch.setattr(translator, 'plan', lambda _case: copy.deepcopy(recipe))
    baseline = translator.tutorial_steps(case)

    def translate(changed):
        monkeypatch.setattr(translator, 'plan', lambda _case: copy.deepcopy(changed))
        return translator.tutorial_steps(case)

    ignored = []
    for index, item in enumerate(recipe['steps']):
        for action_index, action in enumerate(item['actions']):
            if not significant(item, action):
                continue
            error = recipe_action_error(translate, baseline, recipe, index, action_index)
            if error:
                ignored.append((item['id'], action, error))
    assert not ignored, (
        'Scientific actions change translation, consume their exact literal target/value, '
        'or are refused: ' + repr(ignored)
    )


@pytest.mark.parametrize('case', RECIPES)
def test_unknown_recipe_action_is_refused_before_generation(
    case, translator, captions, monkeypatch
):
    monkeypatch.setattr(translator, 'stage_texts', unchanged_captions(captions))
    recipe = copy.deepcopy(RECIPES[case]['plan'])
    monkeypatch.setattr(translator, 'plan', lambda _case: copy.deepcopy(recipe))
    assert translator.tutorial_steps(case), (
        'The valid recipe must translate before its injected unknown action is exercised'
    )
    damaged = copy.deepcopy(recipe)
    damaged['steps'][-1]['actions'].append('unsupported:recipe_action_probe')
    monkeypatch.setattr(translator, 'plan', lambda _case: damaged)
    with pytest.raises(
        (ValueError, RuntimeError, SystemExit), match=r'(?i)action|recipe|translat'
    ):
        translator.tutorial_steps(case)


def test_native_record_reader_keeps_diagnostic_bytes_outside_the_scientific_transport():
    raw = b'Qt comparison: \xb7\nTUTORIAL_RECIPE_BOUNDARY {"id":"control","stage":3}\n'
    assert native_records(raw, 'TUTORIAL_RECIPE_BOUNDARY') == [{'id': 'control', 'stage': 3}], (
        'Non-UTF8 Qt failure diagnostics cannot disable separately valid scientific JSON records'
    )
    with pytest.raises(UnicodeDecodeError):
        native_records(b'TUTORIAL_RECIPE_BOUNDARY {"id":"\xb7"}\n', 'TUTORIAL_RECIPE_BOUNDARY')


def observe_states(tmp_path_factory, wanted):
    assert wanted <= set(RECIPES), (
        'Native recipe selection contains only declared independent cases'
    )
    runner = Path(
        os.environ.get(
            'EDI_APP_TEST_RUNNER',
            ROOT / 'build/app/app' / ('edi_app_tests' + ('.exe' if os.name == 'nt' else '')),
        )
    )
    assert runner.is_file(), 'Recipe boundary observation requires the actual Qt app test host'
    folder = tmp_path_factory.mktemp('tutorial-recipe-state')
    collection = local_collection(folder / 'collection')
    env = {
        **os.environ,
        'QT_QPA_PLATFORM': 'offscreen',
        'QT_QUICK_BACKEND': 'software',
        'EDI_ONLINE_SOURCES': 'easydiffraction=' + collection.as_uri(),
        'OMP_NUM_THREADS': '1',
        'OPENBLAS_NUM_THREADS': '1',
    }
    command = [
        str(runner),
        '-input',
        str(ROOT / 'tests/unit/app/tst_tutorial_navigation.qml'),
        '-o',
        '-,txt',
        '-maxwarnings',
        '0',
    ]
    controls = [
        'TutorialNavigation::test_required_clock_remains_monotonic_within_the_original_window',
        'TutorialNavigation::test_required_fit_guard_tracks_dataset_work',
        'TutorialNavigation::test_required_menu_observer_tracks_actual_popup_visibility',
        'TutorialNavigation::test_required_data_menu_observer_tracks_the_unmeasured_experiment',
        'TutorialNavigation::test_required_recipe_observer_positive_control',
    ]
    artifacts = (
        Path(
            os.environ.get('EDI_TUTORIAL_ARTIFACTS', ROOT / 'build/test-artifacts/tutorial-recipe')
        )
        / uuid.uuid4().hex
    )
    artifacts.mkdir(parents=True)
    (artifacts / 'source.json').write_text(
        json.dumps(
            {
                'root': str(ROOT),
                'input_folder': str(folder),
                'runner': str(runner),
                'runner_sha256': hashlib.sha256(runner.read_bytes()).hexdigest(),
                'script_sha256': hashlib.sha256(
                    (ROOT / 'tests/unit/app/tst_tutorial_navigation.qml').read_bytes()
                ).hexdigest(),
                'recipes_sha256': hashlib.sha256(
                    (ROOT / 'tests/fixtures/tutorial_recipe/recipes.json').read_bytes()
                ).hexdigest(),
            },
            indent=2,
        )
        + '\n'
    )
    deadline = time.monotonic() + 7200
    runs = {
        'controls': run_native_observation(
            command + controls, artifacts / 'controls', env, deadline, cwd=ROOT
        )
    }
    for case in RECIPES:
        if case in wanted:
            runs[case] = run_native_observation(
                command + ['TutorialNavigation::test_required_recipe_boundary_state:' + case],
                artifacts / case,
                env,
                deadline,
                cwd=ROOT,
            )
    records = []
    transport_errors = {}
    for case, run in runs.items():
        try:
            records.extend(
                native_records(Path(run['log']).read_bytes(), 'TUTORIAL_RECIPE_BOUNDARY')
            )
        except (OSError, ValueError, UnicodeDecodeError) as error:
            transport_errors[case] = str(error)
    raw = Path(runs['controls']['log']).read_bytes()
    return {
        'records': records,
        'native_runs': runs,
        'transport_errors': transport_errors,
        'menu_controls': native_records(raw, 'TUTORIAL_MENU_OBSERVER_CONTROL'),
        'data_menu_controls': native_records(raw, 'TUTORIAL_DATA_MENU_CONTROL'),
        'clock_controls': native_records(raw, 'TUTORIAL_CLOCK_CONTROL'),
        'folder': str(artifacts),
    }


def declared_good_state(expected):
    analysis = 'data_analysis\n'
    if expected['aliases']:
        analysis += 'loop_\n_alias.id\n_alias.parameter_unique_name\n' + ''.join(
            key + ' ' + value + '\n' for key, value in expected['aliases'].items()
        )
    if expected['constraints']:
        analysis += 'loop_\n_constraint.expression\n' + ''.join(
            json.dumps(value) + '\n' for value in expected['constraints'].values()
        )
    text = 'data_experiment\n' + ''.join(
        '_experiment_type.' + key + ' ' + json.dumps(value) + '\n'
        for key, value in expected.get('experiment_types', {}).items()
    )
    if expected['regions']:
        text += 'loop_\n_excluded_region.start\n_excluded_region.end\n' + ''.join(
            str(value['start']) + ' ' + str(value['end']) + '\n'
            for value in expected['regions'].values()
        )
    if expected['points']:
        text += 'loop_\n_background.position\n_background.intensity\n' + ''.join(
            str(value['position']) + ' ' + str(value.get('intensity', 1)) + '\n'
            for value in expected['points'].values()
        )
    settings = expected['estimate']
    if settings:
        text += 'loop_\n_background.id\n_background.position\n_background.intensity\n' + ''.join(
            f'{i + 1} {7.25 + i * 0.7} {21.75 + i * 1.2}\n' for i in range(settings['n_points'])
        )
    return {
        'free': expected['free'].copy(),
        'analysis': analysis,
        'structures': [
            {
                'text': 'data_structure\nloop_\n_atom_site.id\n'
                '_atom_site.wyckoff_letter\n'
                + ''.join(
                    key + ' ' + value + '\n' for key, value in expected.get('wyckoff', {}).items()
                )
            }
        ]
        if expected.get('wyckoff')
        else [],
        'values': expected['values'].copy(),
        'targets': ['background.estimate'] * expected['estimate_calls'],
        'applied_estimates': expected['estimate_calls'],
        'fileAlternativeSeen': True,
        'experiments': [
            {
                'text': text,
                'n_points': settings.get('n_points', 2),
                'use_model': settings.get('use_model', 'none'),
                'estimate_points': 2,
                'estimate_note': 'estimated',
            }
        ],
    }


@pytest.mark.parametrize(
    ('case', 'stage', 'damage'),
    [
        ('pd-neut-cwl_lbco-hrpt', 5, 'free'),
        ('pd-neut-cwl_lbco-hrpt', 5, 'relations'),
        ('pd-neut-cwl_lbco-hrpt', 5, 'aliases'),
        ('pd-neut-cwl_lbco-hrpt', 1, 'regions'),
        ('pd-neut-cwl_cosio-d20', 6, 'values'),
        ('pd-neut-cwl_lbco-hrpt', 1, 'points'),
        ('pd-neut-cwl_y2o3-spodi', 1, 'settings'),
        ('pd-xray-cwl_lam7o3-p021', 4, 'residual'),
        ('pd-neut-tof_si-sepd', 1, 'estimate'),
        ('pd-neut-tof_si-sepd', 1, 'file'),
        ('pd-neut-cwl_y2o3-spodi', 1, 'estimate-action'),
    ],
)
def test_missing_action_controls_keep_the_docs_expectation(case, stage, damage):
    expected = boundary_contracts(RECIPES[case])[stage - 1]
    good = declared_good_state(expected)
    assert not state_errors(expected, good), (
        'A positive state built only from the declared docs recipe satisfies the observer contract'
    )
    bad = copy.deepcopy(good)
    if damage == 'free':
        bad['free'].pop()
    elif damage == 'relations':
        bad['analysis'] = bad['analysis'].replace('biso_La', 'unknown')
    elif damage == 'aliases':
        bad['analysis'] = bad['analysis'].replace(
            'lbco.atom_site.La.adp_iso', 'lbco.atom_site.O.adp_iso'
        )
    elif damage == 'regions':
        bad['experiments'][0]['text'] = bad['experiments'][0]['text'].replace(
            '165.0 180.0', '166.0 180.0'
        )
    elif damage == 'values':
        assert expected['values'], 'The value-reset escape uses a genuinely declared reset'
        key = next(iter(expected['values']))
        bad['values'][key] += 0.2
    elif damage == 'points':
        bad['experiments'][0]['text'] = bad['experiments'][0]['text'].replace('160.0', '161.0')
    elif damage == 'settings':
        bad['experiments'][0]['n_points'] += 1
    elif damage == 'residual':
        bad['experiments'][0]['use_model'] = 'none'
    elif damage == 'estimate':
        bad['experiments'][0]['text'] = 'data_experiment\n'
    elif damage == 'file':
        bad['fileAlternativeSeen'] = False
    elif damage == 'estimate-action':
        bad['targets'] = []
    assert state_errors(expected, bad), (
        'Omitting a scientific action cannot change its independent docs expectation into a pass: '
        + damage
    )


@pytest.mark.parametrize('damage', ['peak', 'type', 'wyckoff'])
def test_an_incorrect_default_cannot_satisfy_the_original_declared_model(damage):
    expected = boundary_contracts(RECIPES['pd-neut-cwl_lbco-hrpt'])[0]
    good = declared_good_state(expected)
    assert not state_errors(expected, good), (
        'The declared default-state control satisfies every original model obligation'
    )
    bad = copy.deepcopy(good)
    if damage == 'peak':
        bad['values']['hrpt.peak.broad_gauss_v'] += 0.2
    elif damage == 'type':
        bad['experiments'][0]['text'] = bad['experiments'][0]['text'].replace(
            'powder', 'single crystal'
        )
    else:
        bad['structures'][0]['text'] = bad['structures'][0]['text'].replace('La a', 'La b')
    assert state_errors(expected, bad), (
        'An idempotent source-write adaptation cannot admit an incorrect actual default: ' + damage
    )


@pytest.mark.parametrize('changed', ['page', 'scientific-source'])
def test_page_custody_refresh_preserves_actions_and_refuses_changed_scientific_source(
    tmp_path, changed
):
    from tests.fixtures.tutorial_recipe.generate import refresh_page_custody  # noqa: PLC0415

    files = {
        'website/surfaces/docs/cli/tutorials/cases/case.md': 'Original visible page.\n',
        'docs/user/tutorials/case.py': 'The original declared scientific recipe.\n',
    }
    for relative, content in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    original = {
        'case': {
            'plan': {'steps': []},
            'fits': [],
            'boundaries': [],
            'sources': {
                relative: hashlib.sha256((tmp_path / relative).read_bytes()).hexdigest()
                for relative in files
            },
        }
    }
    path = tmp_path / next(
        key for key in files if key.endswith('.md' if changed == 'page' else '.py')
    )
    path.write_text(path.read_text() + 'A declared transport change.\n')
    witness = copy.deepcopy(original)
    if changed == 'page':
        refreshed = refresh_page_custody(original, tmp_path)
        assert (
            refreshed['case']['plan'] == original['case']['plan']
            and refreshed['case']['fits'] == []
        ), 'Page custody refresh preserves every frozen scientific action and free-set expectation'
        assert (
            refreshed['case']['sources'][path.relative_to(tmp_path).as_posix()]
            == hashlib.sha256(path.read_bytes()).hexdigest()
        ), 'Page custody records the exact current published transport bytes'
    else:
        with pytest.raises(ValueError, match='review the recipe source'):
            refresh_page_custody(original, tmp_path)
    assert original == witness, 'A custody refresh never mutates its independently retained input'


def test_docs_recipe_sources_are_unchanged():
    for case, recipe in RECIPES.items():
        for path, expected in recipe['sources'].items():
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, (
                'Docs recipe sources retain their reviewed identities: ' + case + ' / ' + path
            )


@pytest.mark.parametrize(
    'action',
    [
        'unsupported:new_value',
        'aliasXparameter.0',
        'appBar.tab.missing',
        'background.unhandledOperation',
    ],
)
def test_unclassified_actions_cannot_be_declared_inert(action):
    with pytest.raises(ValueError, match='Unclassified docs recipe action'):
        significant({'id': 'ordinary-stage'}, action)


def test_native_progress_retires_old_fit_guards_and_ignores_diagnostic_activity():
    step = b'TUTORIAL_REPLAY_STEP {"id":"case","step":3}\n'
    wait = b'TUTORIAL_FIT_WAIT {"id":"case","step":3,"milliseconds":65000}\n'
    assert native_progress(step + wait) == (('case', 3), 65), (
        'Only the currently observed actual fit contributes its work-derived completion guard'
    )
    assert native_progress(step + wait + b'QWARN diagnostic activity\n') == (('case', 3), 65), (
        'Diagnostic output cannot invent a new native progress step or restart its guard'
    )
    assert native_progress(step + wait + b'TUTORIAL_REPLAY_STEP {"id":"case","step":4}\n') == (
        ('case', 4),
        0,
    ), 'A later ordinary action retires the earlier fit guard rather than inheriting extra time'
    assert native_progress(step + wait + b'TUTORIAL_REPLAY_STEP {"id":"case"') == (
        ('case', 3),
        65,
    ), 'An in-flight partial log write is buffered until its complete native record arrives'
    with pytest.raises(ValueError, match='nonnegative work guard'):
        native_progress(step + b'TUTORIAL_FIT_WAIT {"id":"case","step":3,"milliseconds":-1}\n')
    with pytest.raises(ValueError, match='actual case and integer step'):
        native_progress(b'TUTORIAL_REPLAY_STEP []\n')

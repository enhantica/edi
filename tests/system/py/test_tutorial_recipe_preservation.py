"""Declared docs actions survive translation and actual pre-fit model state."""

import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.tutorial_cases.notebook_fit import local_collection
from tests.fixtures.tutorial_recipe.reference import boundary_contracts, significant, state_errors

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


def load_captions(translator):
    return {
        case: (source, translator.stage_texts(case, source))
        for case in RECIPES
        for source in [(ROOT / 'docs/user/tutorials' / (case + '.py')).read_text()]
    }


@pytest.fixture(scope='module')
def recipe_context(tmp_path_factory, request):
    selected = {item.originalname for item in request.session.items}
    needs_translation = bool(
        selected
        & {
            'test_every_declared_scientific_action_affects_translation_or_is_refused',
            'test_unknown_recipe_action_is_refused_before_generation',
        }
    )
    wanted = {
        item.callspec.params['case']
        for item in request.session.items
        if item.originalname == 'test_builtin_pre_fit_state_equals_the_declared_docs_recipe'
    }
    module = load_translator() if needs_translation else None
    return {
        'translator': module,
        'captions': load_captions(module) if needs_translation else None,
        'states': observe_states(tmp_path_factory, wanted)
        if wanted or 'test_recipe_observer_has_a_real_positive_control' in selected
        else None,
    }


@pytest.fixture
def translator(recipe_context):
    return recipe_context['translator']


@pytest.fixture
def captions(recipe_context):
    return recipe_context['captions']


@pytest.fixture
def states(recipe_context):
    return recipe_context['states']


def unchanged_captions(captions):
    def read(case, source):
        assert source == captions[case][0], (
            'Only unchanged stage prose is reused while action inputs change'
        )
        return copy.deepcopy(captions[case][1])

    return read


@pytest.mark.parametrize('case', RECIPES)
def test_every_declared_scientific_action_affects_translation_or_is_refused(
    case, translator, captions, monkeypatch
):
    monkeypatch.setattr(translator, 'stage_texts', unchanged_captions(captions))
    recipe = RECIPES[case]['plan']
    monkeypatch.setattr(translator, 'plan', lambda _case: copy.deepcopy(recipe))
    baseline = translator.tutorial_steps(case)
    ignored = []
    for index, item in enumerate(recipe['steps']):
        for action_index, action in enumerate(item['actions']):
            if not significant(item, action):
                continue
            damaged = copy.deepcopy(recipe)
            del damaged['steps'][index]['actions'][action_index]
            monkeypatch.setattr(
                translator, 'plan', lambda _case, changed=damaged: copy.deepcopy(changed)
            )
            try:
                observed = translator.tutorial_steps(case)
            except (ValueError, RuntimeError, SystemExit) as error:
                if any(
                    word in str(error).casefold()
                    for word in ['action', 'recipe', 'plan', 'translate']
                ):
                    continue
                ignored.append((item['id'], action, 'unnamed refusal'))
                continue
            except Exception as error:  # noqa: BLE001 - arbitrary translator crashes do not prove a named refusal
                ignored.append((item['id'], action, type(error).__name__))
                continue
            if observed == baseline:
                ignored.append((item['id'], action, 'no effect'))
    assert not ignored, (
        'Each declared scientific action affects translation or gets a named refusal: '
        + repr(ignored)
    )


@pytest.mark.parametrize('case', RECIPES)
def test_unknown_recipe_action_is_refused_before_generation(
    case, translator, captions, monkeypatch
):
    monkeypatch.setattr(translator, 'stage_texts', unchanged_captions(captions))
    damaged = copy.deepcopy(RECIPES[case]['plan'])
    damaged['steps'][-1]['actions'].append('unsupported:recipe_action_probe')
    monkeypatch.setattr(translator, 'plan', lambda _case: damaged)
    with pytest.raises(
        (ValueError, RuntimeError, SystemExit), match=r'(?i)action|recipe|translat'
    ):
        translator.tutorial_steps(case)


def observe_states(tmp_path_factory, wanted):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
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
    # This run selects only the declared semantic witnesses, not all tutorial replays.
    command = [
        str(runner),
        '-input',
        str(ROOT / 'tests/unit/app/tst_tutorial_navigation.qml'),
        '-o',
        '-,txt',
        '-maxwarnings',
        '0',
    ]
    command += ['TutorialNavigation::test_required_recipe_observer_positive_control']
    command += [
        'TutorialNavigation::test_required_recipe_boundary_state:' + case
        for case in RECIPES
        if case in wanted
    ]
    with (folder / 'native.log').open('w') as output:
        run = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
            timeout=7200,
            check=False,
        )
    text = (folder / 'native.log').read_text()
    return {
        'run': run,
        'records': [
            json.loads(line.partition('TUTORIAL_RECIPE_BOUNDARY ')[2])
            for line in text.splitlines()
            if 'TUTORIAL_RECIPE_BOUNDARY ' in line
        ],
        'folder': str(folder),
    }


@pytest.mark.parametrize('case', RECIPES)
def test_builtin_pre_fit_state_equals_the_declared_docs_recipe(case, states):
    expected = boundary_contracts(RECIPES[case])
    records = [r for r in states['records'] if r['id'] == case]
    problems = []
    for boundary in expected:
        found = [row for row in records if row['stage'] == boundary['stage']]
        if len(found) != 1:
            problems.append((boundary['stage'], ['missing or duplicate actual boundary']))
            continue
        errors = state_errors(boundary, found[0])
        if case == 'pd-neut-tof_si-sepd' and not found[0]['fileAlternativeSeen']:
            errors.append('From file alternative not shown')
        if errors:
            problems.append((boundary['stage'], errors))
    if len(records) != len(expected):
        problems.append(('count', [len(records), len(expected)]))
    assert not problems, 'Actual pre-fit state matches the independent docs recipe: ' + repr(
        problems
    )


def test_recipe_observer_has_a_real_positive_control(states):
    found = [row for row in states['records'] if row['id'] == 'observer-control']
    assert len(found) == 1, (
        'The boundary observer reaches an independently authored real app model'
    )
    assert found[0]['values']['lbco.cell.length_a'] == pytest.approx(3.89), (
        'The passive observer reads the independent onboarding structure cell, without changing it'
    )
    assert found[0]['experiments'], (
        'The passive observer reads the actual experiment text and settings'
    )


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
    text = 'data_experiment\n'
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
    return {
        'free': expected['free'].copy(),
        'analysis': analysis,
        'values': expected['values'].copy(),
        'targets': ['background.estimate'] * expected['estimate_calls'],
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
        bad['experiments'][0]['estimate_points'] = 0
    elif damage == 'file':
        bad['fileAlternativeSeen'] = False
    elif damage == 'estimate-action':
        bad['targets'] = []
    assert state_errors(expected, bad), (
        'Omitting a scientific action cannot change its independent docs expectation into a pass: '
        + damage
    )


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

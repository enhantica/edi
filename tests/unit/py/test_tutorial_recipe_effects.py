"""Source-consumption controls for writes the live app has already satisfied."""

import copy

import pytest

from tests.fixtures.tutorial_recipe.reference import recipe_action_error


@pytest.mark.parametrize(
    'action',
    [
        'fill:peak.broad_gauss_v=-0.1',
        'choose-token:experimentType.sampleForm=powder',
        'type:a:',
    ],
)
def test_redundant_literal_still_has_to_control_its_actual_target_and_operand(action):
    actions = ['atomSite.wyckoffLetter.0', action] if action.startswith('type:') else [action]
    recipe = {'steps': [{'id': 'setup', 'actions': actions}]}
    original = copy.deepcopy(recipe)
    baseline = [{'target': 'home.start', 'check': 'page:project'}]

    def translate(changed):
        values = changed['steps'][0]['actions']
        if not values or values[-1] == action or len(values) < len(actions):
            return copy.deepcopy(baseline)
        if action.startswith('type:'):
            target, value, check = values[-2], values[-1][5:], 'pick'
        else:
            prefix, payload = values[-1].split(':', 1)
            target, value = payload.split('=', 1)
            check = 'field' if prefix == 'fill' else 'token'
        return baseline + [{'target': target, 'check': check + ':' + target + '=' + value}]

    assert recipe_action_error(translate, baseline, recipe, 0, len(actions) - 1) is None, (
        'A redundant literal consumes its changed operand at the exact original target'
    )
    assert recipe == original, 'Sensitivity probes never rewrite the independently frozen recipe'


@pytest.mark.parametrize(
    'escape',
    [
        'ignored',
        'text-only',
        'wrong-target',
        'wrong-value',
        'crash',
        'unnamed',
        'malformed',
    ],
)
def test_default_action_adaptation_never_accepts_a_silent_or_misdirected_translator(escape):
    recipe = {'steps': [{'id': 'setup', 'actions': ['fill:peak.broad_gauss_v=-0.1']}]}
    baseline = [{'target': 'home.start', 'check': 'page:project'}]

    def translate(changed):
        actions = changed['steps'][0]['actions']
        if not actions or actions[0] == recipe['steps'][0]['actions'][0]:
            return copy.deepcopy(baseline)
        value = actions[0].split('=', 1)[1]
        if escape == 'crash':
            raise KeyError('crashed')
        if escape == 'unnamed':
            raise ValueError('unrelated failure')
        if escape == 'malformed':
            return 'not a step sequence'
        return (
            baseline
            + [
                {
                    'target': 'wrong' if escape == 'wrong-target' else 'peak.broad_gauss_v',
                    'check': 'field:peak.broad_gauss_v='
                    + ('-0.1' if escape == 'wrong-value' else value)
                    if escape in {'wrong-target', 'wrong-value'}
                    else '',
                    'text': value if escape == 'text-only' else '',
                }
            ]
            if escape != 'ignored'
            else baseline
        )

    assert recipe_action_error(translate, baseline, recipe, 0, 0) is not None, (
        'Redundant writes reject ignored operands, wrong targets/values, '
        'crashes and malformed output'
    )


def test_nonliteral_actions_cannot_claim_the_redundant_assignment_adaptation():
    recipe = {'steps': [{'id': 'setup', 'actions': ['tick:structures.phase.cell.length_a']}]}
    baseline = [{'target': 'home.start', 'check': 'page:project'}]
    assert recipe_action_error(lambda _changed: baseline, baseline, recipe, 0, 0) == 'no effect', (
        'A dropped scientific selection still has to affect the translated tutorial'
    )


def test_named_refusal_keeps_the_original_action_preservation_contract():
    recipe = {'steps': [{'id': 'setup', 'actions': ['fill:minimizer.maxIterations=1000']}]}

    def translate(_changed):
        raise ValueError('The recipe must supply the declared iteration limit')

    assert recipe_action_error(translate, [], recipe, 0, 0) is None, (
        'The original named refusal remains sufficient for a deleted required action'
    )

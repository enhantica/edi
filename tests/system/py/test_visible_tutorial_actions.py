"""Each built-in step teaches one visible control operation, including web-load substeps."""

import json
from operator import itemgetter
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]


def scripts():
    entries = json.loads((ROOT / 'app/tutorials/manifest.json').read_text())['tutorials']
    for entry in entries:
        if 'steps' not in entry:
            pages = json.loads((ROOT / 'app/tutorials' / entry['tour']).read_text())['pages']
            entry['steps'] = [step for page in pages for step in page['steps']]
    return entries


def visible_action_errors(steps):
    # These operations require multiple separately editable GUI controls under the
    # visible-step rule; their aggregated payload is not one group-header action.
    composite = {
        'download',
        'sites',
        'aliases',
        'group',
        'adp-type',
        'adp-iso',
        'background-points',
        'background-named',
        'constraint',
        'data',
        'value',
    }
    primitive = {
        '',
        'fitted',
        'page',
        'open',
        'creating',
        'text',
        'project',
        'stop-rule',
        'max-iterations',
        'category',
        'filters-clear',
        'free',
        'param',
        'fitting-mode',
        'selected',
        'changed',
        'background-estimated',
        'example',
        'experiment',
        'structures',
        'structure',
        'space-group',
        'cell-a',
        'name-filter',
        'scale',
        'files-saved',
        'fit-done',
        'results-closed',
        'descent',
        'chi-tolerance',
    }
    errors = []
    for index, step in enumerate(steps):
        check = step.get('check', '')
        verb = check.split(':', 1)[0]
        if verb not in primitive | composite:
            errors.append((
                index,
                'unclassified operation requires a visible-control contract',
                check,
            ))
        if ';' in check or verb in composite:
            errors.append((index, 'composite action', check))
        if verb == 'background-estimated' and '=' in check:
            errors.append((index, 'estimate settings and Apply share a step', check))
        if verb == 'structures' and int(check.split(':', 1)[1]) > 1:
            errors.append((index, 'multiple Create actions', check))
        if verb == 'download':
            kind = check.split(':', 2)[1]
            expected = [
                'structures.load' if kind == 'structure' else 'experiments.load',
                'structures.load.web' if kind == 'structure' else 'experiments.load.experimentWeb',
                'onlineLoad.search',
                'onlineLoad.row.0',
            ]
            # This is the independently declared four-control workflow, not the
            # generated controller's claim that one download has completed.
            observed = [row['target'] for row in steps[max(0, index - 3) : index + 1]]
            if observed != expected:
                errors.append((index, 'web load lacks four visible steps', expected))
    return errors


def declared_web_kinds(entry):
    source = ROOT / 'docs/user/tutorials' / (entry['id'] + '.py')
    if not source.exists():
        return []  # The older Interface tour and small teaching lessons have no case plan.
    text = source.read_text()
    if '## Perform the analysis' not in text or "fitting_mode = 'sequential'" in text:
        return []  # These independently declared sources open a complete example.
    records = yaml.safe_load((ROOT / 'docs/user/cli/projects.yml').read_text())['projects']
    record = next(row for row in records if row['id'] == entry['id'])
    project = ROOT / 'docs/user/cli' / entry['id'] / 'project'
    structures = (
        [] if record.get('structure-by-hand') else sorted((project / 'structures').glob('*.edi'))
    )
    experiments = sorted((project / 'experiments').glob('*.edi'))
    return ['structure'] * len(structures) + ['experiment'] * len(experiments)


def web_workflow_errors(steps, kinds):
    targets = [row['target'] for row in steps]
    menus = {
        'structures.load.web': 'structures.load',
        'experiments.load.experimentWeb': 'experiments.load',
        'experiments.load.dataWeb': 'experiments.load',
    }
    starts = [i for i, target in enumerate(targets) if target in menus]
    observed, errors = [], []
    previous = -1
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(steps)
        menu = menus[targets[start]]
        observed.append('structure' if menu == 'structures.load' else 'experiment')
        if menu not in targets[previous + 1 : start]:
            errors.append('missing visible Load menu')
        remaining = targets[start + 1 : end]
        if 'onlineLoad.search' not in remaining or 'onlineLoad.row.0' not in remaining:
            errors.append('missing visible Search or row click')
        elif remaining.index('onlineLoad.search') > remaining.index('onlineLoad.row.0'):
            errors.append('row click precedes Search')
        previous = start
    if observed != kinds:
        errors.append('web-load inventory differs from independent case inputs')
    return errors


@pytest.mark.parametrize('entry', scripts(), ids=itemgetter('id'))
def test_every_authored_step_is_one_visible_operation(entry):
    assert not web_workflow_errors(entry['steps'], declared_web_kinds(entry)), (
        'Every case input has ordered visible Load, From web, Search and row steps: ' + entry['id']
    )
    assert not visible_action_errors(entry['steps']), (
        'Every built-in operation is visibly taught, with Load, From web, Search and row click '
        'in separate ordered steps: '
        + entry['id']
        + ' / '
        + repr(visible_action_errors(entry['steps']))
    )


@pytest.mark.parametrize(
    'check',
    [
        'download:structure:sample=sample',
        'sites:A 0 0 0,B 1 1 1',
        'param:a=1;param:b=2',
        'aliases:a=site.x',
        'group:free:Cell',
        'background-estimated:points=21',
        'unrecognized:multiple-actions',
    ],
)
def test_hidden_multi_control_action_is_detected_even_when_its_target_exists(check):
    assert visible_action_errors([{'target': 'structures.load', 'check': check}]), (
        'A rendered target cannot make an aggregated action a visible single-control lesson'
    )


@pytest.mark.parametrize('missing', range(4))
def test_deleting_any_visible_web_action_keeps_the_independent_recipe(missing):
    steps = [
        {'target': target}
        for target in [
            'structures.load',
            'structures.load.web',
            'onlineLoad.search',
            'onlineLoad.row.0',
        ]
    ]
    assert not web_workflow_errors(steps, ['structure']), (
        'The independent four-control web recipe has a positive control'
    )
    del steps[missing]
    assert web_workflow_errors(steps, ['structure']), (
        'Deleting any visible control cannot delete the independent web-load obligation'
    )

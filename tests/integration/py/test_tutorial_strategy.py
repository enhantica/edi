"""Owner 7101f0fd9: cumulative stages, collective actions and visible app names."""

import json

import pytest

from tests.fixtures.tutorial_cases.command_line import actions
from tests.fixtures.tutorial_cases.contract import CASES, ROOT, interfaces_for
from tests.fixtures.tutorial_cases.stages import observe
from tests.fixtures.tutorial_cases.strategy import (
    app_labels,
    assert_app_group_actions,
    assert_app_names,
    assert_code_group_actions,
    assert_command_group_actions,
    assert_strategy,
)
from tests.integration.py.test_tutorial_fit_stages import source

LABELS = app_labels(
    (ROOT / 'tests/fixtures/dictionary_display/metadata_reference.hpp').read_text()
)


def app_text(case):
    entries = json.loads((ROOT / 'app/tutorials/manifest.json').read_text())['tutorials']
    matches = [entry for entry in entries if entry['id'] == case]
    assert len(matches) == 1, 'Gate 3/4: every declared app case has its own tutorial'
    entry = matches[0]
    if 'tour' in entry:
        tour = json.loads((ROOT / 'app/tutorials' / entry['tour']).read_text())
        steps = [step for page in tour['pages'] for step in page['steps']]
    else:
        steps = entry.get('steps', [])
    # User instructions only; machine check paths and target ids remain internal.
    return '\n'.join(str(step.get(field, '')) for step in steps for field in ['title', 'text'])


@pytest.mark.parametrize('case', [case for case in CASES if 'python' in interfaces_for(case)])
@pytest.mark.parametrize('surface', ['script', 'notebook'])
def test_python_tutorial_uses_one_action_for_large_parameter_groups(case, surface):
    assert_code_group_actions(observe(source(case, surface)))


@pytest.mark.parametrize('case', [case for case in CASES if 'app' in interfaces_for(case)])
@pytest.mark.parametrize('surface', ['built-in', 'docs'])
def test_app_tutorial_uses_group_actions_and_actual_table_parameter_names(case, surface):
    if surface == 'built-in':
        written = app_text(case)
    else:
        path = ROOT / 'website/surfaces/docs/application/tutorials/cases' / (case + '.md')
        assert path.is_file(), 'Gate 3/4: each declared case has a current app tutorial page'
        written = path.read_text()
    assert_app_group_actions(written)
    assert_app_names(written, LABELS)


@pytest.mark.parametrize('case', [case for case in CASES if 'cli' in interfaces_for(case)])
def test_command_line_tutorial_edits_large_parameter_groups_together(case):
    path = ROOT / 'website/surfaces/docs/cli/tutorials/cases' / (case + '.md')
    assert path.is_file(), 'Gate 5: each declared case has its Command line tutorial page'
    assert_command_group_actions(actions(path.read_text()))


GOOD = """project.display.pattern()
structure.cell.length_a.free = True
experiment.scale.free = True
project.analysis.fit()
for point in experiment.background:
    point.intensity.free = True
project.analysis.fit()
experiment.peak.broad_gauss_u.free = True
project.analysis.fit()
"""


@pytest.mark.parametrize(
    'escape',
    [
        'profile-first',
        'two-new-blocks',
        'coordinates-and-adps',
        'accepted-fixed',
        'reset-all',
        'fix-free-between-fits',
        'late-alignment',
        'upstream-excuse',
    ],
)
def test_strategy_observer_refuses_each_withdrawn_or_non_cumulative_route(escape):
    assert_strategy(observe(GOOD))
    if escape == 'profile-first':
        broken = GOOD.replace('structure.cell.length_a', 'experiment.peak.broad_gauss_v')
    elif escape in {'two-new-blocks', 'upstream-excuse'}:
        broken = GOOD.replace(
            'for point in experiment.background:',
            'experiment.peak.broad_gauss_v.free = True\nfor point in experiment.background:',
        )
        if escape == 'upstream-excuse':
            broken = '# Follow diffraction-lib instead because its cycles merge blocks.\n' + broken
    elif escape == 'coordinates-and-adps':
        broken = GOOD + (
            'structure.atom_sites["A"].fract_x.free = True\n'
            'structure.atom_sites["A"].adp_iso.free = True\nproject.analysis.fit()\n'
        )
    elif escape == 'accepted-fixed':
        broken = GOOD.replace(
            'experiment.peak.broad_gauss_u.free',
            'experiment.scale.free = False\nexperiment.peak.broad_gauss_u.free',
        )
    elif escape == 'reset-all':
        broken = GOOD.replace(
            'experiment.peak.broad_gauss_u.free',
            'for parameter in project.free_parameters:\n    parameter.free = False\n'
            'experiment.peak.broad_gauss_u.free',
        )
    elif escape == 'fix-free-between-fits':
        broken = GOOD + (
            'experiment.scale.free = False\nexperiment.scale.free = True\nproject.analysis.fit()\n'
        )
    else:
        broken = GOOD + 'structure.cell.length_b.free = True\nproject.analysis.fit()\n'
    with pytest.raises(AssertionError, match='Gate 3/4:'):
        assert_strategy(observe(broken))


def test_constraint_dependent_can_be_fixed_while_accepted_independent_parameters_stay_free():
    code = (
        GOOD
        + """structure.atom_sites['A'].adp_iso.free = True
structure.atom_sites['B'].adp_iso.free = True
project.analysis.fit()
structure.atom_sites['B'].adp_iso.free = False
project.analysis.aliases.create(id='a', param=structure.atom_sites['A'].adp_iso)
project.analysis.aliases.create(id='b', param=structure.atom_sites['B'].adp_iso)
project.analysis.constraints.create(id='b', expression='b = a')
project.analysis.fit()
"""
    )
    assert_strategy(observe(code))
    collective = code.replace(
        "structure.atom_sites['A'].adp_iso.free = True\n"
        "structure.atom_sites['B'].adp_iso.free = True",
        'for site in structure.atom_sites:\n    site.adp_iso.free = True',
    )
    assert_strategy(observe(collective))
    unrelated = code.replace("expression='b = a'", "expression='a = b'")
    with pytest.raises(AssertionError, match='accepted independent parameters stay free'):
        assert_strategy(observe(unrelated))
    with pytest.raises(AssertionError, match='never fix an accepted parameter and free it again'):
        assert_strategy(
            observe(
                code + "structure.atom_sites['B'].adp_iso.free = True\nproject.analysis.fit()\n"
            )
        )


@pytest.mark.parametrize('count', [3, 4, 14])
@pytest.mark.parametrize('action', ['free', 'fix'])
def test_group_action_observer_distinguishes_few_named_members_from_a_collection(count, action):
    named = '\n'.join(
        f'experiment.background[{index}].intensity.free = {action == "free"}'
        for index in range(count)
    )
    plan = observe(named)
    if count <= 3:
        assert_code_group_actions(plan)
    else:
        with pytest.raises(AssertionError, match='one collection action'):
            assert_code_group_actions(plan)
    assert_code_group_actions(
        observe('for point in experiment.background:\n    point.intensity.free = True')
    )
    prose = '## Background\n' + '\n'.join(
        f'- {action.title()} `Background {index} intensity`' for index in range(count)
    )
    cli = [
        (
            'free-rows' if action == 'free' else 'edit',
            'experiment.edi',
            f'{index} 20 100' + ('()' if action == 'free' else ''),
        )
        for index in range(count)
    ]
    if count <= 3:
        assert_app_group_actions(prose)
        assert_command_group_actions(cli)
    else:
        with pytest.raises(AssertionError, match='Free header'):
            assert_app_group_actions(prose)
        with pytest.raises(AssertionError, match='edited together'):
            assert_command_group_actions(cli)
    assert_command_group_actions([
        ('free-rows', 'experiment.edi', '\n'.join(row[2] for row in cli))
    ])


@pytest.mark.parametrize(
    'name',
    [
        'experiment.background[1].intensity',
        'cell.length_a',
        'calib_twotheta_offset',
        'nonexistent control',
    ],
)
@pytest.mark.parametrize('style', ['code', 'bold', 'plain', 'fenced'])
def test_app_name_observer_refuses_paths_and_invented_parameter_labels(name, style):
    assert_app_names('Free `U`, `V` and `W`.', LABELS)
    assert_app_names('Free `B iso`.', LABELS)
    subject = {
        'code': f'`{name}`',
        'bold': f'**{name}**',
        'plain': name,
        'fenced': f'\n```text\n{name}\n```',
    }[style]
    with pytest.raises(AssertionError, match='Gate 3/4:'):
        assert_app_names('Free ' + subject + '.', LABELS)


@pytest.mark.parametrize('stage', ['first', 'later'])
def test_combined_blocks_require_a_reason_in_their_own_stage(stage):
    first = """# ### Alignment and magnetic moments
# Free the scale, cell and magnetic moments together because their intensities are coupled.
experiment.scale.free = True
structure.cell.length_a.free = True
structure.atom_site_moment['Co'].crystalaxis_y.free = True
project.analysis.fit()
"""
    later = (
        GOOD
        + """# ### Atomic positions and displacements
# Free coordinates and displacement together because separating them leaves a worse fit.
structure.atom_sites['A'].fract_x.free = True
structure.atom_sites['A'].adp_iso.free = True
project.analysis.fit()
"""
    )
    code = first if stage == 'first' else later
    assert_strategy(observe(code))
    missing = '\n'.join(line for line in code.splitlines() if 'because' not in line)
    for mutation in [
        missing,
        missing.replace('# ###', '# Together because the earlier blocks need coupling.\n# ###'),
        '# ### Earlier stage\n# Because coordinates and displacement couple in this earlier fit.\n'
        + missing,
        code + '# ### New stage without a new block\nproject.analysis.fit()\n',
    ]:
        with pytest.raises(AssertionError, match='Gate 3/4:'):
            assert_strategy(observe(mutation))

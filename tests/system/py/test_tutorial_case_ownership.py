"""Only the auxiliary tour and case-owned lessons remain; simulation construction is retained."""

import json
import os
import re
from collections import Counter
from pathlib import Path

import gemmi
import pytest

from tests.fixtures.tutorial_cases.contract import cases_for
from tests.fixtures.tutorial_cases.manual_simulation import model_errors

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(os.environ.get('EDI_TUTORIAL_SOURCE_ROOT', ROOT))
SIMULATION = 'pd-neut-cwl_lbco_simulation'
RETIRED = {'simulation', 'fitting'}


def scripts():
    return json.loads((SOURCE / 'app/tutorials/manifest.json').read_text())['tutorials']


def test_builtin_catalogue_is_exactly_the_tour_and_one_lesson_per_app_case():
    expected = ['interface', *cases_for('app')]
    actual = [entry['id'] for entry in scripts()]
    assert Counter(actual) == Counter(expected), (
        'The Tutorials list has exactly the Interface tour and one lesson per app case, '
        'with no extra, missing or duplicate tutorial: ' + repr(actual)
    )


def test_removed_guides_have_no_manifest_definitions_or_dedicated_json_files():
    stale = []
    for path in (SOURCE / 'app/tutorials').rglob('*.json'):
        value = json.loads(path.read_text())
        entries = value.get('tutorials', []) if isinstance(value, dict) else []
        stale += [
            (str(path.relative_to(SOURCE)), row['id'])
            for row in entries
            if row.get('id') in RETIRED
        ]
        if path.stem in RETIRED:
            stale.append((str(path.relative_to(SOURCE)), 'retired guide file'))
    assert not stale, 'Removed stand-alone guides have no remaining manifest definition: ' + repr(
        stale
    )


def simulation_construction_errors(steps):
    families = [
        ('new-project', lambda name: name == 'project.create'),
        ('new-structure', lambda name: name == 'structures.create'),
        ('space-group', lambda name: name == 'spaceGroup.nameHM'),
        ('cell', lambda name: name.startswith('cell.')),
        ('atom-sites', lambda name: name == 'atomSites.append'),
        ('new-experiment', lambda name: name == 'experiments.create'),
        (
            'structure-link',
            lambda name: (
                name == 'linkedStructure.append' or name.startswith('linkedStructure.scale.')
            ),
        ),
    ]
    positions, errors = [], []
    for label, accepts in families:
        found = [i for i, step in enumerate(steps) if accepts(step['target'])]
        if not found:
            errors.append('missing ' + label)
        else:
            positions.append(min(found))
    if positions != sorted(positions):
        errors.append('construction order')
    if any(
        str(step.get('check', '')).startswith('example:')
        or step['target'].startswith('examples.open.')
        for step in steps
    ):
        errors.append('opens a prepared example instead of constructing its model')
    return errors


def test_lbco_case_teaches_by_hand_simulation_instead_of_opening_its_example():
    found = [entry for entry in scripts() if entry['id'] == SIMULATION]
    assert len(found) == 1, 'Exactly one LBCO simulation case carries the construction lesson'
    errors = simulation_construction_errors(found[0]['steps'])
    assert not errors, 'The simulation case retains ordered by-hand construction: ' + repr(errors)


@pytest.mark.parametrize('missing', range(7))
def test_a_missing_manual_construction_action_cannot_be_replaced_by_an_example(missing):
    names = [
        'project.create',
        'structures.create',
        'spaceGroup.nameHM',
        'cell.length_a',
        'atomSites.append',
        'experiments.create',
        'linkedStructure.append',
    ]
    good = [{'target': name} for name in names]
    assert not simulation_construction_errors(good), (
        'The independent ordered construction contract has a positive control'
    )
    del good[missing]
    good.append({'target': 'examples.open.' + SIMULATION, 'check': 'example:' + SIMULATION})
    assert simulation_construction_errors(good), (
        'A missing manual action fails even when a complete example could supply its final model'
    )


def test_docs_do_not_link_to_or_list_the_removed_builtin_guides():
    stale = []
    for root in [SOURCE / 'docs/user', SOURCE / 'website/surfaces/docs']:
        for path in root.rglob('*.md'):
            retired_link = re.compile(
                r'(?:[?&]tutorial=|tutorials?/)(?:simulation|fitting)(?:[/#?.)\s]|$)'
            )
            if any(
                retired_link.search(line)
                or ('Interface tour' in line and 'Simulation' in line and 'Fitting' in line)
                for line in path.read_text().splitlines()
            ):
                stale.append(str(path.relative_to(SOURCE)))
    assert not stale, (
        'User documentation has no retired-guide links or old three-guide lists: ' + repr(stale)
    )


@pytest.mark.parametrize(
    'field',
    [
        'cell',
        'space-group',
        'species',
        'coordinate',
        'occupancy',
        'displacement',
        'links',
        'measured',
        'calculated',
    ],
)
def test_manual_simulation_state_checks_reject_each_independent_model_escape(field):
    reference = ROOT / 'docs/user/cli' / SIMULATION / 'project/structures/lbco.edi'
    record = {
        'structure': reference.read_text(),
        'links': ['lbco'],
        'measured': 0,
        'positiveCalculated': True,
    }
    assert not model_errors(record, reference), (
        'A state made only from the independent saved input qualifies the model observer'
    )
    block = gemmi.cif.read_string(record['structure']).sole_block()
    if field == 'cell':
        block.set_pair('_cell.length_a', '4.01')
    elif field == 'space-group':
        block.set_pair('_space_group.name_h_m', "'P 1'")
    elif field in {'species', 'coordinate', 'occupancy', 'displacement'}:
        column = {
            'species': 'type_symbol',
            'coordinate': 'fract_x',
            'occupancy': 'occupancy',
            'displacement': 'adp_iso',
        }[field]
        block.find_loop('_atom_site.' + column)[0] = 'Nd' if field == 'species' else '0.625'
    elif field == 'links':
        record['links'] = []
    elif field == 'measured':
        record['measured'] = 3
    elif field == 'calculated':
        record['positiveCalculated'] = False
    record['structure'] = block.as_string()
    assert model_errors(record, reference), (
        'Wrong cell/group/sites/links or a measured/empty calculation cannot pass the saved-input '
        'simulation check: ' + field
    )

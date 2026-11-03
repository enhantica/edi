"""Tutorial inputs and recipe, checked against the independent saved example."""

import json
import os
import re
import subprocess
from pathlib import Path

import gemmi
import pytest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(os.environ.get('EDI_ONBOARDING_SOURCE_ROOT', ROOT))
EXAMPLE = ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt'


def script():
    return next(
        row
        for row in json.loads((SOURCE / 'app/tutorials/manifest.json').read_text())['tutorials']
        if row['id'] == 'fitting'
    )


def tutorial_file(name):
    paths = list((SOURCE / 'app').rglob(name))
    assert len(paths) == 1, 'The app bundles exactly one tutorial input named ' + name
    return paths[0]


def number(value):
    return float(re.sub(r'\([^)]*\)$', '', value))


def test_tutorial_measurement_equals_the_examples_original_measurement():
    actual = tutorial_file('hrpt.xye')
    reference = ROOT / 'tests/fixtures/background_estimate/meas-lbco-hrpt.xye'
    assert actual.read_bytes() == reference.read_bytes(), (
        'The downloadable HRPT tutorial file preserves the independently vendored source bytes'
    )


def test_tutorial_cif_equals_the_examples_structure_source():
    # CIF and the example's dotted EDI use different spelling; compare all of the
    # structure's supplied quantities, not bytes of different serialization formats.
    cif = gemmi.cif.read_file(str(tutorial_file('lbco.cif'))).sole_block()
    edi = gemmi.cif.read_file(str(EXAMPLE / 'project/structures/lbco.edi')).sole_block()
    for axis in ('length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma'):
        actual, expected = (
            (cif.find_value('_cell_' + axis) or cif.find_value('_cell.' + axis)),
            edi.find_value('_cell.' + axis),
        )
        assert actual and expected, 'The tutorial CIF and example both supply each cell quantity'
        assert number(actual) == number(expected), 'The tutorial CIF preserves the example cell'
    group = (
        cif.find_value('_space_group.name_H-M_alt')
        or cif.find_value('_space_group_name_H-M_alt')
        or cif.find_value('_symmetry_space_group_name_H-M')
    )
    assert group and gemmi.cif.as_string(group).replace(' ', '') == gemmi.cif.as_string(
        edi.find_value('_space_group.name_h_m')
    ).replace(' ', ''), 'The tutorial CIF preserves the example space group'
    fields = ('type_symbol', 'fract_x', 'fract_y', 'fract_z', 'occupancy', 'B_iso_or_equiv')
    actual_ids = list(cif.find_values('_atom_site_label')) or list(
        cif.find_values('_atom_site.label')
    )
    expected_ids = list(edi.find_values('_atom_site.id'))
    assert len(actual_ids) == len(set(actual_ids)) and set(actual_ids) == set(expected_ids), (
        'The tutorial CIF contains exactly the example atoms, without duplicates or omissions'
    )
    for field in fields:
        actual = list(cif.find_values('_atom_site_' + field)) or list(
            cif.find_values('_atom_site.' + field)
        )
        expected = list(
            edi.find_values('_atom_site.' + ('adp_iso' if field == 'B_iso_or_equiv' else field))
        )
        assert len(actual) == len(actual_ids) and len(expected) == len(expected_ids), (
            'Every tutorial atom carries every source quantity'
        )
        for label in expected_ids:
            a, b = actual[actual_ids.index(label)], expected[expected_ids.index(label)]
            assert a == b if field == 'type_symbol' else number(a) == number(b), (
                'The tutorial CIF preserves every example atom species, position, '
                'occupancy and Biso'
            )


def test_fitting_tutorial_starts_with_a_new_temporary_project():
    lesson = script()
    assert lesson['project'] == 'temporary', 'The learner project remains temporary'
    assert lesson.get('start') != 'new' and not str(lesson.get('start', '')).startswith(
        'example:'
    ), 'The tutorial never silently creates a project or opens a prepared example'
    steps = lesson['steps']
    actions = [step for step in steps if step.get('check')]
    assert (
        steps[0]['page'] == 'home'
        and steps[0]['target'] == 'home.start'
        and actions
        and [step['target'] for step in actions[:2]] == ['home.start', 'project.create']
    ), 'The learner starts on Home, then creates and names a project'
    assert lesson['completion'] == ['keep', 'discard'], (
        'The from-files tutorial retains the explicit Keep or Discard decision'
    )
    assert lesson['stop'] == 'restore-user-project', (
        'Stopping the from-files tutorial restores the user project'
    )


# These requirements are prose/content invariants; actual controls and numeric
# fitting are separately exercised by the Qt actor, never inferred from this table.
RECIPE = {
    'save-files': r'save.{0,50}(?:files|lbco\.cif)',
    'new-project': r'(?:create|new).{0,50}project',
    'load-cif': r'(?:load|open|import).{0,80}lbco\.cif',
    'load-xye': r'(?:load|open|import).{0,80}hrpt\.xye',
    'experiment-values': r'(?:wavelength|1\.494)',
    'automatic-background': (
        r'(?:automatic|auto|estimate).{0,40}background'
        r'|background.{0,40}(?:automatic|auto)'
    ),
    'unconstrained-biso': (
        r'(?:La.{0,30}Ba|Ba.{0,30}La).{0,90}(?:free|unconstrained|independent)'
        r'|(?:free|unconstrained|independent).{0,90}(?:La.{0,30}Ba|Ba.{0,30}La)'
    ),
    'uncertainty': r'(?:s\.u\.|uncertaint)',
    'correlation': r'correlation',
    'constraint': (
        r'(?:constraint|constrain|tie).{0,100}(?:La|Ba)'
        r'|(?:La|Ba).{0,100}(?:constraint|constrain|tie)'
    ),
    'report': r'report',
    'save-project': r'save.{0,40}project',
}


@pytest.mark.parametrize('requirement', RECIPE)
def test_fitting_script_contains_each_required_instruction(requirement):
    steps = script()['steps']
    assert any(re.search(RECIPE[requirement], step['text'], re.IGNORECASE) for step in steps), (
        'The from-files fitting lesson includes its required instruction: ' + requirement
    )


def test_fitting_recipe_orders_data_background_stages_and_constraint():
    steps = script()['steps']
    positions = {}
    for requirement, pattern in RECIPE.items():
        hits = [
            index
            for index, step in enumerate(steps)
            if re.search(pattern, step['text'], re.IGNORECASE)
        ]
        assert hits, (
            'The ordered fitting recipe includes every required instruction: ' + requirement
        )
        positions[requirement] = hits[0]
    for before, after in (
        ('new-project', 'save-files'),
        ('new-project', 'load-cif'),
        ('load-cif', 'load-xye'),
        ('load-xye', 'experiment-values'),
        ('experiment-values', 'automatic-background'),
        ('automatic-background', 'unconstrained-biso'),
        ('unconstrained-biso', 'uncertainty'),
        ('uncertainty', 'constraint'),
        ('correlation', 'constraint'),
        ('constraint', 'report'),
        ('report', 'save-project'),
    ):
        assert positions[before] < positions[after], (
            'The fitting lesson respects the scientific and file-loading dependency: '
            + before
            + ' before '
            + after
        )
    fits = [index for index, step in enumerate(steps) if step['target'] == 'statusBar.fit.button']
    assert (
        len(fits) >= 2
        and any(index < positions['constraint'] for index in fits)
        and any(index > positions['constraint'] for index in fits)
    ), 'A real fit precedes the La/Ba constraint and another follows it'
    stages = [
        step
        for step in steps[: positions['constraint']]
        if re.search(r'free|vary|select', step['text'], re.IGNORECASE)
    ]
    for group in ('scale', 'background', 'cell', 'peak', 'Biso|B_iso|displacement'):
        assert any(re.search(group, step['text'], re.IGNORECASE) for step in stages), (
            'Staged fitting explicitly introduces each physical parameter group: ' + group
        )
    assert len(stages) >= 2, (
        'Fitting groups are introduced in multiple stages before the constraint'
    )


@pytest.fixture(scope='module')
def actual_fitting_recipe(tmp_path_factory):
    folder = tmp_path_factory.mktemp('tutorial-files-host')
    source = (ROOT / 'tests/fixtures/tutorial_files/actor.qml').read_text()
    for marker, name in (('__TUTORIAL_CIF__', 'lbco.cif'), ('__TUTORIAL_XYE__', 'hrpt.xye')):
        candidates = list((SOURCE / 'app').rglob(name))
        # An absent bundle is independently red above. Still drive the real host
        # here so its new-project/save-step prerequisite has its own red proof.
        parent = candidates[0].parent if candidates else ROOT / 'app/tutorials'
        source = source.replace(marker, parent.as_uri())
    for helper in ('UiInteraction.js', 'RenderedTable.js'):
        source = source.replace(
            '"' + helper + '"', json.dumps((ROOT / 'tests/unit/app' / helper).as_uri())
        )
    actor = folder / 'tst_fitting_tutorial_files.qml'
    actor.write_text(source)
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'The file-based fitting tutorial requires the actual Qt host'
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(actor),
            '-o',
            '-,txt',
            'FittingTutorialFiles::test_saved_files_build_the_staged_fit_and_report',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=150,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
    )
    output = result.stdout + result.stderr
    (folder / 'actual-host.log').write_text(output)
    receipts = re.findall(r'TUTORIAL_FILE_CLAIMS (\[[^\r\n]*\])', output)
    return result.returncode, output, json.loads(receipts[-1]) if receipts else []


@pytest.mark.parametrize(
    'claim',
    [
        'new-project',
        'saved-files',
        'loaded-inputs',
        'experiment-values',
        'background',
        'staged-fits',
        'unconstrained-diagnostics',
        'constrained-fit',
        'example-quality',
        'report-and-save',
    ],
)
def test_actual_from_files_fitting_recipe(actual_fitting_recipe, claim):
    code, output, completed = actual_fitting_recipe
    assert not any(line.startswith('SKIP') for line in output.splitlines()), (
        'The actual fitting tutorial cannot substitute a skip for an input, fit or report'
    )
    assert claim in completed, (
        'The real tutorial must reach its required from-files state: ' + claim + '\n' + output
    )
    if claim == 'report-and-save':
        assert code == 0 and '0 failed' in output, (
            'The complete fitting tutorial finishes its real host run without a later failure'
        )


def test_experiment_type_is_taught_before_data_locks_it():
    steps = script()['steps']
    create = next(
        (i for i, step in enumerate(steps) if step['target'] == 'experiments.create'), -1
    )
    kind = next((i for i, step in enumerate(steps) if step['target'] == 'experimentType'), -1)
    data = next(
        (
            i
            for i, step in enumerate(steps)
            if re.search(r'(?:load|import).{0,80}hrpt\.xye', step['text'], re.IGNORECASE)
        ),
        -1,
    )
    assert 0 <= create < kind < data, (
        'Enabled-instruction class: experiment type is taught after creation '
        'and before data locks its choices'
    )


def test_every_staged_free_set_teaches_category_header_and_clear():
    steps = script()['steps']
    previous_fit = -1
    for category in ('background', 'scale', 'cell', 'peak', 'atomic displacements'):
        choices = [
            i
            for i, step in enumerate(steps)
            if i > previous_fit
            and step['target'] == 'parameters.category'
            and category in step['text'].lower()
        ]
        assert choices, 'Each staged free set targets the category chooser: ' + category
        choose = choices[0]
        if previous_fit >= 0:
            assert any(
                step['target'] == 'parameters.clearFilters'
                for step in steps[previous_fit + 1 : choose]
            ), 'A clear-filter action separates consecutive fitting categories'
        free = next(
            (
                i
                for i in range(choose + 1, len(steps))
                if steps[i]['target'] == 'parameters.freeHeader'
            ),
            -1,
        )
        assert free > choose and re.search(r'filter|shown', steps[free]['text'], re.IGNORECASE), (
            'Each category is followed by its real free-column menu explaining filtered rows'
        )
        fit = next(
            (
                i
                for i in range(free + 1, len(steps))
                if steps[i]['target'] == 'statusBar.fit.button'
            ),
            -1,
        )
        assert fit > free, 'Each staged release is followed by an actual fit instruction'
        previous_fit = fit


def test_fit_results_are_explained_at_their_actual_ok_control():
    steps = script()['steps']
    results = [step for step in steps if 'fit.results' in step['target']]
    assert results, 'Modal-callout coverage includes a real fit-results target'
    assert any(
        all(
            re.search(word, step['text'], re.IGNORECASE)
            for word in ('status', r'chi|χ', r'\bR', 'dataset', r'\bOK\b')
        )
        for step in results
    ), 'The fit-results instruction explains status, reduced chi-square, dataset R values and OK'


def test_constrained_fit_is_reviewed_before_report():
    steps = script()['steps']
    constraint = next(
        (i for i, step in enumerate(steps) if step['target'] == 'constraints.append'), -1
    )
    fit = next(
        (
            i
            for i in range(constraint + 1, len(steps))
            if steps[i]['target'] == 'statusBar.fit.button'
        ),
        -1,
    )
    report = next((i for i in range(fit + 1, len(steps)) if steps[i].get('page') == 'report'), -1)
    assert constraint >= 0 and fit > constraint and report > fit, (
        'The final scientific review follows the constrained fit and precedes Report'
    )
    sequence = [step['target'] for step in steps[fit + 1 : report]]
    expected = [
        'mainArea.analysis.tab.correlations',
        'mainArea.analysis.tab.fitting',
        'parameters.list',
    ]
    positions = [
        next((i for i, target in enumerate(sequence) if target == name), -1) for name in expected
    ]
    assert 0 <= positions[0] < positions[1] < positions[2], (
        'After the constrained fit the lesson reviews Correlations, Pattern, '
        'then parameters in that order'
    )

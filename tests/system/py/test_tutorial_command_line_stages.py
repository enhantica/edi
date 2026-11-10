"""Owner 4cf15ae54: execute visible Command line stages against Python and regression pins."""

import json
import os
import re
import shutil
import subprocess
import sys
from itertools import accumulate

import pytest

from tests.fixtures.tutorial_cases.command_line import actions, edit_project, visible_flag_edits
from tests.fixtures.tutorial_cases.contract import ROOT, interfaces_for
from tests.fixtures.tutorial_cases.pins import compare_regression_pin, machine_values, pinned_start
from tests.fixtures.tutorial_cases.stages import group, observe
from tests.integration.py.test_tutorial_empty_project import api
from tests.integration.py.test_tutorial_fit_stages import FITTING, source


@pytest.mark.parametrize('case', [case for case in FITTING if 'cli' in interfaces_for(case)])
def test_visible_command_line_edits_and_fits_match_python_stages_and_final_pin(case, tmp_path):  # noqa: PLR0914 - observable whole workflow, no hidden fit helper
    page = ROOT / 'website/surfaces/docs/cli/tutorials/cases' / (case + '.md')
    assert page.is_file(), (
        'Gate 5: the executable Command line lesson is a local user page: ' + case
    )
    text = page.read_text()
    steps = actions(text)
    fits = [step for step in steps if step[0] == 'fit']
    assert len(fits) >= 2 and any(
        step[0] == 'download' for step in steps[: steps.index(fits[0])]
    ), 'Gate 5: the visible lesson gets its case and runs successive actual edi fit stages'
    assert any(step[0] in {'edit', 'free-rows'} and '()' in step[2] for step in steps), (
        'Gate 5: the Command line lesson teaches selecting free parameters with empty brackets'
    )
    if case == 'pd-neut-cwl_lbco-hrpt':
        explanation = re.sub(r'\s+', ' ', text.casefold())
        assert 'starting project' in explanation and re.search(
            r'\bbuilding (?:a |the )?project by hand (?:on|from) the command line is planned\b',
            explanation,
        ), (
            'Gate 5: LBCO explains that it loads a starting project and that building the '
            'project by hand on the command line is planned'
        )
    quantities = pinned_start(case)
    first_arguments = fits[0][1]
    assert first_arguments and not first_arguments[0].startswith('-'), (
        'Gate 5: each visible fit names its project'
    )
    project = tmp_path / first_arguments[0]
    assert project.resolve().is_relative_to(tmp_path), (
        'Gate 5: tutorial commands stay in their fresh work folder'
    )
    shutil.copytree(ROOT / 'docs/user/cli' / case / 'project', project)
    expected = (
        observe(source(case, 'script'))['cycles'] if 'python' in interfaces_for(case) else None
    )
    totals = list(accumulate(cycle['constraints'] for cycle in expected)) if expected else None
    actual = []
    final = None
    for operation, argument, body in steps:
        if operation == 'edit':
            edit_project(project, argument, body)
        elif operation in {'clear-free', 'free-rows'}:
            visible_flag_edits(project, argument, body if operation == 'free-rows' else None)
        elif operation in {'fit', 'calc'}:
            if operation == 'fit':
                loaded = api().Project.load(project)
                parameters = json.loads(
                    loaded.report.model(excluded=['data', 'reflections']).to_json()
                )['parameters']
                active = sorted({group(row['unique_name']) for row in parameters if row['free']})
                actual.append({'active': active, 'constraints': len(loaded.analysis.constraints)})
            # Report selection only changes presentation. Preserve every scientific option
            # and execute exactly one real fit per displayed stage, retaining full precision.
            arguments = list(argument)
            assert (tmp_path / arguments[0]).resolve() == project.resolve(), (
                'Gate 5: every stage fits the same progressively edited project'
            )
            arguments[0] = str(project.resolve())
            for option in ['--report', '--verbosity']:
                if option in arguments:
                    at = arguments.index(option)
                    del arguments[at : at + 2]
            run = subprocess.run(
                [
                    sys.executable,
                    '-m',
                    'edi',
                    operation,
                    *arguments,
                    '--report',
                    'machine',
                    '--verbosity',
                    'full',
                ],
                cwd=tmp_path,
                capture_output=True,
                text=True,
                check=False,
                timeout=3600,
                env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
            )
            assert run.returncode == 0, (
                'Gate 5: every visible stage executes successfully: ' + run.stderr
            )
            if operation == 'fit':
                final = run.stdout
    if expected is not None:
        assert actual == [
            {'active': cycle['active'], 'constraints': total}
            for cycle, total in zip(expected, totals, strict=True)
        ], 'Gate 5: declared Command line and Python lessons share their exact stage sequence'
    compare_regression_pin(machine_values(final), quantities)


@pytest.mark.parametrize(
    'damage', ['unchanged', 'staged-model', 'measured-file', 'redirected-input', 'extra-model']
)
def test_stage_fit_admission_preserves_the_catalogue_measurements(tmp_path, damage):
    project = tmp_path / 'project'
    shutil.copytree(ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt/project', project)
    if damage == 'staged-model':
        path = next((project / 'structures').glob('*.edi'))
        path.write_text(path.read_text().replace('_cell.length_a 3.88()', '_cell.length_a 3.89()'))
    elif damage == 'extra-model':
        (project / 'unknown.edi').write_text('data_unknown\n')
    elif damage == 'measured-file':
        path = next((project / 'experiments').glob('*.edi'))
        original = path.read_text()
        changed = re.sub(r'(?m)^10(\s+\d)', r'10.025\1', original, count=1)
        assert changed != original, (
            'Gate 5: the refusal control actually changes a measured coordinate'
        )
        path.write_text(changed)
    loaded = api().Project.load(project)
    if damage == 'redirected-input':
        measured = loaded.experiments[0].data
        values = list(measured.intensity_meas)
        values[0] += 11
        measured.intensity_meas = values
        loaded.save()
        loaded = api().Project.load(project)
    with pytest.raises((TypeError, RuntimeError)) as caught:
        loaded.fit(case_gate_invalid_operand=True)
    expected = 'TypeError' if damage in {'unchanged', 'staged-model'} else 'FitPolicyViolation'
    assert type(caught.value).__name__ == expected, (
        'Gate 5: stages preserve measured data and model inventory: ' + str(caught.value)
    )


def test_visible_edit_observer_applies_real_scalar_and_loop_brackets_without_changing_other_values(
    tmp_path,
):
    root = tmp_path / 'project'
    root.mkdir()
    path = root / 'sample.edi'
    path.write_text(
        'data_sample\n_cell.length_a 3.88\n_cell.length_b 3.88\n'
        'loop_\n_atom_site.id\n_atom_site.fract_z\nLa 0.125\nCo 0.25\n'
    )
    edit_project(
        root,
        'sample.edi',
        '_cell.length_a 3.88()\nloop_\n_atom_site.id\n_atom_site.fract_z\nCo 0.25()\n',
    )
    assert '_cell.length_a 3.88()' in path.read_text() and 'Co 0.25()' in path.read_text(), (
        'Gate 5: visible edits free the scalar and the identified loop parameter'
    )
    assert '_cell.length_b 3.88\n' in path.read_text() and 'La 0.125\n' in path.read_text(), (
        'Gate 5: unmentioned project values remain byte-identical'
    )


@pytest.mark.parametrize('damage', ['no-file', 'outside', 'ambiguous-row'])
def test_visible_edit_observer_refuses_missing_context_and_escaping_paths(tmp_path, damage):
    path = tmp_path / 'sample.edi'
    path.write_text('data_sample\nloop_\n_atom_site.id\n_atom_site.fract_z\nLa 0.125\nLa 0.25\n')
    filename = {
        'no-file': 'missing.edi',
        'outside': '../sample.edi',
        'ambiguous-row': 'sample.edi',
    }[damage]
    with pytest.raises(AssertionError, match='Gate 5:'):
        edit_project(tmp_path, filename, 'loop_\n_atom_site.id\n_atom_site.fract_z\nLa 0.25()\n')


def test_visible_stage_reader_executes_one_route_of_the_linked_command_tabs():
    document = (
        '=== "Standalone executable"\n\n    ```sh\n    edi download-data sample\n'
        '    edi fit project\n    ```\n\n=== "Python package"\n\n'
        '    ```sh\n    python -m edi download-data sample\n'
        '    python -m edi fit project\n    ```\n'
    )
    operations = actions(document)
    assert [step[0] for step in operations] == ['download', 'fit'], (
        'Gate 5: indented linked tabs do not duplicate the scientific fit cycle'
    )


def test_visible_flag_instructions_keep_previous_fit_values_and_expand_counted_uniform_rows(
    tmp_path,
):
    path = tmp_path / 'sample.edi'
    path.write_text(
        'data_sample\n_cell.length_a 3.912(3)\nloop_\n_background.id\n'
        '_background.position\n_background.intensity\n1 8 321.25\n2 9 319.125\n3 10 318.75\n'
    )
    visible_flag_edits(tmp_path, 'sample.edi')
    visible_flag_edits(tmp_path, 'sample.edi', '1 8 340()\n2 9 340()\n… and 1 more lines\n')
    assert '_cell.length_a 3.912\n' in path.read_text() and '1 8 321.25()' in path.read_text(), (
        'Gate 5: marker instructions preserve actual values rather than resetting an earlier fit'
    )
    assert '2 9 319.125()' in path.read_text() and '3 10 318.75()' in path.read_text(), (
        'Gate 5: a counted uniform remainder applies the same visible flag edit to its loop'
    )


def test_visible_relation_edits_can_add_and_update_alias_and_constraint_loops(tmp_path):
    path = tmp_path / 'analysis.edi'
    path.write_text('_fitting_mode.type single\n')
    edit_project(
        tmp_path,
        'analysis.edi',
        'La phase.atom_site.La.adp_iso\nBa phase.atom_site.Ba.adp_iso\nBa "Ba = La"\n',
    )
    assert (
        '_alias.parameter_unique_name' in path.read_text()
        and '_constraint.expression' in path.read_text()
    ), 'Gate 5: explicitly named alias and constraint rows create their standard CIF loops'
    edit_project(tmp_path, 'analysis.edi', 'Ba "Ba = 2*La"\n')
    assert 'Ba "Ba = 2*La"' in path.read_text() and 'Ba "Ba = La"' not in path.read_text(), (
        'Gate 5: updating a displayed constraint retains its identity without duplicating its row'
    )

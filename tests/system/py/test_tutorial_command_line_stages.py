"""Owner 4cf15ae54: execute visible Command line stages against Python and regression pins."""

import os
import re
import shutil
import subprocess

import pytest

from tests.fixtures.tutorial_cases.command_line import (
    actions,
    compare_staged_regression_pin,
    delete_loop,
    edit_project,
    visible_flag_edits,
)
from tests.fixtures.tutorial_cases.contract import ROOT
from tests.integration.py.test_tutorial_empty_project import api


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


def test_staged_pin_keeps_outcomes_strict_and_checks_its_own_work_trace():
    quantities = {
        'iterations': {'value': 5, 'tol_abs': 0, 'tol_rel': None},
        'reduced_chi_square': {'value': 1.25, 'tol_abs': 0, 'tol_rel': None},
        'n_free': {'value': 3, 'tol_abs': 0, 'tol_rel': None},
    }
    actual = {
        'status': 'done',
        'converged': 'true',
        'iterations': '1',
        'iter.1.rwp': '0.125',
        'reduced_chi_square': '1.25',
        'n_free': '3',
    }
    compare_staged_regression_pin(actual, quantities)
    for damage in [
        {'reduced_chi_square': '1.26'},
        {'n_free': '4'},
        {'converged': 'false'},
        {'iterations': '2'},
        {'iter.2.rwp': '0.12'},
    ]:
        with pytest.raises(AssertionError, match=r'Gate [25]:'):
            compare_staged_regression_pin({**actual, **damage}, quantities)


def test_visible_loop_deletion_is_read_from_the_actual_taurine_instruction():
    page = ROOT / 'website/surfaces/docs/cli/tutorials/cases/sc-neut-tof_taurine-senju.md'
    operations = actions(page.read_text())
    deletions = [step for step in operations if step[0] == 'delete-loop']
    assert len(deletions) == 1 and deletions[0][1] == 'structures/taurine.edi', (
        'Gate 5: the published deletion names exactly its real anisotropic loop and file'
    )
    assert deletions[0][2].splitlines() == [
        '_atom_site_aniso.id',
        '_atom_site_aniso.adp_11',
        '_atom_site_aniso.adp_22',
        '_atom_site_aniso.adp_33',
        '_atom_site_aniso.adp_12',
        '_atom_site_aniso.adp_13',
        '_atom_site_aniso.adp_23',
    ], 'Gate 5: the written deletion retains the complete actual tensor column declaration'


@pytest.mark.parametrize('newline', ['\n', '\r\n'])
def test_visible_loop_deletion_preserves_every_other_original_byte(tmp_path, newline):
    before = 'data_sample\n_cell.length_a 3.14159\n# retained prefix β\n'
    loop = 'loop_\n_atom_site_aniso.id\n_atom_site_aniso.adp_11\nS1 0.125\nO1 0.25\n'
    after = '\n# retained suffix β\nloop_\n_atom_site.id\n_atom_site.fract_z\nS1 0.375\n'
    path = tmp_path / 'sample.edi'
    path.write_bytes((before + loop + after).replace('\n', newline).encode())
    delete_loop(tmp_path, 'sample.edi', '_atom_site_aniso.id\n_atom_site_aniso.adp_11\n')
    assert path.read_bytes() == (before + after).replace('\n', newline).encode(), (
        'Gate 5: deletion removes only its named loop; all other bytes and line endings survive'
    )


@pytest.mark.parametrize(
    'damage', ['partial', 'missing', 'duplicate', 'row', 'outside', 'symlink']
)
def test_visible_loop_deletion_refuses_ambiguous_or_escaping_targets(tmp_path, damage):
    project = tmp_path / 'project'
    project.mkdir()
    text = 'data_sample\nloop_\n_atom_site_aniso.id\n_atom_site_aniso.adp_11\nS1 0.125\n'
    path = project / 'sample.edi'
    path.write_text(text)
    filename = 'sample.edi'
    tags = '_atom_site_aniso.id\n_atom_site_aniso.adp_11\n'
    if damage == 'partial':
        tags = '_atom_site_aniso.id\n'
    elif damage == 'missing':
        tags = '_background.id\n_background.intensity\n'
    elif damage == 'duplicate':
        path.write_text(text + text.removeprefix('data_sample\n'))
    elif damage == 'row':
        tags += 'S1 0.125\n'
    elif damage == 'outside':
        filename = '../sample.edi'
    elif damage == 'symlink':
        path.unlink()
        external = tmp_path / 'outside'
        external.mkdir()
        (external / 'sample.edi').write_text(text)
        alias = project / 'external'
        if os.name == 'nt':
            subprocess.run(
                ['cmd.exe', '/d', '/c', 'mklink', '/J', str(alias), str(external)],
                check=True,
                capture_output=True,
            )
        else:
            alias.symlink_to(external, target_is_directory=True)
        filename = 'external/sample.edi'
        path = alias / 'sample.edi'
    before = path.read_bytes()
    with pytest.raises(AssertionError, match='Gate 5:'):
        delete_loop(project, filename, tags)
    assert path.read_bytes() == before, (
        'Gate 5: an inadmissible loop deletion leaves the original target unchanged'
    )

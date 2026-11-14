"""Independent controls for literal tutorial instructions and origin observation."""

import pytest

from tests.fixtures.tutorial_cases.command_line import (
    actions,
    setup_action,
    visible_flag_edits,
    write_project,
)
from tests.fixtures.tutorial_cases.stages import app_cycles, prose_cycles
from tests.fixtures.tutorial_recipe.reference import significant
from tools.testing.fit_policy import (
    _cli_fit_origin,  # noqa: PLC2701 - direct argv observer control
)


def test_written_member_subgroups_keep_repeated_category_releases_and_block_scope():
    population = {
        'sample.peak.broad_gauss_u': ('peak widths', 'sample'),
        'sample.peak.broad_lorentz_x': ('peak widths', 'sample'),
        'other.peak.broad_lorentz_x': ('peak widths', 'other'),
        'sample.absorption.correction': ('absorption', 'sample'),
        'structure.atom_site_aniso.A.adp_11': ('anisotropic displacement', 'structure'),
    }
    prose = (
        '## Gaussian widths\n\nChoose sample in the datablock filter, then tick Free for '
        'the Peak broadening rows the stage names, then press Fit.\n\n'
        '## Lorentzian widths\n\nChoose sample in the datablock filter, then tick Free for '
        'the Peak broadening rows the stage names, then press Fit.\n\n'
        '## Second block\n\nChoose other in the datablock filter, then tick Free for '
        'the Peak broadening rows the stage names, then press Fit.\n\n'
        '## Absorption\n\nTick Free for Absorption, then press Fit.\n\n'
        '## Displacements\n\nFilter Atomic displacement, choose Free · all, then press Fit.'
    )
    steps = []
    for path in population:
        steps += [{'check': 'tick:' + path}, {'check': 'fit-done'}]
    assert prose_cycles(prose, population) == app_cycles(steps, population), (
        'Written instructions retain each newly released member, selected block, absorption '
        'and the offered tensor displacement type before reducing to scientific groups'
    )
    damaged = prose.replace('## Lorentzian widths', '## Gaussian widths')
    assert prose_cycles(damaged, population) != prose_cycles(prose, population), (
        'Releasing the same Gaussian members twice cannot impersonate the Lorentzian stage'
    )
    assert prose_cycles(
        prose.replace('Choose other', 'Choose sample'), population
    ) != prose_cycles(prose, population), (
        'Selecting an already active block cannot impersonate a newly released block'
    )


@pytest.mark.parametrize('operand', ['sample', 'temperature-55K', 'folder with spaces'])
def test_cli_origin_is_the_actual_operand_relative_to_the_launch_directory(tmp_path, operand):
    argv = ['python', '-m', 'edi', 'fit', operand, '--output', 'unrelated-project']
    assert _cli_fit_origin(argv, tmp_path) == str((tmp_path / operand).resolve()), (
        'Fit admission observes the positional project operand, including ordinary names, '
        'rather than a project substring in an unrelated option'
    )
    assert _cli_fit_origin(['edi', 'fit', '--report', 'machine'], tmp_path) is None, (
        'A missing positional project remains unattested; an option is never a corpus origin'
    )


def test_visible_setup_is_executable_once_and_keeps_its_new_file_bytes(tmp_path):
    page = """mkdir example

```console
mkdir -p example/structures example/analysis
edi download-data example-sample
mv data/example-sample.edi example/structures/sample.edi
```

Write `project.edi`:

```edi
_edi.schema_version 3
```
"""
    operations = actions(page)
    assert [row[0] for row in operations] == ['mkdir', 'download', 'move', 'write'], (
        'The visible reader retains construction in order rather than copying a finished project'
    )
    setup_action(tmp_path, *operations[0][:2])
    (tmp_path / 'data').mkdir()
    payload = b'data_sample\n_cell.length_a 4.271\n'
    (tmp_path / 'data/example-sample.edi').write_bytes(payload)
    setup_action(tmp_path, *operations[2][:2])
    write_project(tmp_path / 'example', operations[3][1], operations[3][2])
    assert (tmp_path / 'example/structures/sample.edi').read_bytes() == payload, (
        'A visible move preserves the independently supplied downloaded block exactly'
    )
    assert (tmp_path / 'example/project.edi').read_text() == '_edi.schema_version 3\n', (
        'A visible Write supplies complete initial text even without a data_ block header'
    )
    with pytest.raises(AssertionError, match='Gate 5:'):
        write_project(tmp_path / 'example', 'project.edi', 'replacement')
    with pytest.raises(AssertionError, match='Gate 5:'):
        setup_action(tmp_path, 'mkdir', ['../outside'])
    assert (tmp_path / 'example/project.edi').read_text(
        encoding='utf-8'
    ) == '_edi.schema_version 3\n', (
        'A refused duplicate Write cannot silently replace a previously taught project record'
    )


@pytest.mark.parametrize(
    'action', ['tick:experiment.scale', 'untick:structure.atom_sites.A.adp_iso']
)
def test_current_recipe_row_actions_are_scientific_and_misspellings_refuse(action):
    assert significant({'id': 'parameter-stage'}, action), (
        'A current row-checkbox action is scientific and must reach the deletion mutation gate'
    )
    with pytest.raises(ValueError, match='Unclassified docs recipe action'):
        significant({'id': 'parameter-stage'}, action.replace(':', 'X:', 1))


def test_written_table_context_disambiguates_identical_keys_without_changing_other_loops(tmp_path):
    path = tmp_path / 'sample.edi'
    path.write_text(
        'data_sample\nloop_\n_excluded_region.id\n_excluded_region.start\n_excluded_region.end\n'
        '1 0 140\nloop_\n_background.id\n_background.position\n_background.intensity\n1 0 140\n'
    )
    with pytest.raises(AssertionError, match='Gate 5:'):
        visible_flag_edits(tmp_path, 'sample.edi', '1 0 140()\n')
    visible_flag_edits(tmp_path, 'sample.edi', '# tutorial-heading: Background\n1 0 140()\n')
    text = path.read_text()
    assert '_excluded_region.end\n1 0 140\n' in text, (
        'A named Background stage preserves an identical row in the exclusions table'
    )
    assert '_background.intensity\n1 0 140()\n' in text, (
        'Only the uniquely identified actual Background row receives the displayed free marker'
    )

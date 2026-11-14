"""Independent controls for literal tutorial instructions and origin observation."""

from types import SimpleNamespace

import pytest

from tests.fixtures.tutorial_cases.command_line import (
    actions,
    edit_project,
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


def test_cli_first_terms_scope_keeps_higher_coefficients_fixed_and_count_exact(tmp_path):
    path = tmp_path / 'sample.edi'
    initial = (
        'data_sample\nloop_\n_background.id\n_background.order\n_background.coef\n'
        + ''.join(f'{i} {i - 1} 0\n' for i in range(1, 6))
    )
    path.write_text(initial)
    excerpt = (
        '# tutorial-heading: Background\n'
        '# tutorial-scope: The first three polynomial terms; higher ones stay at zero.\n'
        '1 0 0()\n2 1 0()\n… and 1 more lines\n'
    )
    visible_flag_edits(tmp_path, 'sample.edi', excerpt)
    assert path.read_text() == initial.replace(
        '1 0 0\n2 1 0\n3 2 0', '1 0 0()\n2 1 0()\n3 2 0()'
    ), (
        'The literal first-three instruction frees those coefficients '
        'and preserves the higher terms'
    )
    path.write_text(initial)
    with pytest.raises(AssertionError, match='stated omitted-line count'):
        visible_flag_edits(tmp_path, 'sample.edi', excerpt.replace('1 more', '2 more'))


def test_cli_atomic_remainder_observes_independent_members_and_new_markers(tmp_path, monkeypatch):
    import edi  # noqa: PLC0415 - requires the exported native module only in this control

    def parameter(fixed):
        return SimpleNamespace(symmetry_constrained=fixed, user_constrained=False)

    sites = {
        name: SimpleNamespace(
            fract_x=parameter(name == 'A'),
            fract_y=parameter(name != 'D'),
            fract_z=parameter(name == 'A'),
        )
        for name in ['A', 'B', 'C', 'D']
    }
    model = SimpleNamespace(structures=[SimpleNamespace(name='sample', atom_sites=sites)])
    monkeypatch.setattr(edi.Project, 'load', staticmethod(lambda _path: model))
    path = tmp_path / 'sample.edi'
    initial = (
        'data_sample\nloop_\n_atom_site.id\n_atom_site.type_symbol\n_atom_site.fract_x\n'
        '_atom_site.fract_y\n_atom_site.fract_z\n'
        'A O 0 0 0\nB O 0.12 0.25 0.34\nC O 0.22 0.25 0.44\nD O 0.3 0.4 0.5\n'
    )
    path.write_text(initial)
    excerpt = 'B O 0.12() 0.25 0.34()\nC O 0.22() 0.25 0.44()\n… and 1 more lines\n'
    visible_flag_edits(tmp_path, 'sample.edi', excerpt)
    assert path.read_text().endswith(
        'A O 0 0 0\nB O 0.12() 0.25 0.34()\nC O 0.22() 0.25 0.44()\nD O 0.3() 0.4() 0.5()\n'
    ), (
        'The atomic remainder excludes the fixed site and observes the omitted general site y, '
        'rather than copying the two special-site column masks'
    )
    path.write_text(initial)
    with pytest.raises(AssertionError, match='stated omitted-line count'):
        visible_flag_edits(tmp_path, 'sample.edi', excerpt.replace('1 more', '2 more'))
    path.write_text(initial)
    with pytest.raises(AssertionError, match='shown atomic marker'):
        visible_flag_edits(tmp_path, 'sample.edi', excerpt.replace('0.25', '0.25()', 1))


def test_explicit_headerless_reset_changes_only_its_unique_complete_row(tmp_path):
    path = tmp_path / 'sample.edi'
    initial = (
        'data_sample\nloop_\n_atom_site.id\n_atom_site.type_symbol\n_atom_site.adp_iso\n'
        'A O -0.12()\nB O 0.42()\n'
    )
    path.write_text(initial)
    edit_project(tmp_path, 'sample.edi', 'A O 0.5()\n')
    assert path.read_text() == initial.replace('A O -0.12()', 'A O 0.5()'), (
        'An explicit literal reset writes its displayed values and preserves every other row'
    )
    with pytest.raises(AssertionError, match='complete actual row'):
        edit_project(tmp_path, 'sample.edi', 'A O 0.8() extra_column\n')
    assert 'B O 0.42()\n' in path.read_text(), (
        'A refused reset with the wrong column count cannot change another scientific row'
    )


def test_cli_remainder_owns_its_last_loop_and_preserves_named_bank_endpoints(tmp_path):
    path = tmp_path / 'bank_1_10.edi'
    initial = (
        '_peak.broad_gauss_u 0.2\nloop_\n_background.id\n'
        '_background.position\n_background.intensity\n'
        + ''.join(f'{i} {i * 10} 100\n' for i in range(1, 7))
    )
    path.write_text(initial)
    excerpt = (
        "# tutorial-scope: Bank 1-10's first and last stay fixed.\n"
        '_peak.broad_gauss_u 0.2()\n'
        '2 20 100()\n3 30 100()\n… and 2 more lines\n'
    )
    visible_flag_edits(tmp_path, path.name, excerpt)
    text = path.read_text()
    assert text.startswith('_peak.broad_gauss_u 0.2()\n') and text.endswith('6 60 100\n'), (
        'The abbreviation scopes its final loop and preserves the earlier scalar edit'
    )
    assert '1 10 100\n' in text and '5 50 100()\n' in text, (
        'The named bank first/last exception preserves both endpoints and releases the interior'
    )
    path.write_text(initial)
    with pytest.raises(AssertionError, match='stated omitted-line count'):
        visible_flag_edits(tmp_path, path.name, excerpt.replace('Bank 1-10', 'Bank 2-9'))


def test_cli_historical_columns_keep_free_marks_on_their_original_named_member(tmp_path):
    path = tmp_path / 'sample.edi'
    path.write_text('data_sample\nloop_\n_atom_site.id\n_atom_site.adp_iso\nA 0.3\n')
    schemas = [['_atom_site.id', '_atom_site.symmetry_multiplicity', '_atom_site.adp_iso']]
    visible_flag_edits(tmp_path, path.name, 'A 4 0.3()\n', schemas=schemas)
    assert path.read_text().endswith('A 0.3()\n'), (
        'An actual source-schema column removed by the writer cannot shift the requested ADP mark'
    )
    with pytest.raises(AssertionError, match='column absent after saving'):
        visible_flag_edits(tmp_path, path.name, 'A 4() 0.3\n', schemas=schemas)
    edit_project(tmp_path, path.name, 'A 4 0.5()\n', schemas=schemas)
    assert path.read_text().endswith('A 0.5()\n'), (
        'A literal reset follows the same independently observed historical column names'
    )


def test_named_relation_prose_completes_only_its_explicit_alias_endpoints():
    page = """## Constrain displacements

Constrain B's to follow A's.

In `analysis/analysis.edi`, add these rows to its alias and constraint loops:

```edi
b_a sample.atom_site.A.adp_iso
b_b sample.atom_site.B.adp_iso
```

The same for every other row (1 more).
"""
    edits = [row[2] for row in actions(page) if row[0] == 'edit']
    assert len(edits) == 2 and 'b_b = b_a' in edits[-1], (
        'The one omitted relation follows the explicitly named dependent and independent aliases'
    )
    changed = page.replace("Constrain B's to follow A's", "Constrain A's to follow B's")
    assert actions(changed)[-1] != actions(page)[-1], (
        'Reversing the written dependency must reverse the observed relation, not reuse an oracle'
    )
    with pytest.raises(AssertionError, match='one written alias'):
        actions(page.replace('b_b sample.atom_site.B.adp_iso', 'b_c sample.atom_site.C.adp_iso'))


def test_cli_magnetic_remainder_preserves_each_sites_independent_components(tmp_path, monkeypatch):
    import edi  # noqa: PLC0415 - exported native type is only needed by this observer control

    def parameter(fixed):
        return SimpleNamespace(symmetry_constrained=fixed, user_constrained=False)

    moments = {
        'Co1': SimpleNamespace(**{f'crystalaxis_{axis}': parameter(False) for axis in 'xyz'}),
        'Co2': SimpleNamespace(**{
            f'crystalaxis_{axis}': parameter(axis != 'y') for axis in 'xyz'
        }),
        'Co3': SimpleNamespace(**{
            f'crystalaxis_{axis}': parameter(axis != 'z') for axis in 'xyz'
        }),
    }
    block = SimpleNamespace(
        name='sample',
        atom_sites=dict.fromkeys(moments, SimpleNamespace()),
        atom_site_moment=moments,
    )
    monkeypatch.setattr(
        edi.Project, 'load', staticmethod(lambda _path: SimpleNamespace(structures=[block]))
    )
    path = tmp_path / 'sample.edi'
    initial = (
        'data_sample\nloop_\n_atom_site_moment.label\n_atom_site_moment.crystalaxis_x\n'
        '_atom_site_moment.crystalaxis_y\n_atom_site_moment.crystalaxis_z\n_atom_site_moment.symmform\n'
        'Co1 0 1 0 Mx,My,Mz\nCo2 0 2 0 0,My,0\nCo3 0 0 3 0,0,Mz\n'
    )
    path.write_text(initial)
    excerpt = 'Co1 0() 1() 0() Mx,My,Mz\nCo2 0 2() 0 0,My,0\n… and 1 more lines\n'
    visible_flag_edits(tmp_path, path.name, excerpt)
    assert path.read_text().endswith(
        'Co1 0() 1() 0() Mx,My,Mz\nCo2 0 2() 0 0,My,0\nCo3 0 0 3() 0,0,Mz\n'
    ), 'Each omitted magnetic site releases only its own independent components, not a copied mask'
    path.write_text(initial)
    with pytest.raises(AssertionError, match='shown atomic marker'):
        visible_flag_edits(tmp_path, path.name, excerpt.replace('Co2 0 2()', 'Co2 0() 2()'))

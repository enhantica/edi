"""gate 6: frozen full population, independent token comparison and named outcomes."""

import hashlib
import json
import operator
import re
import sys
import zipfile
from pathlib import Path

import pytest

from tests.fixtures.c34_t28_baseline.generate_bytes import observe
from tests.fixtures.constraint_expressions.ncaf_follower_bytes import historical_followers
from tests.fixtures.cwl_family.historical import current_tokens

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tests/integration/py'))
sys.path.insert(0, str(ROOT / 'tests/unit/py'))
from c13_t12_support import delimiter_only, engine, normalized_record, snapshot  # noqa: E402
from e04_t5_calculator_bytes import without_calculator  # noqa: E402

FIXTURE = ROOT / 'tests/fixtures/c13_t12_ids'
BASELINE = json.loads((FIXTURE / 'baseline.json').read_text())


def test_baseline_anchor_is_main_reachable_and_population_is_total():
    records = BASELINE['candidates']
    accepted = {row['path_sha256'] for row in records if row.get('accepted')}
    assert accepted == {
        hashlib.sha256(row['path'].encode()).hexdigest() for row in BASELINE['accepted']
    }, ' every fork-point accepted project must remain in the comparison population'
    # Reconstruct every tracked directory from the immutable tree, hidden tiers included.
    directory_hashes = json.loads(
        (ROOT / 'tests/fixtures/e04_t12_public_release/history/population.json').read_text()
    )
    assert directory_hashes and len(directory_hashes) == len(set(directory_hashes)), (
        'the retained full population inventory must be nonempty and unique'
    )
    assert {row['path_sha256'] for row in records} == set(directory_hashes), (
        'the corpus must include every independently inventoried historical directory'
    )


def restore_frozen(row, tmp_path):
    with zipfile.ZipFile(FIXTURE / 'baseline.zip') as frozen:
        prefix = row['archive'] + '/input/'
        for name in frozen.namelist():
            if name.startswith(prefix):
                path = tmp_path / 'input' / name[len(prefix) :]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(current_tokens(frozen.read(name)))
        return {
            name: frozen.read(row['archive'] + '/saved/' + name) for name in row.get('files', {})
        }


def without_new_geom(name, source, saved):
    """Compare the old byte oracle after proving the one newly retained input block."""
    if not name.startswith('structures/'):
        return saved
    original = source.read_bytes()
    declarations = (
        b'_geom.min_bond_distance_cutoff 0.\n',
        b'_geom.bond_distance_inc 0.25\n',
    )
    if all(original.count(line) == 1 for line in declarations):
        emitted = b'_geom.min_bond_distance_cutoff 0\n_geom.bond_distance_inc 0.25\n'
        assert saved.count(emitted) == 1, (
            ' preserves each declared geom value once in the saved structure'
        )
        assert saved.count(b'\n' + emitted) == 1, (
            ' the new geom block has its own separator, not a changed prior field'
        )
        return saved.replace(b'\n' + emitted, b'', 1)
    assert not any(line.startswith(b'_geom.') for line in original.splitlines()), (
        ' the frozen input geom declaration changed and needs a new explicit oracle'
    )
    assert not re.search(rb'(?m)^_geom\.', saved), (
        ' an undeclared geom default must remain absent on save'
    )
    return saved


def retain_follower_witness(project, after):
    follower_projects = {
        'docs/user/cli/pd-neut-tof_ncaf-wish-3bank_start-5/project',
        'tests/fixtures/c09_t6_ncaf_5bank_absorption/expected/desired_writer/jvd_absorption',
        'tests/fixtures/e02_t2_ncaf_5bank/project',
    }
    if project in follower_projects:
        after['structures/ncaf.edi'] = historical_followers(
            'structures/ncaf.edi', after['structures/ncaf.edi']
        )


@pytest.mark.parametrize('row', BASELINE['accepted'], ids=operator.itemgetter('path'))
def test_frozen_project_bytes_or_named_identity_only_difference(tmp_path, row, record_property):
    record_property('project', row['path'])
    before = restore_frozen(row, tmp_path)
    for name, data in before.items():
        assert hashlib.sha256(data).hexdigest() == row['files'][name], (
            ' frozen baseline bytes must retain their authoring hash'
        )
    if row['path'] == 'docs/user/cli/pd-neut-cwl_pbso4_beba-asymmetry/project':
        source = ROOT / row['path']
        model = engine.Project.load(source)
        assert hasattr(model.experiments[0].peak, 'mixing_eta_0'), (
            'The replacement for the retired combined profile must select Npr5 mixing'
        )
        first = observe(source, tmp_path / 'first')
        second = observe(tmp_path / 'first', tmp_path / 'second')
        assert first == second, (
            'The Npr5 replacement preserves the complete second-save fixed point'
        )
        return
    try:
        model = engine.Project.load(tmp_path / 'input')
    except (RuntimeError, ValueError) as error:
        record_property('group', 'c-load-refusal')
        record_property('reason', str(error))
        pytest.fail(
            ' accepted baseline project now refuses load: ' + row['path'] + '; ' + str(error)
        )
    if 'save_error' in row:
        if row['path'] == 'app/examples/pd-xray-cwl_lif/project':
            # Before: a generated range refused save. After: save retains the
            # declared range and never turns a calculation grid into observations.
            require_calculation_range_save(
                model, tmp_path / 'input', tmp_path / 'saved', tmp_path, record_property
            )
            return
        with pytest.raises((RuntimeError, ValueError)) as caught:
            model.save_as(tmp_path / 'saved')
        assert str(caught.value) == row['save_error'], (
            ' retain the exact existing refusal for a fork-point unsaveable project'
        )
        record_property('group', 'baseline-save-refusal')
        record_property('reason', str(caught.value))
        return
    try:
        model.save_as(tmp_path / 'saved')
    except (RuntimeError, ValueError) as error:
        record_property('group', 'd-save-refusal')
        record_property('reason', str(error))
        pytest.fail(' accepted project now refuses save: ' + row['path'] + '; ' + str(error))
    after = snapshot(tmp_path / 'saved')
    if set(before) != set(after):
        record_property('group', 'e-other')
        pytest.fail(' identity spelling changed the saved file population: ' + row['path'])
    retain_follower_witness(row['path'], after)
    changed = []
    for name, previous in before.items():
        a = normalized_record(name, previous)
        b = normalized_record(
            name,
            without_new_geom(
                name, tmp_path / 'input' / name, without_calculator(name, after[name])
            ),
        )
        if a != b:
            changed.append(name)
            try:
                identity_only = delimiter_only(a.decode(), b.decode())
            except (ValueError, UnicodeError):
                identity_only = False
            if not identity_only:
                record_property('group', 'e-other')
                record_property('differing_files', ','.join(changed))
                pytest.fail(' group (e): non-identity change in ' + row['path'] + '/' + name)
    record_property('group', 'b-identity-delimiters' if changed else 'a-identical')
    record_property('differing_files', ','.join(changed))


def require_calculation_range_save(model, source, saved, tmp_path, record_property):
    record_property('group', 'calculation-range-save-adaptation')
    experiment_files = sorted((source / 'experiments').glob('*.edi'))
    declared = {
        path.name: {
            fields[0]: float(fields[1])
            for line in path.read_text().splitlines()
            if (fields := line.split()) and fields[0].startswith('_data_range.')
        }
        for path in experiment_files
    }
    assert declared and all(len(values) == 3 for values in declared.values()), (
        'the retained calculation-only input declares its complete min/max/step range'
    )
    before_axes = [list(experiment.data.axis()) for experiment in model.experiments]
    model.save_as(saved)
    files = sorted((saved / 'experiments').glob('*.edi'))
    assert [path.name for path in files] == list(declared), (
        'saving a calculation-only project retains every declared experiment file'
    )
    for path in files:
        text = path.read_text()
        actual = {
            fields[0]: float(fields[1])
            for line in text.splitlines()
            if (fields := line.split()) and fields[0].startswith('_data_range.')
        }
        assert actual == declared[path.name], (
            'the saved calculation-only range keeps every independently declared value'
        )
        assert not re.search(r'(?m)^_data\.(?:id|intensity_meas|intensity_meas_su)\b', text), (
            'a saved calculation-only range must never fabricate measured observations'
        )
    reopened = engine.Project.load(saved)
    assert [list(experiment.data.axis()) for experiment in reopened.experiments] == before_axes, (
        'the saved calculation-only range must reopen with the complete original grid'
    )
    assert observe(saved, tmp_path / 'second') == observe(
        tmp_path / 'second', tmp_path / 'third'
    ), 'calculation-only saving reaches a complete byte-exact serialization fixed point'


@pytest.mark.parametrize(
    ('before', 'after', 'allowed'),
    [
        (
            "loop_\n_atom_site.id\n_atom_site.occupancy\n'X' 0.7\n",
            'loop_\n_atom_site.id\n_atom_site.occupancy\nX 0.7\n',
            True,
        ),
        (
            "loop_\n_atom_site.id\n_atom_site.occupancy\n'X' 0.7\n",
            'loop_\n_atom_site.id\n_atom_site.occupancy\nX 0.8\n',
            False,
        ),
        (
            "loop_\n_atom_site.id\n_atom_site.occupancy\n'X' 0.7\n",
            'loop_\n_atom_site.id\n_atom_site.occupancy\nY 0.7\n',
            False,
        ),
        (
            'loop_\n_atom_site.id\n_atom_site.occupancy\n"\'X\'" 0.7\n',
            'loop_\n_atom_site.id\n_atom_site.occupancy\nX 0.7\n',
            False,
        ),
        ("_metadata.title 'X'\n", '_metadata.title X\n', False),
        (
            'loop_\n_atom_site.id\n_atom_site.occupancy\nX 0.7\n#keep\n',
            'loop_\n_atom_site.id\n_atom_site.occupancy\nX 0.7\n#drop\n',
            False,
        ),
    ],
    ids=[
        'delimiter-only',
        'physical-value',
        'identity-value',
        'literal-quotes',
        'nonidentity',
        'comment',
    ],
)
def test_independent_delimiter_classifier_rejects_semantic_escapes(before, after, allowed):
    assert delimiter_only(before, after) is allowed, (
        ' token classifier permits only equal decoded identity cells'
    )

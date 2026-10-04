"""I21: challenge the independent census reference before trusting it."""

import shutil
from pathlib import Path

import pytest

from tests.fixtures.c34_t28_baseline import census_reference as reference

ROOT = Path(__file__).resolve().parents[3]
REPO = 'edi'


@pytest.mark.parametrize('visibility', ['public', 'private'])
def test_compiler_reference_observes_each_member_without_included_type_aliases(
    tmp_path, visibility
):
    compiler = shutil.which('clang++')
    assert compiler, ' I21 the independent census reference requires Clang'
    prefix = 'include' if REPO == 'crysta' else 'core/include'
    root = tmp_path / REPO
    header = root / prefix / REPO / 'model.hpp'
    header.parent.mkdir(parents=True)
    foreign = header.with_name('foreign.hpp')
    foreign.write_text(
        'namespace ' + REPO + ' { namespace foreign { struct Cell { int decoy; }; }}'
    )
    header.write_text(
        '#include "foreign.hpp"\nnamespace '
        + REPO
        + ' { class Cell { '
        + visibility
        + ': int represented; }; }\n'
    )
    paths = (
        ['src/core/save_project.cpp', 'src/core/model.cpp']
        if REPO == 'crysta'
        else ['core/src/io.cpp']
    )
    for relative in paths:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('const char* tag = "_cell.length_a";\n')
    identity_root = root if REPO == 'crysta' else root / 'build/crysta-src'
    identity = identity_root / 'src/core/identity.cpp'
    identity.parent.mkdir(parents=True, exist_ok=True)
    identity.write_text(
        'auto identity_columns() { auto columns = {{"_atom_site.id", "atom site"}};'
        ' return columns; }'
    )
    result = reference.inventory(root, REPO, compiler)
    assert [(row['owner'], row['member']) for row in result['members']] == [
        (REPO + '::Cell', 'represented')
    ], ' I21 private members count and an included same-named type cannot alias the model'
    assert set(result['io_tags']) == {'_cell.length_a'}, (
        ' I21 the independent I/O reader must retain the actual writer tag'
    )
    assert result['identity_columns'] == [{'tag': '_atom_site.id', 'category': 'atom site'}], (
        ' I21 identity columns are read independently of the generated census'
    )
    data = root / 'data/category-census.json'
    data.parent.mkdir()
    data.write_text('{"forged": "complete"}')
    (header.parent / 'schema.hpp').write_text('the forged schema deliberately omits every field')
    assert reference.inventory(root, REPO, compiler) == result, (
        ' I21 neither a census nor its schema can supply the reference that judges it'
    )

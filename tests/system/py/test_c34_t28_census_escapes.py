"""gate 2: the census must discover model fields outside its own schemas.

These mutations are source-derived counterexamples, never expected census output.
They exercise plain, composite and parameter storage omitted from a schema.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HEADER = 'core/include/edi/model.hpp'


@pytest.fixture(scope='module')
def census_checkout(tmp_path_factory):
    tool = ROOT / 'tools/checks/category_census.py'
    assert tool.is_file(), ' I14/I21 requires the executable category census'
    root = tmp_path_factory.mktemp('c34-census')
    for relative in (
        'core/include',
        'core/src',
        'lib/src',
        'app/src',
        'cli',
        'data',
        'tools/checks',
    ):
        source = ROOT / relative
        if source.is_dir():
            shutil.copytree(
                source,
                root / relative,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns('__pycache__'),
            )
    return root


def census(root):
    return subprocess.run(
        [sys.executable, str(root / 'tools/checks/category_census.py')],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=25,
    )


@pytest.mark.parametrize(
    'declaration',
    [
        'std::vector<double> c34_omitted_column;',
        'std::optional<std::vector<double>> c34_omitted_column;',
        'Parameter c34_omitted_column;',
    ],
    ids=['vector', 'optional-vector', 'parameter'],
)
@pytest.mark.parametrize(
    'owner',
    [
        'AtomSite',
        'Cell',
        'PdDataBase',
        'Structure',
        'ExperimentBase',
        'ProjectMetadata',
        'SequentialFitConfig',
        'Geom',
    ],
)
def test_census_refuses_a_model_member_omitted_from_the_schema(
    census_checkout, declaration, owner
):
    root = census_checkout
    good = census(root)
    assert good.returncode == 0, (
        ' I21 the declared source/schema control must first be complete: '
        + good.stdout
        + good.stderr
    )
    header = root / HEADER
    original = header.read_text()
    pattern = r'\b(?:class|struct)\s+' + re.escape(owner) + r'\b[^;{]*\{'
    matches = list(re.finditer(pattern, original))
    assert len(matches) == 1, ' I21 the independent mutation must reach the actual model row'
    offset = matches[0].end()
    try:
        header.write_text(
            original[:offset] + '\n public:\n    ' + declaration + '\n' + original[offset:]
        )
        rejected = census(root)
    finally:
        header.write_text(original)
    assert rejected.returncode != 0, (
        ' I21 a schema-only inventory cannot admit an unclassified model member'
    )
    assert 'c34_omitted_column' in rejected.stdout + rejected.stderr, (
        ' I21 the refusal must name the omitted source member'
    )


def test_census_refuses_an_io_category_that_has_no_schema(census_checkout):
    root = census_checkout
    good = census(root)
    assert good.returncode == 0, (
        ' I21 source/schema control must admit before I/O changes: ' + good.stdout + good.stderr
    )
    source = root / 'core/src/io.cpp'
    original = source.read_text()
    # This is an executable I/O tag, not a comment or the census's own table.
    needle = '"_cell.length_a"'
    assert needle in original, ' I21 the mutation must reach the real geometry I/O'
    try:
        source.write_text(original.replace(needle, '"_c34_unclassified.operation_xyz"'))
        bad = census(root)
    finally:
        source.write_text(original)
    assert bad.returncode != 0, ' I21 every category known to the loader or writer needs a schema'
    assert '_c34_unclassified' in bad.stdout + bad.stderr, (
        ' I21 the refusal names the unclassified I/O category'
    )


@pytest.mark.parametrize(
    'escape', ['dotted-category', 'cif-category', 'container', 'private-field']
)
def test_census_names_each_new_defect_even_while_unrelated_tables_are_pending(
    census_checkout, escape
):
    # Keep the complete-control gates above unchanged. This bounded exercise
    # reaches the new diagnostic while the initial loop-table implementation is
    # still pending; a red exit alone could only repeat an unrelated defect.
    root = census_checkout
    target = root / ('core/src/io.cpp' if escape.endswith('category') else HEADER)
    original = target.read_text()
    if escape == 'dotted-category':
        label = '_c34_unclassified'
        changed = original.replace('"_cell.length_a"', '"_c34_unclassified.operation_xyz"')
    elif escape == 'cif-category':
        label = '_c34_unclassified_cif'
        changed = original + '\nconst char* c34_probe_tag = "_c34_unclassified_cif";\n'
    elif escape == 'container':
        label = 'PeakCategory'
        changed = original.replace(
            'double cutoff_fwhm = 20.0;', 'std::vector<double> cutoff_fwhm;'
        )
    else:
        label = 'Cell::c34_outside_schema'
        changed = original.replace(
            'struct Cell {', 'struct Cell {\n private:\n double c34_outside_schema;\n public:'
        )
    assert changed != original, ' I21 the escape must reach an actual production declaration'
    before = census(root)
    baseline = before.stdout + before.stderr
    assert label not in baseline, (
        ' I21 the target must have no diagnostic before its isolated defect: ' + baseline
    )
    assert not before.stderr, ' I21 the control must reach the census, not an interpreter error'
    try:
        target.write_text(changed)
        after = census(root)
    finally:
        target.write_text(original)
    new = set((after.stdout + after.stderr).splitlines()) - set(baseline.splitlines())
    assert after.returncode == 1 and any(
        line.startswith('category_census:') and label in line for line in new
    ), ' I14/I21 each planted defect must produce its own new named refusal: ' + repr(new)

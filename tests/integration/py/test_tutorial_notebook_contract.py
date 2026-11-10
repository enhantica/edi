"""Gate 3: published upstream chapters and the owner's notebook presentation contract."""

import ast
import hashlib
import json
import re
from functools import cache

import pytest

from tests.fixtures.tutorial_cases.contract import CASES as ALL_CASES
from tests.fixtures.tutorial_cases.contract import ROOT, cases_for, read_records
from tests.fixtures.tutorial_cases.install_cell import INSTALL_CELL, python_syntax
from tests.fixtures.tutorial_cases.presentation import (
    RULES,
    assert_tag_cell,
    chips,
    notebook,
    section,
    text,
    title_parts,
)

CASES = cases_for('python')


@cache
def records():
    return {record['id']: record for record in read_records()}


def record_for(case):
    assert case in records(), 'Gate 3/4: each selected tutorial has its case record: ' + case
    return records()[case]


def canonical(title):
    words = re.findall(r'[a-z]+', title.casefold())
    words = [word for word in words if word != 'the']
    normalized = (
        ' '.join(words).replace('structures', 'structure').replace('experiments', 'experiment')
    )
    return {'explore interactive report': 'report'}.get(normalized, normalized)


def test_notebook_source_inventory_covers_its_declared_python_cases():
    folder = ROOT / 'docs/user/tutorials'
    for suffix in ['.py', '.ipynb']:
        assert set(CASES) <= {path.stem for path in folder.glob('*' + suffix)} <= set(ALL_CASES), (
            'Gate 3: every case declaring Python has its source and notebook'
        )


@pytest.mark.parametrize('case', CASES)
def test_chapter_order_follows_the_published_reference_with_declared_app_adaptations(case):
    reference = json.loads((ROOT / 'tests/fixtures/tutorial_outline/current.json').read_text())
    assert reference['commit'] == 'cb2cda7be6117199be8f8cac0a666a7bccd32d90', (
        'Gate 3: the outline reference is the independently pinned published tutorial version'
    )
    assert case in reference['cases'], (
        'Gate 3 reference prerequisite: each added case needs its independently '
        'captured published chapter predecessor'
    )
    expected = [canonical(value) for value in reference['cases'][case]['sections']]
    if 'define project' in expected:
        expected.remove('define project')
        expected.insert(expected.index('import library') + 1, 'define project')
    actual = [
        canonical(match[1])
        for cell in notebook(case)['cells']
        if cell['cell_type'] == 'markdown'
        for line in text(cell).splitlines()
        if (match := re.fullmatch(r'##\s+(.+)', line))
    ]
    assert [value for value in actual if value in expected] == expected, (
        'Gate 3: every published chapter remains in order after creating the empty project first: '
        + case
    )
    assert not any(
        re.match(r'^\W', line[3:])
        for cell in notebook(case)['cells']
        for line in text(cell).splitlines()
        if line.startswith('## ')
    ), 'Gate 3: the tutorial headings use words without decorative emoji'


@pytest.mark.parametrize('case', CASES)
def test_install_is_the_only_hidden_cell_and_buttons_are_not_notebook_content(case):
    cells = notebook(case)['cells']
    installs = [cell for cell in cells if '%pip install ' in text(cell)]
    assert len(installs) == 1, 'Gate 3: every notebook has one install cell'
    hidden = [cell for cell in cells if 'hide-in-docs' in cell.get('metadata', {}).get('tags', [])]
    assert hidden == installs, (
        'Gate 3: only the install cell is hidden; the tags cell is visible everywhere'
    )
    assert all(
        label not in text(cell)
        for cell in cells
        for label in ['Open in Google Colab', 'Download Notebook']
    ), 'Gate 3: download and Colab buttons belong to docs chrome, never notebook cells'
    assert all(
        not any(output.get('output_type') == 'error' for output in cell.get('outputs', []))
        for cell in cells
    ), 'Gate 3: a notebook carrying a failed cell cannot be published as an executed tutorial'


@pytest.mark.parametrize('case', CASES)
def test_one_visible_font_derived_tag_cell_follows_the_case_title(case):
    record = record_for(case)
    title_parts(record)
    document = notebook(case)
    cells = document['cells']
    titles = [index for index, cell in enumerate(cells) if re.match(r'^#\s+[^#]', text(cell))]
    assert len(titles) == 1 and text(cells[titles[0]]).strip() == '# ' + record['title'], (
        'Gate 3: the notebook H1 is only the case title, with no source docstring title'
    )
    tagged = [index for index, cell in enumerate(cells) if chips(text(cell))]
    assert tagged == [titles[0] + 1], (
        'Gate 3: one tags cell sits directly after the title and before the description'
    )
    assert_tag_cell(cells[tagged[0]], record)


@pytest.mark.parametrize('case', CASES)
def test_case_section_and_icon_follow_the_owner_rules(case):
    record = record_for(case)
    expected = section(record)
    assert (
        record['section'] == expected
        and record['section_icon'] == dict(RULES['sections'])[expected]
    ), 'Gate 3/4: each case uses the declared section and shared section icon'


def test_page_titles_are_unique_and_the_single_font_is_unchanged():
    titles = [record_for(case)['title'] for case in ALL_CASES]
    assert len(titles) == len(set(titles)), (
        'Gate 3/4: complete tutorial page titles are unique across cases'
    )
    expected = json.loads((ROOT / 'tests/fixtures/tutorial_cases/glyphs.json').read_text())
    path = ROOT / 'website/surfaces/docs/assets/gui-icons/fontawesome-5-solid.otf'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected['font_sha256'], (
        'Gate 3/4: tag outlines use the pinned shared app font, never another font or icon store'
    )


@pytest.mark.parametrize(
    'path', sorted((ROOT / 'docs/user/tutorials').glob('*.ipynb')), ids=lambda p: p.stem
)
def test_every_existing_notebook_starts_with_the_exact_guarded_install_cell(path):
    assert_install_first(json.loads(path.read_text())['cells'])


def assert_install_first(cells):
    assert cells and cells[0]['cell_type'] == 'code' and text(cells[0]) == INSTALL_CELL, (
        'Gate 3/6: every tutorial begins with the exact guarded official install cell'
    )
    assert 'hide-in-docs' in cells[0].get('metadata', {}).get('tags', []), (
        'Gate 3: the guarded install cell keeps the hide-in-docs tag'
    )
    assert sum('%pip install ' in text(cell) for cell in cells) == 1, (
        'Gate 3/6: the guarded first cell is the only notebook installation'
    )


@pytest.mark.parametrize(
    'damage', ['unguarded', 'quiet', 'wrong-index', 'missing-tag', 'not-first', 'duplicate']
)
def test_install_cell_observer_refuses_every_changed_or_displaced_form(damage):
    cell = {'cell_type': 'code', 'source': INSTALL_CELL, 'metadata': {'tags': ['hide-in-docs']}}
    assert_install_first([cell])
    changed = json.loads(json.dumps(cell))
    cells = [changed]
    if damage == 'unguarded':
        changed['source'] = INSTALL_CELL.splitlines()[-1].lstrip() + '\n'
    elif damage == 'quiet':
        changed['source'] = INSTALL_CELL.replace('%pip install ', '%pip install --quiet ')
    elif damage == 'wrong-index':
        changed['source'] = INSTALL_CELL.replace('download.easydiffraction.org', 'example.org')
    elif damage == 'missing-tag':
        changed['metadata']['tags'] = []
    elif damage == 'not-first':
        cells.insert(0, {'cell_type': 'markdown', 'source': '# Tutorial'})
    else:
        cells.append(cell)
    with pytest.raises(AssertionError, match='Gate 3'):
        assert_install_first(cells)


def test_guarded_install_remains_parseable_by_teaching_observers():
    tree = ast.parse(python_syntax(INSTALL_CELL + 'project.analysis.fit()\n'))
    assert isinstance(tree.body[1], ast.If) and isinstance(tree.body[1].body[0], ast.Pass), (
        'Gate 3: static observers preserve the guard while replacing only notebook magic'
    )
    assert isinstance(tree.body[-1], ast.Expr), (
        'Gate 3: observing an install guard must retain the following tutorial actions'
    )

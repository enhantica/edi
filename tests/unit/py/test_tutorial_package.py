"""Tutorial setup and output contracts, independent of fitted values."""

import ast
import json
import re
import tomllib
from pathlib import Path

import pytest

from tests.fixtures.tutorial_cases.install_cell import INSTALL_CELL, python_syntax

ROOT = Path(__file__).resolve().parents[3]
INDEX = 'https://download.easydiffraction.org/pypi/simple/'


def notebooks():
    paths = sorted((ROOT / 'docs/user/tutorials').glob('*.ipynb'))
    assert paths, 'The tutorial catalogue must contain runnable notebooks'
    return [(path, json.loads(path.read_text())) for path in paths]


def code_cells(document):
    return [''.join(cell['source']) for cell in document['cells'] if cell['cell_type'] == 'code']


def test_tutorial_install_is_one_plain_cell_before_the_public_import():
    errors = []
    for path, document in notebooks():
        cells = code_cells(document)
        installs = [cell.strip() for cell in cells if '%pip' in cell]
        if len(installs) != 1 or installs[0] != INSTALL_CELL.strip():
            errors.append(f'{path.name}: requires the published guarded install cell')
            continue
        before_import = '\n'.join(
            cells[
                : next(
                    (i for i, cell in enumerate(cells) if 'import easydiffraction as edi' in cell),
                    len(cells),
                )
            ]
        )
        if before_import.strip() != installs[0]:
            errors.append(f'{path.name}: extra setup before the public import')
        if not any(
            re.search(r'^import easydiffraction as edi$', cell, re.MULTILINE) for cell in cells
        ):
            errors.append(f'{path.name}: missing public import')
    assert not errors, (
        'Every notebook installs with one cell and no setup machinery: ' + '; '.join(errors)
    )


def dotted(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return dotted(node.value) + '.' + node.attr
    return ''


def test_every_tutorial_fit_is_followed_by_pattern_and_fit_results():
    required = {
        'project.display.pattern',
        'project.display.fit.results',
    }
    errors = []
    for path, document in notebooks():
        source = python_syntax('\n'.join(code_cells(document)))
        calls = sorted(
            (node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)),
            key=lambda node: (node.lineno, node.col_offset),
        )
        fits = [
            i
            for i, call in enumerate(calls)
            if dotted(call.func)
            in {
                'project.analysis.fit',
                'project.fit',
                'project.fit_joint',
                'project.fit_sequential',
                'project.fit_independent',
            }
        ]
        if not fits and 'simulation' not in path.stem:
            errors.append(f'{path.name}: no fit')
        for start, end in zip(fits, [*fits[1:], len(calls)][: len(fits)], strict=True):
            seen = {dotted(call.func) for call in calls[start + 1 : end]}
            if dotted(calls[start].func) in {'project.fit_sequential', 'project.fit_independent'}:
                if 'on_file_complete' not in {item.arg for item in calls[start].keywords} or (
                    'result.status.name.lower' not in seen
                ):
                    errors.append(
                        f'{path.name}:{calls[start].lineno}: missing batch completion output'
                    )
                continue
            if not required <= seen:
                errors.append(
                    f'{path.name}:{calls[start].lineno}: missing {sorted(required - seen)}'
                )
    assert not errors, (
        'Every fit must show its pattern and fit results before the next fit: ' + '; '.join(errors)
    )


def test_wheel_declares_the_public_module_package_paths():
    config = tomllib.loads((ROOT / 'pyproject.toml').read_text())
    assert config['project']['name'] == 'easydiffraction', (
        'The public distribution remains easydiffraction'
    )
    packages = config['tool']['hatch']['build']['targets']['wheel']['packages']
    assert 'lib/easydiffraction' in packages, (
        'The wheel must carry the easydiffraction import package'
    )
    # The clean-wheel system gate reads shipped METADATA and executes every notebook;
    # an unused source-build dependency field is not the wheel's dependency contract.


def test_notebook_rules_accept_a_plain_workflow_and_reject_missing_displays(monkeypatch):
    source = [
        INSTALL_CELL,
        'import easydiffraction as edi',
        "project = edi.Project(name='example')",
        'project.display.parameters.free()',
        'project.analysis.fit()',
        'project.display.pattern()',
        'project.display.fit.results()',
    ]
    document = {'cells': [{'cell_type': 'code', 'source': cell} for cell in source]}
    monkeypatch.setitem(globals(), 'notebooks', lambda: [(Path('example.ipynb'), document)])
    test_tutorial_install_is_one_plain_cell_before_the_public_import()
    test_every_tutorial_fit_is_followed_by_pattern_and_fit_results()
    document['cells'].pop()
    with pytest.raises(AssertionError, match='Every fit must show'):
        test_every_tutorial_fit_is_followed_by_pattern_and_fit_results()
    document['cells'].insert(1, {'cell_type': 'code', 'source': 'import subprocess'})
    with pytest.raises(AssertionError, match='no setup machinery'):
        test_tutorial_install_is_one_plain_cell_before_the_public_import()


@pytest.mark.parametrize('method', ['fit_sequential', 'fit_independent'])
def test_batch_tutorial_output_requires_completion_progress_and_terminal_status(
    monkeypatch, method
):
    source = [
        INSTALL_CELL,
        'import easydiffraction as edi',
        f'result = project.{method}(on_file_complete=lambda *args: fitted.append(args))',
        'print(result.status.name.lower(), len(fitted))',
    ]
    document = {'cells': [{'cell_type': 'code', 'source': cell} for cell in source]}
    monkeypatch.setitem(globals(), 'notebooks', lambda: [(Path('batch.ipynb'), document)])
    test_every_tutorial_fit_is_followed_by_pattern_and_fit_results()
    document['cells'].pop()
    with pytest.raises(AssertionError, match='batch completion output'):
        test_every_tutorial_fit_is_followed_by_pattern_and_fit_results()
    document['cells'].append({'cell_type': 'code', 'source': source[-1]})
    document['cells'][2]['source'] = f'result = project.{method}()'
    with pytest.raises(AssertionError, match='batch completion output'):
        test_every_tutorial_fit_is_followed_by_pattern_and_fit_results()

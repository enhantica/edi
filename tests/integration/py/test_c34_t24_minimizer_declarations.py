"""project-declared minimization conditions: round-trip and boundary invariants."""

from __future__ import annotations

import re
import shlex
import shutil
from pathlib import Path

import edi as engine
import pytest

ROOT = Path(__file__).resolve().parents[3]
CORPUS = Path(
    __import__('os').environ.get('EDI_CRYSTA_CORPUS_ROOT', ROOT / 'build/crysta-src/tests/fitting')
)
FIELDS = {'descent': 'fast_descent', 'chi_square_tolerance': '0.00037', 'max_iterations': '7'}


def copy_project(tmp_path, values):
    target = tmp_path / 'project'
    shutil.copytree(CORPUS / 'cosio-d20-s1/project', target)
    analysis = target / 'analysis/analysis.edi'
    text = re.sub(
        r'(?m)^_minimizer\.(?:descent|chi_square_tolerance|max_iterations)\s+[^\n]*\n?',
        '',
        analysis.read_text(),
    )
    analysis.write_text(
        text + '\n' + ''.join(f'_minimizer.{key} {value}\n' for key, value in values.items())
    )
    return target


def settings(path):
    return dict(
        shlex.split(line)[0:2]
        for line in path.read_text().splitlines()
        if line.startswith('_minimizer.')
    )


def test_declared_conditions_survive_load_save_and_second_round_trip(tmp_path):
    source = copy_project(tmp_path, FIELDS)
    for index in range(2):
        saved = tmp_path / f'saved-{index}'
        engine.Project.load(source).save_as(saved)
        actual = settings(saved / 'analysis/analysis.edi')
        assert actual.get('_minimizer.descent') == FIELDS['descent'], (
            ' save must retain the declared non-default descent'
        )
        for key in ('chi_square_tolerance', 'max_iterations'):
            assert f'_minimizer.{key}' in actual, (
                ' save must retain every declared stopping condition'
            )
            assert float(actual[f'_minimizer.{key}']) == float(FIELDS[key]), (
                ' stopping conditions must round-trip without unit or precision changes'
            )
        source = saved


@pytest.mark.parametrize(
    ('key', 'value'),
    [
        ('descent', 'not_registered'),
        pytest.param('descent', '"fast_descent "', id='descent-trailing-space'),
        ('chi_square_tolerance', '0'),
        ('chi_square_tolerance', '-0.00037'),
        ('chi_square_tolerance', 'nan'),
        ('max_iterations', '0'),
        ('max_iterations', '-7'),
        ('max_iterations', '1.5'),
    ],
)
def test_invalid_declared_condition_refuses_at_load(tmp_path, key, value):
    source = copy_project(tmp_path, {**FIELDS, key: value})
    with pytest.raises((ValueError, RuntimeError), match=key):
        engine.Project.load(source)


def test_unknown_descent_error_names_the_registry(tmp_path):
    source = copy_project(tmp_path, {**FIELDS, 'descent': 'not_registered'})
    with pytest.raises((ValueError, RuntimeError)) as caught:
        engine.Project.load(source)
    # ADR-0060's committed registry, independent of this project's parser.
    for name in (
        'ladder',
        'fast_descent',
        'fast_descent_linear_snap',
        'fast_descent_guarded_linear_snap',
        'multistart_prune',
    ):
        assert name in str(caught.value), (
            ' unknown descent must identify the complete valid registry'
        )


def test_analysis_reference_documents_conditions_and_all_registered_values():
    references = [
        path.read_text()
        for path in (ROOT / 'docs').rglob('*.md')
        if 'analysis.edi' in path.read_text()
    ]
    pages = [text for text in references if all(f'_minimizer.{field}' in text for field in FIELDS)]
    assert pages, ' analysis.edi reference must document all three minimization conditions'
    assert any(all(name in text for name in engine._descent_ids()) for text in pages), (
        ' analysis.edi reference must document every registered descent value'
    )

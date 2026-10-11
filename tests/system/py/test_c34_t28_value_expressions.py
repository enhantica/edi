"""F20: value expressions preserved by immutable pre-move headers."""

import shutil
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.c34_t28_compiler import crysta_headers
from tests.fixtures.c34_t28_compiler import standard_headers as _standard_headers
from tests.system.py.test_c34_t28_native_surface import frozen_headers

standard_headers = _standard_headers
ROOT = Path(__file__).resolve().parents[3]
# Each expression is reached by an ordinary value read or replacing assignment.
# The former mutable forms stay forbidden in the separate T8 escape witness.
EXPRESSIONS = []
for _owner, _member in [
    ('PdDataBase', 'intensity_meas'),
    ('PdDataBase', 'intensity_meas_su'),
]:
    EXPRESSIONS.extend([
        (_owner, _member, 'mixed-list', 'o.M = {1, 2.5};'),
        (_owner, _member, 'empty-list', 'o.M = {};'),
        (
            _owner,
            _member,
            'vector-equality',
            '(void)(o.M == std::vector<double>{1.25}); (void)(std::vector<double>{1.25} != o.M);',
        ),
        (_owner, _member, 'member-equality', '(void)(o.M == other.M); (void)(o.M != other.M);'),
    ])
for _member in ['two_theta', 'time_of_flight']:
    EXPRESSIONS.extend([
        (
            'PdDataBase',
            _member,
            'optional-equality',
            (
                '(void)(o.M == std::optional<std::vector<double>>{std::vector<double>{1.25}}); '
                '(void)(std::optional<std::vector<double>>{std::vector<double>{1.25}} != o.M);'
            ),
        ),
        (
            'PdDataBase',
            _member,
            'value-equality',
            '(void)(o.M == std::vector<double>{1.25}); (void)(std::vector<double>{1.25} != o.M);',
        ),
        (
            'PdDataBase',
            _member,
            'axis-equality',
            '(void)(o.M == other.M); (void)(o.M != other.M);',
        ),
    ])
for _owner, _member in [
    ('AtomSite', 'wyckoff_letter'),
    ('SequentialExtractRule', 'target'),
    ('SequentialExtractRule', 'pattern'),
]:
    EXPRESSIONS.extend([
        (
            _owner,
            _member,
            'const-iterators',
            '(void)o.M.begin(); (void)o.M.end(); (void)o.M.cbegin(); (void)o.M.cend();',
        ),
        (
            _owner,
            _member,
            'const-elements',
            '(void)o.M.at(0); (void)o.M.front(); (void)o.M.back(); (void)o.M.find("b", 1);',
        ),
        (
            _owner,
            _member,
            'ordering',
            (
                '(void)(o.M < std::string("b")); (void)(std::string("b") > o.M); '
                '(void)(o.M <= other.M); (void)(o.M >= other.M);'
            ),
        ),
    ])
for _owner, _member, _value in [
    ('Structure', 'scattering_lengths_fm', 'std::map<std::string, double>{{"Si", 4.1491}}'),
    ('ExperimentBase', 'excluded_regions', 'std::vector<std::pair<double, double>>{{1.25, 4.5}}'),
    ('CarriedLoop', 'columns', 'std::vector<std::string>{"z"}'),
    ('CarriedLoop', 'rows', 'std::vector<std::vector<std::string>>{{"z"}}'),
]:
    EXPRESSIONS.append((
        _owner,
        _member,
        'ordering',
        (
            f'(void)(o.M < {_value}); (void)({_value} > o.M); '
            '(void)(o.M <= other.M); (void)(o.M >= other.M);'
        ),
    ))


@pytest.fixture
def old_headers(tmp_path):
    return frozen_headers(tmp_path / 'old')


def compile_values(directory, include, owner, expression, standard_headers):
    compiler = shutil.which('clang++')
    assert compiler, ' F20 the value-expression witness requires the real compiler'
    unit = directory / 'value.cpp'
    unit.write_text(
        '#include "edi/model.hpp"\nvoid probe(edi::'
        + owner
        + '& o, const edi::'
        + owner
        + '& other) { '
        + expression
        + ' }\n'
    )
    return subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-fsyntax-only',
            '-include-pch',
            str(standard_headers),
            '-I',
            str(include),
            '-I',
            str(crysta_headers()),
            str(unit),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=25,
    )


@pytest.mark.parametrize(
    ('owner', 'member', 'route', 'expression'),
    EXPRESSIONS,
    ids=[f'{o}-{m}-{r}' for o, m, r, _ in EXPRESSIONS],
)
def test_value_expression_keeps_its_old_header_admission(
    tmp_path,
    old_headers,
    standard_headers,
    owner,
    member,
    route,
    expression,
):
    expression = expression.replace('M', member)
    reference = compile_values(tmp_path, old_headers, owner, expression, standard_headers)
    assert reference.returncode == 0, (
        ' F20 the immutable old headers must admit the actual value expression: '
        + reference.stderr
    )
    if member == 'excluded_regions':
        # Stored rows expose bounds through the declared snapshot projection.
        # Keep the frozen vector premise and every relational operand intact.
        expression = expression.replace(
            'other.excluded_regions', 'edi::excluded_region_ranges(other.excluded_regions)'
        ).replace('o.excluded_regions', 'edi::excluded_region_ranges(o.excluded_regions)')
    current = compile_values(tmp_path, ROOT / 'core/include', owner, expression, standard_headers)
    assert current.returncode == 0, (
        f' I20/F20 preserves {owner}::{member} {route}, outside the four removed forms: '
        + current.stderr
    )

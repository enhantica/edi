"""Owner 7dea80601: actual parameter-table notation at both magnitude boundaries."""

import json
import re
import shutil
from decimal import Decimal
from pathlib import Path

import edi
import pytest
from bs4 import BeautifulSoup

from tests.fixtures.parameter_notation.reference import (
    SU_VALUES,
    VALUES,
    expected_pair,
    expected_plain,
    parse,
)
from tests.system.py.test_tutorial_display_tables import document, named_table

ROOT = Path(__file__).resolve().parents[3]
HEADERS = [
    '#',
    'datablock',
    'category',
    'entry',
    'parameter',
    'value',
    's.u.',
    'min',
    'max',
    'units',
    'free',
]


def project(tmp_path, value, su, rule):
    directory = tmp_path / 'project'
    shutil.copytree(ROOT / 'tests/fixtures/loop_parameter_ids/line-segment', directory)
    loaded = edi.Project.load(directory)
    loaded.su_rule = rule
    parameter = loaded.experiments['bank'].background[0].intensity
    parameter.value = value
    parameter.uncertainty = su
    parameter.start_value = value
    parameter.free = True
    return loaded, parameter


def cells(loaded, surface):
    if surface == 'model':
        rows = json.loads(loaded.report.model(excluded=['data', 'reflections']).to_json())[
            'parameters'
        ]
        row = next(row for row in rows if row['unique_name'] == 'bank.background.pA.intensity')
        return row['value_cell'], row.get('su_cell', ''), row.get('start_cell', '')
    if surface == 'notebook':
        soup = document(loaded.display.parameters.all())
    else:
        soup = BeautifulSoup(loaded.report.as_html(offline=False), 'html.parser')
        for table in soup.find_all('table'):
            headings = [
                cell.get_text(' ', strip=True).casefold() for cell in table.select('thead th')
            ]
            if (
                len(headings) == 2
                and headings[0].startswith('position')
                and headings[1] == 'intensity'
            ):
                token = table.select('tbody tr')[0].find_all('td')[1].get_text('', strip=True)
                match = re.fullmatch(r'([^()]+)\(([^()]+)\)(.*)', token)
                if not match:
                    return token, '', None
                mantissa, power = parse(match[1] + match[3])
                error = match[2]
                error_value = Decimal(error)
                if not any(char in error.lower() for char in '.e'):
                    error_value *= Decimal(1).scaleb(mantissa.as_tuple().exponent)
                suffix = '' if power is None else 'e' + str(power)
                return match[1] + match[3], str(error_value) + suffix, None
        raise AssertionError(
            'Parameter notation: HTML report contains its actual background parameter table'
        )
    table = named_table(soup, HEADERS)
    for row in table.select('tbody tr'):
        columns = [cell.get_text('', strip=True) for cell in row.find_all('td', recursive=False)]
        if columns[1:5] == ['bank', 'background', 'pA', 'intensity']:
            return columns[5], columns[6], None
    raise AssertionError(
        'Parameter notation: the actual table must contain the authored background row'
    )


def check_plain(text, value):
    actual, power = parse(text)
    expected, expected_power = expected_plain(value)
    assert (actual, power) == (expected, expected_power), (
        'Parameter notation: decimal at 0.001 inclusive to 1000 '
        'exclusive, scientific otherwise; zero is zero'
    )
    if value == 0:
        assert str(text).strip() == '0', 'Parameter notation: zero is written as the literal 0'
    if power is not None:
        assert len(actual.as_tuple().digits) == 3, (
            'Parameter notation: a number without s.u. has exactly three '
            'scientific significant digits'
        )


@pytest.mark.parametrize('surface', ['model', 'report', 'notebook'])
@pytest.mark.parametrize('value', VALUES)
def test_plain_value_and_start_obey_exact_owner_magnitude_boundaries(tmp_path, surface, value):
    loaded, parameter = project(tmp_path, value, 0.0, 'iucr_19')
    before = parameter.value.hex()
    shown, _su, start = cells(loaded, surface)
    check_plain(shown, value)
    if surface == 'model':
        check_plain(start, value)
    assert parameter.value.hex() == before, (
        'Parameter notation: rendering cannot replace the stored double '
        'with its displayed rounding'
    )


@pytest.mark.parametrize('surface', ['model', 'report', 'notebook'])
@pytest.mark.parametrize('rule', ['iucr_19', 'iucr_99'])
@pytest.mark.parametrize('value', SU_VALUES)
def test_value_and_su_keep_iucr_rounding_and_share_the_value_power(tmp_path, surface, rule, value):
    su = 0.00000201 if abs(value) < 1 else 0.00201
    loaded, parameter = project(tmp_path, value, su, rule)
    before = parameter.value.hex(), parameter.uncertainty.hex()
    shown, uncertainty, _start = cells(loaded, surface)
    # Reports always use recommendation 12, including their shared notebook/model views.
    # The project rule still governs app fields and saved files.
    expected_value, expected_su, expected_power = expected_pair(value, su, 'iucr_19')
    assert parse(shown) == (expected_value, expected_power), (
        'Parameter notation: s.u.-bearing values retain the IUCr last '
        'place when switching notation'
    )
    assert parse(shown)[0].as_tuple().exponent == expected_value.as_tuple().exponent, (
        'Parameter notation: value mantissas retain every last-place digit implied by the s.u.'
    )
    assert parse(uncertainty) == (expected_su, expected_power), (
        'Parameter notation: the s.u. uses the value exponent, including '
        'negative powers and decimal-range values'
    )
    assert (parameter.value.hex(), parameter.uncertainty.hex()) == before, (
        'Parameter notation: shared-power display does not change either scientific input double'
    )


@pytest.mark.parametrize('value', VALUES)
def test_actual_app_parameter_table_has_the_same_boundaries(value, app_observations):
    check_plain(app_observations['plain'][VALUES.index(value)], value)


@pytest.fixture(scope='module')
def app_observations():
    import os  # noqa: PLC0415 - native app-only observation
    import subprocess  # noqa: PLC0415

    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    from tests.fixtures.native_ui_script.runner import require_runner  # noqa: PLC0415

    require_runner(runner)
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/fixtures/parameter_notation/observe.qml'),
            '-o',
            '-,txt',
        ],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, (
        'Parameter notation: the real Qt observer reaches both project uncertainty rules: '
        + result.stdout
        + result.stderr
    )
    prefix = 'PARAMETER_NOTATION_PAIRS '
    lines = [line.split(prefix, 1)[1] for line in result.stdout.splitlines() if prefix in line]
    assert len(lines) == 1, (
        'Parameter notation: the native observer returns one complete pair matrix'
    )
    return json.loads(lines[0])


@pytest.mark.parametrize('rule', ['iucr_19', 'iucr_99'])
@pytest.mark.parametrize('value', SU_VALUES)
def test_actual_app_value_and_su_use_the_same_power(value, rule, app_observations):
    row = next(
        item
        for item in app_observations['pairs']
        if item['value'] == value and item['rule'] == rule
    )
    shown, error, power = expected_pair(value, row['su'], rule)
    assert parse(row['shown']) == (shown, power), (
        'Parameter notation: the actual app keeps the project IUCr '
        'rounded value in the selected power'
    )
    assert parse(row['error']) == (error, power), (
        'Parameter notation: the actual app s.u. has the value power, '
        'including both range boundaries'
    )

"""Unit 9: sigma repair comes from published inputs, never fitted output."""

import json
import re

import numpy as np
import pytest

from tests.fixtures.cosio_heidi_2008.generate import rows
from tests.fixtures.cosio_heidi_2008.reference import REFERENCE
from tests.fixtures.tutorial_cases.contract import ROOT, case_record
from tests.fixtures.tutorial_cases.notebook_fit import local_collection
from tests.fixtures.tutorial_cases.presentation import text

CASE = 'sc-neut-cwl_cosio-heidi'


def family(row):
    # Pnma's orthorhombic Laue group mmm; signs select the same measured family.
    return tuple(abs(value) for value in row[:3])


def sigma_reference():
    high = [
        {family(row): row for row in REFERENCE['cases'][temp]['rows']} for temp in ('55K', '300K')
    ]
    result, unresolved = {}, {}
    for row in REFERENCE['cases']['2.5K']['rows']:
        key = family(row)
        origin = next((data[key] for data in high if key in data), None)
        if origin is None:
            unresolved[key] = 'median neighborhood unspecified by owner record'
        elif origin[4] <= 0:
            result[key] = origin[5]
        elif origin[4] > 2 * origin[5]:
            result[key] = max(origin[5] * row[4] / origin[4], origin[5])
        else:
            # The record calls weak reflections "near zero" but specifies no cutoff.
            unresolved[key] = 'positive near-zero cutoff unspecified by owner record'
    return result, unresolved


@pytest.fixture(scope='module')
def collection(tmp_path_factory):
    return local_collection(tmp_path_factory.mktemp('cosio-collection'))


@pytest.fixture(scope='module')
def low_file(collection):
    expected = [row[:5] for row in REFERENCE['cases']['2.5K']['rows']]
    candidates = []
    for path in (collection / 'data').iterdir():
        if not path.is_file() or path.suffix not in {'.hkl', '.cif', '.dat', '.int'}:
            continue
        try:
            data = rows(path)
        except (ValueError, RuntimeError, IndexError):
            continue
        if [row[:5] for row in data] == expected:
            candidates.append((path, data))
    assert len(candidates) == 1, (
        'Unit 9: the collection supplies one 2.5 K CIF reflection file pres'
        'erving every published h k l, F²calc and F²meas'
    )
    return candidates[0]


def test_low_temperature_collection_sigma_recomputed_from_original_high_temperature_data(low_file):
    path, data = low_file
    expected, unresolved = sigma_reference()
    actual = {family(row): row[5] for row in data}
    assert expected and unresolved, (
        'Unit 9: the independent estimate covers known high-temperature bra'
        'nches and exposes unspecified fallback branches'
    )
    wrong = [
        (key, actual[key], value)
        for key, value in expected.items()
        if not np.isclose(actual[key], value, rtol=5e-4, atol=0.005)
    ]
    assert not wrong, (
        'Unit 9: collection sigma follows the original 55 K relative error '
        'and absolute floor, with 300 K fallback; discrepancies='
    ) + str(wrong[:8])
    header = path.read_text().split('loop_', 1)[0].casefold()
    assert 'estimat' in header and re.search(r'55\s*k', header), (
        'Unit 9: the collection reflection header explicitly labels sigma estimated from 55 K'
    )
    assert all(np.isfinite(row[5]) and row[5] > 0 for row in data), (
        'Unit 9: every estimated sigma, including fallback reflections, is finite and positive'
    )


@pytest.mark.parametrize(
    'surface', ['record', 'readme', 'python', 'notebook', 'app', 'command-line']
)
def test_estimated_uncertainty_is_disclosed_on_every_surface(surface):
    if surface == 'record':
        source = json.dumps(case_record(CASE), ensure_ascii=False)
    elif surface == 'readme':
        matches = [
            path
            for path in (ROOT / 'docs/user/cli' / CASE).rglob('*')
            if path.is_file() and path.name.casefold().startswith('readme')
        ]
        matches += [
            path
            for path in (ROOT / 'app/tutorials/files').glob('*')
            if CASE in path.name and 'readme' in path.name.casefold()
        ]
        assert matches, 'Unit 9: the three-temperature data have a committed README'
        source = '\n'.join(path.read_text() for path in matches)
    elif surface == 'notebook':
        path = ROOT / 'docs/user/tutorials' / (CASE + '.ipynb')
        assert path.is_file(), 'Unit 9: the three-temperature case has a notebook'
        source = '\n'.join(text(cell) for cell in json.loads(path.read_text())['cells'])
    else:
        path = {
            'python': ROOT / 'docs/user/tutorials' / (CASE + '.py'),
            'app': ROOT / 'website/surfaces/docs/application/tutorials/cases' / (CASE + '.md'),
            'command-line': ROOT / 'website/surfaces/docs/cli/tutorials/cases' / (CASE + '.md'),
        }[surface]
        assert path.is_file(), (
            'Unit 9: the three-temperature case has every declared tutorial surface'
        )
        source = path.read_text()
    plain = source.casefold()
    assert (
        'estimat' in plain and re.search(r'55\s*k', plain) and re.search(r'2[.·]5\s*k', plain)
    ), (
        'Unit 9: record, data README and every tutorial plainly disclose es'
        'timated 2.5 K uncertainties from 55 K'
    )
    if surface in {'python', 'notebook', 'app', 'command-line'}:
        assert (
            'moment' in plain
            and any(token in plain for token in ('s.u.', 'uncertaint', 'standard error'))
            and re.search(r'(?:inherit|estimat)', plain)
        ), (
            'Unit 9: the tutorial explains that fitted moment uncertainties inh'
            'erit the estimated data uncertainties'
        )

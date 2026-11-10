"""CLI expectations bind FullProf weighted-least-squares SUM values.

CeCoAl uses FullProf's Iwg=0 refit, per the owner decision development hub c98ab7f36;
its original Iwg=1 maximum-likelihood SUM remains provenance, not a fit oracle.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

import edi
import numpy as np
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/c13_t6_background'
REFERENCE = json.loads((FIXTURE / 'reference.json').read_text())
CLI = json.loads((FIXTURE / 'cli_reference.json').read_text())


def _quantities(expected):
    result = [expected['quantities']] if 'quantities' in expected else []
    result.extend(unit['quantities'] for unit in expected.get('variants', {}).values())
    if 'edi' in expected:
        result.append(expected['edi']['quantities'])
    return result


def _bound(spec, value, sigma):
    assert spec.get('kind') == 'reference', (
        ' FullProf values must be labelled independent references, never product pins'
    )
    assert math.isfinite(spec['value']) and abs(spec['value'] - value) <= 1e-10 * max(
        1, abs(value)
    ), ' each expected CLI parameter must equal the independently printed SUM value'
    assert spec.get('tol_rel') is None and isinstance(spec.get('tol_abs'), (int, float)), (
        ' CLI fit bounds must carry an explicit absolute standard-uncertainty allowance'
    )
    assert 0 <= spec['tol_abs'] <= CLI['sigma_multiple'] * sigma, (
        ' fit tolerances must stay within four SUM uncertainties'
    )


def _check_observations(project, case):
    source_rows = []
    for line in (FIXTURE / (case + '.dat')).read_text().splitlines():
        words = line.split()
        if len(words) != 3:
            continue
        try:
            source_rows.append([float(word) for word in words])
        except ValueError:
            continue
    independent_data = np.asarray(source_rows)
    assert independent_data.shape[0] > 1000, (
        ' the independent FullProf measured data must preserve its full pattern'
    )
    axis = 'two_theta' if case == 'lab6' else 'time_of_flight'
    for index, column in enumerate((axis, 'intensity_meas', 'intensity_meas_su')):
        actual = np.asarray(getattr(project.experiment.data, column))
        assert actual.shape == independent_data[:, index].shape, (
            ' CLI fits must retain all source measurements and sigmas'
        )
        assert np.allclose(actual, independent_data[:, index], rtol=0, atol=1e-8), (
            ' CLI fits must consume the independent FullProf X-Y-sigma observations; '
            'PEARL must use the converted reference whose provenance explains the RALF sigma'
        )


@pytest.mark.parametrize('case', tuple(REFERENCE['cases']))
def test_cli_projects_execute_and_pin_independent_parameters_with_sum_bounds(case):
    row = REFERENCE['cases'][case]
    cli = CLI['cases'][case]
    source = FIXTURE / cli['source']
    assert hashlib.sha256(source.read_bytes()).hexdigest() == cli['source_sha256'], (
        ' each fit oracle must retain the independent FullProf SUM source identity'
    )
    directory = ROOT / 'docs/user/cli' / row['project']
    registry = yaml.safe_load((ROOT / 'docs/user/cli/projects.yml').read_text())['projects']
    entries = [entry for entry in registry if entry['id'] == row['project']]
    assert (
        len(entries) == 1 and entries[0]['executing'] and not entries[0].get('offline', False)
    ), ' all three FullProf background projects must be in the CI/verify executing set'
    expected_file = directory / 'expected.json'
    assert expected_file.is_file(), (
        ' each new CLI project must carry its independent expected-result artifact'
    )
    expected = json.loads(expected_file.read_text())
    if case == 'cecoal':
        assert cli['source'] == 'cecoal-ls.sum' and 'M.L.' not in source.read_text(), (
            ' CeCoAl compares FullProf Iwg=0 least squares; Iwg=1 M.L. is provenance'
        )
        assert 'M.L.' in (FIXTURE / 'cecoal.sum').read_text(), (
            ' the original maximum-likelihood SUM must remain vendored as provenance'
        )
        assert (
            hashlib.sha256((directory / expected['source']['artifact']).read_bytes()).hexdigest()
            == cli['source_sha256']
        ), ' the CLI expectation must name the same independent least-squares SUM'
    units = _quantities(expected)
    assert units, ' each CLI project must execute at least one fit with independent quantities'
    for quantities in units:
        assert 'n_free' in quantities, ' every CLI fit must pin its complete FullProf free set'
        _bound(quantities['n_free'], CLI['cases'][case]['n_free'], 0)
        for name, (value, sigma) in CLI['cases'][case]['parameters'].items():
            # Pm-3m contains the cyclic axis permutation (x,y,z)->(z,x,y).
            # FullProf B=(1/2,1/2,z) and crysta 6f B=(x,1/2,1/2) are the same orbit.
            identity_name = 'B.fract_x' if case == 'lab6' and name == 'B.fract_z' else name
            matches = [
                spec
                for key, spec in quantities.items()
                if key.lower() == f'param.{identity_name}.value'.lower()
            ]
            assert len(matches) == 1, (
                ' each SUM parameter needs an expectation bound to its identity'
            )
            _bound(matches[0], value, sigma)
        for index, (value, sigma) in enumerate(
            zip(cli['background_coefficients'], cli['background_uncertainties'], strict=True)
        ):
            if sigma == 0:
                continue
            identity = re.compile(
                r'(?:background|coef(?:ficient)?|bg)[^\d]*' + str(index) + r'(?:\D|$)',
                re.IGNORECASE,
            )
            matches = [
                spec
                for key, spec in quantities.items()
                if key.startswith('param.') and key.endswith('.value') and identity.search(key)
            ]
            assert len(matches) == 1, (
                ' each free background coefficient needs its own SUM expectation'
            )
            _bound(matches[0], value, sigma)
    # The runtime declaration is checked through the real loader, not prose or source presence.
    project = edi.Project.load(directory / 'project')
    assert len(project.free_parameters) == CLI['cases'][case]['n_free'], (
        ' loaded CLI projects must retain the full independent free set'
    )
    _check_observations(project, case)
    if case == 'lab6':
        assert project.structure.space_group.name_h_m == 'P m -3 m', (
            ' cyclic axis equivalence requires the independent cubic Pm-3m space group'
        )
        lengths = dict(project.structure.scattering_lengths_fm or {})
        boron = project.structure.atom_sites['B']
        assert boron.wyckoff_letter == 'f', (
            ' the coordinate identity map requires the cubic 6f boron orbit'
        )
        assert boron.fract_y.value == 0.5 and boron.fract_z.value == 0.5, (
            ' the cyclic coordinate map must retain both fixed half coordinates'
        )
        assert boron.fract_x.free and not boron.fract_y.free and not boron.fract_z.free, (
            ' FullProf boron z must map to exactly the single free representative x'
        )
        assert boron.type_symbol in {'B11', '11B'} or lengths.get(boron.type_symbol) == 6.65, (
            ' LaB6 must declare 11B or an explicit 6.65 fm override'
        )
        assert project.experiment.peak.asym_fcj_1.value == pytest.approx(0.08, rel=0, abs=0), (
            ' the owner LaB6 model must retain fixed S_L=0.08'
        )
        assert project.experiment.peak.asym_fcj_2.value == pytest.approx(0.08, rel=0, abs=0), (
            ' the owner LaB6 model must retain fixed D_L=0.08'
        )
        assert (
            not project.experiment.peak.asym_fcj_1.free
            and not project.experiment.peak.asym_fcj_2.free
        ), ' fixed FCJ geometry must not absorb omitted background/shift fitting columns'

"""Published ionic factors must reach both the tables and live intensities."""

import hashlib
import json
import math
import re
from pathlib import Path

import edi as engine
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/xray_doublet'
PUBLISHED = json.loads((FIXTURE / 'published-f0.json').read_text())


def f0(coefficients, s):
    return coefficients['c'] + sum(
        a * math.exp(-b * s * s) for a, b in zip(coefficients['a'], coefficients['b'], strict=True)
    )


def ionic_project(path, key, table):
    path.mkdir()
    (path / 'structures').mkdir()
    (path / 'experiments').mkdir()
    template = (ROOT / 'tests/fixtures/c15_t2_polarization/isolated.edi').read_text()
    structure, experiment = template.replace('X a Li ', f'X a {key} ').split('data_experiment', 1)
    (path / 'structures/structure.edi').write_text(structure)
    grid = [2 * math.degrees(math.asin(1.54 * math.sqrt(n) / 4)) for n in (1, 2, 3)]
    experiment = ('data_experiment' + experiment).replace(
        'xray_form_factor it1992', f'xray_form_factor {table}'
    )
    experiment += '\nloop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
    experiment += ''.join(f'{x:.17g} 0 1\n' for x in grid)
    (path / 'experiments/experiment.edi').write_text(experiment)
    return engine.Project.load(path)


@pytest.mark.parametrize('ion', ['Fe3+', 'O2-'])
@pytest.mark.parametrize('table', ['wk1995', 'it1992'])
def test_ionic_site_intensity_ratio_matches_published_factors(tmp_path, ion, table):
    neutral = re.match(r'[A-Z][a-z]?', ion)[0]
    outputs = []
    for key in (neutral, ion):
        project = ionic_project(tmp_path / key, key, table)
        project.analysis.calculate()
        outputs.append(np.asarray(project.experiment.data.intensity_calc).copy())
    assert np.all(outputs[0] > 0), 'Neutral single-site control must have nonzero reflections'
    expected = [
        (
            f0(PUBLISHED[table][ion], math.sqrt(n) / 4)
            / f0(PUBLISHED[table][neutral], math.sqrt(n) / 4)
        )
        ** 2
        for n in (1, 2, 3)
    ]
    assert max(abs(v - 1) for v in expected) > 0.01, (
        'The ionic witness must discriminate the neutral substitution'
    )
    np.testing.assert_allclose(
        outputs[1] / outputs[0],
        expected,
        rtol=3e-6,
        atol=1e-8,
        err_msg='Ionic site amplitudes must use the declared published factors before squaring',
    )


def test_external_coefficient_snapshot_retains_its_digest():
    manifest = json.loads((FIXTURE / 'manifest.json').read_text())
    assert (
        hashlib.sha256((FIXTURE / 'published-f0.json').read_bytes()).hexdigest()
        == manifest['published-f0.json']
    ), 'Published ionic reference coefficients must retain their independent snapshot bytes'

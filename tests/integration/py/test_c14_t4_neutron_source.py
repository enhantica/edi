""": source selection crosses the experiment, project and numeric seams.

Independent published Gd values and closed form: fixtures/c14_t4_neutron/PROVENANCE.md.
"""

import json
import math
from pathlib import Path

import edi as engine
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/c14_t4_neutron'
CONTRACT = json.loads((FIXTURE / 'sources.json').read_text())
FIELD = CONTRACT['field']
SOURCES = CONTRACT['sources']
THETA = math.asin(1.54 / 4)
GRID = [2 * math.degrees(THETA) + offset for offset in (-0.01, 0, 0.01)]


def _project(tmp_path, value=None, *, radiation='neutron', extra='', boron=False):
    structure, experiment = (FIXTURE / 'model.edi').read_text().split('data_experiment', 1)
    if boron:
        structure = structure.rstrip() + '\nB b B Biso 0.5 0.5 0.5 0.7 0.8\n'
    (tmp_path / 'structures').mkdir(parents=True)
    (tmp_path / 'experiments').mkdir()
    (tmp_path / 'structures/structure.edi').write_text(
        structure.replace('data_structure', 'data_structure\n_edi.schema_version 3')
    )
    experiment = 'data_experiment\n_edi.schema_version 3' + experiment
    experiment = experiment.replace('radiation_probe neutron', 'radiation_probe ' + radiation)
    if value is not None:
        experiment += f'\n_scattering_source.{FIELD} {value}\n'
    experiment += extra
    experiment += '\nloop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
    experiment += ''.join(f'{x:.17g} 0 1\n' for x in GRID)
    (tmp_path / 'experiments/experiment.edi').write_text(experiment)
    return tmp_path


def _saved_source(root):
    tokens = [
        line.split(maxsplit=1)[1].strip().strip('\'"')
        for path in (root / 'experiments').glob('*.edi')
        for line in path.read_text().splitlines()
        if line.startswith('_scattering_source.' + FIELD + ' ')
    ]
    assert len(tokens) <= 1, ' must emit at most one neutron source per experiment'
    return tokens[0] if tokens else None


@pytest.mark.parametrize('source', [None, *SOURCES])
def test_neutron_source_preserves_presence_and_value_twice(tmp_path, source):
    path = _project(tmp_path / 'input', source)
    for index in range(2):
        project = engine.Project.load(path)
        path = tmp_path / f'saved-{index}'
        project.save_as(path)
        assert _saved_source(path) == source, (
            ' neutron source must survive repeated save/load as declared, including absence'
        )


@pytest.mark.parametrize('source', SOURCES)
@pytest.mark.parametrize('boron', [False, True], ids=['magnitude', 'interference-sign'])
def test_published_source_reaches_closed_form_pattern(tmp_path, source, boron):
    # The second site prevents |b|^2 alone from hiding an incorrect sign.
    project = engine.Project.load(_project(tmp_path, source, boron=boron))
    project.analysis.calculate()
    b = SOURCES[source] - (5.30 if boron else 0)
    # Neutron intensities use barns: 1 barn = 100 fm squared.
    area = 6 * (0.7 * b) ** 2 * math.exp(-1.6 / 16) / 100
    area /= math.sin(THETA) * math.sin(2 * THETA)
    expected = [
        area
        * math.sqrt(4 * math.log(2) / math.pi)
        / 0.1
        * math.exp(-4 * math.log(2) * delta**2 / 0.01)
        for delta in (-0.01, 0, 0.01)
    ]
    np.testing.assert_allclose(
        project.experiments[0].data.intensity_calc,
        expected,
        rtol=2e-7,
        atol=1e-7,
        err_msg=' must use the selected published Gd length, not an ignored/default source',
    )
    project.save_as(tmp_path / 'saved')
    restored = engine.Project.load(tmp_path / 'saved')
    restored.analysis.calculate()
    np.testing.assert_allclose(
        restored.experiments[0].data.intensity_calc,
        expected,
        rtol=2e-7,
        atol=1e-7,
        err_msg=' reloaded source must still reach calculation',
    )


@pytest.mark.parametrize(
    ('radiation', 'field', 'value'),
    [
        ('neutron', FIELD, 'not-a-publication'),
        ('neutron', FIELD, 'fullprof-compat'),
        ('neutron', FIELD, 'crysta-default'),
        ('xray', FIELD, 'sears1992'),
        ('xray', FIELD, 'rauch2003ext'),
        ('neutron', 'xray_form_factor', 'wk1995'),
        ('neutron', 'xray_dispersion', 'none'),
    ],
)
def test_wrong_probe_and_unknown_source_are_structured_errors(tmp_path, radiation, field, value):
    path = _project(tmp_path, radiation=radiation, extra=f'\n_scattering_source.{field} {value}\n')
    with pytest.raises(engine.IoError) as raised:
        engine.Project.load(path)
    assert field in str(raised.value), (
        ' source refusal must identify its field in a structured input error'
    )


DEFAULT_REFERENCE = json.loads((FIXTURE / 'rauch2003ext.json').read_text())['rows']


def _closed_form(real_b, boron):
    amplitude = real_b - (5.30 if boron else 0)
    area = 6 * (0.7 * amplitude) ** 2 * math.exp(-1.6 / 16) / 100
    area /= math.sin(THETA) * math.sin(2 * THETA)
    return np.asarray([
        area
        * math.sqrt(4 * math.log(2) / math.pi)
        / 0.1
        * math.exp(-4 * math.log(2) * delta**2 / 0.01)
        for delta in (-0.01, 0, 0.01)
    ])


@pytest.mark.parametrize('element', DEFAULT_REFERENCE)
def test_named_default_matches_omission_and_independent_table_for_every_element(tmp_path, element):
    # Two contrasts identify signed b: equal b squared alone admits a sign escape.
    for boron in (False, True):
        calculated = []
        for source in (None, 'rauch2003ext'):
            path = _project(tmp_path / f'{source}-{boron}', source, boron=boron)
            structure = path / 'structures/structure.edi'
            structure.write_text(structure.read_text().replace('X a Gd ', f'X a {element} '))
            project = engine.Project.load(path)
            project.analysis.calculate()
            actual = np.asarray(project.experiments[0].data.intensity_calc).copy()
            np.testing.assert_allclose(
                actual,
                _closed_form(DEFAULT_REFERENCE[element]['b_real_fm'], boron),
                rtol=2e-7,
                atol=1e-9,
                err_msg=' gate 6 each default path must use published signed b',
            )
            calculated.append(actual)
        np.testing.assert_array_equal(
            calculated[0],
            calculated[1],
            err_msg=' gate 6 declaring the default must change no calculated value',
        )

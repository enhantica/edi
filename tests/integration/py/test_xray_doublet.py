"""Independent FullProf profiles and nontrivial wavelength/absorption seams."""

import hashlib
import json
import math
from pathlib import Path

import edi as engine
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/xray_doublet'
TERMS = ('setup_wavelength_2', 'setup_wavelength_2_to_1_ratio')


def reference(case):
    stem = json.loads((FIXTURE / 'manifest.json').read_text())[case]['stem']
    rows = (FIXTURE / case / f'{stem}.prf').read_text().split('BEGIN', 1)[1].split('END', 1)[0]
    return np.array([
        [float(v) for v in line.split()[:3]] for line in rows.splitlines() if line.strip()
    ])[:, [0, 2]]


def project_at(path, *, case='doublet', tokens=''):
    path.mkdir(parents=True)
    (path / 'structures').mkdir()
    (path / 'experiments').mkdir()
    structure, experiment = (FIXTURE / 'lif.edi').read_text().split('data_experiment', 1)
    (path / 'structures/structure.edi').write_text(structure)
    experiment = 'data_experiment' + experiment + '\n' + tokens
    experiment += '\nloop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
    experiment += ''.join(f'{x:.17g} 0 1\n' for x in reference(case)[:, 0])
    (path / 'experiments/experiment.edi').write_text(experiment)
    return engine.Project.load(path)


def term(project, name):
    instrument = project.experiment.instrument
    assert hasattr(instrument, name), f'X-ray doublet requires instrument parameter {name}'
    return getattr(instrument, name)


def set_doublet(project, ratio=0.5, wavelength=1.5444):
    term(project, TERMS[0]).value = wavelength
    term(project, TERMS[1]).value = ratio


def pattern(project):
    project.analysis.calculate()
    values = np.asarray(project.experiment.data.intensity_calc).copy()
    assert np.isfinite(values).all(), 'X-ray witness must calculate finite intensity'
    assert values.max() > 0, 'X-ray witness must calculate nonzero intensity'
    return values


def agree(actual, expected):
    assert np.linalg.norm(actual - expected) / np.linalg.norm(expected) < 0.01, (
        'Fixed LiF settings must agree with the independent FullProf profile within one percent L2'
    )


@pytest.mark.parametrize('case', ['absorption', 'doublet'])
def test_independent_profile_rejects_the_uncorrected_single_component(tmp_path, case):
    tokens = (
        '_absorption.type cylinder-hewat\n_absorption.mu_r 0\n' if case == 'absorption' else ''
    )
    project = project_at(tmp_path / 'input', case=case, tokens=tokens)
    with pytest.raises(AssertionError, match='independent FullProf profile'):
        agree(pattern(project), reference(case)[:, 1])


@pytest.mark.parametrize('case', ['absorption', 'doublet'])
def test_fixed_fullprof_profile_and_reached_correction_escape(tmp_path, case):
    tokens = (
        '_absorption.type cylinder-hewat\n_absorption.mu_r 0.9\n' if case == 'absorption' else ''
    )
    project = project_at(tmp_path / 'input', case=case, tokens=tokens)
    if case == 'doublet':
        set_doublet(project)
    expected = reference(case)[:, 1]
    agree(pattern(project), expected)
    if case == 'absorption':
        project.experiment.absorption.mu_r.value = 0.0
    else:
        term(project, TERMS[1]).value = 0.0
    with pytest.raises(AssertionError, match='independent FullProf profile'):
        agree(pattern(project), expected)


def test_zero_ratio_is_bitwise_single_wavelength_boundary(tmp_path):
    project = project_at(tmp_path / 'input')
    single = pattern(project)
    set_doublet(project, ratio=0.0, wavelength=1.6732)
    np.testing.assert_array_equal(
        pattern(project),
        single,
        err_msg='Zero ratio must preserve the single-wavelength path byte for byte',
    )


def test_nonidentity_ratio_is_linear_and_warm_changes_invalidate(tmp_path):
    project = project_at(tmp_path / 'input')
    single = pattern(project)
    set_doublet(project, ratio=1.0)
    second = pattern(project) - single
    assert np.linalg.norm(second) > 1.0, 'The second wavelength must contribute nonzero intensity'
    for ratio in (0.375, 0.8125, 0.375):
        term(project, TERMS[1]).value = ratio
        np.testing.assert_allclose(
            pattern(project),
            single + ratio * second,
            rtol=2e-12,
            atol=1e-10,
            err_msg='Warm calculations must weight only the second component by the ratio',
        )


def test_second_wavelength_has_its_own_bragg_position_and_lorentz_factor(tmp_path):
    source = ROOT / 'tests/fixtures/c15_t2_polarization/isolated.edi'
    structure, experiment = source.read_text().split('data_experiment', 1)
    path = tmp_path / 'input'
    (path / 'structures').mkdir(parents=True)
    (path / 'experiments').mkdir()
    (path / 'structures/structure.edi').write_text(structure)
    (path / 'experiments/experiment.edi').write_text(
        'data_experiment'
        + experiment
        + '\nloop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
        + '10 0 1\n11 0 1\n'
    )
    project = engine.Project.load(path)
    for wavelength in (1.9, 1.8, 1.9):
        angles = [math.asin(value / 4) for value in (1.54, wavelength)]
        grid = [2 * math.degrees(angle) for angle in angles]
        project.experiment.data = engine.PdCwlData(
            two_theta=grid, intensity_meas=[0.0, 0.0], intensity_meas_su=[1.0, 1.0]
        )
        set_doublet(project, ratio=0.375, wavelength=wavelength)
        actual = pattern(project)
        expected = (
            0.375
            * (math.sin(angles[0]) * math.sin(2 * angles[0]))
            / (math.sin(angles[1]) * math.sin(2 * angles[1]))
        )
        assert actual[0] > 0, 'The first-wavelength Bragg peak must remain nonzero'
        assert actual[1] / actual[0] == pytest.approx(expected, rel=2e-10), (
            'Each wavelength must use its own Bragg angle and CW Lorentz factor'
        )


def check_roundtrip(project, before):
    for name, value in zip(TERMS, (1.5444, 0.375), strict=True):
        assert term(project, name).value == value, (
            'Saved doublet must preserve both parameter values exactly'
        )
    assert term(project, TERMS[1]).free, 'Saved doublet must preserve the free ratio flag'
    np.testing.assert_array_equal(
        pattern(project),
        before,
        err_msg='Saved doublet must preserve the calculated pattern exactly',
    )


@pytest.mark.parametrize('drop_ratio', [False, True])
def test_doublet_roundtrip_and_reached_serialization_escape(tmp_path, drop_ratio):
    project = project_at(tmp_path / 'input')
    set_doublet(project, ratio=0.375)
    term(project, TERMS[1]).free = True
    before = pattern(project)
    saved = tmp_path / 'saved'
    project.save_as(saved)
    snapshots = {p.name: p.read_bytes() for p in (saved / 'experiments').glob('*.edi')}
    if drop_ratio:
        changed = 0
        for path in (saved / 'experiments').glob('*.edi'):
            lines = path.read_text().splitlines(keepends=True)
            kept = [line for line in lines if not line.startswith('_instrument.' + TERMS[1])]
            changed += len(lines) - len(kept)
            path.write_text(''.join(kept))
        assert changed == 1, 'Serialization escape must remove the actual saved ratio token'
        with pytest.raises(AssertionError, match='Saved doublet must preserve'):
            check_roundtrip(engine.Project.load(saved), before)
    else:
        restored = engine.Project.load(saved)
        check_roundtrip(restored, before)
        restored.save_as(tmp_path / 'again')
        assert snapshots == {
            p.name: p.read_bytes() for p in (tmp_path / 'again/experiments').glob('*.edi')
        }, 'Doublet experiment serialization must be a byte-identical fixed point'


@pytest.mark.parametrize('case', ['doublet', 'absorption'])
def test_fullprof_bytes_match_the_committed_external_source(case):
    manifest = json.loads((FIXTURE / 'manifest.json').read_text())
    for name, digest in manifest[case]['files'].items():
        assert hashlib.sha256((FIXTURE / case / name).read_bytes()).hexdigest() == digest, (
            'FullProf reference bytes must retain their independently recorded provenance'
        )

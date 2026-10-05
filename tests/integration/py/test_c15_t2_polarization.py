"""public correction seam; closed form and independent FullProf values."""

import hashlib
import json
import math
from pathlib import Path

import edi as engine
import numpy as np
import pytest

from tests.conftest import corpus_case_dir

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/c15_t2_polarization'
TERMS = ('setup_polarization_coefficient', 'setup_monochromator_twotheta')
GRID = np.array([2 * math.degrees(math.asin(1.54 * math.sqrt(n) / 4)) for n in (1, 2, 3)])


def _project(path, *, lif=False, tokens=''):
    text = (FIXTURE / ('lif.edi' if lif else 'isolated.edi')).read_text()
    structure, experiment = text.split('data_experiment', 1)
    (path / 'structures').mkdir(parents=True)
    (path / 'experiments').mkdir()
    (path / 'structures/structure.edi').write_text(structure)
    grid = np.loadtxt(FIXTURE / 'reference.tsv')[:, 0] if lif else GRID
    experiment = 'data_experiment' + experiment + tokens
    experiment += '\nloop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
    experiment += ''.join(f'{x:.17g} 0 1\n' for x in grid)
    (path / 'experiments/experiment.edi').write_text(experiment)
    return engine.Project.load(path)


def _term(project, name):
    instrument = project.experiment.instrument
    assert hasattr(instrument, name), f' missing capability: X-ray instrument parameter {name}'
    return getattr(instrument, name)


def _set(project, coefficient, angle):
    for name, value in zip(TERMS, (coefficient, angle), strict=True):
        _term(project, name).value = value


def _calculate(project):
    project.analysis.calculate()
    result = np.array(project.experiment.data.intensity_calc)
    assert np.isfinite(result).all() and np.max(result) > 0, (
        ' physical witness must calculate finite nonzero intensity'
    )
    return result


def _factor(coefficient, angle):
    # Independent FullProf section 3.4 / upstream convention; see fixture provenance.
    return (
        1
        - coefficient
        + coefficient * math.cos(math.radians(angle)) ** 2 * np.cos(np.radians(GRID)) ** 2
    )


@pytest.mark.parametrize(
    ('coefficient', 'angle'), [(0.5, 26.5650511771), (0.37, 41.0), (0.8, 67.0)]
)
def test_nonidentity_correction_uses_degrees_and_bragg_angle(tmp_path, coefficient, angle):
    project = _project(tmp_path)
    baseline = _calculate(project)
    _set(project, coefficient, angle)
    np.testing.assert_allclose(
        _calculate(project) / baseline,
        _factor(coefficient, angle),
        rtol=1e-10,
        atol=1e-12,
        err_msg=' intensity must contain K and cos-squared monochromator angle in degrees',
    )
    # Two warm changes, then restore, exercise both CALIBRATION invalidation paths.
    for k, a in ((0.63, angle), (0.63, 33.0), (coefficient, angle)):
        _set(project, k, a)
        np.testing.assert_allclose(
            _calculate(project) / baseline,
            _factor(k, a),
            rtol=1e-10,
            atol=1e-12,
            err_msg=' either live parameter change must invalidate cached intensity',
        )


def test_zero_coefficient_preserves_prior_lorentz_path_exactly(tmp_path):
    project = _project(tmp_path)
    baseline = _calculate(project)
    _set(project, 0.0, 41.0)
    np.testing.assert_array_equal(
        _calculate(project),
        baseline,
        err_msg=' zero K must retain the  unpolarized intensity exactly',
    )


def test_polarized_lif_matches_fixed_fullprof_profile_without_scale_fit(tmp_path):
    project = _project(tmp_path, lif=True)
    _set(project, 0.5, 26.5650511771)
    expected = np.loadtxt(FIXTURE / 'reference.tsv')[:, 1]
    actual = _calculate(project)
    assert np.linalg.norm(actual - expected) / np.linalg.norm(expected) < 0.01, (
        ' fixed polarized LiF must agree with independent FullProf within 1 percent L2'
    )
    _set(project, 0.0, 26.5650511771)
    assert np.linalg.norm(_calculate(project) - expected) / np.linalg.norm(expected) > 0.1, (
        ' independent profile must detect removal of the polarization term'
    )


def _check_saved(project, before, values):
    for name, expected in zip(TERMS, values, strict=True):
        parameter = _term(project, name)
        assert parameter.value == expected and parameter.free, (
            f' save/load must preserve {name} value and free flag exactly'
        )
    np.testing.assert_array_equal(
        _calculate(project),
        before,
        err_msg=' save/load must preserve the calculated polarized pattern exactly',
    )


def test_both_parameter_tokens_roundtrip_bytes_and_pattern(tmp_path):
    values = (0.375, 31.25)
    tokens = ''.join(
        f'\n_instrument.{name} {value}()\n' for name, value in zip(TERMS, values, strict=True)
    )
    project = _project(tmp_path / 'input', tokens=tokens)
    before = _calculate(project)
    _check_saved(project, before, values)
    snapshots = []
    for i in range(2):
        saved = tmp_path / f'saved-{i}'
        project.save_as(saved)
        snapshots.append({p.name: p.read_bytes() for p in (saved / 'experiments').glob('*.edi')})
        project = engine.Project.load(saved)
        _check_saved(project, before, values)
    assert snapshots[0] == snapshots[1], (
        ' canonical experiment serialization must be byte-identical after reload'
    )


@pytest.mark.parametrize('name', TERMS)
def test_serialization_witness_rejects_a_dropped_parameter(tmp_path, name):
    # Exercise the same invariant as the live round trip, with one serialized token lost.
    project = _project(tmp_path / 'input')
    _set(project, 0.375, 31.25)
    for term in TERMS:
        _term(project, term).free = True
    before = _calculate(project)
    project.save_as(tmp_path / 'saved')
    tokens = ''.join(
        f'\n_instrument.{term} {value}()\n'
        for term, value in zip(TERMS, (0.375, 31.25), strict=True)
        if term != name
    )
    restored = _project(tmp_path / 'dropped', tokens=tokens)
    with pytest.raises(AssertionError, match='save/load must preserve'):
        _check_saved(restored, before, (0.375, 31.25))


@pytest.mark.parametrize('name', TERMS)
def test_each_parameter_moves_in_public_fit(name):
    # Before: off-corpus isolated self-data. After: the declared LiF corpus
    # with every other parameter fixed; the same single-column recovery
    # invariant remains, while independent FullProf gates own accuracy.
    project = engine.Project.load(corpus_case_dir('lif-xray-s1') / 'project')
    for owner in (project.experiment.instrument, project.experiment.peak):
        for parameter in owner.parameters:
            parameter.free = False
    project.experiment.linked_structure.scale.free = False
    _set(project, 0.37, 41.0)
    observed = _calculate(project)
    project.experiment.data.intensity_meas = observed.tolist()
    project.experiment.data.intensity_meas_su = [1.0] * len(observed)
    parameter = _term(project, name)
    target = parameter.value
    parameter.value = target * 0.9
    parameter.free = True
    # Self-data establishes a fit round trip only; accuracy comes from FullProf above.
    project.analysis.fit()
    assert abs(parameter.value - target) < 2e-4, (
        f' public fitting must include and move the free {name} parameter'
    )


def test_frozen_reference_and_author_run_remain_independent():
    manifest = json.loads((FIXTURE / 'manifest.json').read_text())
    for directory, files in (
        (FIXTURE, manifest['files']),
        (FIXTURE / 'author-run', manifest['author_run']['files']),
    ):
        for name, digest in files.items():
            assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest, (
                ' independent FullProf inputs and outputs must retain their pinned bytes'
            )
    upstream = np.loadtxt(FIXTURE / 'reference.tsv')
    text = (FIXTURE / 'author-run/lif_single_polarized.prf').read_text()
    rows = text.split('BEGIN', 1)[1].split('END', 1)[0].strip().splitlines()
    rerun = np.array([[float(s) for s in line.split()[:3]] for line in rows])
    np.testing.assert_array_equal(
        rerun[:, 0],
        upstream[:, 0],
        err_msg=' author-time FullProf grid must equal the upstream grid',
    )
    # Independent builds of FullProf differ in single-precision profile rounding.
    # Use the same fixed-parameter physical acceptance bound as the product comparison.
    assert np.linalg.norm(rerun[:, 2] - upstream[:, 1]) / np.linalg.norm(upstream[:, 1]) < 0.01, (
        ' author-time FullProf must reproduce the upstream profile within 1 percent L2'
    )


def test_c33_owned_page_is_the_measured_filename_difference():
    baseline = json.loads((FIXTURE / 'page-baseline.json').read_text())
    before = set(baseline['before_pages'])
    # The independently gated two-bank verification page is now retained prior art.
    before.add('pd-neut-tof_ferrite-austenite_beer_joint')
    after = {p.stem for p in (ROOT / 'docs/dev/verification').glob('*.py')}
    # ADR-0078 adds its separately gated tied-Biso page; keep this task's delta exact.
    after.discard('pd-neut-cwl_cosio-d20_biso-tied')
    assert before <= after and after - before == {'pd-xray-cwl_LiF_single_polarization'}, (
        ' C33 filename difference must contain exactly its owned polarization page'
    )

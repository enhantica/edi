"""The six-dataset taurine example against the sealed converged independent fit."""

import hashlib
import json
import math
import shutil
from pathlib import Path

import numpy as np
import pytest

from tests.fixtures.single_crystal.freeze_taurine_converged import extract
from tests.integration.py.test_single_crystal import engine

ROOT = Path(__file__).resolve().parents[3]
REFERENCE = ROOT / 'tests/fixtures/single_crystal/example_fits/taurine_converged'
CASE = 'single-crystal-senju-taurine-converged'
BACKEND = 'edi'


def parameter(model, path):
    block, category, *items = path.split('.')
    if category in {'atom_site', 'atom_site_aniso'}:
        structure = model.structures[block]
        rows = structure.atom_sites if category == 'atom_site' else structure.atom_site_aniso
        return getattr(next(a for a in rows if a.id == items[0]), items[1])
    experiment = next(e for e in model.experiments if e.name == block)
    if category == 'extinction':
        return getattr(experiment.extinction, items[0])
    return experiment.linked_structure.scale


def test_converged_artifacts_and_parameter_conventions_are_independent():
    record = json.loads((REFERENCE / 'reference.json').read_text())
    for name, digest in record['artifacts'].items():
        assert hashlib.sha256((REFERENCE / name).read_bytes()).hexdigest() == digest, (
            'The converged FullProf input, output and stimulus bytes must retain '
            'their sealed hashes'
        )
    parsed = extract(REFERENCE, (REFERENCE / 'original.pcr').read_text())
    for key, value in parsed.items():
        expected = (
            pytest.approx(value, rel=2e-15)
            if key == 'reduced_chi_square_from_printed_rows'
            else value
        )
        assert record[key] == expected, (
            'Every reference value must be recoverable from committed FullProf files'
        )
    assert record['cycle'] == 52, 'The independent output must explicitly converge at cycle 52'
    assert record['n_free'] == 135, (
        'Every one of the independent final parameters must be retained'
    )
    assert record['n_selected'] == 947, 'The comparison must retain FullProf observation selection'
    assert (
        sum(
            p['codeword_coefficient'] == pytest.approx(0.2, rel=0, abs=0)
            for p in record['parameters']
        )
        == 9
    ), 'The six scales and three extinction terms must cross the nonidentity codeword convention'
    original = (REFERENCE / 'original.pcr').read_bytes().splitlines(keepends=True)
    tightened = (REFERENCE / 'input.pcr').read_bytes().splitlines(keepends=True)
    assert [
        i for i, pair in enumerate(zip(original, tightened, strict=True)) if pair[0] != pair[1]
    ] == [10], 'The starting control must change only NCY and Eps on the documented input line'
    assert tightened[10].split()[:2] == [b'200', b'0.01'], (
        'The independent fit must use the authorized cycle and convergence precision settings'
    )


def test_actual_taurine_fit_matches_all_fullprof_parameters_and_uncertainties(tmp_path):  # noqa: PLR0914
    record = json.loads((REFERENCE / 'reference.json').read_text())
    source = (
        ROOT / 'docs/user/cli/sc-neut-tof_taurine-senju/project'
        if BACKEND == 'edi'
        else ROOT / 'tests/fitting' / CASE / 'project'
    )
    staged = tmp_path / 'project'
    shutil.copytree(source, staged)
    model = engine().Project.load(staged)
    assert len(model.free_parameters) == record['n_free'], (
        'The taurine example must solve the same 135 independent parameters as FullProf'
    )
    displacement = {
        'taurine.atom_site.S1.fract_x': 0.005,
        'taurine.atom_site.O1.fract_y': -0.005,
        'taurine.atom_site.N1.fract_z': 0.005,
        'taurine.atom_site.C1.fract_x': -0.005,
    }
    for p in record['parameters']:
        live = parameter(model, p['path'])
        expected = (
            0.0
            if '.atom_site_aniso.' in p['path'] or '.extinction.' in p['path']
            else p['start'] + displacement.get(p['path'], 0.0)
        )
        assert live.value == pytest.approx(expected, rel=0, abs=1e-12), (
            'The example starts with zero beta and extinction values and the four '
            'declared coordinate displacements; other independent starts stay unchanged'
        )
    assert all(
        getattr(experiment.extinction, 'coefficient_' + component).value == 0
        for experiment in model.experiments
        for component in ('11', '22', '33', '12', '13', '23')
    ), 'Every dataset must start with all extinction coefficients zero, including fixed slots'
    result = model.analysis.fit()
    distances = []
    for p in record['parameters']:
        live = parameter(model, p['path'])
        assert math.isfinite(live.value), 'Every fitted taurine parameter must remain finite'
        assert live.uncertainty is not None, (
            'Every independent fitted parameter must publish an uncertainty'
        )
        assert live.uncertainty > 0, 'Every independent fitted uncertainty must be positive'
        assert abs(live.value - p['value']) <= p['su'], (
            'Every fitted value must agree within one conventional independent '
            'FullProf uncertainty: ' + p['symbol']
        )
        assert live.uncertainty == pytest.approx(p['su'], rel=0.2), (
            'FullProf codeword coefficients must be undone before comparing standard '
            'uncertainties: ' + p['symbol']
        )
        distances.append(abs(live.value - p['value']) / live.uncertainty)
    # The reported claim uses independent FullProf targets, never pinned product values.
    assert max(distances) <= 0.58, (
        'The claimed taurine agreement must hold for all 135 values within 0.58 '
        'product standard uncertainties'
    )
    residual = denominator = 0.0
    n = 0
    model.analysis.calculate()
    for experiment in model.experiments:
        observed = np.asarray(experiment.refln.intensity_meas)
        sigma = np.asarray(experiment.refln.intensity_meas_su)
        calculated = np.asarray(experiment.refln.intensity_calc)
        selected = observed > 3 * sigma
        n += int(np.count_nonzero(selected))
        residual += float(
            np.sum(((observed[selected] - calculated[selected]) / sigma[selected]) ** 2)
        )
        denominator += float(np.sum((observed[selected] / sigma[selected]) ** 2))
    assert n == record['n_selected'], (
        'Both engines must fit exactly the same selected observations'
    )
    chi2 = residual / (n - record['n_free'])
    assert result.reduced_chi_square == pytest.approx(chi2, rel=1e-9), (
        'The joint objective must use every selected residual and the N minus p denominator'
    )
    assert chi2 == pytest.approx(record['reduced_chi_square_from_printed_rows'], rel=0.01), (
        'The fitted objective must agree with the independently summed FullProf residual table'
    )
    # Convergence regression pin from the displaced-start CLI fit.
    assert chi2 == pytest.approx(30.27111635, rel=1e-7), (
        'The displaced-start example must retain its documented convergence regression pin '
        'alongside the independent FullProf comparison'
    )
    assert math.sqrt(residual / denominator) == pytest.approx(
        record['rf2w_percent'] / 100, abs=0.001
    ), 'The weighted reflection factor must agree with the converged FullProf summary'
    # The unweighted factor is point-sensitive: compare the exact independent parameter point.
    for p in record['parameters']:
        parameter(model, p['path']).value = p['value']
    model.analysis.calculate()
    reference_difference = reference_observed = 0.0
    for experiment in model.experiments:
        observed = np.asarray(experiment.refln.intensity_meas)
        sigma = np.asarray(experiment.refln.intensity_meas_su)
        calculated = np.asarray(experiment.refln.intensity_calc)
        selected = observed > 3 * sigma
        reference_difference += float(np.sum(abs(observed[selected] - calculated[selected])))
        reference_observed += float(np.sum(abs(observed[selected])))
    assert reference_difference / reference_observed == pytest.approx(
        record['rf2_percent'] / 100, abs=0.0005
    ), 'The absolute factor at the FullProf parameter point must match its printed rounding'

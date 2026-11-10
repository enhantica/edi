""": independent March-Dollase invariants at the consuming project seam."""

import itertools
import math
from pathlib import Path

import edi as engine
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/c13_t4_march'


def _project(path, ratio, fraction=0.0, axis=(0, 0, 1), *, ortho=False, free=False):
    structure, experiment = (FIXTURE / 'model.edi').read_text().split('data_experiment', 1)
    lengths = (2.2, 3.1, 4.3) if ortho else (2.0, 2.0, 2.0)
    if ortho:
        structure = structure.replace('"P m -3 m"', '"P 1"')
        for key, value in zip('abc', lengths, strict=True):
            structure = structure.replace(f'_cell.length_{key} 2', f'_cell.length_{key} {value}')
    hkls = [(0, 0, 1), (0, 1, 0), (1, 0, 0)] if ortho else [(1, 0, 0), (1, 1, 0), (1, 1, 1)]
    grid = [
        2
        * math.degrees(
            math.asin(
                1.54 / 2 * math.sqrt(sum((h / a) ** 2 for h, a in zip(hkl, lengths, strict=True)))
            )
        )
        for hkl in hkls
    ]
    (path / 'structures').mkdir(parents=True)
    (path / 'experiments').mkdir()
    (path / 'structures/structure.edi').write_text(structure)
    experiment = 'data_experiment' + experiment
    if ratio is not None:
        experiment += '\nloop_\n' + ''.join(
            f'_preferred_orientation.{key}\n'
            for key in (
                'structure_id',
                'march_r',
                'march_random_fract',
                'index_h',
                'index_k',
                'index_l',
            )
        )
        experiment += (
            f'structure {ratio}{"()" if free else ""} {fraction} {" ".join(map(str, axis))}\n'
        )
    experiment += '\nloop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
    experiment += ''.join(f'{x:.17g} 0 1\n' for x in grid)
    (path / 'experiments/experiment.edi').write_text(experiment)
    return engine.Project.load(path), hkls, lengths


def _pattern(project):
    project.analysis.calculate()
    result = np.asarray(project.experiments[0].data.intensity_calc).copy()
    assert result.shape == (3,) and np.isfinite(result).all() and (result > 0).all(), (
        ' isolated reference reflections must produce finite positive intensities'
    )
    return result


def _factor(hkl, lengths, axis, ratio, fraction, ortho):
    orbit = (
        {hkl, tuple(-h for h in hkl)}
        if ortho
        else {
            tuple(h * s for h, s in zip(p, signs, strict=True))
            for p in itertools.permutations(hkl)
            for signs in itertools.product((-1, 1), repeat=3)
        }
    )
    a = np.asarray(axis) / lengths
    factors = []
    for member in orbit:
        h = np.asarray(member) / lengths
        c2 = float(h @ a) ** 2 / float((h @ h) * (a @ a))
        factors.append(fraction + (1 - fraction) * (ratio**2 * c2 + (1 - c2) / ratio) ** -1.5)
    return np.mean(factors)


@pytest.mark.parametrize(('ratio', 'fraction'), [(0.73, 0.0), (1.2, 0.3), (1.0, 0.0), (1.4, 1.0)])
@pytest.mark.parametrize(
    ('ortho', 'axis'), [(False, (0, 0, 1)), (False, (1, 1, 0)), (True, (1, 0, 1))]
)
def test_march_ratio_reaches_each_reflection_with_orbit_and_metric(
    tmp_path, ratio, fraction, ortho, axis
):
    random, _, _ = _project(tmp_path / 'random', None, ortho=ortho)
    textured, hkls, lengths = _project(tmp_path / 'textured', ratio, fraction, axis, ortho=ortho)
    expected = [_factor(h, lengths, axis, ratio, fraction, ortho) for h in hkls]
    np.testing.assert_allclose(
        _pattern(textured) / _pattern(random),
        expected,
        rtol=2e-7,
        atol=1e-9,
        err_msg=' missing March orbit average and reciprocal metric correction',
    )


def test_march_parameter_is_live_free_and_roundtrips(tmp_path):
    project, hkls, lengths = _project(tmp_path / 'input', 1.2, 0.3, free=True)
    experiment = project.experiments[0]
    assert hasattr(experiment, 'preferred_orientation'), (
        ' missing capability: experiment-owned preferred_orientation collection'
    )
    row = experiment.preferred_orientation['structure']
    assert row.march_r.free, ' dictionary must load the ratio free flag'
    before = _pattern(project)
    row.march_r.value = 0.73
    after = _pattern(project)
    expected = [
        _factor(h, lengths, (0, 0, 1), 0.73, 0.3, ortho=False)
        / _factor(h, lengths, (0, 0, 1), 1.2, 0.3, ortho=False)
        for h in hkls
    ]
    np.testing.assert_allclose(
        after / before,
        expected,
        rtol=2e-7,
        atol=1e-9,
        err_msg=' changing march_r must invalidate calculated reflection intensities',
    )
    for index in range(2):
        saved = tmp_path / f'saved-{index}'
        project.save_as(saved)
        project = engine.Project.load(saved)
        row = project.experiments[0].preferred_orientation['structure']
        assert row.march_r.free and row.march_r.value == pytest.approx(0.73), (
            ' ratio value and free flag must survive repeated save/load'
        )
        np.testing.assert_allclose(
            _pattern(project),
            after,
            rtol=1e-12,
            err_msg=' restored orientation must still reach the calculated pattern',
        )


@pytest.mark.parametrize(
    ('ratio', 'fraction', 'axis'),
    [
        (0, 0, (0, 0, 1)),
        (-1, 0, (0, 0, 1)),
        (1.2, -0.1, (0, 0, 1)),
        (1.2, 1.1, (0, 0, 1)),
        (1.2, 0, (0, 0, 0)),
    ],
)
def test_invalid_orientation_is_a_structured_input_error(tmp_path, ratio, fraction, axis):
    diagnostic = (
        r'texture axis.*no direction' if axis == (0, 0, 0) else r'preferred_orientation|march_r'
    )
    with pytest.raises(engine.IoError, match=diagnostic):
        _project(tmp_path, ratio, fraction, axis)


def test_texture_keeps_phase_link_and_axis_sign_invariant(tmp_path):
    random, hkls, lengths = _project(tmp_path / 'random', None)
    baseline = _pattern(random)
    results = []
    for index, axis in enumerate(((0, 0, 1), (0, 0, -2))):
        root = tmp_path / f'mixed-{index}'
        _project(root, 0.73, 0.3, axis)
        project = engine.Project.load(root)
        row = project.experiments[0].preferred_orientation['structure']
        assert row.structure_id == 'structure', ' texture must retain the structure phase link'
        expected = np.asarray([
            _factor(h, lengths, (0, 0, 1), 0.73, 0.3, ortho=False) for h in hkls
        ])
        actual = _pattern(project)
        np.testing.assert_allclose(
            actual / baseline,
            expected,
            rtol=2e-7,
            atol=1e-9,
            err_msg=' March must retain phase link and axis sign/scale invariance',
        )
        results.append(actual)
    np.testing.assert_allclose(
        results[0],
        results[1],
        rtol=1e-12,
        err_msg=' an equivalent unoriented axis must give the same pattern',
    )


def _edit_and_use_texture(project, edit, operation, destination):
    # Validation may occur at editing or consuming; no wrong-key model may escape either use.
    edit()
    if operation == 'calculate':
        project.analysis.calculate()
    else:
        project.save_as(destination)


@pytest.mark.parametrize('operation', ['calculate', 'save'])
@pytest.mark.parametrize('bad_key', ['strcuture', 'unknown', ''])
def test_texture_create_unknown_key_cannot_calculate_or_save(tmp_path, bad_key, operation):
    project, _, _ = _project(tmp_path / 'input', None)
    baseline = _pattern(project)
    rows = project.experiments[0].preferred_orientation
    with pytest.raises(ValueError, match=r'(?i)structure|preferred.orientation'):
        _edit_and_use_texture(
            project,
            lambda: rows.create(structure_id=bad_key, march_r=0.73, march_random_fract=0.3),
            operation,
            tmp_path / 'invalid-output',
        )
    np.testing.assert_array_equal(
        project.experiments[0].data.intensity_calc,
        baseline,
        err_msg=' a rejected key must never activate the March factor',
    )


@pytest.mark.parametrize('operation', ['calculate', 'save'])
@pytest.mark.parametrize('bad_key', ['strcuture', 'unknown', ''])
def test_texture_mutated_key_cannot_calculate_or_save(tmp_path, operation, bad_key):
    project, _, _ = _project(tmp_path / 'input', 0.73, 0.3)
    _pattern(project)  # Exercise mutation after a cached successful calculation.
    row = project.experiments[0].preferred_orientation['structure']
    with pytest.raises(ValueError, match=r'(?i)structure|preferred.orientation'):
        _edit_and_use_texture(
            project,
            lambda: setattr(row, 'structure_id', bad_key),
            operation,
            tmp_path / 'invalid-output',
        )
    row.structure_id = 'structure'
    assert row.structure_id == 'structure', ' a valid texture key must remain assignable'
    _pattern(project)


def test_programmatic_texture_correct_key_activates_closed_form(tmp_path):
    project, hkls, lengths = _project(tmp_path / 'input', None)
    baseline = _pattern(project)
    rows = project.experiments[0].preferred_orientation
    rows.create(structure_id='structure', march_r=0.73, march_random_fract=0.3)
    rows['structure'].structure_id = 'structure'
    np.testing.assert_allclose(
        _pattern(project) / baseline,
        [_factor(h, lengths, (0, 0, 1), 0.73, 0.3, ortho=False) for h in hkls],
        rtol=2e-7,
        atol=1e-9,
        err_msg=' correct programmatic key must apply the independent March factor',
    )
    project.save_as(tmp_path / 'saved')
    np.testing.assert_array_equal(
        _pattern(engine.Project.load(tmp_path / 'saved')),
        _pattern(project),
        err_msg=' a valid programmatic texture must survive saving and loading',
    )


@pytest.mark.parametrize('bad_key', ['strcuture', 'unknown'])
def test_texture_loader_preserves_structure_key_rejection(tmp_path, bad_key):
    _project(tmp_path / 'input', 0.73, 0.3)
    source = tmp_path / 'input/experiments/experiment.edi'
    source.write_text(source.read_text().replace('structure 0.73', f'{bad_key} 0.73'))
    with pytest.raises(ValueError, match=r'(?i)structure|preferred.orientation'):
        engine.Project.load(tmp_path / 'input')


@pytest.mark.parametrize('operation', ['calculate', 'save'])
@pytest.mark.parametrize('bad_key', ['strcuture', 'unknown', ''])
def test_texture_add_unknown_key_cannot_calculate_or_save(tmp_path, bad_key, operation):
    project, _, _ = _project(tmp_path / 'input', None)
    baseline = _pattern(project)
    row = engine.PrefOrient()
    row.structure_id = bad_key
    row.march_r = 0.73
    row.march_random_fract = 0.3
    rows = project.experiments[0].preferred_orientation
    with pytest.raises(ValueError, match=r'(?i)structure|preferred.orientation'):
        _edit_and_use_texture(
            project, lambda: rows.add(row), operation, tmp_path / 'invalid-output'
        )
    np.testing.assert_array_equal(
        project.experiments[0].data.intensity_calc,
        baseline,
        err_msg=' rejected pre-built row must never activate the March factor',
    )


def test_texture_add_correct_key_preserves_live_item_and_factor(tmp_path):
    project, hkls, lengths = _project(tmp_path / 'input', None)
    baseline = _pattern(project)
    row = engine.PrefOrient()
    row.structure_id = 'structure'
    row.march_r = 0.73
    row.march_random_fract = 0.3
    project.experiments[0].preferred_orientation.add(row)
    assert project.experiments[0].preferred_orientation['structure'] is row, (
        ' valid insertion must retain the keyed collection live-item contract'
    )
    np.testing.assert_allclose(
        _pattern(project) / baseline,
        [_factor(h, lengths, (0, 0, 1), 0.73, 0.3, ortho=False) for h in hkls],
        rtol=2e-7,
        atol=1e-9,
        err_msg=' valid pre-built texture must apply the independent March factor',
    )


@pytest.mark.parametrize('field', ['index_h', 'index_k', 'index_l'])
@pytest.mark.parametrize('entrance', ['create', 'mutate'])
def test_texture_axis_loader_domain_at_programmatic_entrances(tmp_path, field, entrance):
    for value in (1001, -1001, 2**31 - 1, -(2**31)):
        for operation in ('calculate', 'save'):
            path = tmp_path / f'{value}-{operation}'
            project, _, _ = _project(path, None if entrance == 'create' else 0.73, 0.3)
            rows = project.experiments[0].preferred_orientation
            if entrance == 'mutate':
                _pattern(project)

            def attempt(project=project, value=value, rows=rows, operation=operation):
                if entrance == 'create':
                    rows.create(
                        structure_id='structure',
                        march_r=0.73,
                        march_random_fract=0.3,
                        **{field: value},
                    )
                else:
                    setattr(rows['structure'], field, value)
                _edit_and_use_texture(
                    project, lambda: None, operation, tmp_path / 'invalid-output'
                )

            with pytest.raises(ValueError, match=r'(?i)axis|index|bound|1000'):
                attempt()
    for value in (-1000, 1000):
        project, _, _ = _project(tmp_path / f'valid-{value}', None)
        project.experiments[0].preferred_orientation.create(
            structure_id='structure', march_r=0.73, march_random_fract=0.3, **{field: value}
        )
        row = project.experiments[0].preferred_orientation['structure']
        setattr(row, field, -value)
        expected = _pattern(project)
        destination = tmp_path / f'saved-{value}'
        project.save_as(destination)
        np.testing.assert_allclose(
            _pattern(engine.Project.load(destination)),
            expected,
            rtol=1e-10,
            err_msg=' accepted axis endpoints must remain calculable after round-trip',
        )


@pytest.mark.parametrize('field', ['index_h', 'index_k', 'index_l'])
def test_texture_prebuilt_axis_obeys_loader_domain(tmp_path, field):
    for value in (1001, -1001, 2**31 - 1, -(2**31)):
        for operation in ('calculate', 'save'):
            project, _, _ = _project(tmp_path / f'{value}-{operation}', None)

            def attempt(project=project, value=value, operation=operation):
                row = engine.PrefOrient()
                row.structure_id = 'structure'
                row.march_r = 0.73
                row.march_random_fract = 0.3
                setattr(row, field, value)
                project.experiments[0].preferred_orientation.add(row)
                _edit_and_use_texture(
                    project, lambda: None, operation, tmp_path / 'invalid-output'
                )

            with pytest.raises(ValueError, match=r'(?i)axis|index|bound|1000'):
                attempt()
    project, _, _ = _project(tmp_path / 'positive', None)
    row = engine.PrefOrient()
    row.structure_id = 'structure'
    row.march_r = 0.73
    row.march_random_fract = 0.3
    setattr(row, field, 1000)
    project.experiments[0].preferred_orientation.add(row)
    expected = _pattern(project)
    project.save_as(tmp_path / 'positive-saved')
    np.testing.assert_allclose(
        _pattern(engine.Project.load(tmp_path / 'positive-saved')),
        expected,
        rtol=1e-10,
        err_msg=' valid prebuilt axis endpoint must calculate and round-trip',
    )

"""Hill-Howard fractions from unequal scales, cell masses and volumes."""

import math
import re
from decimal import Decimal

import edi as engine
import numpy as np
import pytest

from tests.fixtures.multiphase import support as case
from tests.fixtures.weight_fractions.single_phase_bytes import COLUMN, historical_single_fraction


def weighted_project(path, *, free_scales=True):
    case.write_project(path)
    beta = path / 'structures/beta.edi'
    beta.write_text(beta.read_text() + 'Y a Gd Biso 0.23 0.31 0.47 0.35 0.8\n')
    project = engine.Project.load(path)
    rows = case.links(project.experiments[0])
    for name, uncertainty in (('alpha', 0.03), ('beta', 0.012)):
        rows[name].scale.free = free_scales
        if free_scales:
            rows[name].scale.uncertainty = uncertainty
    return project


def expected(scales):
    cell_masses = (0.7, 1.05)
    q = [
        math.prod(case.LENGTHS[name]) * mass
        for name, mass in zip(('alpha', 'beta'), cell_masses, strict=True)
    ]
    denominator = sum(s * mass_volume for s, mass_volume in zip(scales, q, strict=True))
    fractions = [s * mass_volume / denominator for s, mass_volume in zip(scales, q, strict=True)]
    error = q[0] * q[1] * math.hypot(scales[1] * 0.03, scales[0] * 0.012) / denominator**2
    return fractions, error


def fractions(project):
    project.analysis.calculate()
    rows = case.links(project.experiments[0])
    for name in ('alpha', 'beta'):
        assert hasattr(rows[name], 'weight_fraction'), (
            'Linked structures must expose the Hill-Howard weight fraction with its uncertainty'
        )
    return [rows[name].weight_fraction for name in ('alpha', 'beta')]


def test_hill_howard_values_uncertainties_and_warm_scale_changes(tmp_path):
    project = weighted_project(tmp_path / 'input')
    rows = case.links(project.experiments[0])
    for scales in ((2.75, 0.375), (1.125, 0.875), (2.75, 0.375)):
        for name, scale in zip(('alpha', 'beta'), scales, strict=True):
            rows[name].scale.value = scale
        wanted, error = expected(scales)
        actual = fractions(project)
        np.testing.assert_allclose(
            [item.value for item in actual],
            wanted,
            rtol=2e-12,
            atol=1e-14,
            err_msg='Weight fractions must include scale, occupied cell mass and unit-cell volume',
        )
        np.testing.assert_allclose(
            [item.uncertainty for item in actual],
            [error, error],
            rtol=2e-10,
            atol=1e-14,
            err_msg='Weight-fraction uncertainties must propagate scales through normalization',
        )
        assert sum(item.value for item in actual) == pytest.approx(1.0, abs=1e-14), (
            'Calculated phase weight fractions must sum to unity'
        )


def check_saved_fraction(token, wanted):
    match = re.fullmatch(r'([-+\d.eE]+)\(([-+\d.eE]+)\)', token)
    assert match, 'Each free-scale fraction must save its numeric value and standard uncertainty'
    value, uncertainty = match.groups()
    sigma = Decimal(uncertainty)
    if re.fullmatch(r'\d+', uncertainty):
        sigma *= Decimal(10) ** Decimal(value).as_tuple().exponent
    decoded = float(value), float(sigma)
    assert all(math.isfinite(number) for number in decoded), (
        'A saved derived value and its propagated uncertainty must be finite'
    )
    assert decoded[1] > 0, 'A saved nonzero propagated uncertainty must be positive'
    assert decoded == wanted, (
        'The saved fraction and standard uncertainty must each round-trip exactly'
    )


@pytest.mark.parametrize('free_scales', [False, True])
def test_derived_weight_fraction_and_su_are_written_to_edi(tmp_path, free_scales):
    project = weighted_project(tmp_path / 'input', free_scales=free_scales)
    before = [(item.value, item.uncertainty) for item in fractions(project)]
    saved = tmp_path / 'saved'
    project.save_as(saved)
    text = '\n'.join(p.read_text() for p in (saved / 'experiments').glob('*.edi'))
    assert '_linked_structure.weight_fraction' in text, (
        'Saved experiment must carry the derived linked-structure weight fraction'
    )
    lines = text.splitlines()
    index = lines.index('_linked_structure.weight_fraction')
    headers = []
    start = index
    while start and lines[start - 1].startswith('_linked_structure.'):
        start -= 1
    while start < len(lines) and lines[start].startswith('_linked_structure.'):
        headers.append(lines[start])
        start += 1
    column = headers.index('_linked_structure.weight_fraction')
    rows = [line.split() for line in lines[start:] if line.strip()][:2]
    assert len(rows) == 2, 'Saved weight fractions must cover both linked structures'
    if free_scales:
        for row, wanted in zip(rows, before, strict=True):
            token = row[column]
            check_saved_fraction(token, wanted)
            # Exercise missing, zero, truncated and wrong-convention s.u. channels on
            # the actual writer's token; reopening recomputes this dependent quantity.
            value, _sigma = token.split('(', 1)
            for changed in (value, value + '(0)', value + '(nan)', value + '(99)'):
                with pytest.raises(AssertionError):
                    check_saved_fraction(changed, wanted)
    else:
        assert all(re.fullmatch(r'[-+\d.eE]+', row[column]) for row in rows), (
            'Fractions built only from fixed scales must save bare derived values'
        )
        assert all(error is None or error == 0 for _value, error in before), (
            'Fractions built only from fixed scales must have no uncertainty in memory'
        )
    restored = engine.Project.load(saved)
    after = [(item.value, item.uncertainty) for item in fractions(restored)]
    np.testing.assert_allclose(
        [value for value, _error in after],
        [value for value, _error in before],
        rtol=5e-5,
        atol=1e-9,
        err_msg='Reopened derived fractions must retain their values from the persisted scales',
    )
    if free_scales:
        np.testing.assert_allclose(
            [error for _value, error in after],
            [error for _value, error in before],
            rtol=5e-5,
            atol=1e-9,
            err_msg='Reopened free-scale fractions must recompute their nonzero uncertainties',
        )
    else:
        assert all(error is None or error == 0 for _value, error in after), (
            'Reopened fractions built only from fixed scales must have no uncertainty'
        )


@pytest.mark.parametrize('rho', [0.625, -0.375])
def test_stored_cross_scale_correlation_matches_closed_form_quotient(tmp_path, rho):
    source = tmp_path / 'input'
    project = weighted_project(source)
    project.save_as(tmp_path / 'seed')
    analysis = tmp_path / 'seed/analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text().rstrip()
        + f"""

loop_
_fit_parameter_correlation.id
_fit_parameter_correlation.source_kind
_fit_parameter_correlation.parameter_unique_name_i
_fit_parameter_correlation.parameter_unique_name_j
_fit_parameter_correlation.correlation
cross deterministic pattern.linked_structure.alpha.scale pattern.linked_structure.beta.scale {rho}
"""
    )
    project = engine.Project.load(tmp_path / 'seed')
    scales = (2.75, 0.375)
    q = (math.prod(case.LENGTHS['alpha']) * 0.7, math.prod(case.LENGTHS['beta']) * 1.05)
    denominator = sum(s * z for s, z in zip(scales, q, strict=True))
    gradient = (
        q[0] * q[1] * scales[1] / denominator**2,
        -q[0] * q[1] * scales[0] / denominator**2,
    )
    # ADR-0092 writes two significant figures. Reload uses that stored
    # coefficient in the quotient rather than the original fit precision.
    written_rho = {0.625: '0.63', -0.375: '-0.38'}[rho]
    uncorrelated = expected(scales)[1]
    for stage, coefficient in (('memory', rho), ('reopened', float(written_rho))):
        variance = (
            (gradient[0] * 0.03) ** 2
            + (gradient[1] * 0.012) ** 2
            + 2 * gradient[0] * gradient[1] * coefficient * 0.03 * 0.012
        )
        wanted = math.sqrt(variance)
        assert not math.isclose(wanted, uncorrelated, rel_tol=0.05), (
            'The independently authored covariance must distinguish omission of the cross term'
        )
        actual = fractions(project)
        np.testing.assert_allclose(
            [item.uncertainty for item in actual],
            [wanted, wanted],
            rtol=5e-5,
            atol=1e-12,
            err_msg='Stored scale correlation must propagate with signed quotient gradients',
        )
        if stage == 'memory':
            saved = tmp_path / 'correlated'
            project.save_as(saved)
            text = (saved / 'analysis/analysis.edi').read_text()
            assert '_fit_parameter_correlation.correlation' in text, (
                'Saving a correlated derived result must retain the correlation loop'
            )
            stored_rows = [
                row.split()
                for row in text.splitlines()
                if row.split()[:2] == ['cross', 'deterministic']
            ]
            assert stored_rows == [
                [
                    'cross',
                    'deterministic',
                    'pattern.linked_structure.alpha.scale',
                    'pattern.linked_structure.beta.scale',
                    written_rho,
                ]
            ], 'Saving must retain the named nonzero cross-scale correlation at ADR-0092 precision'
            project = engine.Project.load(saved)

    check_correlation_omission(saved, written_rho, wanted, uncorrelated)


def check_correlation_omission(saved, rho, wanted, uncorrelated):
    path = saved / 'analysis/analysis.edi'
    text = path.read_text()
    row = (
        r'(?m)^(cross\s+deterministic\s+pattern\.linked_structure\.alpha\.scale\s+'
        r'pattern\.linked_structure\.beta\.scale\s+)' + re.escape(str(rho)) + r'(?=\s|$)'
    )
    changed, count = re.subn(row, r'\g<1>0', text)
    assert count == 1, 'The covariance escape must zero the actual stored cross-scale coefficient'
    path.write_text(changed)
    zeroed = fractions(engine.Project.load(saved))
    np.testing.assert_allclose(
        [item.uncertainty for item in zeroed],
        [uncorrelated, uncorrelated],
        rtol=5e-5,
        atol=1e-12,
        err_msg='An absent cross covariance must recover the independent scale-error formula',
    )
    with pytest.raises(AssertionError, match='stored covariance escape'):
        np.testing.assert_allclose(
            [item.uncertainty for item in zeroed],
            [wanted, wanted],
            rtol=5e-5,
            atol=1e-12,
            err_msg='stored covariance escape',
        )


@pytest.mark.parametrize('state', ['single', 'one-disabled', 'all-disabled'])
@pytest.mark.parametrize('free_scale', [False, True])
def test_single_enabled_fraction_is_unity_in_memory_save_and_reopen(tmp_path, state, free_scale):
    source = tmp_path / 'input'
    phases = ('alpha',) if state == 'single' else ('alpha', 'beta')
    case.write_project(source, phases=phases)
    project = engine.Project.load(source)
    experiment = project.experiments[0]
    rows = case.links(experiment)
    if state in {'one-disabled', 'all-disabled'}:
        case.enable(rows['beta'], value=False)
    if state == 'all-disabled':
        case.enable(rows['alpha'], value=False)
    for name in tuple(rows.keys()):
        row = rows[name]
        disabled = state == 'all-disabled' or (state == 'one-disabled' and name == 'beta')
        if free_scale and disabled:
            with pytest.raises(
                ValueError, match=re.escape("this fit's data cannot determine it")
            ) as error:
                row.scale.free = True
            assert f'linked_structure.{name}.scale' in str(error.value), (
                'A disabled-link free refusal names its scale and the missing data reason'
            )
            assert not row.scale.free, 'A refused disabled-link scale stays fixed'
        else:
            row.scale.free = free_scale
        if free_scale:
            row.scale.uncertainty = 0.03
    for stage in ('first', 'reopened'):
        rows = case.links(project.experiments[0])
        for name in tuple(rows.keys()):
            row = rows[name]
            disabled = state == 'all-disabled' or (state == 'one-disabled' and name == 'beta')
            assert row.scale.free == (free_scale and not disabled), (
                'Only enabled-link scales retain their free choice in memory and after reload'
            )
            fraction = row.weight_fraction
            if state == 'all-disabled' or name == 'beta':
                assert fraction is None, 'Disabled links retain no share in memory or after reload'
            else:
                assert fraction is not None, 'A sole enabled link exposes its derived fraction'
                assert fraction.value.hex() == (1.0).hex(), (
                    'A sole enabled linked structure has exactly unity weight fraction'
                )
                assert fraction.uncertainty is None, (
                    'A sole enabled fraction has no uncertainty even with a free uncertain scale'
                )
        destination = tmp_path / stage
        project.save_as(destination)
        data = (destination / 'experiments/pattern.edi').read_bytes()
        legacy = historical_single_fraction('experiments/pattern.edi', data)
        assert COLUMN not in legacy, 'The historical byte view retains the pre-column schema'
        assert COLUMN in data, 'Every saved linked experiment gains the fraction column'
        project = engine.Project.load(destination)


@pytest.mark.parametrize('damage', ['missing', 'wrong', 'uncertainty', 'duplicate', 'disabled'])
def test_unity_byte_adaptation_refuses_changed_or_missing_fraction(damage):
    before = (
        b'data_pattern\nloop_\n_linked_structure.structure_id\n'
        b'_linked_structure.scale\n_linked_structure.enabled\n'
        b'alpha 2.75 true\nbeta 0.375 false\n\n'
    )
    after = before.replace(b'alpha 2.75 true', COLUMN + b'alpha 2.75 true 1.0').replace(
        b'beta 0.375 false', b'beta 0.375 false .'
    )
    assert historical_single_fraction('experiments/pattern.edi', after) == before, (
        'Before: absent column; after: checked unity/dot cells preserve every other byte'
    )
    changed = {
        'missing': before,
        'wrong': after.replace(b'1.0', b'0.9'),
        'uncertainty': after.replace(b'1.0', b'1.0(0)'),
        'duplicate': after.replace(COLUMN, COLUMN * 2),
        'disabled': after.replace(b'false .', b'false 1.0'),
    }[damage]
    with pytest.raises(AssertionError):
        historical_single_fraction('experiments/pattern.edi', changed)
    different = after.replace(b'2.75', b'2.76')
    assert historical_single_fraction('experiments/pattern.edi', different) != before, (
        'The fraction adaptation retains unrelated scale changes for the exact old byte oracle'
    )
    assert historical_single_fraction('structures/pattern.edi', after) == after, (
        'The fraction adaptation never removes similarly spelled structure bytes'
    )


def test_three_enabled_fractions_keep_hill_howard_normalization_and_saved_values(tmp_path):
    source = tmp_path / 'input'
    case.write_project(source)
    gamma = source / 'structures/gamma.edi'
    gamma.write_text(
        (source / 'structures/alpha.edi').read_text().replace('data_alpha', 'data_gamma')
    )
    path = source / 'experiments/pattern.edi'
    path.write_text(path.read_text().replace('beta 0.375\n', 'beta 0.375\ngamma 1.25\n'))
    project = engine.Project.load(source)
    amounts = [
        2.75 * math.prod(case.LENGTHS['alpha']),
        0.375 * math.prod(case.LENGTHS['beta']),
        1.25 * math.prod(case.LENGTHS['alpha']),
    ]
    wanted = [amount / sum(amounts) for amount in amounts]
    rows = case.links(project.experiments[0])
    np.testing.assert_allclose(
        [rows[name].weight_fraction.value for name in ('alpha', 'beta', 'gamma')],
        wanted,
        rtol=2e-12,
        atol=1e-14,
        err_msg='Three enabled structures retain normalized scale times cell mass times volume',
    )
    project.save_as(tmp_path / 'saved')
    data = (tmp_path / 'saved/experiments/pattern.edi').read_bytes()
    assert historical_single_fraction('experiments/pattern.edi', data) == data, (
        'The single-structure adaptation leaves every byte of a multiphase saved experiment intact'
    )
    match = re.search(rb'_linked_structure.weight_fraction\n((?:[^\n]+\n)+)', data)
    assert match, 'Three linked structures retain their saved weight-fraction column'
    np.testing.assert_allclose(
        [float(line.split()[-1]) for line in match[1].splitlines()],
        wanted,
        rtol=2e-12,
        atol=1e-14,
        err_msg='Every multiphase saved fraction retains its independently normalized value',
    )

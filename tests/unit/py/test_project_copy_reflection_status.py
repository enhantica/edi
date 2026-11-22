"""Copy status respects the separate reporting threshold and fit admission cut."""

import gemmi
import pytest

from tests.fixtures.project_archive.recalculated_copy import check_reflections


@pytest.mark.parametrize(
    ('multiple', 'basis', 'cutoff', 'statuses', 'observed_count', 'fit_count'),
    [
        (None, None, None, '<<ooo', 3, 5),
        (2, 'intensity', 1, '<<ooo', 3, 4),
        (2, 'intensity', 3, '<<<<o', 3, 1),
        (4, 'amplitude', 3, '<<<<o', 3, 1),
        (6, 'amplitude', 2, '<<<<o', 1, 3),
    ],
    ids=[
        'default-no-cutoff',
        'cut-below-observed',
        'cut-above-observed',
        'amplitude-cut-above',
        'amplitude-observed-above',
    ],
)
def test_copy_status_retains_both_thresholds(
    multiple, basis, cutoff, statuses, observed_count, fit_count
):
    # ADR-0104: I > n*u(I), F > n*u(F) means I > (n/2)*u(I).
    # ADR-0134: failing fit admission also writes '<'. Equality is outside.
    # The five rows exercise equality at 2 and 3, the interval between, and both sides.
    measured = [1.0, 2.0, 2.5, 3.0, 4.0]
    declaration = (
        ''
        if multiple is None
        else (f'_reflns.threshold_sigma {multiple}\n_reflns.threshold_basis {basis}\n')
    )
    symbol = 'I' if basis != 'amplitude' else 'F'
    expression = 'I>2u(I)' if multiple is None else (f'{symbol}>{multiple}u({symbol})')
    header = (
        'data_copy\n'
        + declaration
        + f'_reflns.threshold_expression "{expression}"\n'
        + f'_reflns.number_total 5\n_reflns.number_gt {observed_count}\n'
        + f'_refine_ls.number_reflns {fit_count}\n'
        + '\n'.join(
            '_refine_ls.' + name + ' 0'
            for name in (
                'R_factor_all',
                'R_factor_gt',
                'wR_factor_all',
                'wR_factor_gt',
                'wR_factor_ref',
            )
        )
        + '\nloop_\n'
        + '\n'.join(
            '_refln.' + name
            for name in (
                'index_h',
                'index_k',
                'index_l',
                'd_spacing',
                'sin_theta_over_lambda',
                'intensity_meas',
                'intensity_meas_su',
                'intensity_calc',
                'include_status',
            )
        )
        + '\n'
    )

    def body(flags):
        return (
            header
            + '\n'.join(
                f'1 0 0 1 0.5 {value} 1 {value} {status}'
                for value, status in zip(measured, flags, strict=True)
            )
            + '\n'
        ).encode()

    cell = gemmi.UnitCell(1, 1, 1, 90, 90, 90)
    check_reflections(body(statuses), measured, cell=cell, cutoff=cutoff)
    for index, status in enumerate(statuses):
        escaped = statuses[:index] + ('o' if status == '<' else '<') + statuses[index + 1 :]
        with pytest.raises(ValueError, match='Every include status'):
            check_reflections(body(escaped), measured, cell=cell, cutoff=cutoff)

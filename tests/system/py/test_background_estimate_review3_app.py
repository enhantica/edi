"""Bounded real app worker, type/basis edit, delegated save and typed Undo entries."""

import json
import os
import re
import subprocess
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal, localcontext
from pathlib import Path

import edi as engine
import numpy as np
import pytest

from tests.fixtures.background_estimate.review3 import (
    basis,
    estimate_control,
    materialize,
    rows,
    state,
)

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    'transition_line_segment_polynomial',
    'undo_line_segment_polynomial',
    'transition_line_segment_chebyshev',
    'undo_line_segment_chebyshev',
    'transition_polynomial_line_segment',
    'undo_polynomial_line_segment',
    'transition_polynomial_chebyshev',
    'undo_polynomial_chebyshev',
    'transition_chebyshev_line_segment',
    'undo_chebyshev_line_segment',
    'transition_chebyshev_polynomial',
    'undo_chebyshev_polynomial',
    'basis_polynomial_origin',
    'basis_chebyshev_x_min',
    'basis_chebyshev_x_max',
    'mixed_line_segment_single',
    'mixed_line_segment_joint',
    'mixed_polynomial_single',
    'mixed_polynomial_joint',
    'mixed_chebyshev_single',
    'mixed_chebyshev_joint',
    'delegated_polynomial',
    'delegated_chebyshev',
]


def iucr19_value(value, uncertainty):
    """Independent decimal construction from the declared IUCr rule (ADR-0092).

    Round s.u. up to two digits, retain 10-19 and a carried 10, otherwise one;
    round the value half away from zero to that last digit, preserving nonzero.
    """
    if uncertainty is None or not np.isfinite(uncertainty) or uncertainty <= 0:
        return value
    with localcontext() as context:
        context.prec = 350
        v, su = Decimal(str(value)), Decimal(str(uncertainty))
        quantum = Decimal(1).scaleb(su.adjusted() - 1)
        leading = (su / quantum).to_integral_value(rounding=ROUND_CEILING)
        if leading >= 20:
            quantum = Decimal(1).scaleb(su.adjusted())
        rounded = v.quantize(quantum, rounding=ROUND_HALF_UP)
        if v != 0 and rounded == 0:
            digits = 2 if leading < 20 or leading == 100 else 1
            quantum = Decimal(1).scaleb(v.copy_abs().adjusted() - digits + 1)
            rounded = v.quantize(quantum, rounding=ROUND_HALF_UP)
        return float(rounded)


@pytest.mark.parametrize('case', CASES)
def test_app_estimate_lifecycle_crosses_each_publication_boundary(tmp_path, case):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'The lifecycle sweep requires the actual built production Qt host'
    selected = 'BackgroundReview3::test_' + case
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_background_estimate_review3.qml'),
            selected,
            '-o',
            '-,txt',
        ],
        capture_output=True,
        text=True,
        # Process scheduling headroom; the measured system tier stays five seconds.
        timeout=15.0,
        check=False,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0 and f'PASS   : edi_app::{selected}()' in output, (
        'Auto refresh, fit publication, save and typed Undo must remain coherent: ' + output
    )
    assert 'BACKGROUND_REVIEW3' in output, (
        'The real app sweep must reach its final lifecycle receipt'
    )
    if case.startswith('basis_'):
        receipt = json.loads(re.findall(r'BACKGROUND_REVIEW3_BASIS (\{[^\n]+\})', output)[0])
        project = engine.Project.load(materialize(tmp_path / 'control', receipt['kind']))
        project.experiment.background_estimate.use_model = 'ignore'
        project.analysis.calculate()
        basis(project.experiment, receipt['field'])
        expected = estimate_control(project)
        np.testing.assert_allclose(
            [r[2] for r in receipt['rows']],
            [r[2] for r in expected],
            rtol=1e-11,
            atol=1e-8,
            err_msg='App basis edits must estimate the fresh Python control coefficients',
        )

    # A bounded Qt producer proves the live action and writes its actual file.
    # Its complementary loader checks exact typed persistence and unchanged
    # calculation here, rather than opening a second full window inside one deadline.
    if case.startswith(('delegated_', 'transition_', 'undo_', 'mixed_')):
        receipt = json.loads(re.findall(r'BACKGROUND_REVIEW3_SAVED (\{[^\n]+\})', output)[0])
        source = materialize(tmp_path / 'app-saved', receipt['kind'])
        (source / 'experiments/d20.edi').write_text(receipt['file'])
        loaded = engine.Project.load(source)
        host = receipt['state']
        expected = [
            host['type'],
            host['origin'],
            host['low'],
            host['high'],
            host['mode'],
            host['points'] if host['type'] == 'line-segment' else host['terms'],
        ]
        assert json.loads(json.dumps(state(loaded.experiment))) == expected, (
            'Every app lifecycle save must write the exact typed background published to its host'
        )
        if case.startswith('mixed_'):
            observed = rows(loaded.experiment)
            live, uncertainties = receipt['live_rows'], receipt['live_su']
            assert len(observed) == len(live) == len(uncertainties), (
                'Saving a fitted background must preserve every live row '
                'and its uncertainty witness'
            )
            for actual, prior, uncertainty in zip(observed, live, uncertainties, strict=True):
                assert actual[:2] == tuple(prior[:2]) and actual[3] == prior[3], (
                    'IUCr save normalization must preserve fitted ids, '
                    'positions/orders and free flags'
                )
                assert actual[2] == iucr19_value(prior[2], uncertainty), (
                    'Saving fitted Auto values must use the declared independent IUCr decimal rule'
                )
        before = rows(loaded.experiment)
        loaded.analysis.calculate()
        assert rows(loaded.experiment) == before, (
            'The actual app lifecycle file must reload and calculate '
            'without replacing its saved rows'
        )

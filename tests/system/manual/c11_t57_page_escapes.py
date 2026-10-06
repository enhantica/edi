"""Actual-page execution/escape helper, shared by the system gates and manual runner.

Run with edi's Python from its repository root. The actual page and its actual
agreement function execute twice. A disabled kernel must reach that agreement
function and fail there; an import, selector, or unrelated exception is not proof.
"""

import runpy
import sys
import time
from pathlib import Path
from unittest.mock import patch

import edi
import numpy as np
from edi import verification

ROOT = Path(__file__).resolve().parents[3]
PAGES = {
    'fcj': 'pd-neut-cwl_LaB6_fcj-asymmetry',
    'beba': 'pd-neut-cwl_PbSO4_beba-asymmetry',
    'tof': 'pd-neut-tof_Fe_pseudo-voigt',
}


def exercise(kind):
    page = ROOT / 'docs/dev/verification' / f'{PAGES[kind]}.py'
    assert page.is_file(), f' missing capability: executable page {PAGES[kind]}'
    original_factory = edi.ExperimentFactory.from_cif_str
    original_agreement = verification.assert_patterns_agree
    for disabled in (False, True):
        state = {'comparisons': 0, 'rejected': False, 'changed': False}

        def factory(text, *, disabled=disabled, state=state):
            if disabled:
                #  pages now load project-file text. Mutate only peak
                # fields; retain the declared scattering source and other data.
                lines = text.splitlines()
                data = {
                    'peak': {
                        line.split(None, 1)[0].removeprefix('_peak.'): line.split(None, 1)[1]
                        for line in lines
                        if line.startswith('_peak.')
                    }
                }
                if kind == 'tof':
                    data['peak'] = {
                        key: value
                        for key, value in data['peak'].items()
                        if not key.startswith('broad_lorentz_')
                    }
                    data['peak'].update(
                        type='tof-jorgensen',
                        broad_gauss_size=0.0,
                        broad_gauss_strain=0.0,
                        rise_alpha_0=0.1,
                        rise_alpha_1=0.0,
                        decay_beta_0=0.1,
                        decay_beta_1=0.0,
                    )
                elif kind == 'beba':
                    # The page now assigns mapped coefficients before its first
                    # assertion. Keep that typed interface and disable the
                    # correction at every reflection through its zero cutoff.
                    data['peak'] = {**data['peak'], 'asym_beba_limit': 0.0}
                else:
                    data['peak'] = {
                        key: value
                        for key, value in data['peak'].items()
                        if not key.startswith('asym_')
                    }
                    data['peak']['type'] = 'cwl-tch-pseudo-voigt'
                text = (
                    '\n'.join(
                        [line for line in lines if not line.startswith('_peak.')]
                        + [f'_peak.{key} {value}' for key, value in data['peak'].items()]
                    )
                    + '\n'
                )
                state['changed'] = True
            return original_factory(text)

        def agreement(*args, disabled=disabled, state=state, **kwargs):
            for _label, expected, actual in args[0]:
                assert np.isfinite(expected).all() and np.isfinite(actual).all(), (
                    ' selector escape must produce finite profiles before agreement'
                )
            state['comparisons'] += 1
            try:
                return original_agreement(*args, **kwargs)
            except AssertionError:
                state['rejected'] = True
                if not disabled:
                    raise
                raise

        started = time.perf_counter()
        with (
            patch.object(edi.ExperimentFactory, 'from_cif_str', side_effect=factory),
            patch.object(verification, 'assert_patterns_agree', side_effect=agreement),
        ):
            try:
                runpy.run_path(str(page), run_name='__main__')
            except AssertionError:
                if not (disabled and state['rejected']):
                    raise
        print(f' {kind} disabled={disabled} page_seconds={time.perf_counter() - started:.6f}')
        assert state['comparisons'], ' page must reach its real agreement assertion'
        if disabled:
            assert state['changed'] and state['rejected'], (
                ' disabling the kernel must fail the actual page agreement assertion'
            )
    print(f' {kind}: original page green; disabled kernel rejected by page agreement')


if __name__ == '__main__':
    for name in sys.argv[1:] or PAGES:
        exercise(name)

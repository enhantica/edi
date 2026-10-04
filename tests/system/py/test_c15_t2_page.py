"""execute the page, bind both operands, and disable its physical correction."""

import hashlib
import json
import runpy
from pathlib import Path
from unittest.mock import patch

import edi
import numpy as np
import pytest
from edi import verification as verify

ROOT = Path(__file__).resolve().parents[3]
PAGE = ROOT / 'docs/dev/verification/pd-xray-cwl_LiF_single_polarization.py'
FIXTURE = ROOT / 'tests/fixtures/c15_t2_polarization'


@pytest.mark.parametrize('disabled', [False, True])
def test_page_uses_fullprof_and_rejects_disabled_polarization(disabled):
    assert PAGE.is_file(), ' missing capability: executable polarized LiF verification page'
    manifest = json.loads((FIXTURE / 'manifest.json').read_text())
    oracle = np.loadtxt(FIXTURE / 'reference.tsv')
    loader = verify.load_fullprof_calc_profile
    measured = verify.set_reference_as_measured
    agreement = verify.assert_patterns_agree
    calculate = edi.Analysis.calculate
    state = {}

    def load(project, profile, background, zero):
        assert profile == 'lif_single_polarized.prf', (
            ' page must load the polarized independent FullProf profile'
        )
        directory = ROOT / 'knowledge/verification/fullprof' / project
        for name, digest in manifest['files'].items():
            assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest, (
                ' page reference assets must be byte-identical to committed diffraction-lib'
            )
        assert 'diffraction-lib' in (directory / 'PROVENANCE.md').read_text(), (
            ' vendored FullProf project must name its independent provenance'
        )
        x, y = loader(project, profile, background, zero)
        np.testing.assert_allclose(
            np.column_stack((x, y)),
            oracle,
            rtol=0,
            atol=1e-9,
            err_msg=' page loader must consume the frozen FullProf grid and calculation',
        )
        state['loaded'] = True
        return x, y

    def measure(experiment, x, y):
        state['experiment'] = experiment
        return measured(experiment, x, y)

    def calc(analysis, *args, **kwargs):
        assert state.get('loaded') and 'experiment' in state, (
            ' page must load the independent profile before calculating its experiment'
        )
        instrument = state['experiment'].instrument
        assert type(instrument).__name__ == 'CwlPdXrayInstrument', (
            ' page must exercise the declared X-ray CW instrument'
        )
        if not state.get('checked_settings'):
            assert instrument.setup_polarization_coefficient.value == pytest.approx(0.5), (
                ' page must use the FullProf K=0.5 nonidentity witness'
            )
            assert instrument.setup_monochromator_twotheta.value == pytest.approx(26.5650511771), (
                ' page must convert Cthm=0.8 to the physical monochromator angle'
            )
            state['checked_settings'] = True
        if disabled:
            instrument.setup_polarization_coefficient.value = 0.0
            state['disabled'] = True
        return calculate(analysis, *args, **kwargs)

    def compare(triples, **kwargs):
        assert triples and state.get('loaded'), ' page must reach a nonempty comparison'
        experiment = state['experiment']
        expected = verify.restrict_to_included(experiment, oracle[:, 1])
        calculated = verify.restrict_to_included(experiment, experiment.data.intensity_calc)
        for _label, reference, candidate in triples:
            np.testing.assert_allclose(
                reference,
                expected,
                rtol=0,
                atol=1e-9,
                err_msg=' comparison reference must be the independent FullProf array',
            )
            np.testing.assert_array_equal(
                candidate,
                calculated,
                err_msg=' comparison candidate must be the live calculated experiment',
            )
        state['compared'] = True
        if disabled:
            with pytest.raises(AssertionError):
                agreement(triples, **kwargs)
            state['rejected'] = True
        else:
            assert np.linalg.norm(calculated - expected) / np.linalg.norm(expected) < 0.01, (
                ' page must retain 1 percent L2 FullProf agreement'
            )
            return agreement(triples, **kwargs)
        return None

    with (
        patch.object(verify, 'load_fullprof_calc_profile', side_effect=load),
        patch.object(verify, 'set_reference_as_measured', side_effect=measure),
        patch.object(verify, 'assert_patterns_agree', side_effect=compare),
        patch.object(verify, 'plot_pattern_comparison'),
        patch.object(edi.Analysis, 'calculate', calc),
    ):
        runpy.run_path(str(PAGE), run_name='__main__')
    assert state.get('compared'), ' executable page must reach the agreement assertion'
    if disabled:
        assert state.get('disabled') and state.get('rejected'), (
            ' disabling polarization must be rejected at the real page agreement assertion'
        )

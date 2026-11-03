"""Execute each LiF page with its independent operand and a disabled correction."""

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
FIXTURE = ROOT / 'tests/fixtures/xray_doublet'
PAGES = {'doublet': 'pd-xray-cwl_LiF_doublet', 'absorption': 'pd-xray-cwl_LiF_single_absorption'}


def case_data(case):
    manifest = json.loads((FIXTURE / 'manifest.json').read_text())[case]
    stem = manifest['stem']
    rows = (FIXTURE / case / f'{stem}.prf').read_text().split('BEGIN', 1)[1].split('END', 1)[0]
    oracle = np.array([
        [float(value) for value in line.split()[:3]] for line in rows.splitlines() if line.strip()
    ])[:, [0, 2]]
    return manifest, stem, oracle


def correction(experiment, case):
    if case == 'doublet':
        instrument = experiment.instrument
        assert instrument.setup_wavelength_2.value == pytest.approx(1.5444), (
            'The doublet page must use the independent second wavelength'
        )
        parameter = instrument.setup_wavelength_2_to_1_ratio
        return parameter, 0.5
    parameter = experiment.absorption.mu_r
    return parameter, 0.9


@pytest.mark.parametrize('case', ['absorption', 'doublet'])
@pytest.mark.parametrize('disabled', [False, True])
def test_page_compares_live_calculation_and_rejects_disabled_correction(case, disabled):
    page = ROOT / 'docs/dev/verification' / (PAGES[case] + '.py')
    assert page.is_file(), 'The declared LiF capability requires its executing verification page'
    manifest, stem, oracle = case_data(case)
    loader = verify.load_fullprof_calc_profile
    measured = verify.set_reference_as_measured
    agreement = verify.assert_patterns_agree
    calculate = edi.Analysis.calculate
    state = {}

    def load(project, profile, background, zero):
        assert profile == f'{stem}.prf', (
            'The LiF page must load its declared independent FullProf case'
        )
        directory = ROOT / 'knowledge/verification/fullprof' / project
        for name, digest in manifest['files'].items():
            assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest, (
                'Vendored FullProf files must remain byte-identical to diffraction-lib'
            )
        assert 'diffraction-lib' in (directory / 'PROVENANCE.md').read_text(), (
            'The page must name the independent FullProf source'
        )
        x, y = loader(project, profile, background, zero)
        np.testing.assert_allclose(
            np.column_stack((x, y)),
            oracle,
            rtol=0,
            atol=1e-9,
            err_msg='The page loader must consume the frozen FullProf calculation',
        )
        state['loaded'] = True
        return x, y

    def measure(experiment, x, y):
        state['experiment'] = experiment
        return measured(experiment, x, y)

    def calc(analysis, *args, **kwargs):
        assert state.get('loaded'), 'The page must load the independent profile before calculation'
        experiment = state['experiment']
        assert type(experiment.instrument).__name__ == 'CwlPdXrayInstrument', (
            'The LiF pages must exercise the X-ray CW path'
        )
        parameter, wanted = correction(experiment, case)
        if not state.get('checked'):
            assert parameter.value == pytest.approx(wanted), (
                'The page must start at the declared nonidentity FullProf correction'
            )
            state['checked'] = True
        if disabled:
            parameter.value = 0.0
            state['disabled'] = True
        return calculate(analysis, *args, **kwargs)

    def compare(triples, **kwargs):
        assert triples, 'The LiF page must execute a nonempty agreement assertion'
        experiment = state['experiment']
        expected = verify.restrict_to_included(experiment, oracle[:, 1])
        actual = verify.restrict_to_included(experiment, experiment.data.intensity_calc)
        for _label, reference, candidate in triples:
            np.testing.assert_allclose(
                reference,
                expected,
                rtol=0,
                atol=1e-9,
                err_msg='The agreement operand must be independent FullProf intensity',
            )
            np.testing.assert_array_equal(
                candidate,
                actual,
                err_msg='The agreement candidate must be the live calculated experiment',
            )
        state['compared'] = True
        if disabled:
            with pytest.raises(AssertionError):
                agreement(triples, **kwargs)
            state['rejected'] = True
            return None
        assert np.linalg.norm(actual - expected) / np.linalg.norm(expected) < 0.01, (
            'LiF pages must retain the one-percent FullProf agreement bound'
        )
        return agreement(triples, **kwargs)

    with (
        patch.object(verify, 'load_fullprof_calc_profile', side_effect=load),
        patch.object(verify, 'set_reference_as_measured', side_effect=measure),
        patch.object(verify, 'assert_patterns_agree', side_effect=compare),
        patch.object(verify, 'plot_pattern_comparison'),
        patch.object(edi.Analysis, 'calculate', calc),
    ):
        runpy.run_path(str(page), run_name='__main__')
    assert state.get('compared'), 'The executable page must reach its agreement assertion'
    if disabled:
        assert state.get('disabled'), 'The page escape must reach the real correction parameter'
        assert state.get('rejected'), (
            'The actual page assertion must reject the disabled correction'
        )

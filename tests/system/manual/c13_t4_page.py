""": execute the real page with independent operands and a kernel escape."""

import hashlib
import json
import runpy
import sys
from pathlib import Path
from unittest.mock import patch

import edi
import numpy as np
from edi import verification as verify

ROOT = Path(__file__).resolve().parents[3]
PAGE = ROOT / 'docs/dev/verification/pd-neut-cwl_LBCO_preferred-orientation.py'
MANIFEST = json.loads((ROOT / 'tests/fixtures/c13_t4_march/fullprof.json').read_text())


def _oracle():
    # The local project adds the instrument suffix; MANIFEST keeps upstream's identity.
    folder = ROOT / 'knowledge/verification/fullprof/pd-neut-cwl_lbco-hrpt_preferred-orientation'
    for name, digest in MANIFEST['files'].items():
        path = folder / name
        assert path.is_file(), ' missing capability: vendored independent FullProf project'
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, (
            ' FullProf reference must remain byte-identical to diffraction-lib'
        )
    assert (folder / 'PROVENANCE.md').is_file(), ' independent assets need named provenance'
    # Independent parser for the pinned IGOR reference; no production oracle call.
    body = (folder / 'lbco.prf').read_text().split('BEGIN', 1)[1].split('END', 1)[0]
    rows = np.asarray([
        [float(v) for v in line.split()] for line in body.splitlines() if line.strip()
    ])
    background = np.loadtxt(folder / 'lbco.bac', comments='!')
    x = rows[:, 0]
    return x, rows[:, 2] - np.interp(x, background[:, 0] + 0.62040, background[:, 1])


def _execute(disabled):
    assert PAGE.is_file(), ' missing capability: executable LBCO preferred-orientation page'
    x, oracle = _oracle()
    state = {'compared': False, 'disabled': False}
    measured = verify.set_reference_as_measured
    agreement = verify.assert_patterns_agree
    calculate = edi.Analysis.calculate
    fit = edi.Analysis.fit

    def set_measured(experiment, grid, values):
        np.testing.assert_allclose(
            grid,
            x,
            rtol=0,
            atol=1e-9,
            err_msg=' page grid must be the independent FullProf grid',
        )
        np.testing.assert_allclose(
            values,
            oracle,
            rtol=0,
            atol=1e-9,
            err_msg=' measured operand must be the independent FullProf profile',
        )
        return measured(experiment, grid, values)

    def disable(analysis):
        if disabled:
            for experiment in analysis._project.experiments:
                assert hasattr(experiment, 'preferred_orientation'), (
                    ' missing capability: a page kernel-disable seam'
                )
                for row in experiment.preferred_orientation:
                    row.march_r.value = 1.0
                    row.march_r.free = False
                    state['disabled'] = True

    def calc(analysis, *args, **kwargs):
        # The page also calculates an untextured control; bind the witness to
        # the experiment carrying the March row, not the last measured operand.
        for experiment in analysis._project.experiments:
            if list(experiment.preferred_orientation):
                state['experiment'] = experiment
        disable(analysis)
        return calculate(analysis, *args, **kwargs)

    def fitting(analysis, *args, **kwargs):
        disable(analysis)
        return fit(analysis, *args, **kwargs)

    def compare(triples, **kwargs):
        assert 'experiment' in state and triples, (
            ' page must compare an actual experiment against FullProf'
        )
        experiment = state['experiment']
        expected = verify.restrict_to_included(experiment, oracle)
        actual = verify.restrict_to_included(experiment, experiment.data.intensity_calc)
        for _label, reference, candidate in triples:
            np.testing.assert_allclose(
                reference,
                expected,
                rtol=0,
                atol=1e-9,
                err_msg=' self-oracle escape: comparison operand must be FullProf',
            )
            np.testing.assert_array_equal(
                candidate,
                actual,
                err_msg=' fabricated-candidate escape: compare the calculated experiment',
            )
        state['compared'] = True
        try:
            result = agreement(triples, **kwargs)
            # New per-page pins may tighten the inherited reference bounds, never weaken them.
            agreement(triples)
        except AssertionError:
            state['agreement_red'] = True
            raise
        else:
            return result

    with (
        patch.object(verify, 'set_reference_as_measured', side_effect=set_measured),
        patch.object(verify, 'assert_patterns_agree', side_effect=compare),
        patch.object(verify, 'plot_pattern_comparison'),
        patch.object(edi.Analysis, 'calculate', calc),
        patch.object(edi.Analysis, 'fit', fitting),
    ):
        try:
            runpy.run_path(str(PAGE), run_name='__main__')
        except AssertionError:
            if not (disabled and state.get('agreement_red')):
                raise
    assert state['compared'], ' page must reach its numeric agreement assertion'
    if disabled:
        assert state['disabled'] and state.get('agreement_red'), (
            ' escape: setting the March factor to identity must make real page agreement RED'
        )


if __name__ == '__main__':
    _execute(sys.argv[1] == 'disabled')
    print(' actual page agreement and escape checked')

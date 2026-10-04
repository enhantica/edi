""": execute the shipped comparison and bind its operand to FullProf bytes."""

import ast
import hashlib
import json
import re
from pathlib import Path
from unittest.mock import patch

import edi
import numpy as np
import pytest
from edi import verification

ROOT = Path(__file__).resolve().parents[3]
PAGE = ROOT / 'docs/dev/verification/pd-xray-cwl_LiF_single.py'
FIXTURE = ROOT / 'tests/fixtures/c15_t1_xray'


def _execute(tree):
    oracle = np.loadtxt(FIXTURE / 'reference.tsv')
    manifest = json.loads((FIXTURE / 'manifest.json').read_text())
    loader = verification.load_fullprof_calc_profile
    set_measured = verification.set_reference_as_measured
    agreement = verification.assert_patterns_agree
    state = {}
    factory = edi.ExperimentFactory.from_dict
    text_factory = edi.ExperimentFactory.from_cif_str

    def make(data):
        state['sources'] = data.get('scattering_source')
        return factory(data)

    def make_text(text):
        state['sources'] = dict(re.findall(r'_scattering_source\.(\w+)\s+([^\s]+)', text))
        return text_factory(text)

    def load(project, profile, background, zero):
        assert (project, profile) == ('pd-xray-cwl_lif_single', 'lif_single_unpolarized.prf'), (
            ' wrong-project escape: page must load the fixed LiF FullProf project'
        )
        base = ROOT / 'knowledge/verification/fullprof' / project
        for name in (profile, background):
            assert (
                hashlib.sha256((base / name).read_bytes()).hexdigest() == manifest['files'][name]
            ), ' loaded reference bytes must match the independent project digest'
        x, y = loader(project, profile, background, zero)
        np.testing.assert_allclose(
            x,
            oracle[:, 0],
            rtol=0,
            atol=1e-9,
            err_msg=' loaded grid must match the FullProf fixture',
        )
        np.testing.assert_allclose(
            y,
            oracle[:, 1],
            rtol=0,
            atol=1e-9,
            err_msg=' loaded intensity must match the FullProf fixture',
        )
        state['loaded'] = True
        return x, y

    def measured(experiment, x, y):
        state['experiment'] = experiment
        return set_measured(experiment, x, y)

    def compare(triples, **kwargs):
        assert state.get('loaded') and 'experiment' in state, (
            ' agreement must follow the independent profile load and grid setup'
        )
        experiment = state['experiment']
        assert experiment.experiment_type.radiation_probe == edi.RadiationProbeEnum.XRAY, (
            ' comparison must exercise the declared X-ray experiment'
        )
        assert type(experiment.instrument).__name__ == 'CwlPdXrayInstrument', (
            ' comparison must consume the selected X-ray instrument'
        )
        assert state.get('sources') == {
            'xray_form_factor': 'it1992',
            'xray_dispersion': 'sasaki1989',
        }, ' LiF page must explicitly declare IT1992 and sasaki1989 source names'
        expected = verification.restrict_to_included(experiment, oracle[:, 1])
        calculated = verification.restrict_to_included(experiment, experiment.data.intensity_calc)
        assert triples, ' page must execute a nonempty FullProf comparison'
        for _label, reference, candidate in triples:
            np.testing.assert_allclose(
                reference,
                expected,
                rtol=0,
                atol=1e-9,
                err_msg=' comparison operand must be the independent FullProf array',
            )
            np.testing.assert_array_equal(
                candidate,
                calculated,
                err_msg=' candidate must be the declared X-ray calculated pattern',
            )
        for _label, reference, candidate in triples:
            assert (
                np.linalg.norm(np.asarray(candidate) - reference) / np.linalg.norm(reference)
                < 0.01
            ), ' LiF page must retain the original 1 percent bound without scale fitting'
        state['compared'] = True
        return agreement(triples, **kwargs)

    with (
        patch.object(edi.ExperimentFactory, 'from_dict', side_effect=make),
        patch.object(edi.ExperimentFactory, 'from_cif_str', side_effect=make_text),
        patch.object(verification, 'load_fullprof_calc_profile', side_effect=load),
        patch.object(verification, 'set_reference_as_measured', side_effect=measured),
        patch.object(verification, 'assert_patterns_agree', side_effect=compare),
        patch.object(verification, 'plot_pattern_comparison'),
    ):
        exec(  # noqa: S102 -- execute only the committed page and its test-owned AST mutations
            compile(ast.fix_missing_locations(tree), str(PAGE), 'exec'),
            {'__name__': '__main__', '__file__': str(PAGE)},
        )
    assert state.get('compared'), ' executable page must reach its agreement assertion'


def test_page_comparison_consumes_the_digest_pinned_fullprof_operand():
    assert PAGE.is_file(), ' missing capability: executable LiF reference page'
    _execute(ast.parse(PAGE.read_text()))


@pytest.mark.parametrize(
    'escape', ['self-comparison', 'wrong-project', 'candidate-from-reference']
)
def test_page_reference_binding_rejects_executable_escape(escape):
    # ACCIDENT: the page retains FullProf assets but compares its own output to itself.
    assert PAGE.is_file(), ' missing capability: executable LiF reference page'
    tree = ast.parse(PAGE.read_text())
    changed = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if escape == 'wrong-project' and node.func.attr == 'load_fullprof_calc_profile':
            node.args[0] = ast.Constant('pd-neut-cwl_y2o3_isotropic-adp')
            changed = True
        if (
            escape in {'self-comparison', 'candidate-from-reference'}
            and node.func.attr == 'assert_patterns_agree'
        ):
            for triple in ast.walk(node.args[0]):
                if isinstance(triple, (ast.Tuple, ast.List)) and len(triple.elts) == 3:
                    if escape == 'self-comparison':
                        triple.elts[1] = triple.elts[2]
                    else:
                        triple.elts[2] = triple.elts[1]
                    changed = True
    assert changed, ' escape must mutate the executable comparison or loader'
    reason = {
        'self-comparison': 'comparison operand',
        'wrong-project': 'wrong-project escape',
        'candidate-from-reference': 'candidate must be',
    }[escape]
    with pytest.raises(AssertionError, match=reason):
        _execute(tree)

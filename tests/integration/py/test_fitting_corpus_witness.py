"""A real pinned-corpus fit, judged by its independent FullProf normal equation."""

import json
import shutil

import edi
import pytest

from tests.conftest import corpus_case_dir


def test_pinned_single_crystal_fit_reaches_independent_reference(tmp_path):
    case = corpus_case_dir('single-crystal-cwl-tbti-basic')
    source = case / 'project'
    staged = tmp_path / 'project'
    shutil.copytree(source, staged)
    expected = json.loads((case / 'expected.json').read_text())
    scale_reference = expected['quantities']['param.scale.value']
    assert scale_reference['kind'] == 'reference', (
        'The fitting witness must use the independent FullProf normal equation, not an engine pin'
    )
    project = edi.Project.load(staged)
    result = project.analysis.fit()
    scale = project.experiments[0].linked_structure.scale.value
    assert scale == pytest.approx(
        scale_reference['value'],
        rel=scale_reference['tol_rel'] or 0,
        abs=scale_reference['tol_abs'] or 0,
    ), 'The pinned measured corpus must reach its independently computed weighted scale optimum'
    objective = expected['quantities']['reduced_chi_square']
    assert result.reduced_chi_square == pytest.approx(
        objective['value'], rel=objective['tol_rel'] or 0, abs=objective['tol_abs'] or 0
    ), 'The corpus witness must retain its independently computed admitted-residual objective'

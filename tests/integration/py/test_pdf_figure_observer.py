"""Qualify saved-PDF image geometry independently of the app report writer."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/pdf_figures'
spec = importlib.util.spec_from_file_location(
    'pdf_figure_observer', ROOT / 'tests/unit/app/ReportPdf.py'
)
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)
REFERENCE = json.loads((FIXTURE / 'reference.json').read_text())['cases']


@pytest.mark.parametrize('name', sorted(REFERENCE))
def test_saved_pdf_image_bounds_follow_the_independent_affine_reference(name):
    report = observer.inspect(FIXTURE / (name + '.pdf'))
    draws = report['pages'][0]['image_draws']
    assert len(draws) == 1, 'The PDF geometry observer must reach the actual image draw operation'
    draw, expected = draws[0], REFERENCE[name]
    assert draw['bounds'] == pytest.approx(expected['bounds']), (
        'Saved image bounds must include all four transformed corners in top-down page points'
    )
    assert [draw['edge_width'], draw['edge_height']] == pytest.approx(expected['edges']), (
        'Independent image edges retain both nontrivial scales through nested and rotated matrices'
    )
    assert draw['pixels'] == expected['pixels'], (
        'The PDF observer reads intrinsic dimensions from the actual image XObject'
    )
    assert draw['clip'] == pytest.approx(expected['clip']), (
        'The image clip stays distinct from the full transformed image bounding box'
    )
    if name == 'clipped':
        assert draw['bounds'][2] > draw['clip'][2], (
            'The negative control must expose the discarded right half of the actual image'
        )

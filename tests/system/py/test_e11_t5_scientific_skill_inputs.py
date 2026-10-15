"""Actual example input/API reachability, independently committed measurements.

No numerical golden, fit acceptance/adoption or generated-CIF substitute is used.
The staged call has a real saved model iteration bound, never an alternate engine.
"""

from __future__ import annotations

import hashlib
import runpy
from pathlib import Path

import edi

ROOT = Path(__file__).resolve().parents[3]
MEASURED = ROOT / 'knowledge/verification/fullprof/pd-neut-cwl_lbco-hrpt_basic/lbco.dat'
SOURCE_SHA = '83c7f3d27d2e254367dd7dc3730261b9a5ebb811baaeed01fde050a7ba99be24'


def example():
    return runpy.run_path(str(ROOT / 'examples/fit_lbco_hrpt.py'), run_name='original_example')


def original_rows():
    return [
        tuple(map(float, line.split()))
        for line in MEASURED.read_text().splitlines()
        if line.strip()
    ]


def test_existing_lbco_example_reads_its_committed_genuine_measurement():
    module = example()
    actual = module['load_measurement'](module['MEASUREMENT'])
    assert hashlib.sha256(module['MEASUREMENT'].read_bytes()).hexdigest() == SOURCE_SHA, (
        'SCI INPUT: actual example resolves the original provenance-bound LBCO measurement'
    )
    assert list(zip(*actual, strict=True)) == original_rows(), (
        'SCI INPUT: example retains every genuine measured coordinate, intensity and uncertainty'
    )


def test_existing_lbco_stage_calls_real_project_managed_fit_and_preserves_population(tmp_path):
    module = example()
    rows = original_rows()
    grid, observed, sigma = map(list, zip(*rows, strict=True))
    project = module['build_project']()
    project.experiment.data = edi.PdCwlData(
        two_theta=grid, intensity_meas=observed, intensity_meas_su=sigma
    )
    module['release'](project, full=False)
    exclusions = list(project.experiment.excluded_regions)
    staged = tmp_path / 'actual-bounded-stage'
    project.save_as(staged)
    analysis = staged / 'analysis/analysis.edi'
    analysis.write_text(analysis.read_text() + '\n_minimizer.max_iterations 2\n')
    actual = edi.Project.load(staged)
    result = module['fit_stage']('Actual bounded public stage', actual, (grid, observed, sigma))
    assert result.iterations <= 2, 'SCI API: actual stage honors the saved model iteration budget'
    data = actual.experiment.data
    assert (
        list(zip(data.two_theta, data.intensity_meas, data.intensity_meas_su, strict=True)) == rows
    ), 'SCI API: ordinary example fit uses actual project data without replacing measured weights'
    assert list(actual.experiment.excluded_regions) == exclusions, (
        'SCI API: a staged example call preserves the declared excluded population'
    )

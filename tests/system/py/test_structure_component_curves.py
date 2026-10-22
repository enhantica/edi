"""Each phase agrees with a scale-zero calculation of the other phase."""

import importlib
import math
import re
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def require_component_surface():
    engine = importlib.import_module('edi')
    assert hasattr(engine.PdDataBase, 'component_intensities_net') and hasattr(
        engine.PdDataBase, 'component_presentation_order'
    ), 'Edi Python publishes both component buffers and their independent structure order'
    return engine


def links(experiment):
    return (
        experiment.linked_structures
        if hasattr(experiment, 'linked_structures')
        else experiment.linked_structure
    )


def close_vectors(actual, expected, *, abs_tol=2e-11):
    assert len(actual) == len(expected), 'Every component has exactly the experiment grid length'
    for a, b in zip(actual, expected, strict=True):
        if math.isnan(b):
            assert math.isnan(a), 'Excluded points keep the calculated-data NaN convention'
        else:
            assert math.isclose(a, b, rel_tol=2e-11, abs_tol=abs_tol), (
                'A net component equals an isolated whole-pattern calculation minus its background'
            )


@pytest.mark.parametrize('bank', ['expt_s2', 'expt_n2'])
def test_two_structure_curves_match_independent_scale_zero_controls(tmp_path, bank):
    engine = require_component_surface()
    directory = tmp_path / 'input'
    shutil.copytree(ROOT / 'tests/fixtures/multiphase/beer/projects/initial', directory)
    project = engine.Project.load(directory)
    project.analysis.calculate()
    experiment = project.experiments[bank]
    components = [list(row) for row in experiment.data.component_intensities_net]
    # Independent order: the committed BEER experiment's _linked_structure loop
    # lists ferrite then austenite. Project map keys are alphabetically ordered.
    order = ['ferrite', 'austenite']
    assert list(experiment.data.component_presentation_order) == order, (
        'Component columns name the linked structures in the independent BEER fixture order'
    )
    assert len(order) == 2, 'The BEER reference vehicle contains two distinct structures'
    assert len(components) == len(experiment.data.intensity_calc), (
        'The two-structure vehicle publishes one component list for every data point'
    )
    background, total = list(experiment.data.intensity_bkg), list(experiment.data.intensity_calc)
    for column, name in enumerate(order):
        isolated = engine.Project.load(directory)
        for row in links(isolated.experiments[bank]):
            if row.structure_id != name:
                row.scale.value = 0
        isolated.analysis.calculate()
        data = isolated.experiments[bank].data
        expected = [a - b for a, b in zip(data.intensity_calc, data.intensity_bkg, strict=True)]
        # Subtracting two rounded whole-pattern intensities loses relative accuracy
        # near zero. Eight binary64 ulps at the whole-pattern/background scale
        # conservatively cover the separate calculation, addition and subtraction;
        # the allowance is independent of the observed component discrepancy.
        scale = max(
            abs(value)
            for vector in (data.intensity_calc, data.intensity_bkg)
            for value in vector
            if math.isfinite(value)
        )
        close_vectors([row[column] for row in components], expected, abs_tol=8 * math.ulp(scale))
    close_vectors([b + sum(row) for b, row in zip(background, components, strict=True)], total)
    # A changed physical input must reach the same component path and invalidate its cache.
    links(experiment)[order[0]].scale.value *= 1.75
    project.analysis.calculate()
    changed = [list(row) for row in experiment.data.component_intensities_net]
    close_vectors([row[0] for row in changed], [row[0] * 1.75 for row in components])
    close_vectors([row[1] for row in changed], [row[1] for row in components])
    saved = tmp_path / 'saved'
    project.save_as(saved)
    text = (saved / 'experiments' / f'{bank}.edi').read_text()
    assert text.startswith('#\\#CIF_2.0\n'), (
        'Calculated component lists are saved with the CIF2 heading'
    )
    assert '_pd_calc.component_intensities_net' in text, (
        'The saved data loop includes the component lists'
    )
    assert re.search(r'_pd_calc_overall.component_presentation_order\s+\[', text), (
        'The saved presentation order names the members of every point list'
    )
    reopened_project = engine.Project.load(saved)
    reopened = reopened_project.experiments[bank]
    assert list(reopened.data.component_presentation_order) == order, (
        'Saving and reopening retains the independently named component column order'
    )
    for actual, expected in zip(reopened.data.component_intensities_net, changed, strict=True):
        close_vectors(actual, expected)

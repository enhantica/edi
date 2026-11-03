"""Auto permits free/fixed toggles; explicit Manual permits structural and value edits."""

import edi as engine
import pytest

from tests.fixtures.background_estimate.readonly import KINDS, edit, materialize, snapshot
from tests.fixtures.project_save.reference import six_digits


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('field', ['id', 'coordinate', 'value', 'free', 'add', 'remove'])
@pytest.mark.parametrize('transition', [False, True], ids=['loaded-auto', 'manual-to-auto'])
def test_auto_rows_allow_free_toggles_but_require_manual_for_other_edits(
    tmp_path, kind, field, transition
):
    source = materialize(tmp_path / 'input', kind)
    if not transition:
        path = source / 'experiments/bank.edi'
        path.write_text(
            path.read_text().replace(
                '_background_estimate.mode manual', '_background_estimate.mode auto'
            )
        )
    project = engine.Project.load(source)
    if transition:
        project.experiment.background_estimate.mode = 'auto'
    before = snapshot(project)
    # Before: free was refused with value edits. After: both toggle directions stay Auto.
    if field == 'free':
        expected = [(*before[0][:-1], not before[0][-1]), *before[1:]]
        edit(project, engine, field)
        assert snapshot(project) == expected, (
            'Auto toggling must change only the selected free flag, preserving row ids and values'
        )
        assert project.experiment.background_estimate.mode == 'auto', (
            'A permitted free toggle must retain Auto after loading or changing mode'
        )
        edit(project, engine, field)
    else:
        with pytest.raises(ValueError, match=r'(?i)manual'):
            edit(project, engine, field)
    assert snapshot(project) == before, (
        'Refused Auto edits and a pair of permitted free toggles must preserve every row cell'
    )
    assert project.experiment.background_estimate.mode == 'auto', (
        'Both permitted flag toggles and refused row edits must preserve Auto mode'
    )
    project.experiment.background_estimate.mode = 'manual'
    edit(project, engine, field)
    expected = snapshot(project)
    assert expected != before, (
        'The Manual positive control must actually change the requested cell or row'
    )
    saved = tmp_path / 'saved'
    project.save_as(saved)
    again = engine.Project.load(saved)
    expected = [
        (name, coordinate, six_digits(value), free) for name, coordinate, value, free in expected
    ]
    assert snapshot(project) == expected, (
        'Save adopts six-digit Manual coefficients while retaining row identity and flags'
    )
    assert snapshot(again) == expected, (
        'Manual point and term edits round-trip independently rounded cells and exact row identity'
    )
    assert again.experiment.background_estimate.mode == 'manual', (
        'Manual edit permissions must follow the explicitly saved mode after reload'
    )

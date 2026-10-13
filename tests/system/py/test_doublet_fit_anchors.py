"""A participating fixed second wavelength breaks Bragg's dilation null direction."""

import edi as engine
import pytest

from tests.fixtures.xray_doublet import anchoring


@pytest.mark.parametrize('key', anchoring.GRAPHS)
@pytest.mark.parametrize('state', ['fixed-second', 'inactive', 'free-second'])
@pytest.mark.parametrize('entry', ['direct', 'analysis'])
def test_doublet_fit_admission_follows_each_active_anchor(tmp_path, key, state, entry):
    root = tmp_path / 'input'
    mode, admitted = anchoring.write(root, key, state, reverse=entry == 'analysis')
    project = engine.Project.load(root)
    call = (
        project.analysis.fit
        if entry == 'analysis'
        else project.fit
        if mode == 'single'
        else project.fit_joint
    )
    if admitted:
        result = call(should_cancel=lambda: True)
        assert result is not None, 'An admitted fit must return its structured result'
        assert result.cancelled, (
            'A fixed active second wavelength must admit the requested single or connected '
            'joint fit before cancellation'
        )
    else:
        with pytest.raises(ValueError, match=r'dilation|null direction'):
            call(should_cancel=lambda: True)

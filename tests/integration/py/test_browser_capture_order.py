"""Actual capture-file ordering belongs to integration; full historical qualifier retained."""

import copy
from types import SimpleNamespace

import pytest

from tests.fixtures.e04_t11_wasm import solver_vehicles, written
from tests.unit.py.test_browser_solver_vehicles import (
    ROOT,
    StopBeforeCurrentFitError,
    _immutable_sources,  # noqa: F401, PLC2701 - shared authentication fixture
    historical,  # noqa: F401 - exact full-vector pytest fixture
    report_text,
)


@pytest.mark.parametrize('historical_bad', [False, True])
def test_capture_uses_two_fresh_projects_and_never_carries_historical_settings_into_default(
    historical,  # noqa: F811 - pytest injects the exact imported fixture
    tmp_path,
    monkeypatch,
    historical_bad,
):
    events, projects = [], []
    real_qualifier = written.qualify_historical

    class Analysis:
        def __init__(self):
            object.__setattr__(self, 'edits', [])
            object.__setattr__(self, 'descent', 'auto')
            object.__setattr__(self, 'stop_rules', 'chi_square_change shift_su')
            object.__setattr__(self, 'fitting_mode', 'joint')

        def __setattr__(self, key, value):
            self.edits.append((key, value))
            object.__setattr__(self, key, value)

    def load(source):
        assert source == historical.source, 'Each phase loads the exact authenticated source'
        if projects:
            assert 'historical-qualified' in events, (
                'Current loading cannot precede successful full historical qualification'
            )
        project = SimpleNamespace(
            analysis=Analysis(),
            su_rule='iucr_99',
            free_parameters=[None] * 193,
            _minimizer_max_iterations=1000,
            _minimizer_chi_square_tolerance=1e-4,
        )
        projects.append(project)
        events.append('load')
        return project

    def fit(project, loaded):
        if len(projects) == 2:
            assert project is not projects[0], (
                'The default run cannot reuse the fitted historical model'
            )
            assert project.analysis.edits == [], 'The current default receives no setter overrides'
            assert loaded['descent'] == 'auto', 'The fresh default keeps its actual descent'
            events.append('current-start')
            raise StopBeforeCurrentFitError
        assert dict(project.analysis.edits) == solver_vehicles.HISTORICAL, (
            'Exactly the two historically backed selectors change before the historical fit'
        )
        assert len(project.analysis.edits) == 2, 'Historical setup cannot retune another setting'
        raw = copy.deepcopy(historical.raw)
        if historical_bad:
            raw['values'][next(iter(raw['values']))] += 1
        events.append('historical-fit')
        return raw, object()

    def qualified(*args, **kwargs):
        result = real_qualifier(*args, **kwargs)
        events.append('historical-qualified')
        return result

    monkeypatch.setattr(written.edi, 'Project', SimpleNamespace(load=load))
    monkeypatch.setattr(written, 'fit_with_trace', fit)
    monkeypatch.setattr(written, 'qualify_historical', qualified)
    monkeypatch.setattr(
        written.edi, 'machine_report', lambda *_args: report_text(historical.record)
    )
    destination = tmp_path / 'not-a-qualified-capture'
    expected = ValueError if historical_bad else StopBeforeCurrentFitError
    with pytest.raises(expected):
        written.capture(
            ROOT,
            'ncaf',
            destination,
            written.sha(written.edi._edi.__file__),
            written.edi.__build_commit__,
        )
    assert len(projects) == (1 if historical_bad else 2), (
        'A failed historical reference blocks the fresh current run completely'
    )
    assert not (destination / 'result.json').exists(), (
        'Control-flow spies stop before Save and can never produce qualification evidence'
    )

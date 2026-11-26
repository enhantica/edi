"""Actual capture-file ordering belongs to integration; full historical qualifier retained."""

import copy
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.fixtures.e04_t11_wasm import solver_vehicles, written
from tests.fixtures.native_process import environment_bash
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
            _minimizer_max_iterations=50,
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


@pytest.mark.parametrize('capture_exit', [0, 23])
def test_shared_capture_keeps_success_and_clears_failed_output(tmp_path, capture_exit):
    script = (ROOT / 'tools/ci/wasm-check.sh').read_text()
    start = script.index('\nstatus=0\n') + 1
    provider = tmp_path / 'tools/ci/wasm-written-reference.sh'
    provider.parent.mkdir(parents=True)
    provider.write_text(
        'echo -n "$1" > "$OUT/captured-path"\n'
        'echo native-record > "$1/native-record"\nexit ' + str(capture_exit) + '\n'
    )
    output = tmp_path / 'output'
    output.mkdir()
    env = {
        **os.environ,
        'ROOT': str(tmp_path),
        'OUT': str(output),
        'SITE': 'site',
        'DRIVER': 'driver',
        'CHROME': 'chrome',
        'ZIP': 'site.zip',
    }
    env.pop('EDI_WASM_WRITTEN_REFERENCE', None)
    consumers = (
        'python() { [[ "$(declare -p EDI_WASM_WRITTEN_REFERENCE)" == "declare -x"* ]] '
        '|| return 71; '
        'echo "python:$EDI_WASM_WRITTEN_REFERENCE" >> "$OUT/consumers"; }\n'
        'node() { [[ "$(declare -p EDI_WASM_WRITTEN_REFERENCE)" == "declare -x"* ]] || return 72; '
        '[[ "$7" == "--written-reference=$EDI_WASM_WRITTEN_REFERENCE" ]] || return 73; '
        'echo "node:$4:$EDI_WASM_WRITTEN_REFERENCE" >> "$OUT/consumers"; }\n'
    )
    run = subprocess.run(
        [
            environment_bash(),
            '-c',
            'set -euo pipefail\n' + consumers + script[start:],
            'wasm-check',
            'checks.py',
        ],
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert run.returncode == (1 if capture_exit else 0), (
        'A failed shared capture remains a failed aggregate while independent checks continue'
    )
    expected = (output / 'captured-path').read_text()
    reference = Path(expected)
    assert reference.is_dir() and reference.resolve().is_relative_to(output.resolve()), (
        'Every consumer receives the freshly allocated owner directory with an exported reference'
    )
    assert (output / 'consumers').read_text().splitlines() == [
        'python:' + expected,
        'node:multithread:' + expected,
        'node:shim:' + expected,
    ], (
        'Both browser modes and the Python checks execute independently '
        'after either capture outcome'
    )
    assert {path.name for path in reference.iterdir()} == (
        {'native-record'} if capture_exit == 0 else set()
    ), (
        'Successful capture bytes survive, while every partial failed-capture byte '
        'is removed before handoff'
    )

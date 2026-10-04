"""dispatch adapted by : formerly --descent, now analysis.edi.

All registry ids, real native dispatch, API/CLI parity and numerical pins remain asserted.

The per-strategy result pins come from the committed crysta fitting corpus. The omitted-selector
record is a labelled pre-selector edi regression pin, not a correctness oracle.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import edi
import pytest

from conftest import (
    calculator_load_warning,
    corpus_case_dir,
    crysta_reference_prefix,
    crysta_reference_source,
)

ROOT = Path(__file__).resolve().parents[3]
CRYSTA = crysta_reference_prefix() / 'bin/crysta'
CRYSTA_FETCH = crysta_reference_source()
DEFAULT_RECORD_REGRESSION_PIN = (
    ROOT / 'tests/fixtures/c11_t35_descent_selector/default-record-no-elapsed.txt'
)


@dataclass(frozen=True)
class DescentRegistry:
    default: str
    ids: tuple[str, ...]


def _crysta_registry() -> DescentRegistry:
    recorded = (crysta_reference_prefix() / '.crysta-sha').read_text(encoding='utf-8').strip()
    fetched = subprocess.run(
        ['git', '-C', str(CRYSTA_FETCH), 'rev-parse', 'HEAD'],
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    assert recorded == fetched, (
        'the descent oracle must be the source linked into edi and its matching installed CLI'
    )
    completed = subprocess.run(
        [str(CRYSTA), 'fit', '--list-descents', '--version'],
        text=True,
        capture_output=True,
        check=True,
    )
    fields = dict(line.split('=', 1) for line in completed.stdout.splitlines() if '=' in line)
    ids = tuple(fields.get('descents', '').split(','))
    assert fields.get('record') == 'descents' and fields.get('default') in ids and all(ids), (
        'the independent crysta oracle must name a non-empty registry containing its default'
    )
    return DescentRegistry(default=fields['default'], ids=ids)


def _project_case() -> Path:
    case = corpus_case_dir('cosio-d20-s1')
    assert (case / 'expected.json').is_file(), (
        'the selector control requires the committed crysta strategy-result regression pins'
    )
    return case


def _without_elapsed(record: str) -> str:
    lines = [line for line in record.splitlines() if not line.startswith('elapsed_ms=')]
    assert len(lines) + 1 == len(record.splitlines()), (
        'the real machine record must carry exactly one nondeterministic elapsed_ms field'
    )
    return '\n'.join(lines) + '\n'


def _record_fields(record: str) -> dict[str, str]:
    fields = dict(line.split('=', 1) for line in record.splitlines())
    assert fields.get('record') == 'fit' and fields.get('status') == 'done', (
        'the real selector route must produce one successful terminal fit record'
    )
    return fields


def _strategy_pins(selected: str) -> dict[str, object]:
    if selected == 'ladder':
        return {}
    expected = json.loads((_project_case() / 'expected.json').read_text(encoding='utf-8'))
    variant = selected.replace('_', '-')
    assert variant in expected['variants'], (
        f'the independent crysta corpus must carry regression pins for {selected!r}'
    )
    return expected['variants'][variant]['quantities']


def _run_real_cli(
    *arguments: str, project_path: Path | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            '-m',
            'edi',
            'fit',
            str(project_path or _project_case() / 'project'),
            *arguments,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


@pytest.mark.parametrize('selected', _crysta_registry().ids)
def test_each_registered_id_routes_through_cli_and_project_analysis(
    selected: str, tmp_path: Path
) -> None:
    project = edi.Project.load(_project_case() / 'project')
    project.analysis.descent = selected
    assert project.analysis.descent == selected, (
        'project.analysis must expose the same descent id for Python callers'
    )
    assert project.descent == selected, (
        'the Python facade must route the selection into the project model'
    )
    outcome = project.analysis.fit()
    api_record = edi.machine_report(project, outcome, edi.VerbosityEnum.COMPACT)
    api_fields = _record_fields(api_record)
    assert api_fields['descent'] == selected, (
        'the real native fit result must record the descent selected through project.analysis'
    )
    for field, pin in _strategy_pins(selected).items():
        assert float(api_fields[field]) == pin['value'], (
            f'regression pin: the real {selected!r} dispatch moved crysta corpus field '
            f'{field!r} away from its committed value'
        )

    declared = tmp_path / 'project'
    shutil.copytree(_project_case() / 'project', declared)
    analysis = declared / 'analysis/analysis.edi'
    analysis.write_text(analysis.read_text() + f'\n_minimizer.descent {selected}\n')
    expected_warning = calculator_load_warning(declared)
    completed = _run_real_cli(
        '--dry', '--report', 'machine', '--verbosity', 'compact', project_path=declared
    )
    assert completed.returncode == 0 and completed.stderr == expected_warning, (
        f'the real CLI admits only the declared load warning for registered descent {selected!r}: '
        + completed.stdout
        + completed.stderr
    )
    cli_fields = _record_fields(completed.stdout)
    assert cli_fields['descent'] == selected, (
        ' native terminal record must carry the descent declared in the CLI project'
    )
    assert _without_elapsed(completed.stdout) == _without_elapsed(api_record), (
        'the CLI and project.analysis selections must reach the same real native dispatch '
        f'for {selected!r}'
    )


def test_omitted_descent_preserves_the_default_record_bytes_regression_pin() -> None:
    registry = _crysta_registry()
    expected_warning = calculator_load_warning(_project_case() / 'project')
    completed = _run_real_cli('--dry', '--report', 'machine', '--verbosity', 'compact')
    assert completed.returncode == 0 and completed.stderr == expected_warning, (
        'the omitted selector must fit successfully with only the declared load warning: '
        + completed.stdout
        + completed.stderr
    )
    assert _record_fields(completed.stdout)['descent'] == registry.default, (
        'the omitted selector must record the default declared by crysta itself'
    )
    expected = DEFAULT_RECORD_REGRESSION_PIN.read_text(encoding='utf-8')
    assert _without_elapsed(completed.stdout) == expected, (
        'regression pin: omitted descent must retain every deterministic byte of the '
        'record remeasured after the  model and uncertainty correction'
    )

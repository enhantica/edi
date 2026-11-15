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
from tests.fixtures.correlations.machine_record import without_pair_count
from tests.fixtures.engine_fit_records.records import record as engine_record
from tests.fixtures.engine_fit_records.selector_projection import (
    current_quantities,
    historical_ladder_record,
)

ROOT = Path(__file__).resolve().parents[3]
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
        ['git', '-C', str(crysta_reference_source()), 'rev-parse', 'HEAD'],
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    assert recorded == fetched, (
        'the descent oracle must be the source linked into edi and its matching installed CLI'
    )
    completed = subprocess.run(
        [str(crysta_reference_prefix() / 'bin/crysta'), 'fit', '--list-descents', '--version'],
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
    expected = (
        engine_record('cosio-ladder')['status'] if fields.get('descent') == 'ladder' else 'done'
    )
    assert fields.get('record') == 'fit' and fields.get('status') == expected, (
        'The real selector route must retain the independent engine terminal status'
    )
    return fields


def _strategy_pins(selected: str) -> dict[str, object]:
    if selected == 'ladder':
        return {}
    expected_bytes = (_project_case() / 'expected.json').read_bytes()
    expected = json.loads(expected_bytes)
    selected = {
        'multistart_prune': 'fast_descent_and_ladder',
        'fast_descent_linear_snap': 'fast_descent',
        'fast_descent_guarded_linear_snap': 'fast_descent',
    }.get(selected, selected)
    # The engine corpus retains the historical variant key and its complete values.
    variant = (
        'multistart-prune' if selected == 'fast_descent_and_ladder' else selected.replace('_', '-')
    )
    assert variant in expected['variants'], (
        f'the independent crysta corpus must carry regression pins for {selected!r}'
    )
    return current_quantities(
        selected, expected['variants'][variant]['quantities'], expected_bytes
    )


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


# Crysta ADR-0060 section 4 / ADR-0061's machine-record contract. Collection
# needs the declared identifiers; execution still checks the matching SDK's registry.
DECLARED_DESCENTS = (
    'ladder',
    'fast_descent',
    'fast_descent_linear_snap',
    'fast_descent_guarded_linear_snap',
    'multistart_prune',
    'fast_descent_and_ladder',
)
CANONICAL_DESCENTS = ('ladder', 'fast_descent', 'fast_descent_and_ladder')


def canonical(selected):
    return {
        'multistart_prune': 'fast_descent_and_ladder',
        'fast_descent_linear_snap': 'fast_descent',
        'fast_descent_guarded_linear_snap': 'fast_descent',
    }.get(selected, selected)


@pytest.mark.parametrize('selected', DECLARED_DESCENTS)
def test_each_registered_id_routes_through_cli_and_project_analysis(
    selected: str, tmp_path: Path
) -> None:
    assert sorted(_crysta_registry().ids) == sorted(CANONICAL_DESCENTS), (
        'ADR-0060 and ADR-0061 declared descents cover the complete matching SDK registry'
    )
    project = edi.Project.load(_project_case() / 'project')
    if selected in {'fast_descent_linear_snap', 'fast_descent_guarded_linear_snap'}:
        with pytest.raises(ValueError, match='edi descent: unknown descent') as refused:
            project.analysis.descent = selected
        assert str(refused.value) == (
            f"edi descent: unknown descent '{selected}' (registered descents: "
            'ladder, fast_descent, fast_descent_and_ladder)'
        ), 'Retired native dispatches must refuse cleanly and advertise exactly the live registry'
        return
    project.analysis.descent = selected
    assert project.analysis.descent == canonical(selected), (
        'project.analysis must expose the same descent id for Python callers'
    )
    assert project.descent == canonical(selected), (
        'the Python facade must route the selection into the project model'
    )
    outcome = project.analysis.fit()
    api_record = edi.machine_report(project, outcome, edi.VerbosityEnum.COMPACT)
    api_fields = _record_fields(api_record)
    assert api_fields['descent'] == canonical(selected), (
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
    assert cli_fields['descent'] == canonical(selected), (
        ' native terminal record must carry the descent declared in the CLI project'
    )
    assert _without_elapsed(completed.stdout) == _without_elapsed(api_record), (
        'the CLI and project.analysis selections must reach the same real native dispatch '
        f'for {selected!r}'
    )


def test_historical_ladder_preserves_the_default_record_bytes_regression_pin(tmp_path) -> None:
    declared = tmp_path / 'historical-ladder'
    shutil.copytree(_project_case() / 'project', declared)
    analysis = declared / 'analysis/analysis.edi'
    analysis.write_text(analysis.read_text() + '\n_minimizer.descent ladder\n')
    expected_warning = calculator_load_warning(declared)
    completed = _run_real_cli(
        '--dry', '--report', 'machine', '--verbosity', 'compact', project_path=declared
    )
    assert completed.returncode == 0 and completed.stderr == expected_warning, (
        'the omitted selector must fit successfully with only the declared load warning: '
        + completed.stdout
        + completed.stderr
    )
    assert _record_fields(completed.stdout)['descent'] == 'ladder', (
        'The historical byte witness must retain its explicitly selected ladder policy'
    )
    expected = DEFAULT_RECORD_REGRESSION_PIN.read_text(encoding='utf-8')
    assert (
        historical_ladder_record(_without_elapsed(without_pair_count(completed.stdout)))
        == expected
    ), (
        'regression pin: omitted descent must retain every deterministic byte of the '
        'record remeasured after the  model and uncertainty correction'
    )


def test_omitted_selector_matches_explicit_canonical_default_and_corpus_pin():
    registry = _crysta_registry()
    assert registry.default == 'fast_descent_and_ladder', (
        'The matching engine must declare the canonical two-probe default'
    )
    project = edi.Project.load(_project_case() / 'project')
    project.analysis.descent = registry.default
    outcome = project.analysis.fit()
    explicit = edi.machine_report(project, outcome, edi.VerbosityEnum.COMPACT)
    completed = _run_real_cli('--dry', '--report', 'machine', '--verbosity', 'compact')
    assert completed.returncode == 0 and completed.stderr == calculator_load_warning(
        _project_case() / 'project'
    ), 'The omitted default must reach the real CLI with exactly its declared load warning'
    assert _without_elapsed(completed.stdout) == _without_elapsed(explicit), (
        'Omitted and explicit canonical defaults must retain every deterministic API/CLI record '
        'byte'
    )
    fields = _record_fields(completed.stdout)
    assert fields['descent'] == registry.default, (
        'The omitted default must emit the canonical selector in its actual terminal record'
    )
    for field, pin in _strategy_pins(registry.default).items():
        assert float(fields[field]) == pin['value'], (
            'The omitted default must retain each independently committed engine corpus '
            'regression pin'
        )

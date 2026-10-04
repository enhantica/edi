# ruff: noqa: PLC0415
# Ported verbatim from the retired hidden fitting-test file ( phase C): the
# body keeps its hidden-tier-authored shape — reshaping it for the visible tier's
# lint would churn what the port must preserve.
"""red-first gates for the 193-column joint absorption fit."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/c09_t6_ncaf_5bank_absorption'


def _project() -> Path:
    from conftest import corpus_case_dir

    return corpus_case_dir('ncaf-wish-3bank-s5') / 'project'


ORACLE = FIXTURE / 'crysta_cli_joint_fit.json'
OBSERVER_SOURCE = ROOT / 'tests/unit/cpp/c08_t2_native_observer.c'
OBSERVER_HARNESS = ROOT / 'tests/system/py/c09_t6_joint_native_harness.py'
BANKS = ('wish_1_10', 'wish_2_9', 'wish_3_8', 'wish_4_7', 'wish_5_6')
BANK_COUNTS = {
    'wish_1_10': 37,
    'wish_2_9': 33,
    'wish_3_8': 32,
    'wish_4_7': 38,
    'wish_5_6': 37,
}
PROFILE_FIELDS = (
    'peak.rise_alpha_0',
    'peak.rise_alpha_1',
    'peak.decay_beta_0',
    'peak.decay_beta_1',
    'peak.broad_gauss_sigma_0',
    'peak.broad_gauss_sigma_1',
    'peak.broad_gauss_sigma_2',
    'peak.broad_gauss_size',
    'peak.broad_gauss_strain',
    'peak.broad_lorentz_gamma_0',
    'peak.broad_lorentz_gamma_1',
    'peak.broad_lorentz_gamma_2',
    'peak.broad_lorentz_size',
    'peak.broad_lorentz_strain',
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _oracle() -> dict[str, Any]:
    return json.loads(ORACLE.read_text(encoding='utf-8'))


def _edi_path(label: str) -> str:
    bank_match = re.fullmatch(r'([^.]*)\.(.*)', label)
    if bank_match is not None and bank_match.group(1) in BANKS:
        bank, field = bank_match.groups()
        aliases = {
            'calib_d_to_tof_offset': 'instrument.calib_d_to_tof_offset',
            'calib_d_to_tof_linear': 'instrument.calib_d_to_tof_linear',
            'calib_d_to_tof_quadratic': 'instrument.calib_d_to_tof_quadratic',
            'scale': 'linked_structure.scale',
            'abscor1': 'absorption.abscor1',
        }
        background = re.fullmatch(r'background\[(\d+)\]', field)
        if background is not None:
            field = f'background[{background.group(1)}].intensity'
        elif field in aliases:
            field = aliases[field]
        elif not field.startswith((
            'peak.',
            'instrument.',
            'linked_structure.',
            'absorption.',
        )):
            field = f'peak.{field}'  # profile leaves live under the peak category
        return f'experiments[{bank}].{field}'
    if label == 'cell_length_a':
        return 'structure.cell.length_a'
    site, field = label.split('.', maxsplit=1)
    allowed = {'fract_x', 'fract_y', 'fract_z', 'adp_iso', 'occupancy'}
    assert field in allowed, f'unmapped crysta structural label in frozen oracle: {label!r}'
    return f'structure.atom_sites[{site}].{field}'


def _outcome(result: Any) -> dict[str, tuple[float, float]]:
    assert isinstance(result.values, Mapping)
    assert isinstance(result.uncertainty, Mapping), (
        'the _outcome requirement must hold: isinstance(result.uncertainty, Mapping)'
    )
    assert set(result.values) == set(result.uncertainty), (
        'the _outcome requirement must hold: set(result.values) == set(result.uncertainty)'
    )
    return {
        str(path): (float(result.values[path]), float(result.uncertainty[path]))
        for path in result.values
    }


def _assert_physical(
    actual: float, expected: float, where: str, *, esd: float | None = None
) -> None:
    """Delegate to the ONE shared golden-pin comparator (`conftest.assert_matches_golden_pin`).

    The former `rel=5e-9` bound asserted x86_64 arithmetic, not the fit: crysta's aarch64 build
    dispatches SLEEF NEON kernels and lands ~3e-07 relative away on a converged parameter,
    exceeding it 62x. A parameter VALUE is now bounded by a fraction of its own ESD; an ESD, rwp
    and chi-square take the relative bound instead, which is why those callers omit `esd`.
    """
    from conftest import assert_matches_golden_pin

    assert_matches_golden_pin(actual, expected, where, esd=esd)


def test_c09_t6_cli_oracle_has_exact_joint_layout_and_metrics() -> None:
    manifest = json.loads((FIXTURE / 'manifest.json').read_text(encoding='utf-8'))
    oracle = _oracle()
    assert manifest['crysta_cli_oracle']['pin'] == 'e1f0452810006d1dd529f26a26cbcd3ad835f33c'
    assert _sha256(ORACLE) == manifest['crysta_cli_oracle']['output_sha256']
    assert oracle['config']['fitting_mode'] == 'joint'
    assert oracle['ramp'] is False
    assert oracle['auto_cutoff'] == 'off'
    assert oracle['converged'] is True
    assert oracle['iterations'] == 18
    assert len(oracle['parameters']) == 193
    labels = [row['label'] for row in oracle['parameters']]
    assert len(labels) == len(set(labels))
    decomposition = Counter(
        label.split('.', maxsplit=1)[0] if label.startswith('wish_') else 'shared'
        for label in labels
    )
    assert decomposition == Counter({'shared': 16, **BANK_COUNTS})
    assert [bank['name'] for bank in oracle['banks']] == list(BANKS)
    assert all(bank['n_points'] > 3000 for bank in oracle['banks'])


def _frec_expected() -> dict[str, dict[str, float]]:
    """The re-derived cross-surface expected table (ruling 8a: regenerated, never ported).

    Parsed from the ruled vehicle's committed `goldens/joint-default.json` — the crysta CLI's
    full-verbosity record at the engine-default configuration, the like-for-like config the
    F-live producer runs — mapped into edi paths by the same label grammar as before.
    """
    from conftest import frec_golden_record

    record = frec_golden_record('ncaf-wish-3bank-s5', 'joint-default')
    expected: dict[str, dict[str, float]] = {}
    for key, value in record.items():
        if key.startswith('param.') and key.endswith('.value'):
            label = key.removeprefix('param.').removesuffix('.value')
            expected[_edi_path(label)] = {
                'value': float(value),
                'esd': float(record[f'param.{label}.esd']),
            }
    assert expected, 'the F-rec golden must carry the full parameter table'
    return expected


def test_c09_t6_joint_refit_matches_the_full_value_set_from_the_shared_producer(
    session_joint_fit,
) -> None:
    """The full-value-set parity of the ONE shared refit (P1.2b: consumes F-live).

    Renamed from `matches_all_193` with the re-frozen oracle (ruling 7a consumer 1): the
    5-bank-derived payload is RE-DERIVED on `ncaf-wish-3bank-s5` — the expected table is the
    committed F-rec golden of the like-config crysta CLI record, so cross-surface parity of
    the converged result holds through a shared, independently-anchored reference (the case's
    FullProf-referenced `expected.json` holds the physics anchor, I16).
    """
    expected = _frec_expected()
    outcome = session_joint_fit.outcome
    record = session_joint_fit.record

    assert set(outcome.values) == set(outcome.uncertainty) == set(expected), (
        'the refined columns must reproduce the complete CLI layout'
    )
    structural = {path for path in outcome.values if path.startswith('structure.')}
    assert structural, 'shared structural parameters must be present'
    bank_prefixes = {path.split('.', 1)[0] for path in outcome.values if path.startswith('exp')}
    assert len(bank_prefixes) == 3, 'every bank must contribute per-bank parameters'

    write_back = record['model_parameters']
    for path, row in expected.items():
        _assert_physical(
            float(outcome.values[path]), row['value'], f'{path}.value', esd=row['esd']
        )
        _assert_physical(float(outcome.uncertainty[path]), row['esd'], f'{path}.uncertainty')
        _assert_physical(
            write_back[path][0], row['value'], f'{path}.write_back.value', esd=row['esd']
        )
        _assert_physical(write_back[path][1], row['esd'], f'{path}.write_back.uncertainty')

    from conftest import frec_golden_record

    golden = frec_golden_record('ncaf-wish-3bank-s5', 'joint-default')
    _assert_physical(float(outcome.rwp), float(golden['rwp']), 'rwp')
    _assert_physical(
        float(outcome.reduced_chi_square),
        float(golden['reduced_chi2']),
        'reduced_chi_square',
    )
    assert outcome.iterations == int(golden['iterations'])
    assert outcome.converged is True
    assert golden['converged'] == 'true'
    assert len(record['callback_history']) == outcome.iterations

    banks = {bank.name: bank for bank in outcome.banks}
    assert len(banks) == 3
    for name, bank in banks.items():
        assert bank.n_points == int(golden[f'bank.{name}.n_points'])
        _assert_physical(float(bank.rwp), float(golden[f'bank.{name}.rwp']), f'{name}.rwp')
    assert len({float(bank.rwp) for bank in banks.values()}) == 3, (
        'per-bank Rwp must be DISTINCT on the live result (P1.13)'
    )
    from conftest import corpus_case_dir

    scale_line = next(
        line
        for line in (
            corpus_case_dir('ncaf-wish-3bank-s5') / 'project' / 'experiments' / 'wish_5_6.edi'
        )
        .read_text(encoding='utf-8')
        .splitlines()
        if line.startswith('ncaf ')
    )
    declared_scale = float(scale_line.split()[1].split('(')[0])
    assert outcome.values['experiments[wish_5_6].linked_structure.scale'] != declared_scale, (
        'the shared refit must actually move the independently declared scale'
    )


def _run(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str] | None = None,
    timeout: int = 180,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def _build_native_observer(tmp_path: Path) -> tuple[Path, str]:
    compiler = shutil.which('cc')
    assert compiler is not None, 'the native I/O observer requires the pinned C compiler'
    if sys.platform.startswith('linux'):
        library = tmp_path / 'c09_t6_native_observer.so'
        command = [compiler, '-shared', '-fPIC', str(OBSERVER_SOURCE), '-ldl', '-o', str(library)]
        preload_variable = 'LD_PRELOAD'
    elif sys.platform == 'darwin':
        library = tmp_path / 'c09_t6_native_observer.dylib'
        command = [compiler, '-dynamiclib', str(OBSERVER_SOURCE), '-o', str(library)]
        preload_variable = 'DYLD_INSERT_LIBRARIES'
    else:
        raise AssertionError(f'no fail-closed native I/O observer for {sys.platform!r}')
    _run(command, cwd=tmp_path)
    return library, preload_variable


def _native_events(
    tmp_path: Path,
    library: Path,
    preload_variable: str,
    *,
    counterfactual: bool,
) -> list[str]:
    log_path = tmp_path / ('counterfactual-native.log' if counterfactual else 'fit-native.log')
    sentinel = tmp_path / 'absolute-native-read-counterfactual'
    sentinel.write_bytes(b'observer must report this absolute native read')
    environment = os.environ.copy()
    environment['EDI_C08_NATIVE_OBSERVER_LOG'] = str(log_path)
    previous_preload = environment.get(preload_variable)
    environment[preload_variable] = (
        str(library) if not previous_preload else os.pathsep.join((str(library), previous_preload))
    )
    if sys.platform == 'darwin':
        environment['DYLD_FORCE_FLAT_NAMESPACE'] = '1'
    _run(
        [
            sys.executable,
            str(OBSERVER_HARNESS),
            str(_project()),
            'counterfactual' if counterfactual else 'fit',
            str(sentinel),
        ],
        cwd=tmp_path,
        environment=environment,
    )
    assert log_path.is_file(), 'native observer did not initialise'
    return log_path.read_text(encoding='utf-8').splitlines()


def test_c09_t6_joint_refit_performs_no_native_file_io_or_subprocess(
    tmp_path: Path,
    session_joint_fit,
) -> None:
    """The I/O invariant on the ONE shared refit (P1.2b: consumes F-live).

    The producer ran the session's single live fit inside the preloaded native observer; its
    observation log must be empty. The counterfactual — the same observer catching a real
    native read — stays here, proving the instrument is alive without running another fit.
    """
    observer, preload_variable = _build_native_observer(tmp_path)
    assert _native_events(tmp_path, observer, preload_variable, counterfactual=True)
    assert session_joint_fit.observations == [], (
        'the joint refit performed native file I/O or spawned a subprocess'
    )

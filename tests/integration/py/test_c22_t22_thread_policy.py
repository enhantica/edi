from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
WAIT_VARIABLES = ('OMP_WAIT_POLICY', 'GOMP_SPINCOUNT', 'KMP_BLOCKTIME')
THREAD_VARIABLES = (*WAIT_VARIABLES, 'OMP_NUM_THREADS', 'OMP_DYNAMIC')

RUNTIME_PROBE = r"""
import ctypes
import importlib
import json
import os
import re
import sys
import time

requested_affinity = int(sys.argv[2])
if requested_affinity and hasattr(os, 'sched_getaffinity'):
    available = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, set(available[:requested_affinity]))
visible = (len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity')
           else (os.cpu_count() or 1))

importlib.import_module(sys.argv[1])

if sys.platform == 'darwin':
    process = ctypes.CDLL(None)
    process._dyld_image_count.restype = ctypes.c_uint32
    process._dyld_get_image_name.argtypes = [ctypes.c_uint32]
    process._dyld_get_image_name.restype = ctypes.c_char_p
    loaded_images = [
        process._dyld_get_image_name(index).decode()
        for index in range(process._dyld_image_count())
        if process._dyld_get_image_name(index)
    ]
elif sys.platform.startswith('linux'):
    loaded_images = []
    for line in open('/proc/self/maps', encoding='utf-8'):
        fields = line.rstrip().split(maxsplit=5)
        if len(fields) == 6 and fields[-1].startswith('/'):
            loaded_images.append(fields[-1])
else:
    raise SystemExit(f'unsupported platform for loaded-image inspection: {sys.platform}')

runtime_images = {}
for image in loaded_images:
    match = re.search(r'(?:^|/)lib(gomp|omp)(?:[.\-]|$)', image)
    if match:
        runtime_images.setdefault(f'lib{match.group(1)}', image)
if len(runtime_images) != 1:
    raise SystemExit(
        'edi must expose exactly one loaded OpenMP runtime image through its linked crysta core; '
        f'found {runtime_images}'
    )
runtime_name, runtime_image = next(iter(runtime_images.items()))
runtime = ctypes.CDLL(runtime_image)
if not hasattr(runtime, 'omp_get_num_threads') or not hasattr(runtime, 'omp_get_max_threads'):
    raise SystemExit(f'edi loaded an unqueryable OpenMP runtime: {runtime_image}')

runtime.omp_get_num_threads.restype = ctypes.c_int
runtime.omp_get_max_threads.restype = ctypes.c_int
seen = []
if runtime_name == 'libgomp':
    if not hasattr(runtime, 'GOMP_parallel'):
        raise SystemExit(f'the loaded GNU runtime has no GOMP_parallel: {runtime_image}')
    Callback = ctypes.CFUNCTYPE(None, ctypes.c_void_p)
    def record_team(_data):
        seen.append(runtime.omp_get_num_threads())
    callback = Callback(record_team)
    runtime.GOMP_parallel.argtypes = [Callback, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
    def enter_region():
        runtime.GOMP_parallel(callback, None, 0, 0)
elif runtime_name == 'libomp':
    if not hasattr(runtime, '__kmpc_fork_call'):
        raise SystemExit(f'the loaded LLVM runtime has no __kmpc_fork_call: {runtime_image}')
    class Ident(ctypes.Structure):
        _fields_ = [
            ('reserved_1', ctypes.c_int32), ('flags', ctypes.c_int32),
            ('reserved_2', ctypes.c_int32), ('reserved_3', ctypes.c_int32),
            ('source', ctypes.c_char_p),
        ]
    Microtask = ctypes.CFUNCTYPE(
        None, ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32)
    )
    def record_team(_global_id, _bound_id):
        seen.append(runtime.omp_get_num_threads())
    callback = Microtask(record_team)
    location = Ident(0, 2, 0, 0, b';;edi-thread-policy;1;1;;')
    runtime.__kmpc_fork_call.restype = None
    def enter_region():
        runtime.__kmpc_fork_call(ctypes.byref(location), 0, callback)
else:
    raise SystemExit(f'edi loaded an unsupported OpenMP runtime: {runtime_name}')

enter_region()
cpu_start = time.process_time()
wall_start = time.monotonic()
for _gap in range(8):
    # A 20 ms gap makes callback overhead small beside the runtime-owned idle
    # interval, while staying within LLVM's explicit 200 ms spinning escape.
    time.sleep(0.02)
    enter_region()
print(json.dumps({
    'cpu_wall': (time.process_time() - cpu_start) / (time.monotonic() - wall_start),
    'environment': {name: os.environ.get(name) for name in sys.argv[3:]},
    'max_threads': runtime.omp_get_max_threads(),
    'runtime': runtime_name,
    'team': max(seen),
    'visible': visible,
}))
"""


def _clean_environment(overrides: dict[str, str] | None = None) -> dict[str, str]:
    environment = os.environ.copy()
    for name in THREAD_VARIABLES:
        environment.pop(name, None)
    # The probe attributes process CPU to the OpenMP pool. Keep NumPy's unrelated OpenBLAS
    # pool serial so its idle policy cannot counterfeit either the passive or spinning result.
    environment['OPENBLAS_NUM_THREADS'] = '1'
    environment.update(overrides or {})
    return environment


def _wait_knob_spins(*, name: str, passive: bool, runtime: str) -> bool:
    runtime_spin_knob = {'libgomp': 'GOMP_SPINCOUNT', 'libomp': 'KMP_BLOCKTIME'}[runtime]
    return not passive and name in {'OMP_WAIT_POLICY', runtime_spin_knob}


def _probe(*, affinity: int = 4, overrides: dict[str, str] | None = None) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, '-c', RUNTIME_PROBE, 'edi', str(affinity), *THREAD_VARIABLES],
        cwd=ROOT,
        env=_clean_environment(overrides),
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, (
        'the edi-process runtime-effect probe must complete successfully; output:\n'
        + completed.stdout
        + completed.stderr
    )
    return json.loads(completed.stdout.splitlines()[-1])


def _assert_spinning(observed: dict[str, Any], requirement: str) -> None:
    # Visible VM cores do not guarantee concurrent CPU time for every waiting worker.
    # Measure a busy worker and its effect against the same team's passive control.
    workers = min(observed['visible'], observed['team'] - 1)
    assert workers >= 1, f'the wait-effect observation must have an idle worker: {observed}'
    passive = _probe(
        overrides={
            'OMP_NUM_THREADS': str(observed['team']),
            'OMP_DYNAMIC': 'FALSE',
            'OMP_WAIT_POLICY': 'passive',
        }
    )
    assert passive['team'] == observed['team'] and passive['runtime'] == observed['runtime'], (
        f'the passive counterfactual must use the same worker team and runtime: {passive}'
    )
    assert passive['cpu_wall'] < 0.25, (
        'a matched passive team must sleep during the same gaps, distinguishing the spin '
        f'escape from incidental process CPU: {passive} versus {observed}'
    )
    threshold = max(0.6, 4 * passive['cpu_wall'])
    assert observed['cpu_wall'] > threshold, (
        'caller spin control must consume CPU during serial gaps and exceed matched passive CPU; '
        f'{requirement}: {threshold=} {observed} versus {passive}'
    )


def test_c22_t22_vm_spin_observation_controls(monkeypatch) -> None:
    # Active observations come from the macOS CI failure; passive values below are synthetic.
    passive = {'cpu_wall': 0.05, 'team': 4, 'visible': 4, 'runtime': 'libomp'}
    monkeypatch.setattr(sys.modules[__name__], '_probe', lambda **_kwargs: passive)
    for measured in (1.1438590354248368, 1.1503788797490127):
        _assert_spinning({**passive, 'cpu_wall': measured}, 'recorded VM active wait')
    for measured in (0.0, 0.05, 0.599, 0.6):
        with pytest.raises(AssertionError):
            _assert_spinning({**passive, 'cpu_wall': measured}, 'synthetic non-spinning control')
    with pytest.raises(AssertionError):
        _assert_spinning({**passive, 'team': 1, 'cpu_wall': 1.2}, 'no waiting worker')
    with pytest.raises(AssertionError):
        _assert_spinning({**passive, 'runtime': 'libgomp', 'cpu_wall': 1.2}, 'different runtime')
    passive['cpu_wall'] = 0.24
    with pytest.raises(AssertionError):
        _assert_spinning({**passive, 'cpu_wall': 0.9}, 'insufficient matched passive effect')
    passive['cpu_wall'] = 0.25
    with pytest.raises(AssertionError):
        _assert_spinning({**passive, 'cpu_wall': 1.2}, 'passive control is busy')


def test_c22_t22_edi_extension_inherits_passive_max_minus_two_policy() -> None:
    observed = _probe(affinity=4)
    assert observed['team'] == max(1, observed['visible'] - 2), (
        'edi links crysta into its own extension, so the observed region must use '
        f'max(1, independently observed visible cores - 2): {observed}'
    )
    assert observed['cpu_wall'] < 0.25, (
        'edi-process OpenMP workers must sleep during the serial gap; CPU/wall is the '
        f'runtime-owned effect observation: {observed}'
    )

    explicit = _probe(affinity=4, overrides={'OMP_DYNAMIC': 'FALSE', 'OMP_WAIT_POLICY': 'passive'})
    assert explicit['environment']['OMP_WAIT_POLICY'] == 'passive', (
        f'the explicit passive caller policy must survive import edi: {explicit}'
    )
    assert explicit['team'] == explicit['visible'], (
        'the explicit passive caller policy must stand down max-minus-two while retaining the '
        f"caller's independently observed unconstrained team: {explicit}"
    )
    assert explicit['cpu_wall'] < 0.25, (
        'the explicit passive caller policy must keep workers asleep while retaining the '
        f"caller's unconstrained team size: {explicit}"
    )


def test_c22_t22_edi_extension_honours_explicit_thread_count_exactly() -> None:
    observed = _probe(affinity=4, overrides={'OMP_DYNAMIC': 'FALSE', 'OMP_NUM_THREADS': '3'})
    assert observed['team'] == 3, (
        f'edi must leave explicit OMP_NUM_THREADS=3 in control inside the region: {observed}'
    )
    assert observed['environment']['OMP_NUM_THREADS'] == '3', (
        f'edi/crysta must not rewrite the caller-owned thread setting: {observed}'
    )


@pytest.mark.parametrize(
    ('name', 'value'),
    [
        ('OMP_WAIT_POLICY', 'active'),
        ('GOMP_SPINCOUNT', '1000000000'),
        ('KMP_BLOCKTIME', '200'),
    ],
)
def test_c22_t22_edi_process_preserves_each_wait_escape(name: str, value: str) -> None:
    observed = _probe(affinity=4, overrides={name: value, 'OMP_DYNAMIC': 'FALSE'})
    assert observed['environment'][name] == value, (
        f'the caller-owned {name} escape hatch must survive import edi: {observed}'
    )
    assert observed['team'] == observed['visible'], (
        f'the presence of caller-owned {name} must stand down max-minus-two in the edi process '
        f'and leave the independently observed available CPU team unchanged: {observed}'
    )
    if _wait_knob_spins(name=name, passive=False, runtime=observed['runtime']):
        _assert_spinning(
            observed,
            (
                f'the caller-owned {name} spin control must retain measurable wait behaviour on '
                f'{observed["runtime"]} inside the edi process, not merely survive as a string: '
                f'{observed}'
            ),
        )


def test_c22_t22_edi_active_counterfactual_still_spins() -> None:
    observed = _probe(affinity=4, overrides={'OMP_WAIT_POLICY': 'active'})
    _assert_spinning(
        observed,
        (
            'explicit active must keep the old spin behaviour measurable in an edi process: '
            f'{observed}'
        ),
    )


def test_c22_t22_edi_runtime_specific_wait_escape_keeps_spinning() -> None:
    expectation_cases = [
        ('libgomp', 'OMP_WAIT_POLICY', True, False),
        ('libgomp', 'OMP_WAIT_POLICY', False, True),
        ('libgomp', 'GOMP_SPINCOUNT', False, True),
        ('libgomp', 'KMP_BLOCKTIME', False, False),
        ('libomp', 'OMP_WAIT_POLICY', True, False),
        ('libomp', 'OMP_WAIT_POLICY', False, True),
        ('libomp', 'GOMP_SPINCOUNT', False, False),
        ('libomp', 'KMP_BLOCKTIME', False, True),
    ]
    for runtime, name, passive, expected in expectation_cases:
        assert _wait_knob_spins(name=name, passive=passive, runtime=runtime) is expected, (
            'the runtime-specific wait expectation must distinguish GNU GOMP_SPINCOUNT from '
            f'LLVM KMP_BLOCKTIME when the detected runtime is injected: {runtime=} {name=}'
        )

    baseline = _probe(affinity=4)
    runtime_spin_knob = {'libgomp': 'GOMP_SPINCOUNT', 'libomp': 'KMP_BLOCKTIME'}[
        baseline['runtime']
    ]
    spin_value = {'GOMP_SPINCOUNT': '1000000000', 'KMP_BLOCKTIME': '200'}[runtime_spin_knob]
    observed = _probe(affinity=4, overrides={runtime_spin_knob: spin_value})
    _assert_spinning(
        observed,
        (
            'the linked runtime-specific escape must keep old spin behaviour measurable inside '
            f'an edi process, not merely preserve an environment string: {observed}'
        ),
    )


def test_c22_t22_edi_entrypoint_inventory_is_mechanical() -> None:
    root_cmake = (ROOT / 'CMakeLists.txt').read_text(encoding='utf-8')
    cli_cmake = (ROOT / 'cli/CMakeLists.txt').read_text(encoding='utf-8')
    binding_cmake = (ROOT / 'lib/CMakeLists.txt').read_text(encoding='utf-8')
    test_cmake = (ROOT / 'core/CMakeLists.txt').read_text(encoding='utf-8')
    assert 'add_subdirectory(cli)' in root_cmake and 'add_subdirectory(lib)' in root_cmake, (
        ' inventory must continue to reach both shipped edi hosts'
    )
    cli_targets = set(re.findall(r'add_executable\s*\(\s*([A-Za-z0-9_]+)', cli_cmake))
    extension_targets = set(
        re.findall(r'nanobind_add_module\s*\(\s*([A-Za-z0-9_]+)', binding_cmake)
    )
    assert cli_targets == {'easydiffraction'}, (
        ' mechanically inventories every edi CLI target; a new entry point needs its '
        f'own policy-effect probe before it can ship: {sorted(cli_targets)}'
    )
    assert extension_targets == {'_edi'}, (
        ' mechanically inventories every edi extension target; a new entry point needs '
        f'its own policy-effect probe before it can ship: {sorted(extension_targets)}'
    )
    assert 'add_test(NAME edi_unit COMMAND edi_tests)' in test_cmake, (
        'the runtime-policy inventory lost the registered C++ test entry point'
    )


def test_c22_t22_edi_build_links_no_nested_blas_runtime() -> None:
    build = (
        ROOT
        / 'build'
        / ('ci-consumer' if os.environ.get('EDI_USE_CONSUMER_BUILD') == '1' else 'ci')
    )
    artifacts = [build / 'cli/easydiffraction']
    artifacts.extend(path for path in (build / 'python/edi').glob('_edi*') if path.is_file())
    assert len(artifacts) >= 2, (
        'core-build must expose the edi CLI and extension for the nested-runtime inventory'
    )
    for artifact in artifacts:
        command = (
            ['otool', '-L', str(artifact)] if sys.platform == 'darwin' else ['ldd', str(artifact)]
        )
        completed = subprocess.run(
            command, check=False, capture_output=True, text=True, timeout=30
        )
        assert completed.returncode == 0, (
            'the edi shipped-artifact dependency inventory must complete successfully; output:\n'
            + completed.stdout
            + completed.stderr
        )
        dependencies = completed.stdout.casefold()
        assert not re.search(r'openblas|libblas|mkl|blis|accelerate\.framework', dependencies), (
            'edi now links a threaded BLAS through its crysta core; add a runtime-owned '
            'inside-solve count and scoped set/restore effect gate before shipping: '
            f'{artifact}\n{dependencies}'
        )

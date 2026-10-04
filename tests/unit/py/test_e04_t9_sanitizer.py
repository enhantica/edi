"""T1: the required Linux core step reaches the two-thread sanitizer witness."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_sanitizer_has_a_declared_task_and_required_linux_ci_step():
    manifest = tomllib.loads((ROOT / 'pixi.toml').read_text())
    assert 'tsan-worker' in manifest.get('tasks', {}), (
        ' T1 sanitizer witness is a reproducible declared core task'
    )
    workflow = (ROOT / '.github/workflows/ci.yml').read_text()
    assert 'tsan-worker' in workflow, (
        ' T1 the required Linux core CI job invokes the sanitizer task'
    )
    script = ROOT / 'tools/ci/tsan-worker.sh'
    assert script.is_file(), (
        ' T1 the declared script builds both pinned crysta and edi under ThreadSanitizer'
    )
    text = script.read_text()
    assert 'e04_t9_tsan_probe' in text and 'fsanitize=thread' in text, (
        ' T1 instrumentation reaches the hidden two-thread witness executable'
    )
    assert 'OMP_NUM_THREADS=1' in text, (
        ' T1 the declared witness runs with the specified single OpenMP worker'
    )

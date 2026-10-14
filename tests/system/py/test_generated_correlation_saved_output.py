"""Real fit completion complements the deterministic full-loop serialization witness."""

import math
import os
import shlex
import shutil
import subprocess
from pathlib import Path

import edi
import pytest

from tests.conftest import corpus_case_dir, crysta_reference_prefix
from tests.fixtures.shared_correlations.freeze_saved import HERE, hashes, loop_bytes

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def correlation_producer(tmp_path_factory):
    build = tmp_path_factory.mktemp('numeric-correlation-producer')
    core = Path(edi._edi.__file__).resolve().parents[2] / 'core/libedi_core.a'
    subprocess.run(
        [
            'cmake',
            '-S',
            str(ROOT / 'tests/fixtures/generated_correlations'),
            '-B',
            str(build),
            '-G',
            'Ninja',
            '-DCMAKE_CXX_COMPILER=' + os.environ.get('CXX', 'c++'),
            '-DCMAKE_PREFIX_PATH=' + str(crysta_reference_prefix()),
            '-DEDI_INCLUDE=' + str(ROOT / 'core/include'),
            '-DEDI_CORE=' + str(core),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(['cmake', '--build', str(build)], check=True, capture_output=True, text=True)
    return build / 'correlation_producer'


@pytest.mark.parametrize('case', ['single', 'scan'])
def test_real_fit_emits_every_pinned_single_or_template_correlation_row(
    tmp_path, case, correlation_producer
):
    source = tmp_path / 'source'
    shutil.copytree(HERE / (case + '-input'), source)
    corpus_id = {'single': 'lbco-hrpt-s2', 'scan': 'cosio-d20-scan-3f'}[case]
    corpus_project = corpus_case_dir(corpus_id) / 'project'
    for directory in ['structures', 'experiments']:
        assert hashes(source / directory) == hashes(corpus_project / directory), (
            'The declared disposable fit site must retain its pinned corpus physical inputs'
        )
    assert b'_fit_parameter_correlation.' not in (source / 'analysis/analysis.edi').read_bytes(), (
        'The real generated-output witness must start without saved expected correlation rows'
    )
    destination = tmp_path / 'saved'
    completed = subprocess.run(
        [str(correlation_producer), str(source), case, str(destination)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, (
        'The pinned corpus producer must complete its real fit and save: ' + completed.stderr
    )
    numerical_rows = [shlex.split(line) for line in completed.stdout.splitlines()]
    assert numerical_rows and all(len(row) == 3 for row in numerical_rows), (
        'The completed producer must expose its actual numerical pairs before saving'
    )
    numerical = {(i, j): float.fromhex(value) for i, j, value in numerical_rows}
    assert len(numerical) == len(numerical_rows), (
        'The same-fit numerical snapshot must contain no duplicate parameter pairs'
    )
    actual = loop_bytes((destination / 'analysis/analysis.edi').read_bytes())
    expected = (HERE / (case + '-correlations.edi')).read_bytes()
    actual_rows = [row.split() for row in actual.decode().splitlines() if ' deterministic ' in row]
    expected_rows = [
        row.split() for row in expected.decode().splitlines() if ' deterministic ' in row
    ]
    assert actual_rows and len(actual_rows) == len(expected_rows), (
        'Actual fit settlement and saving must emit every original producer pair'
    )
    assert set(numerical) == {(row[2], row[3]) for row in expected_rows}, (
        'The same-fit numerical table retains every historically declared ordered pair'
    )
    for produced, pinned in zip(actual_rows, expected_rows, strict=True):
        assert produced[:4] + produced[5:] == pinned[:4] + pinned[5:], (
            'Actual generated rows must keep every id, source, ordered endpoint and template file'
        )
        # A serialization invariant against this completed fit, not fitted physics inferred
        # from a different platform's optimizer endpoint. Historical numeric-state pins stay
        # byte-exact in the separate frozen conversion and reload witnesses.
        wanted = numerical[produced[2], produced[3]]
        assert math.isfinite(wanted) and math.isfinite(float(produced[4])), (
            'The generated correlation and its completed numerical reference must be finite'
        )
        assert abs(float(produced[4]) - wanted) <= max(5e-9 * abs(wanted), 5e-10), (
            'Saved coefficients must match the completed same-fit numerical table '
            'within the retained bound'
        )

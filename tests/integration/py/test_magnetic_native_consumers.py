"""Run each native decoded-member consumer in the integration tier, never the unit tier."""

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'tests/integration/cpp/test_magnetic_compound_consumers.cpp'
CASES = re.findall(r'TEST_CASE\("([^"\n]+)"\)', SOURCE.read_text())


@pytest.fixture(scope='module')
def native_consumers():
    supplied = os.environ.get('EDI_MAGNETIC_INTEGRATION_TEST_EXE')
    candidates = (
        [Path(supplied)]
        if supplied
        else [
            ROOT / 'build/ci/core/edi_integration_tests',
            ROOT / 'build/ci-consumer/core/edi_integration_tests',
        ]
    )
    binary = next((path for path in candidates if path.is_file()), None)
    assert binary is not None, (
        'Build the native integration consumer from tests/integration/cpp before this gate; '
        'a missing downstream consumer is a failure, never a skip'
    )
    return binary


@pytest.mark.parametrize('case', CASES)
def test_each_decoded_member_reaches_its_native_integration_consumer(native_consumers, case):
    result = subprocess.run(
        [
            str(native_consumers),
            '--no-colors',
            '--test-case=' + case,
            '--source-file=*test_magnetic_compound_consumers.cpp',
        ],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, 'OMP_NUM_THREADS': '1'},
    )
    assert re.search(r'test cases:\s+1\s+\|', result.stdout), (
        'The selected compiled downstream consumer actually executes: '
        + result.stdout
        + result.stderr
    )
    assert result.returncode == 0, (
        'ADR-0108 complete typed values survive and malformed compounds refuse at this consumer: '
        + result.stdout
        + result.stderr
    )

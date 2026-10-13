"""Count operations in real ItemVec instantiations; elapsed time is never a verdict."""

import os
import subprocess
from pathlib import Path

import edi
import pytest

from tests.conftest import crysta_reference_prefix

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def comparison_probe(tmp_path_factory):
    build = tmp_path_factory.mktemp('admission-comparisons')
    core = Path(edi._edi.__file__).resolve().parents[2] / 'core/libedi_core.a'
    compiler = os.environ.get('CXX', 'c++')
    subprocess.run(
        [
            'cmake',
            '-S',
            str(ROOT / 'tests/fixtures/linear_admission'),
            '-B',
            str(build),
            '-G',
            'Ninja',
            '-DCMAKE_CXX_COMPILER=' + compiler,
            '-DCMAKE_PREFIX_PATH=' + str(crysta_reference_prefix()),
            '-DEDI_INCLUDE=' + str(ROOT / 'core/include'),
            '-DEDI_CORE=' + str(core),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(['cmake', '--build', str(build)], check=True, capture_output=True, text=True)
    return build / 'admission_count'


@pytest.mark.parametrize(
    'operation', ['keyed', 'replace', 'reorder', 'copy', 'default-ids', 'unkeyed']
)
def test_admission_comparison_budget_is_proportional_to_rows(comparison_probe, operation):
    # Fixed primitive-operation allowance, per row, through the owner's large-table witness.
    # The small witnesses fail first on a quadratic implementation rather than executing its
    # billions of operations at 120000. No elapsed-time limit decides this property.
    previous = None
    for count in [512, 2048, 120000]:
        result = subprocess.run(
            [str(comparison_probe), str(count), operation],
            capture_output=True,
            text=True,
            check=True,
        )
        rows, comparisons = map(int, result.stdout.strip().split())
        assert rows == count and comparisons > 0, (
            'The compiler counter must reach admission of the whole requested real collection'
        )
        assert comparisons <= 256 * rows, (
            'Admission and row replacement must stay within a fixed comparison budget per row: '
            f'{operation}, {rows} rows, {comparisons} executed comparisons'
        )
        if previous is not None:
            earlier_rows, earlier_comparisons = previous
            assert comparisons * earlier_rows <= earlier_comparisons * rows * 1.1, (
                'A larger fixed-width input must not add a size-dependent admission factor: '
                f'{operation}, {previous} then {(rows, comparisons)}'
            )
        previous = rows, comparisons

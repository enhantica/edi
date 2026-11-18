"""Check full lattice neighbourhoods and affine shells against independent geometry."""

import os
from pathlib import Path

import pytest

from tests.fixtures.fast_chart_redraws.rendering import capture

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    *[
        f'test_complete_periodic_neighbourhood:{kind}-{mode}'
        for kind in ('orthogonal', 'skew')
        for mode in ('distance', 'bonds')
    ],
    *[
        f'test_affine_shell_volume:{shape}'
        for shape in ('coplanar-square', 'coplanar-hexagon', 'octahedron', 'cube')
    ],
]


@pytest.mark.parametrize('case', CASES)
def test_polyhedra_independent_geometry(case):
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Independent geometry requires the actual native application host'
    status, output = capture(
        [
            binary,
            '-input',
            ROOT / 'tests/unit/app/tst_polyhedra_neighbourhood.qml',
            'PolyhedraNeighbourhood::' + case,
        ],
        env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
    )
    function, tag = case.split(':')
    assert status == 0, (
        'The actual scene satisfies independent lattice and affine-volume contracts: ' + output
    )
    assert f'PolyhedraNeighbourhood::{function}({tag})' in output and '0 failed' in output, (
        'The requested independent geometry witness executes its native assertions'
    )
    assert 'SKIP' not in output, 'Independent geometry executes on the actual native scene'

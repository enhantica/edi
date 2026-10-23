"""Execute the actual C++ matrix-selection method against external covariances.

Container and notification carriers avoid needing a GUI build for this numeric
boundary. The separately authored Qt actor checks paint, popup and app wiring.
"""

import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/correlations'
REFERENCE = json.loads((FIXTURE / 'scan-reference.json').read_text())


@pytest.fixture(scope='module')
def selection_probe(tmp_path_factory):
    compiler = shutil.which('clang++')
    assert compiler, 'The correlation selection gate requires the declared C++ compiler'
    source = (ROOT / 'app/src/correlation_view_model.cpp').read_text()
    start = source.index('void CorrelationViewModel::rebuild()')
    opening = source.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        assert end < len(source), 'The production correlation rebuild method must close its body'
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    directory = tmp_path_factory.mktemp('correlation-selection')
    cpp = directory / 'probe.cpp'
    cpp.write_text(
        (FIXTURE / 'selection_probe.cpp')
        .read_text()
        .replace('// PRODUCTION_REBUILD', source[start:end])
    )
    executable = directory / 'probe'
    artifact = Path(sys.modules['edi._edi'].__file__).resolve().parents[2]
    library = artifact / 'core/libedi_core.a'
    assert library.is_file(), 'The app selection witness requires the matching built core archive'
    built = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-O0',
            '-I' + str(ROOT / 'core/include'),
            str(cpp),
            str(library),
            '-o',
            str(executable),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert built.returncode == 0, (
        'The unedited production correlation selection method must compile: ' + built.stderr
    )
    return executable


@pytest.mark.parametrize(
    ('case', 'level', 'kept', 'missing'),
    [
        (0, 0.8, [0, 1, 2], None),
        (1, 0.65, [0, 1, 2], None),
        (0, 0.9, [1, 2], None),
        (0, 0.8, [0, 1, 2], 'nan'),
        (0, 0.8, [0, 1, 2], 'inf'),
        (0, 0.8, [0, 1, 2], '-inf'),
    ],
    ids=['weak-positive', 'weak-negative', 'parameter-selection', 'nan', 'inf', 'negative-inf'],
)
def test_every_finite_lower_pair_of_selected_parameters_remains_visible(
    selection_probe,
    case,
    level,
    kept,
    missing,
):
    truth = REFERENCE['cases'][case]
    matrix = [list(row) for row in truth['matrix']]
    if missing:
        matrix[0][2] = matrix[2][0] = float(missing)
    payload = '3\n' + '\n'.join(truth['names']) + '\n'
    payload += '\n'.join(' '.join(str(value) for value in row) for row in matrix) + '\n'
    run = subprocess.run(
        [str(selection_probe), str(level), '3'],
        input=payload,
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
    )
    assert run.returncode == 0, 'The production selection method must execute the external matrix'
    lines = run.stdout.splitlines()
    count = int(lines[0])
    labels = lines[1 : count + 1]
    values = [float(value) for value in lines[count + 1 :]]
    assert labels == [truth['names'][i] for i in kept], (
        'The level must select parameters through their strongest pair and preserve '
        'their identities'
    )
    assert len(values) == count * count, 'The shown correlation values must form a complete square'
    for row, original_row in enumerate(kept):
        for column, original_column in enumerate(kept):
            actual = values[row * count + column]
            expected = matrix[original_row][original_column]
            if column >= row or not math.isfinite(expected):
                assert math.isnan(actual), (
                    'The diagonal, upper triangle and non-finite correlations must stay blank'
                )
            else:
                assert actual == pytest.approx(expected, abs=1e-12), (
                    'Every finite lower-triangle pair among shown parameters must retain its '
                    'external coefficient, even below the parameter-selection level'
                )

"""Report integer domains come from the destination types, independent of the schema seed."""

import copy
import ctypes
import json
from pathlib import Path

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]
SEED = json.loads((ROOT / 'tests/fixtures/report_integer_domain/schema-seed.json').read_text())
INDEX_PATHS = [
    'structures.0.scene.atoms.0.row',
    'structures.0.scene.atoms.0.parts.0.row',
    'structures.0.scene.atoms.0.major',
    'structures.0.scene.bonds.0.row',
    'structures.0.scene.bonds.0.atom_1',
    'structures.0.scene.bonds.0.atom_2',
    'structures.0.scene.labels.0.atom',
    'structures.0.drawing.spheres.0.atom',
    'structures.0.drawing.cylinders.0.atom',
    'structures.0.drawing.shared.0',
    'structures.0.labels.0.atom',
    'experiments.0.pattern.series.0.rows.0',
]
SIGNED_PATHS = ['structures.0.scene.atoms.0.cluster_id', 'correlations.available']


def replace(document, path, value):
    tokens = [int(word) if word.isdigit() else word for word in path.split('.')]
    target = document
    for token in tokens[:-1]:
        target = target[token]
    target[tokens[-1]] = value


@pytest.mark.parametrize('path', SIGNED_PATHS)
@pytest.mark.parametrize('value', [None, 1e300, 1.25, 2**31, -(2**31) - 1])
def test_signed_report_integers_refuse_before_narrowing(path, value):
    document = copy.deepcopy(SEED)
    replace(document, path, value)
    with pytest.raises((ValueError, OverflowError)) as error:
        edi.ReportModel.from_json(json.dumps(document, allow_nan=False))
    assert str(error.value), (
        'Malformed signed report integers are refused with a diagnostic before conversion'
    )


@pytest.mark.parametrize('path', INDEX_PATHS)
@pytest.mark.parametrize('value', [None, 1e300, 1.25, -2, 2**64, 2**53 + 2])
def test_every_report_index_refuses_invalid_destination_values(path, value):
    document = copy.deepcopy(SEED)
    replace(document, path, value)
    with pytest.raises((ValueError, OverflowError)) as error:
        edi.ReportModel.from_json(json.dumps(document, allow_nan=False))
    assert str(error.value), (
        'Every scene, instance, label and pattern index rejects null, fractional and '
        'out-of-domain values before size_t conversion'
    )


@pytest.mark.parametrize('path', INDEX_PATHS)
def test_report_index_checks_the_platform_size_t_domain(path):
    document = copy.deepcopy(SEED)
    value = 2 ** (8 * ctypes.sizeof(ctypes.c_size_t))
    replace(document, path, value)
    with pytest.raises((ValueError, OverflowError)) as error:
        edi.ReportModel.from_json(json.dumps(document, allow_nan=False))
    assert str(error.value), 'An index outside the actual platform size_t cannot reach a cast'


def test_valid_signed_endpoints_indices_and_pattern_gap_keep_their_integer_identity():
    document = copy.deepcopy(SEED)
    replace(document, SIGNED_PATHS[0], -(2**31))
    replace(document, SIGNED_PATHS[1], 2**31 - 1)
    for path in INDEX_PATHS:
        replace(document, path, -1 if '.series.' in path else 7)
    text = edi.ReportModel.from_json(json.dumps(document)).to_json()
    assert json.loads(text) == document, (
        'The integer gate reaches the real decoder and retains signed endpoints, nonzero '
        'indices and the independently declared -1 pattern-gap sentinel'
    )

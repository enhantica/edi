"""Every offered table has an independent published reference and bundling licence."""

import csv
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
REFERENCES = json.loads((ROOT / 'tests/fixtures/scan_views/maps.json').read_text())
OFFERED = sorted((ROOT / 'data/colormaps').glob('*.tsv'))


def test_scan_offers_multiple_published_maps_without_fixing_the_final_set():
    assert len(OFFERED) > 1, (
        'The palette menu offers several published maps beside its custom ramps'
    )


@pytest.mark.parametrize('path', OFFERED, ids=lambda path: path.stem)
def test_each_offered_map_equals_its_independent_published_table(path):
    reference = REFERENCES.get(path.stem)
    assert reference is not None, (
        'Each offered map needs an independently frozen published table; extend the reference '
        'catalogue when adding a candidate, rather than choosing from a fixed test whitelist'
    )
    assert reference['source'].startswith('https://') and len(reference['source_sha256']) == 64, (
        'Every reference names its published source and the exact producer source bytes'
    )
    assert reference['license'] and reference['license_source'].startswith('https://'), (
        'Every candidate records its independently checked bundling licence and primary text'
    )
    with path.open() as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    assert [int(row['index']) for row in rows] == list(range(len(reference['colours']))), (
        'A complete published map retains every independently indexed sample in order'
    )
    assert [row['colour'].upper() for row in rows] == reference['colours'], (
        'Every offered sample equals the published source table, including interior intensities'
    )
    assert len(set(reference['colours'])) > 1, 'A map must contain a real intensity encoding'

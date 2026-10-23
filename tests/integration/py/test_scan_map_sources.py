"""Every offered table has an independent published reference and bundling licence."""

import csv
import json
from pathlib import Path

import pytest

from tests.fixtures.approved_palettes.reference import lab

ROOT = Path(__file__).resolve().parents[3]
REFERENCES = json.loads((ROOT / 'tests/fixtures/scan_views/maps.json').read_text())
OFFERED = sorted((ROOT / 'data/colormaps').glob('*.tsv'))


def test_scan_retains_all_owner_selected_candidate_maps():
    kept = json.loads((ROOT / 'tests/fixtures/scan_views/offered.json').read_text())
    assert kept['authority'] == 'owner decision 3b42802d3', (
        'The keep-all roster names its committed owner authority'
    )
    assert sorted(path.stem for path in OFFERED) == kept['maps'] and len(kept['maps']) == 28, (
        'Every one of the 28 owner-retained candidate maps remains offered; '
        'source/table correctness is checked independently below'
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


def test_light_ended_candidates_are_offered_without_fixing_their_names():
    light = []
    for path in OFFERED:
        reference = REFERENCES.get(path.stem)
        assert reference is not None, (
            'Light-ended candidates also require independent published tables'
        )
        first, last = reference['colours'][0], reference['colours'][-1]
        if lab(first)[0] >= 0.85 and lab(first)[0] > lab(last)[0]:
            light.append(path.stem)
            assert reference['license'] and reference['license_source'], (
                'Every offered light-ended candidate records its bundling licence'
            )
    assert len(light) >= 2, (
        'The owner comparison offers several light-ended candidates with independently sourced '
        'low-end '
        'Oklab lightness at least 0.85 and a darker high end, without a fixed final catalogue'
    )

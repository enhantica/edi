"""Independent published-colour checks for the older table and legend actors."""

import csv
import json
from pathlib import Path

from tests.fixtures.palette_sources.oklab_reference import contrast, gamut_hue_chroma_preserved


def require_readable_elements(output):
    rows = [
        json.loads(line.partition('LEGACY_ELEMENT ')[2])
        for line in output.splitlines()
        if 'LEGACY_ELEMENT ' in line
    ]
    assert len(rows) == 2 and {row['scheme'] for row in rows} == {'jmol', 'vesta'}, (
        'Both older scheme actors publish their actual table and companion colours'
    )
    source = Path(__file__).parents[1] / 'e04_t10/published-elements.tsv'
    with source.open() as stream:
        published = {row['symbol']: row for row in csv.DictReader(stream, delimiter='\t')}
    for row in rows:
        assert row['symbol'] == 'La', (
            'The older GUI actors retain their independent lanthanum input'
        )
        original = published[row['symbol']][row['scheme']]
        assert len(row['consumers']) == 2, (
            'Both real element consumers supply independent receipts'
        )
        for consumer in row['consumers']:
            actual, backgrounds = consumer['colour'], consumer['backgrounds']
            assert backgrounds, 'A flat element colour has an observed drawing background'
            assert all(contrast(actual, background) >= 2 for background in backgrounds), (
                'Every flat element consumer reaches strict 2:1 contrast on all its underlays'
            )
            if all(contrast(original, background) >= 2 for background in backgrounds):
                assert actual.lower() == original.lower(), (
                    'Published element bytes already readable on all underlays stay unchanged'
                )
            else:
                assert gamut_hue_chroma_preserved(original, actual), (
                    'Adjusted elements preserve hue and all chroma that remains inside sRGB'
                )

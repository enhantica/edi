"""Dictionary-formatted computed columns; closed-form P1 cancellation supplies zero."""

import json
import re
import shutil
from pathlib import Path

import edi

from tests.fixtures.dictionary_display.reference import display

ROOT = Path(__file__).resolve().parents[3]


def test_reflection_columns_have_fixed_decimals_and_no_exponents_in_model_and_html(tmp_path):
    source = tmp_path / 'equal_sites'
    shutil.copytree(ROOT / 'tests/fixtures/loop_parameter_ids/line-segment', source)
    structure = source / 'structures/phase.edi'
    text = structure.read_text().replace(
        'A La a Biso 0.17 0.23 0.31 0.7 0.3', 'A La a Biso 0 0 0 1 0'
    )
    text = text.replace('B La a Biso 0.17 0.23 0.31 0.3 0.8', 'B La a Biso 0.5 0.5 0.5 1 0')
    structure.write_text(text)
    loaded = edi.Project.load(source)
    loaded.calculate()
    assert hasattr(loaded, 'report'), (
        'The computed-column seam reaches the production report model and HTML writer'
    )
    document = json.loads(loaded.report.model().to_json())
    categories = document['experiments'][0]['categories']
    matches = [part['table'] for part in categories if part['id'] == 'refln']
    assert len(matches) == 1, (
        'The independently calculated P1 project supplies exactly one Reflections table'
    )
    table = matches[0]
    assert len(table['rows']) >= 2, (
        'The fixed-precision witness contains multiple physical reflection rows'
    )
    assert all(len(row) == len(table['columns']) for row in table['rows']), (
        'Every reflection row supplies every declared table column'
    )
    html = loaded.report.as_html()
    checked = 0
    zero_seen = False
    for index in range(3, len(table['columns'])):
        cells = [row[index] for row in table['rows']]
        if not all(re.fullmatch(r'[-+]?\d+(?:\.\d*)?(?:[eE][-+]?\d+)?', value) for value in cells):
            continue
        checked += 1
        # Before: all computed columns were fixed decimals. Intensities now use
        # significant digits; d-spacing and angles retain their dictionary fixed formats.
        heading = str(table['columns'][index]).lower()
        if 'intens' in heading or '|f|' in heading or 'f²' in heading:
            assert all(value == display(float(value), 'significant', 5) for value in cells), (
                'Computed intensities use the dictionary significant-digit format'
            )
        else:
            assert all('e' not in value.lower() for value in cells), (
                'Dictionary fixed-format reflection quantities retain decimal notation'
            )
            precision = {len(value.partition('.')[2]) for value in cells if float(value) != 0}
            assert len(precision) <= 1, (
                'Fixed-format reflection columns retain consistent decimal precision'
            )
        zero_seen |= any(value == '0' for value in cells)
        assert all(value in html for value in cells), (
            'The HTML writer retains the exact computed-column text used by the preview model'
        )
    assert checked >= 2, (
        'The precision gate reaches multiple computed reflection quantities beyond h, k and l'
    )
    assert zero_seen, (
        'Closed-form odd-index P1 cancellation is shown as zero rather than a tiny exponent'
    )

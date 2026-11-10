"""Fixed computed columns against a two-site P1 structure-factor closed form."""

import json
import re
import shutil
from pathlib import Path

import edi

ROOT = Path(__file__).resolve().parents[3]


def check_phase_sum(rows, index, indices):
    for row in rows:
        odd = sum(int(row[indices[k]]) for k in ('h', 'k', 'l')) % 2
        # Sears La is 8.24 fm, or 0.824 in the reported 10^-12 cm units.
        # The phase sum of sites separated by (1/2,1/2,1/2) is 0 or 2b.
        amplitude = 0.0 if odd else 2 * 8.24 / 10
        expected = amplitude if index == indices['F calc'] else amplitude**2
        assert row[index] == format(expected, '.3f'), (
            'F and F squared match the independent two-site phase-sum closed form'
        )


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
    indices = {name: table['columns'].index(name) for name in ('h', 'k', 'l', 'F calc', 'F² calc')}
    checked = 0
    zero_seen = False
    for index in range(3, len(table['columns'])):
        cells = [row[index] for row in table['rows']]
        if not all(re.fullmatch(r'[-+]?\d+(?:\.\d*)?(?:[eE][-+]?\d+)?', value) for value in cells):
            continue
        checked += 1
        assert all('e' not in value.lower() for value in cells), (
            'Computed reflection columns use fixed decimals without exponent notation'
        )
        precision = {len(value.partition('.')[2]) for value in cells if float(value) != 0}
        assert len(precision) <= 1, (
            'Every computed reflection column retains one decimal precision for all nonzero rows'
        )
        if index in {indices['F calc'], indices['F² calc']}:
            assert precision == {3}, 'F and F squared use the owner fixed-three report precision'
            check_phase_sum(table['rows'], index, indices)
        zero_seen |= index in {indices['F calc'], indices['F² calc']} and any(
            float(value) == 0 for value in cells
        )
        assert all(value in html for value in cells), (
            'The HTML writer retains the exact computed-column text used by the preview model'
        )
    assert checked >= 2, (
        'The precision gate reaches multiple computed reflection quantities beyond h, k and l'
    )
    assert zero_seen, (
        'Closed-form odd-index P1 cancellation is shown as zero rather than a tiny exponent'
    )

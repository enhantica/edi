"""Independent case rule and strict records for rendered application captions."""

import math
import re

SYMBOLS = re.compile(
    r'^(?:2θ|\u03c7²|\u03bb|TOF|s\.u\.|h k l|μR|\u03c3[₀₁₂]²|x[123]{2}|[abcdfhklqrxyz]|'
    r'[\u03b1-\u03b3\u03c6\u03b8][₀-₉0-9⁰¹²³⁴⁵⁶⁷⁸⁹]*)(?=$|[\s(:/\u2032])'
)


def check_caption(text):
    first = next((char for char in text if char.isalpha()), '')
    return not first or first.isupper() or bool(SYMBOLS.match(text))


def caption_problems(rows):
    if not isinstance(rows, list) or not rows:
        return ['Rendered caption census is empty or malformed']
    problems = []
    for row in rows:
        if not isinstance(row, dict) or row.keys() != {
            'kind',
            'owner',
            'slot',
            'text',
            'width',
            'height',
            'enabled',
        }:
            problems.append('Rendered caption record has missing or foreign fields')
            continue
        name = str(row['owner'])
        if (
            not isinstance(row['kind'], str)
            or row['kind'] not in {'field', 'group', 'header'}
            or not isinstance(row['owner'], str)
            or not name
        ):
            problems.append(name + ': unknown or unnamed caption role')
        if (
            not isinstance(row['slot'], int)
            or isinstance(row['slot'], bool)
            or row['slot'] < 0
            or not isinstance(row['enabled'], bool)
        ):
            problems.append(name + ': malformed caption identity or enabled state')
        if not isinstance(row['text'], str) or not row['text'].strip():
            problems.append(name + ': missing painted caption')
            continue
        if not all(
            isinstance(row[key], (int, float))
            and not isinstance(row[key], bool)
            and math.isfinite(row[key])
            and row[key] > 0
            for key in ('width', 'height')
        ):
            problems.append(name + ': caption has no finite painted area')
        if not check_caption(row['text']):
            problems.append(name + ': lowercase prose ' + repr(row['text']))
    return problems

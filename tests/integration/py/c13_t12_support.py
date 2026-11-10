"""independent STAR token accounting; never imports a product decoder."""

import re
from pathlib import Path

import pytest
import test_c13_t12_loop_identity as loops

engine = loops.engine
ROOT = Path(__file__).resolve().parents[3]
IDENTITY_TAGS = {
    '_atom_site.id',
    '_atom_site_label',
    '_atom_site_aniso_label',
    '_scattering_length.type_symbol',
    '_linked_structure.structure_id',
    '_pd_phase_block.id',
    '_preferred_orientation.structure_id',
    '_background.id',
    '_pd_background.id',
    '_excluded_region.id',
    '_easydiffraction_excluded_region.id',
    '_data.id',
    '_pd_data.point_id',
    '_data_calc.point_id',
    '_joint_fit.experiment_id',
    '_sequential_fit_extract.id',
    '_fit_parameter.id',
}
# Hand transcribed from CIF 1.1 paragraphs 9-19, 22-25 + packet D6 precedence.
SPELLINGS = [
    ('X', 'X'),
    ('X Y', "'X Y'"),
    ('X\tY', "'X\tY'"),
    ('_x', "'_x'"),
    ('#x', "'#x'"),
    ('$x', "'$x'"),
    ('[x', "'[x'"),
    (']x', "']x'"),
    (';x', "';x'"),
    ('data_a', "'data_a'"),
    ('DaTa_a', "'DaTa_a'"),
    ('loop_', "'loop_'"),
    ('save_a', "'save_a'"),
    ('stop_', "'stop_'"),
    ('global_', "'global_'"),
    ('?', "'?'"),
    ('.', "'.'"),
    ("''", "''''"),
    ("'X'", "''X''"),
    ('"X"', '\'"X"\''),
    ("X'Y", "X'Y"),
    ('X"Y', 'X"Y'),
    ("a' b", '"a\' b"'),
    ('a" b', "'a\" b'"),
    ('', "''"),
]
BAD_IDS = [
    ('LF', 'bad\nid'),
    ('CR', 'bad\rid'),
    ('NUL', 'bad\0id'),
    ('control', 'bad\x01id'),
    ('DEL', 'bad\x7fid'),
    ('non-ASCII', 'bäd'),
    ('single-line', 'a\' b" c'),
]
BAD_NAMES = [
    'C:bank',
    'c:bank',
    'D:bank',
    '\\\\srv\\share',
    '/abs',
    'a/b',
    'a\\b',
    '.',
    '..',
    'bank.',
    'bank.1',
    'bank ',
    'WISH_1~1',
    'con',
    'NUL',
    'com1',
    'Lpt9',
    'bänk',
]


def tokens(text):
    """Lossless lexemes and decoded values; CIF quotes close only before whitespace."""
    result = []
    index = 0
    while index < len(text):
        if text[index].isspace():
            index += 1
            continue
        if text[index] == '#':
            end = text.find('\n', index)
            index = len(text) if end < 0 else end + 1
            continue
        start = index
        quote = text[index] if text[index] in '\'"' else None
        if quote:
            index += 1
            while index < len(text):
                if text[index] == quote and (index + 1 == len(text) or text[index + 1].isspace()):
                    index += 1
                    break
                index += 1
            else:
                message = 'unterminated CIF quote'
                raise ValueError(message)
        elif text[index] == ';' and (index == 0 or text[index - 1] == '\n'):
            end = text.find('\n;', index + 1)
            if end < 0:
                message = 'unterminated CIF text field'
                raise ValueError(message)
            index = end + 2
        else:
            while index < len(text) and not text[index].isspace():
                index += 1
        raw = text[start:index]
        value = raw[1:-1] if quote else raw
        result.append((raw, value, start, index))
    return result


def identity_positions(lexemes):
    positions = set()
    i = 0
    while i < len(lexemes):
        if lexemes[i][0].lower() != 'loop_':
            i += 1
            continue
        i += 1
        tags = []
        while i < len(lexemes) and lexemes[i][0].startswith('_'):
            tags.append(lexemes[i][0])
            i += 1
        if not tags:
            message = 'empty loop'
            raise ValueError(message)
        row_start = i
        while i < len(lexemes):
            raw = lexemes[i][0]
            if raw.startswith('_') or raw.lower().startswith('data_') or raw.lower() == 'loop_':
                break
            if tags[(i - row_start) % len(tags)] in IDENTITY_TAGS:
                positions.add(i)
            i += 1
        if (i - row_start) % len(tags):
            message = 'incomplete loop row'
            raise ValueError(message)
    return positions


def delimiter_only(before, after):
    """Only equal decoded ID tokens may differ; gaps/comments and all other bytes stay exact."""
    a, b = tokens(before), tokens(after)
    if len(a) != len(b):
        return False
    ids_a, ids_b = identity_positions(a), identity_positions(b)
    if ids_a != ids_b:
        return False
    previous_a = previous_b = 0
    for i, (left, right) in enumerate(zip(a, b, strict=True)):
        if before[previous_a : left[2]] != after[previous_b : right[2]]:
            return False
        if left[0] != right[0] and (i not in ids_a or left[1] != right[1]):
            return False
        previous_a, previous_b = left[3], right[3]
    return before[previous_a:] == after[previous_b:]


def snapshot(root):
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob('*'))
        if p.is_file()
    }


def project(tmp_path):
    return loops._load(tmp_path, 'data', 'project')[0]


def named(action, identity, category=None):
    with pytest.raises((ValueError, RuntimeError)) as caught:
        action()
    message = str(caught.value)
    assert identity in message, ' refusal must name the supplied identity'
    if category:
        assert category.lower() in message.lower(), ' refusal must name the identity category'
    return message


def normalized_record(path, data):
    # Existing wall-clock contract: compare the exact record except these generated dates.
    if path == 'project.edi':
        return re.sub(
            rb'(?m)^(_metadata\.(?:created|last_modified)\s+)[^\n]*', rb'\1<WALL-CLOCK>', data
        )
    return data


def case_id(value):
    """Keep literal inputs unchanged while giving timing tools compact node ids."""
    return value.replace(' ', '%20') if isinstance(value, str) and ' ' in value else None

"""Literal CIF 1.1 lexemes and their independently authored record shape."""

TOKENS = (
    '?',
    '.',
    "'?'",
    '"?"',
    "'.'",
    '"."',
    "'two words'",
    '"quoted words"',
    ';?\n;',
    ';.\n;',
    ';single line with spaces\n;',
    ';"first\nlast"\n;',
    ';\nbody  \n\nlast \t \n;',
    "'loop_'",
    '"data_literal"',
    "'a\"b'",
    '"a\'b"',
)


def declarations():
    scalar = []
    expected = []
    for index, token in enumerate(TOKENS):
        name = f'_iso_contract_scalar_{index}'
        scalar.append(name + '\n' + token + '\n')
        expected.append({'names': [name], 'rows': [[token]], 'loop': False})
    cut = 5
    names = ['_iso_contract_loop.id', '_iso_contract_loop.token']
    loop = 'loop_\n' + '\n'.join(names) + '\n'
    rows = []
    for index, token in enumerate(TOKENS):
        row = [f'row{index}', token]
        rows.append(row)
        loop += '\n'.join(row) + '\n'
    expected.insert(cut, {'names': names, 'rows': rows, 'loop': True})
    return ''.join(scalar[:cut]) + loop + ''.join(scalar[cut:]), expected

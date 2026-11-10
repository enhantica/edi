# SPDX-License-Identifier: BSD-3-Clause
"""Names from the closed ASCII contract and Windows' documented device namespace."""

import itertools
import string

DEVICES = (
    'CON',
    'PRN',
    'AUX',
    'NUL',
    *(f'COM{index}' for index in range(1, 10)),
    *(f'LPT{index}' for index in range(1, 10)),
    *(prefix + digit for prefix in ('COM', 'LPT') for digit in '¹²³'),
    'CONIN$',
    'CONOUT$',
)
EXTENSIONS = ('', '.', '.txt', '.EDI', '.tar.gz')


def device_names():
    for device in DEVICES:
        choices = [
            (letter.lower(), letter.upper()) if letter.isalpha() else (letter,)
            for letter in device
        ]
        for spelling in itertools.product(*choices):
            for extension in EXTENSIONS:
                yield ''.join(spelling) + extension


def excluded_names():
    allowed = set(string.ascii_letters + string.digits + '._-')
    yield from ('', '.', '..', '.hidden', 'a' * 256, 'unicode-é', 'unicode-☃')
    for code in range(128):
        if chr(code) not in allowed:
            yield 'left' + chr(code) + 'right'


VALID = ('reference-7', 'Sample_2.edi', 'Concorde', 'nulled')

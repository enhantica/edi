"""Freeze independent Sasaki table brackets for the synchrotron reference."""

import argparse
import hashlib
import json
import re
from pathlib import Path

TABLE_SHA256 = '366fd51e8ffbbde89fe86fd536761fd43ea6f9a797c9f2d62f9ce59b2f5157bb'
ELEMENTS = ['La', 'Ti', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'O']


def freeze(table):
    raw = table.read_bytes()
    if hashlib.sha256(raw).hexdigest() != TABLE_SHA256:
        raise ValueError('The independent Sasaki wide table must match its recorded source')
    brackets, current, real = {}, None, None
    for text in raw.decode().splitlines():
        symbol = re.match(r'\s*ATOMIC SYMBOL =\s*(\w+)', text)
        if symbol:
            current = symbol[1].capitalize()
            real = None
        first = re.match(r"\s*0\.20 TO\s+0\.29 F'\s+(.*)", text)
        if first:
            real = [float(value) for value in first[1].split()[:2]]
        imaginary = re.match(r'\s*F"\s+(.*)', text)
        if imaginary and current in ELEMENTS and first is None and real is not None:
            brackets.setdefault(
                current,
                {
                    'wavelength_angstrom': [0.20, 0.21],
                    'f_prime': real,
                    'f_double_prime': [float(value) for value in imaginary[1].split()[:2]],
                },
            )
            real = None
    if set(brackets) != set(ELEMENTS):
        raise ValueError('Every synchrotron scatterer needs independent tabulated brackets')
    wavelength = 0.207109
    fraction = (1 / wavelength - 1 / 0.20) / (1 / 0.21 - 1 / 0.20)
    return {
        'source': 'Sasaki (1989), KEK Report 88-14, cctbx reference/sasaki/fpwide.tbl',
        'source_url': 'https://github.com/cctbx/cctbx_project/blob/master/cctbx/reference/sasaki/fpwide.tbl',
        'table_sha256': TABLE_SHA256,
        'interpolation': 'linear in photon energy between independent table nodes',
        'case': 'pd-xray-cwl_lam7o3-p021',
        'experiment': 'p021',
        'dispersion_source': 'sasaki1989',
        'wavelength_angstrom': wavelength,
        'brackets': {element: brackets[element] for element in ELEMENTS},
        'values': {
            element: [
                pair[0] + fraction * (pair[1] - pair[0])
                for pair in [brackets[element]['f_prime'], brackets[element]['f_double_prime']]
            ]
            for element in ELEMENTS
        },
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--table', type=Path, required=True)
    args = parser.parse_args()
    Path(__file__).with_name('synchrotron-dispersion.json').write_text(
        json.dumps(freeze(args.table), indent=2) + '\n'
    )

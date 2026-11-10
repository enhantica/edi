import ast
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
# Independent manual transcription of natural-element (or first carrier isotope)
# b_c in ILL 2003 Table 2, PDF pages 14--23. No product data is read.
book = {
    'H': -3.7409,
    'He': 3.26,
    'Li': -1.9,
    'Be': 7.79,
    'B': 5.3,
    'C': 6.6484,
    'N': 9.36,
    'O': 5.805,
    'F': 5.654,
    'Ne': 4.566,
    'Na': 3.63,
    'Mg': 5.375,
    'Al': 3.449,
    'Si': 4.15071,
    'P': 5.13,
    'S': 2.847,
    'Cl': 9.5792,
    'Ar': 1.909,
    'K': 3.67,
    'Ca': 4.7,
    'Sc': 12.1,
    'Ti': -3.37,
    'V': -0.443,
    'Cr': 3.635,
    'Mn': -3.75,
    'Fe': 9.45,
    'Co': 2.49,
    'Ni': 10.3,
    'Cu': 7.718,
    'Zn': 5.68,
    'Ga': 7.288,
    'Ge': 8.185,
    'As': 6.58,
    'Se': 7.97,
    'Br': 6.79,
    'Kr': 7.81,
    'Rb': 7.08,
    'Sr': 7.02,
    'Y': 7.75,
    'Zr': 7.16,
    'Nb': 7.054,
    'Mo': 6.715,
    'Tc': 6.8,
    'Ru': 7.02,
    'Rh': 5.9,
    'Pd': 5.91,
    'Ag': 5.922,
    'Cd': 4.83,
    'In': 4.065,
    'Sn': 6.225,
    'Sb': 5.57,
    'Te': 5.68,
    'I': 5.28,
    'Xe': 4.69,
    'Cs': 5.42,
    'Ba': 5.07,
    'La': 8.24,
    'Ce': 4.84,
    'Pr': 4.58,
    'Nd': 7.69,
    'Pm': 12.6,
    'Sm': 0.0,
    'Eu': 5.3,
    'Gd': 9.5,
    'Tb': 7.34,
    'Dy': 16.9,
    'Ho': 8.44,
    'Er': 7.79,
    'Tm': 7.07,
    'Yb': 12.41,
    'Lu': 7.21,
    'Hf': 7.77,
    'Ta': 6.91,
    'W': 4.755,
    'Re': 9.2,
    'Os': 10.7,
    'Ir': 10.6,
    'Pt': 9.6,
    'Au': 7.9,
    'Hg': 12.595,
    'Tl': 8.776,
    'Pb': 9.401,
    'Bi': 8.532,
    'Ra': 10.0,
    'Th': 10.31,
    'Pa': 9.1,
    'U': 8.417,
    'Np': 10.55,
    'Pu': 7.7,
    'Am': 8.3,
    'Cm': 9.5,
    '157Gd': 4.0,
}
nsf = root / 'libraries/periodictable/periodictable/nsf.py'
tree = ast.parse(nsf.read_text())
table = next(
    ast.literal_eval(n.value)
    for n in tree.body
    if isinstance(n, ast.Assign)
    and any(isinstance(t, ast.Name) and t.id == 'nsftable' for t in n.targets)
)


def number(text):
    return float(text.split('(')[0].replace('*', '')) if text else None


carrier = {}
for line in table.splitlines():
    cols = line.split(',')
    parts = cols[0].split('-')
    sym = parts[1]
    if sym == 'n':
        continue
    val = number(cols[3])
    if val is None:
        continue
    if sym not in carrier or len(parts) == 2:
        carrier[sym] = [val, number(cols[10]) or 0]
    if cols[0] == '64-Gd-157':
        carrier['157Gd'] = [val, number(cols[10])]
updates = {
    'He': (3.0985, 'Haun', '2020', '10.1103/PhysRevLett.124.012501'),
    'Li': (-1.93, 'Gehlhaar', '2025', '10.1088/1361-648X/add3a6'),
    'C': (6.6472, 'Snow', '2020', '10.1103/PhysRevD.101.062004'),
    'O': (5.8037, 'Snow', '2020', '10.1103/PhysRevD.101.062004'),
    'Pr': (4.44, 'Gehlhaar', '2026', '10.1088/1361-648X/ae1ec0'),
    'Nd': (7.87, 'Gehlhaar', '2026', '10.1088/1361-648X/ae1ec0'),
    'Sn': (6.2239, 'Snow', '2020', '10.1103/PhysRevD.101.062004'),
    'Pb': (9.4024, 'Snow', '2020', '10.1103/PhysRevD.101.062004'),
    'Bi': (8.5242, 'Snow', '2020', '10.1103/PhysRevD.101.062004'),
}
rows = {}
assert set(carrier) == set(book), 'independent carrier and booklet coverage differ'
for key, base in book.items():
    value = updates[key][0] if key in updates else base
    assert carrier[key][0] == value, (key, carrier[key], value)
    rows[key] = {
        'b_real_fm': round(value, 4),
        'b_imag_fm': round(-carrier[key][1] / 3596, 4),
        'booklet_b_real_fm': base,
        'absorption_barn': carrier[key][1],
        'publication': list(updates[key][1:])
        if key in updates
        else ['Rauch', 'Waschkowski', '2003'],
    }
# Compare at the served table's precision: Si's rounding is not an extension.
extended = [
    element
    for element, row in rows.items()
    if row['b_real_fm'] != round(row['booklet_b_real_fm'], 4)
]
fixture = {
    'source': 'rauch2003ext',
    'booklet_sha256': ('4a632ba0a155275c6c39090f14cf29448dce10548f2676a728a4b9485a173e94'),
    'carrier_nsf_sha256': hashlib.sha256(nsf.read_bytes()).hexdigest(),
    'extended_elements': extended,
    'rows': rows,
}
(Path(__file__).parent / 'rauch2003ext.json').write_text(json.dumps(fixture, indent=2) + '\n')

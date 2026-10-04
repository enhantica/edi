"""Extract independent Sasaki rows and transcribe signed IT Vol C p.255 values.

Usage: python generate_named_dispersion.py LIBRARIES_ROOT VOL_C_PDF
Sasaki: KEK Report 88-14 (1989), cctbx/reference/sasaki/README.
IT1992: Table 4.2.6.8, printed p.255 (PDF page 283). Signs visually checked;
pdftotext drops them. No product imports or product data are read.
"""

import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
corpus = Path(sys.argv[1])
pdf = Path(sys.argv[2])
wide = corpus / 'cctbx/cctbx/reference/sasaki/fpwide.tbl'
edge = corpus / 'cctbx/cctbx/reference/sasaki/fpk.tbl'
raw = wide.read_text()


def rows(symbol):
    section = raw.split('ATOMIC SYMBOL = ' + symbol.upper() + ' ', 1)[1]
    lines = section.split('ATOMIC SYMBOL', 1)[0].splitlines()
    values = {}
    for index, line in enumerate(lines):
        if ' TO ' in line:
            fields = line.split()
            start = float(fields[0])
            for offset, (fp, fpp) in enumerate(
                zip(fields[4:], lines[index + 1].split()[1:], strict=True)
            ):
                values[round(start + offset / 100, 2)] = [float(fp), float(fpp)]
    return values


sas = {symbol: rows(symbol) for symbol in ('Li', 'F', 'Fe')}
selected = [[symbol, wave, *sas[symbol][wave]] for symbol in sas for wave in (0.71, 1.23, 1.54)]
# ADR-0066: f-prime linear in log energy; f-double-prime log-log.
for wave in (1.2325, 1.2375):
    lo, hi = sas['Fe'][1.23], sas['Fe'][1.24]
    t = math.log(wave / 1.23) / math.log(1.24 / 1.23)
    selected.append([
        'Fe',
        wave,
        lo[0] + t * (hi[0] - lo[0]),
        math.exp(math.log(lo[1]) + t * math.log(hi[1] / lo[1])),
    ])
edge_header = next(
    line for line in edge.read_text().splitlines() if re.match(r'ATOMIC SYMBOL = FE\s', line)
)
# 1.74345 lies between the 1.7434/1.7435 fine-grid rows around the declared 1.74346 edge.
it_wave = [
    2.748510,
    2.289620,
    1.935970,
    1.788965,
    1.540520,
    0.709260,
    0.559360,
    0.215947,
    0.209010,
    0.180195,
]
it_fp = [-0.8901, -1.2935, -2.0554, -3.3307, -1.1336, 0.3463, 0.2886, 0.0438, 0.0386, 0.0173]
it_fpp = [1.0521, 0.7620, 0.5649, 0.4901, 3.1974, 0.8444, 0.5448, 0.0840, 0.0787, 0.0582]
it = [['Fe', wave, fp, fpp] for wave, fp, fpp in zip(it_wave, it_fp, it_fpp, strict=True)]
for name, values in [('sasaki1989', selected), ('it1992', it)]:
    (ROOT / (name + '_reference.tsv')).write_text(
        ''.join(f'{el} {wave:.17g} {fp:.17g} {fpp:.17g}\n' for el, wave, fp, fpp in values)
    )
manifest = {
    'libraries_commit': '57d1cf5fcad9ba4fd86224eb4047af35214766cd',
    'physics_commit': '8d835ab60b82ec3aae549927fd048f57d915dfe6',
    'sources': {
        str(path.relative_to(corpus))
        if path != pdf
        else 'InternationalTables_VolC.pdf': hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (wide, edge, pdf)
    },
    'sasaki_edge_header': edge_header,
    'sasaki_edge_refusal': 1.74345,
    'sasaki_interpolation_rows': [[1.23, *sas['Fe'][1.23]], [1.24, *sas['Fe'][1.24]]],
    'sasaki_rows': selected,
    'it1992_rows': it,
    'it1992_signed_source': 'Visually checked printed p.255, PDF page 283, Table 4.2.6.8',
}
(ROOT / 'named_dispersion.json').write_text(json.dumps(manifest, indent=2) + '\n')

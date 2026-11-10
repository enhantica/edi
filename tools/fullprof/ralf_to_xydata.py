# SPDX-License-Identifier: BSD-3-Clause
"""Convert a FullProf RALF (GSAS ALT) TOF data file to plain X-Y-sigma ``XYDATA``.

FullProf's RALF reader (``Ins = 12``) weights ``Ceo2_PEARL`` with sigma 100x too large relative
to the intensity it normalises, so the fit's chi2 prints 1e4 too small. Plain ``XYDATA``
(``Ins = 10``) carries the same data with the file's own sigma:

- X is the RALF time of flight in its native unit of 1/32 microsecond, divided by 32;
- Y is the observed intensity FullProf itself read from the RALF file (the ``Iobs`` column of a
  RALF run's ``Prf = 2`` IGOR ``.prf``, FullProf's highest-precision print of it), so FullProf's
  per-point normalisation is kept;
- sigma is the RALF sigma scaled by that same point's normalisation factor Y / I.

FullProf's factor is 32 / (10 * dt) with dt the FORWARD bin width in RALF units (measured on
this file: the IGOR Iobs agree with it to 0.01, the print resolution). The last point has no
following edge, so FullProf does not read it; it is kept with dt = (the header's dt/t) * TOF, the
ALT binning rule every other log-binned width follows to one raw unit (so that point's Y carries
~1.6e-3 relative uncertainty) -- the one value here that FullProf did not produce.

The RALF triples are read here from the fixed-width records, independently of FullProf.

Usage: ``python tools/fullprof/ralf_to_xydata.py <ralf> <ralf-run.prf> <out.dat>``
"""

import sys
from pathlib import Path

_TRIPLE_WIDTH = 20
_HEADER = (
    'XYDATA  CeO2 (NBS SRM 674a) from PEARL at ISIS, converted from RALF\n'
    '  X = RALF TOF / 32 (microseconds); Y = FullProf RALF-read Iobs; sigma = RALF sigma * Y / I\n'
    '  Last point (not read by FullProf): Y = I * 32 / (10 * dt), dt = header dt/t * TOF\n'
    '  Converted by tools/fullprof/ralf_to_xydata.py; original bytes: Ceo2_PEARL.ralf\n'
    'INTER   1.0   1.0   0  0\n'
    'TEMP    0.0\n'
)


def read_ralf(text: str) -> list[tuple[int, int, int]]:
    """Return the (TOF*32, I, sigma) integer triples of a single-bank RALF ALT file."""
    return _read(text)[0]


def ralf_dt_over_t(text: str) -> float:
    """Return the constant bin-width ratio dt/t the RALF ALT header declares."""
    return _read(text)[1]


def _read(text: str) -> tuple[list[tuple[int, int, int]], float]:
    lines = text.splitlines()
    bank = lines[1].split()
    if bank[0] != 'BANK' or bank[4] != 'RALF' or bank[-1] != 'ALT':
        msg = f'not a RALF ALT bank header: {lines[1]!r}'
        raise ValueError(msg)
    count = int(bank[2])
    triples = []
    for line in lines[2:]:
        for start in range(0, len(line), _TRIPLE_WIDTH):
            field = line[start : start + _TRIPLE_WIDTH]
            if field.strip():
                triples.append((int(field[0:8]), int(field[8:15]), int(field[15:20])))
    if len(triples) != count:
        msg = f'RALF header declares {count} points, records hold {len(triples)}'
        raise ValueError(msg)
    return triples, float(bank[8])


def read_prf_yobs(text: str) -> list[tuple[float, float]]:
    """Return (TOF, Iobs) from the first wave block of a FullProf IGOR ``.prf`` (``Prf = 2``)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != 'IGOR':
        msg = 'expected a Prf = 2 (IGOR) .prf'
        raise ValueError(msg)
    rows = []
    for line in lines[lines.index('BEGIN') + 1 :]:
        if line.strip() == 'END':
            break
        cells = line.split()
        rows.append((float(cells[0]), float(cells[1])))
    return rows


def convert(ralf_text: str, prf_text: str) -> str:
    """Return the ``XYDATA`` file text for a RALF file and the ``.prf`` of a run over it."""
    triples = read_ralf(ralf_text)
    observed = read_prf_yobs(prf_text)
    if not observed or len(observed) > len(triples):
        msg = f'.prf holds {len(observed)} points for {len(triples)} RALF points'
        raise ValueError(msg)
    dt_over_t = ralf_dt_over_t(ralf_text)
    out = [_HEADER]
    for i, (tof32, intensity, sigma) in enumerate(triples):
        x = tof32 / 32
        if i < len(observed):
            x_prf, y = observed[i]
            if abs(x - x_prf) > 1e-3:
                msg = f'.prf point at {x_prf} does not match RALF point at {x}'
                raise ValueError(msg)
        else:
            y = intensity * 32 / (10 * dt_over_t * tof32)
        out.append(f'{x:14.5f} {y:14.6f} {sigma * y / intensity:14.6f}\n')
    return ''.join(out)


def main(argv: list[str]) -> int:
    ralf, prf, dest = (Path(a) for a in argv)
    dest.write_text(convert(ralf.read_text(), prf.read_text()))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))

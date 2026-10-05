"""Archive the one owner-supplied FullProf run and its inactive all-fixed twin."""

import argparse
import hashlib
import shutil
from pathlib import Path


def all_fixed(text):  # noqa: PLR0912 -- follow the supplied PCR record order
    """Zero this input's explicitly labelled parameter codes, preserving values."""
    lines = text.splitlines()
    backgrounds = False
    code_after_value = 0
    calibration = False
    for index, line in enumerate(lines):
        if '!Number of ' in line:
            lines[index] = '       0    !' + line.partition('!')[2]
        elif line.startswith('!'):
            backgrounds = line.startswith('!2Theta/TOF/E(Kev)')
            calibration = line.startswith('!    Zero ')
            if any(
                name in line
                for name in (
                    '!Atom   Typ',
                    '!  Scale ',
                    '!      Sigma-2',
                    '!      Gamma-2',
                    '# Cell Info',
                    '!      Pref1',
                )
            ):
                code_after_value = 2
        elif line.strip() == 'VARY backgd':
            lines[index] = '! Background variation disabled in the all-fixed twin'
        elif line.strip():
            fields = line.split()
            if backgrounds:
                if len(fields) != 3:
                    raise ValueError('Every background record must have value and code')
                fields[2] = '0.00'
                lines[index] = ' '.join(fields)
            elif calibration:
                if len(fields) != 9:
                    raise ValueError('The TOF calibration must retain four value/code pairs')
                for column in (1, 3, 5, 7):
                    fields[column] = '0.00'
                lines[index] = ' '.join(fields)
                calibration = False
            elif code_after_value:
                code_after_value -= 1
                if not code_after_value:
                    lines[index] = ' '.join('0.00' for _ in fields)
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fitting-home', type=Path, required=True)
    parser.add_argument('--verification-home', type=Path, required=True)
    parser.add_argument('--executable', type=Path, required=True)
    args = parser.parse_args()
    source, target = args.fitting_home, args.verification_home
    stem = 'duplex_mode6-IRF'
    required = (
        'owner-input.inp',
        'full-fit.inp',
        'full-fit.out',
        f'{stem}.pcr',
        f'{stem}.new',
        f'{stem}.sum',
        f'{stem}.out',
        f'{stem}_1.prf',
        f'{stem}_2.prf',
        'Duplex_in_HR_for_IRF_S2.dat',
        'Duplex_in_HR_for_IRF_N2.dat',
    )
    if any(not (source / name).is_file() for name in required):
        raise ValueError('The single authoring run must produce both complete bank outputs')
    if hashlib.sha256((source / 'owner-input.inp').read_bytes()).hexdigest() != (
        'e98108ee023e02a470ba9b9a7c46fe32a27eb6a1c0b979802623e1c63ffd3f26'
    ):
        raise ValueError('This capture only supports the exact owner-supplied input')
    prepared = (
        (source / 'owner-input.inp')
        .read_text()
        .replace('../duplex_mode6/', '')
        .replace('   1   1   0   0   0   0\n', '   1   2   0   0   0   0\n')
    )
    if (source / 'full-fit.inp').read_text() != prepared:
        raise ValueError('Only data paths and the input-preservation flag may change')
    summary = (source / f'{stem}.sum').read_text()
    if 'Version 8.40 - Feb2026-ILL JRC' not in summary:
        raise ValueError('The archived run must identify its FullProf version')
    if 'Normal end, final calculations and writing' not in (source / 'full-fit.out').read_text():
        raise ValueError('The captured authoring invocation must have ended normally')
    target.mkdir(parents=True, exist_ok=False)
    (target / f'{stem}.pcr').write_text(all_fixed((source / f'{stem}.new').read_text()))
    # These are the single fitting run's final profiles, explicitly not another run.
    for name in (f'{stem}_1.prf', f'{stem}_2.prf', f'{stem}.sum'):
        shutil.copyfile(source / name, target / name)
    for bank in ('S2', 'N2'):
        name = f'Duplex_in_HR_for_IRF_{bank}.dat'
        (target / name).symlink_to((source / name).readlink())
    common = """Owner-supplied BEER duplex project: ferrite and austenite, two neutron
TOF banks at 90 degrees, Npr 7 pseudo-Voigt. This archive is INACTIVE: no
test, fitting-corpus entry or verification page compares against it. It will
be activated only when shared site-parameter constraints are available.

FullProf.2k 8.40 (Feb2026-ILL JRC). Executable: `~/Applications/fullprof/fp2k`.
One authoring-time invocation, in the fitting home:
`printf 'duplex_mode6-IRF\\n\\n' | ~/Applications/fullprof/fp2k > full-fit.out 2>&1`.
No test runs FullProf. `owner-input.inp` retains the original owner PCR bytes.
`full-fit.inp` records the exact run input: only the two data paths were made
local and Pcr changed from 1 to 2 to preserve the input and write `.new`.
The number of fitted variables, all parameter values and codes are retained.

FullProf Occ = site occupancy * site multiplicity / general multiplicity.
The fully occupied ferrite Fe site is 2a of I m -3 m: 2/96 = 1/48.
The fully occupied austenite Fe site is 4a of F m -3 m: 4/192 = 1/48.
Both owner Occ values are 0.02083, their five-decimal representation of 1/48;
this is not a partial physical occupancy. No occupancy or scale was restated.
Both Fe Biso parameters share code 81 in the fitting input and `.new`.
That shared parameter constraint must be preserved when verification is
activated; this archive does not activate it.

SHA256 proves both owner data files byte-identical to the existing measured
BEER data under `tests/fixtures/multiphase/beer/data/`. Both homes link to that
single copy with local `.dat` names. No additional data copy is committed.
"""
    for home, names, note in (
        (source, required, "\nThis is the fitting form, with the owner's free codes intact.\n"),
        (
            target,
            tuple(p.name for p in sorted(target.iterdir())),
            """
This is the all-fixed twin at the `.new` values. Every background, calibration,
atom, scale, profile, cell and preferred-orientation code is zero, and the
declared parameter count is zero. `capture_fullprof_beer.py` creates it without
running FullProf. The two profiles and summary are copied from the SINGLE
fitting invocation's final state; they are not claimed as a separate twin run.
""",
        ),
    ):
        hashes = '\n'.join(
            f'- `{name}` `{hashlib.sha256((home / name).read_bytes()).hexdigest()}`'
            for name in names
        )
        binary_hash = hashlib.sha256(args.executable.read_bytes()).hexdigest()
        (home / 'PROVENANCE.md').write_text(
            '# BEER duplex FullProf archive, inactive\n\n'
            + common
            + note
            + f'\nExecutable SHA256: `{binary_hash}`.\n\nFile SHA256:\n\n'
            + hashes
            + '\n'
        )


if __name__ == '__main__':
    main()

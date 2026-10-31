"""Independent source declarations for CLI fit-witness admission (ADR-0052)."""

from pathlib import Path

import gemmi

MEASURED = ('_data.intensity_meas', '_refln.intensity_meas')


def has_measured_data(source):
    for path in sorted((Path(source) / 'experiments').glob('*.edi')):
        document = gemmi.cif.read_file(str(path))
        document.check_for_duplicates()
        block = document.sole_block()
        if any(len(block.find_values(tag)) > 0 for tag in MEASURED):
            return True
    return False

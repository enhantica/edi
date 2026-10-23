"""Read the catalogue's committed FullProf IGOR exports independently."""

from pathlib import Path

import numpy as np


def read_profile(path):
    lines = Path(path).read_text(encoding='utf-8').splitlines()
    if not lines or lines[0].strip() != 'IGOR':
        raise ValueError(f'Expected an IGOR profile in {path}')
    begin, end = lines.index('BEGIN'), lines.index('END')
    values = []
    for line in lines[begin + 1 : end]:
        if not line.strip():
            continue
        # FullProf emits four 12-column fields; large intensities can touch.
        if len(line) >= 48 and not line[48:].strip():
            fields = [line[index : index + 12] for index in range(0, 48, 12)]
        else:
            fields = line.split()
        if len(fields) != 4:
            raise ValueError(f'Incomplete FullProf profile row in {path}: {line!r}')
        values.append([float(value) for value in fields])
    if not values:
        raise ValueError(f'Empty FullProf profile in {path}')
    data = np.asarray(values)
    return data[:, 0], data[:, 2]

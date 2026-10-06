"""Small ordinary projects and independent CSVs for user accident witnesses."""

import csv
import io

from tests.fixtures.scan_app.harness import SMALL, copy_project, files


def project(destination, *, fitted=False, count=3):
    destination = copy_project(SMALL, destination, iterations=1)
    existing = files(destination)
    for index in range(3, count):
        (destination / 'experiments/d20_scan' / f'zz{index:03}.dat').write_bytes(
            existing[index % 3].read_bytes()
        )
    if fitted:
        rows = []
        for index, path in enumerate(files(destination)):
            rows.append({
                'file_path': 'experiments/d20_scan/' + path.name,
                'fit_result.success': 'False',
                'fit_result.reduced_chi_square': repr(1.125 + index / 100),
                'fit_result.iterations': '1',
                'diffrn.ambient_temperature': repr(137.25 + index),
                'cosio.cell.length_a': f'{10.125 + index / 1000:.3f}',
                'cosio.cell.length_a.uncertainty': '0.000125',
            })
        output = io.StringIO(newline='')
        writer = csv.DictWriter(output, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
        (destination / 'analysis/results.csv').write_text(output.getvalue())
    return destination

"""Preserve local paired-raster measurements as evidence, never as a golden oracle."""

import argparse
import json
import re
from pathlib import Path
from statistics import median


def record(log, output):
    text = log.read_text()
    rows = [
        json.loads(line.split('LINE_QUALITY_RESULT ', 1)[1])
        for line in text.splitlines()
        if line.startswith('LINE_QUALITY_RESULT ')
    ]
    expected = {
        (dpr, mode, shape)
        for dpr in (1, 2)
        for mode in ('gpu', 'software')
        for shape in ('peak', 'needle')
    }
    if (
        len(rows) != len(expected)
        or {(row['dpr'], row['mode'], row['shape']) for row in rows} != expected
    ):
        raise ValueError('A quality measurement receipt needs all eight actual raster pairs')
    for row in rows:
        for key in ('reference', 'candidate'):
            row[key] = Path(row[key]).name
        row['pattern_frame_delivery_median_ms'] = median(row['pattern_frame_delivery_ms'])
        row['stacked_frame_delivery_median_ms'] = median(row['stacked_frame_delivery_ms'])
        print(
            row['dpr'],
            row['mode'],
            row['shape'],
            row['pattern_frame_delivery_median_ms'],
            row['stacked_frame_delivery_median_ms'],
        )
    output.write_text(
        json.dumps(
            {
                'purpose': 'Local diagnostic evidence; never read as a correctness oracle',
                'provenance': log.name,
                'native_sha256': re.findall(
                    r'Native artifact edi_app_tests sha256=([a-f0-9]+)', text
                ),
                'reported_native_build': sorted(
                    set(re.findall(r'edi_app_tests: built at (\S+)', text))
                ),
                'cost': (
                    'Eight explicit redraw requests per path; '
                    'includes event delivery and frame waits'
                ),
                'rows': rows,
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    parser.add_argument('output', type=Path)
    arguments = parser.parse_args()
    record(arguments.log, arguments.output)

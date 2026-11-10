"""Derive tooltip values with Decimal and the independent IUCr reference."""

import json
import runpy
from decimal import Decimal, localcontext
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    rounded_pair = runpy.run_path(HERE.parent / 'report_units/iucr_reference.py')['rounded_pair']
    reference = json.loads((HERE / 'fullprof.json').read_text())
    row = reference['cases']['sc-neut-cwl_tbti_basic']['input_rows'][4]
    with localcontext() as context:
        context.prec = 80
        intensity = Decimal(str(row[3]))
        sigma = Decimal(str(row[4]))
        amplitude = intensity.sqrt()
        amplitude_su = sigma / (2 * amplitude)
        values = {'f_squared': (intensity, sigma), 'f': (amplitude, amplitude_su)}
        result = {'index': 4, 'hkl': row[:3], 'rule': 'iucr_19', 'quantities': {}}
        for name, (value, uncertainty) in values.items():
            shown, shown_su = rounded_pair(str(value), str(uncertainty))
            result['quantities'][name] = {
                'raw': str(value),
                'raw_su': str(uncertainty),
                'shown': shown,
                'shown_su': shown_su,
            }
    (HERE / 'hover.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()

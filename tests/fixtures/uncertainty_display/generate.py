"""Read saved NCAF decimals and apply the independent ADR-0017 §21 reference."""

import importlib.util
import json
import re
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFERENCE = HERE.parent / 'report_units/iucr_reference.py'
SPEC = importlib.util.spec_from_file_location('iucr_reference', REFERENCE)
iucr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(iucr)
FIELDS = ('rise_alpha_0', 'rise_alpha_1', 'decay_beta_0', 'decay_beta_1')


def scientific(number):
    mantissa, power = format(number, 'E').split('E')
    return f'{mantissa}e{int(power)}'


def expectation(token, rule):
    match = re.fullmatch(r'(-?\d+(?:\.\d+)?)(?:\((\d+)\))?', token)
    if match is None:
        raise ValueError(f'Unexpected authored NCAF decimal: {token}')
    value = Decimal(match[1])
    if match[2] is None:
        plain = format(value, 'f')
        return {
            'value': float(value),
            'su': None,
            'value_text': plain,
            'su_text': '',
            'value_scientific': scientific(value),
            'su_scientific': '',
            'saved': plain,
        }
    su = Decimal(match[2]).scaleb(value.as_tuple().exponent)
    rounded_value, rounded_su = iucr.rounded_pair(value, su, rule)
    error = Decimal(str(rounded_su))
    leading = error.scaleb(-error.adjusted())
    figures = 2 if rule == 'iucr_99' or leading < 2 else 1
    quantum = Decimal(1).scaleb(error.adjusted() - figures + 1)
    shown = Decimal(str(rounded_value)).quantize(quantum)
    error = error.quantize(quantum)
    return {
        'value': float(value),
        'su': float(su),
        'value_text': format(shown, 'f'),
        'su_text': format(error, 'f'),
        'value_scientific': scientific(shown),
        'su_scientific': scientific(error),
        'saved': f'{shown:f}({int(error / quantum)})',
    }


def generate():
    result = {'definition': 'ADR-0017 §21; report_units/iucr_reference.py', 'rules': {}}
    for rule in ('iucr_19', 'iucr_99'):
        rows = []
        for file in sorted((HERE.parent / 'fit_tables/five/experiments').glob('*.edi')):
            source = file.read_text()
            for field in FIELDS:
                match = re.search(rf'^_peak\.{field}\s+(\S+)', source, re.MULTILINE)
                if match is None:
                    raise ValueError(f'Missing NCAF parameter: {file.name}: {field}')
                rows.append({
                    'block': file.stem,
                    'name': field,
                    'token': match[1],
                    **expectation(match[1], rule),
                })
        result['rules'][rule] = rows
    return result


if __name__ == '__main__':
    (HERE / 'expected.json').write_text(json.dumps(generate(), indent=2) + '\n')

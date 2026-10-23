"Independent decimal reference for the written precision in the uncertainty ADR."

import re
from decimal import Decimal

from tests.fixtures.report_units.iucr_reference import rounded_pair, rounded_record, rounded_token

NUMBER = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'
VALUE_SU = re.compile(rb'(' + NUMBER.encode() + rb')\((' + NUMBER.encode() + rb')?\)')
RULE = b'_su_format.rule iucr_19\n'


def spelling(value, uncertainty):
    """Render the committed independent reference from an unrounded numeric pair."""
    value = Decimal(str(float(value)))
    uncertainty = Decimal(str(float(uncertainty)))
    if not uncertainty:
        return format(value.normalize(), 'f') + '(0)'
    value = format(value, 'f')
    su = format(uncertainty, 'f')
    if '.' not in su:
        su += '.'
    match = VALUE_SU.fullmatch((value + '(' + su + ')').encode())
    assert match, 'The independent spelling reference requires a complete finite numeric pair'
    return rounded_token(match).decode()


def decode(token):
    """Decode a CIF integer bracket or the older decimal bracket independently."""
    match = VALUE_SU.fullmatch(token.encode() if isinstance(token, str) else token)
    assert match, 'The uncertainty reference requires one complete value and bracket token'
    value, su = (part.decode() if part is not None else '' for part in match.groups())
    if not su:
        return float(value), None
    uncertainty = Decimal(su)
    if '.' not in su and 'e' not in su.lower():
        uncertainty = uncertainty.scaleb(Decimal(value).as_tuple().exponent)
    return float(value), float(uncertainty)


def with_default_rule(record):
    """Insert the absent default after the existing metadata, preserving all other bytes."""
    assert not re.search(rb'(?m)^_su_format\.', record), (
        'The historical record must have no uncertainty setting before adding its exact default'
    )
    lines = record.splitlines(keepends=True)
    positions = [index for index, line in enumerate(lines) if line.startswith(b'_metadata.')]
    assert positions, 'The historical project record carries the existing owned metadata block'
    lines.insert(positions[-1] + 1, RULE)
    return b''.join(lines)


def historical_spelling(name, data):
    """Change only numeric bracket tokens in model files and the absent project default."""
    if name == 'project.edi':
        return with_default_rule(data)
    if not name.startswith(('structures/', 'experiments/')):
        return data

    return rounded_record(data)


def saved_pair(value, uncertainty):
    """Predict the reloaded pair from the original numbers using the shared reference."""
    return rounded_pair(value, uncertainty)

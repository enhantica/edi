"""Extract a frozen upstream tutorial as data; never invoke pickle objects.

This fixture tool interprets only the tutorial's data opcodes. GLOBAL, REDUCE
and BUILD produce inert records. No named function, class or module is loaded.
"""

from __future__ import annotations

import hashlib
import json
import pickletools
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_SHA256 = '05f78024156b62d4ed3483e3824cf37af144d5b39fa830269d595137cb91e79c'
MARK = object()


def read_record(stream):  # noqa: PLR0912, PLR0915 - explicit inert data-opcode dispatch
    stack = []
    memo = {}

    def marked():
        index = len(stack) - 1 - stack[::-1].index(MARK)
        items = stack[index + 1 :]
        del stack[index:]
        return items

    for opcode, value, _ in pickletools.genops(stream):
        name = opcode.name
        if name in {'PROTO', 'FRAME'}:
            continue
        if name == 'MARK':
            stack.append(MARK)
        elif name == 'NONE':
            stack.append(None)
        elif name in {'NEWTRUE', 'NEWFALSE'}:
            stack.append(name == 'NEWTRUE')
        elif name in {
            'BININT',
            'BININT1',
            'BININT2',
            'LONG1',
            'LONG4',
            'BINFLOAT',
            'BINUNICODE',
            'SHORT_BINUNICODE',
            'BINBYTES',
            'SHORT_BINBYTES',
        }:
            stack.append(value)
        elif name == 'EMPTY_LIST':
            stack.append([])
        elif name == 'EMPTY_DICT':
            stack.append({})
        elif name == 'EMPTY_TUPLE':
            stack.append(())
        elif name in {'BINPUT', 'LONG_BINPUT'}:
            memo[value] = stack[-1]
        elif name == 'MEMOIZE':
            memo[len(memo)] = stack[-1]
        elif name in {'BINGET', 'LONG_BINGET'}:
            stack.append(memo[value])
        elif name == 'APPEND':
            item = stack.pop()
            stack[-1].append(item)
        elif name == 'APPENDS':
            items = marked()
            stack[-1].extend(items)
        elif name == 'SETITEM':
            val, key = stack.pop(), stack.pop()
            stack[-1][key] = val
        elif name == 'SETITEMS':
            items = marked()
            stack[-1].update(zip(items[::2], items[1::2], strict=True))
        elif name == 'TUPLE':
            stack.append(tuple(marked()))
        elif name in {'TUPLE1', 'TUPLE2', 'TUPLE3'}:
            count = int(name[-1])
            values = tuple(stack[-count:])
            del stack[-count:]
            stack.append(values)
        elif name == 'GLOBAL':
            stack.append({'global': value})
        elif name == 'REDUCE':
            args, function = stack.pop(), stack.pop()
            stack.append({'call': function, 'args': args})
        elif name == 'BUILD':
            state = stack.pop()
            stack[-1]['state'] = state
        elif name == 'STOP':
            if len(stack) != 1:
                raise ValueError('tutorial record has an invalid stack')
            return stack[0]
        else:
            raise ValueError(f'unsupported data opcode: {name}')
    raise ValueError('truncated tutorial record')


def numeric(value):  # noqa: PLR0911 - separate scalar, array and container encodings
    if isinstance(value, dict) and value.get('call', {}).get('global') == '_codecs encode':
        text, encoding = value['args']
        if encoding != 'latin1':
            raise ValueError('only the frozen tutorial byte encoding is supported')
        return text.encode('latin1')
    if isinstance(value, dict) and 'state' in value:
        state = value['state']
        if value.get('call', {}).get('global') == 'numpy dtype':
            return value['args'][0]
        if len(state) in {5, 7} and isinstance(state[1], tuple):
            shape, dtype, raw = state[1], numeric(state[2]), numeric(state[4])
            if dtype not in {'f8', 'f4', 'i8', 'i4'}:
                raise ValueError(f'unsupported tutorial numeric dtype: {dtype}')
            endian = state[2]['state'][1]
            if endian not in {'<', '>'}:
                raise ValueError('tutorial numeric endian must be explicit')
            code = {'f8': 'd', 'f4': 'f', 'i8': 'q', 'i4': 'i'}[dtype]
            values = list(struct.unpack(endian + code * (len(raw) // int(dtype[1:])), raw))
            if len(shape) == 1:
                return values
            if len(shape) == 2:
                return [values[i : i + shape[1]] for i in range(0, len(values), shape[1])]
            raise ValueError('tutorial array rank is unsupported')
    if (
        isinstance(value, dict)
        and value.get('call', {}).get('global') == 'numpy.core.multiarray scalar'
    ):
        dtype, raw = value['args']
        dtype = numeric(dtype)
        return struct.unpack(
            '<' + {'f8': 'd', 'f4': 'f', 'i8': 'q', 'i4': 'i'}[dtype], numeric(raw)
        )[0]
    if isinstance(value, dict):
        return {str(key): numeric(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [numeric(item) for item in value]
    return value


def main():
    source = ROOT / 'reference/NXPbSO4.gpx'
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError('this extractor accepts only the frozen upstream tutorial')
    records = []
    with source.open('rb') as stream:
        while stream.peek(1):
            records.append(numeric(read_record(stream)))
    phase = records[-1][1][1]
    neutron = dict(records[6])
    name = records[6][0][0]
    header, arrays = neutron[name][:2]
    evidence = {
        'schema': 'independent-gsas-tutorial/1',
        'source_sha256': SOURCE_SHA256,
        'source_version': records[1][0][1]['LastSavedUsing'],
        'phase': {
            'name': phase['General']['Name'],
            'type': phase['General']['Type'],
            'cell': phase['General']['Cell'],
            'space_group': phase['General']['SGData']['SpGrp'],
            'atoms': phase['Atoms'],
            'histogram_parameters': phase['Histograms'][name],
        },
        'histogram': {
            'name': name,
            'n_observations': header['Nobs'],
            'limits': neutron['Limits'],
            'background': neutron['Background'],
            'instrument': neutron['Instrument Parameters'],
            'sample': neutron['Sample Parameters'],
        },
        'upstream_joint_fit': records[2][0][1]['Rvals'],
        'array_columns': [
            'two_theta',
            'observed',
            'weight',
            'calculated',
            'background',
            'difference',
        ],
        'pattern': arrays,
        'status': 'unsupported: histogram strain and sample displacement require mappings',
    }
    (ROOT / 'reference/gsas-tutorial-data.json').write_text(
        json.dumps(evidence, indent=2, allow_nan=False) + '\n'
    )


if __name__ == '__main__':
    main()

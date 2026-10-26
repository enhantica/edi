"""Native model readback shared by display and CIF-refusal gates."""

from pathlib import Path

import gemmi

ROOT = Path(__file__).resolve().parents[2]
API = 'edi'


def key(tag):
    return tag.lower().replace('.', '_', 1)


def cells(text):
    result = {}
    for block in gemmi.cif.read_string(text):
        for item in block:
            if item.pair is not None:
                result[key(item.pair[0])] = [gemmi.cif.as_string(item.pair[1])]
            elif item.loop is not None:
                for index, tag in enumerate(item.loop.tags):
                    result[key(tag)] = [
                        gemmi.cif.as_string(v)
                        for v in item.loop.values[index :: len(item.loop.tags)]
                    ]
    return result

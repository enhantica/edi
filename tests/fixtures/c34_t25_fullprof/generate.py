"""Freeze the independent cctbx Wyckoff oracle, never FullProf multiplicities.

Run with cctbx-base=2026.8 and Python 3.12 ('s oracle).
The matrix entries are general-position operations; their orbit at each actual
site determines its multiplicity, checked against the Wyckoff table.
"""

import json
from pathlib import Path

from cctbx import sgtbx

SYMBOLS = [
    'P m -3 m',
    'P n m a',
    'I a -3',
    'P m m a',
    'F m -3 m',
    'F d -3 m:1',
    'F d -3 m:2',
    'I 21 3',
    'P b n m',
    'R -3 c:H',
]
result = {'source': 'cctbx-base 2026.8, cctbx.sgtbx.wyckoff_table', 'groups': {}}
for symbol in SYMBOLS:
    info = sgtbx.space_group_info(symbol)
    table = sgtbx.wyckoff_table(info.type())
    result['groups'][symbol.replace(' ', '')] = {
        'general': info.group().order_z(),
        'operations': [
            {'r': list(op.r().as_double()), 't': list(op.t().as_double())} for op in info.group()
        ],
        'wyckoff': [
            {
                'letter': table.position(i).letter(),
                'multiplicity': table.position(i).multiplicity(),
                'special_op': str(table.position(i).special_op()),
            }
            for i in range(table.size())
        ],
    }
Path(__file__).with_name('wyckoff.json').write_text(json.dumps(result, indent=2) + '\n')

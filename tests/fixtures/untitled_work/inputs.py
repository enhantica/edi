"""Authored replacement observations and unchanged fit-policy declarations."""

from pathlib import Path

from tests.fixtures.fittability.inputs import materialize


def generate(root):
    root = Path(root)
    for name, single in [('powder', False), ('single', True)]:
        project = materialize(root / name, single=single)
        if not single:
            bank = project / 'experiments/bank.edi'
            bank.write_text(bank.read_text().replace('a 20 3\n', 'a 20 3()\n'))
    (root / 'replacement.xye').write_text('31 23 1\n39 29 1\n47 19 1\n55 31 1\n63 17 1\n71 37 1\n')
    (root / 'replacement.dat').write_text('1 1 1 23 1\n2 1 3 29 1\n4 1 3 19 1\n')
    return root

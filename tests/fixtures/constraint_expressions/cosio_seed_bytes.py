"""Reverse only the ADR-0078 CoSiO model edits for the retained seed-byte witness."""

import re

DECLARATION = """loop_
_alias.id
_alias.parameter_unique_name
biso_Co1 cosio.atom_site.Co1.adp_iso
biso_Co2 cosio.atom_site.Co2.adp_iso

loop_
_constraint.id
_constraint.expression
biso_Co2 "biso_Co2 = biso_Co1"

"""


def legacy_seed(name, contents):
    text = contents.decode()
    if name == 'analysis/analysis.edi':
        if text.count(DECLARATION) != 1:
            raise ValueError('the seed requires exactly the declared Co2 = Co1 relation')
        return text.replace(DECLARATION, '', 1).encode()
    if name != 'structures/cosio.edi':
        return contents
    # Co1 gains the leader flag; Co2 loses the dependent flag. Reverse both,
    # without changing values, column order, whitespace or any other site.
    for site, current, old in (('Co1', '0.01()', '0.01'), ('Co2', '0.01', '0.01()')):
        rows = list(re.finditer(rf'(?m)^{site}[^\n]*$', text))
        if len(rows) != 1:
            raise ValueError('the seed requires exactly one row for each Co Biso parameter')
        headers = []
        for line in text[: rows[0].start()].splitlines():
            if line == 'loop_':
                headers = []
            elif line.startswith('_atom_site.'):
                headers.append(line)
        index = headers.index('_atom_site.adp_iso')
        tokens = list(re.finditer(r'\S+', rows[0][0]))
        token = tokens[index]
        if token[0] != current:
            raise ValueError('the seed changes only the original 0.01 Co Biso free flags')
        absolute = rows[0].start() + token.start()
        text = text[:absolute] + old + text[absolute + len(token[0]) :]
    return text.encode()

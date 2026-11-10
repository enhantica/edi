""": admit only the new canonical calculator block in frozen save bytes."""

import re

from tests.fixtures.cwl_family.historical import original_tokens


def without_calculator(name, saved):
    if not (name.startswith('experiments/') and name.endswith('.edi')):
        return saved
    declaration = b'_calculator.type crysta\n\n'
    assert saved.count(declaration) == 1, (
        ' every saved experiment adds exactly one canonical calculator block'
    )
    assert len(re.findall(rb'(?m)^_calculator\.', saved)) == 1, (
        ' no extra or unsupported calculator declaration may escape the byte oracle'
    )
    return original_tokens(saved.replace(declaration, b'', 1))
